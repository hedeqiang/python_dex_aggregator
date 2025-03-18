from typing import Dict, Optional, List, Tuple, Any
from web3 import Web3
from eth_typing import ChecksumAddress
from ...core.exceptions import ProviderError, ValidationError
from ...utils.logger import get_logger
from ...config.contracts import UNISWAP_V3_CONTRACTS
import re
import json

logger = get_logger(__name__)

class UniswapClient:
    """Uniswap API 客户端"""
    
    # Uniswap V3 支持的费率档位
    FEE_TIERS = [100, 500, 3000, 10000]  # 0.01%, 0.05%, 0.3%, 1%
    
    def __init__(self, web3: Web3, chain_id: str):
        if chain_id not in UNISWAP_V3_CONTRACTS:
            raise ValueError(f"Unsupported chain ID for Uniswap V3: {chain_id}")
            
        self.web3 = web3
        self.chain_id = chain_id
        self.contracts = UNISWAP_V3_CONTRACTS[chain_id]
        
        self.factory_contract = self._get_factory_contract()
        self.router_contract = self._get_router_contract()
        self.quoter_contract = self._get_quoter_contract()

    def _get_factory_contract(self):
        """获取 Factory 合约实例"""
        from ...utils.abi_helper import ABIHelper
        abi = ABIHelper.get_instance().get_abi('uniswap/v3/factory')
        return self.web3.eth.contract(
            address=self.web3.to_checksum_address(self.contracts["factory"]),
            abi=abi
        )

    def _get_router_contract(self):
        """获取 Router 合约实例"""
        from ...utils.abi_helper import ABIHelper
        if self.chain_id == "1":
            abi = ABIHelper.get_instance().get_abi('uniswap/v3/router02_eth')
        else:
            abi = ABIHelper.get_instance().get_abi('uniswap/v3/router02')
        return self.web3.eth.contract(
            address=self.web3.to_checksum_address(self.contracts["router"]),
            abi=abi
        )

    def _get_quoter_contract(self):
        """获取 Quoter 合约实例"""
        from ...utils.abi_helper import ABIHelper
        abi = ABIHelper.get_instance().get_abi('uniswap/v3/quoter')
        return self.web3.eth.contract(
            address=self.web3.to_checksum_address(self.contracts["quoter"]),
            abi=abi
        )

    @property
    def router_address(self) -> str:
        """获取 Router 地址"""
        return self.contracts["router"]
    
    def validate_address(self, address: str) -> ChecksumAddress:
        """验证并返回 checksum 格式的地址"""
        try:
            if not address or not re.match(r'^0x[a-fA-F0-9]{40}$', address):
                raise ValidationError(f"Invalid Ethereum address format: {address}")
            return self.web3.to_checksum_address(address)
        except Exception as e:
            logger.error(f"Address validation failed for {address}: {str(e)}")
            raise ValidationError(f"Invalid address {address}: {str(e)}")

    def get_pool(self, token_a: str, token_b: str, fee: int = 3000) -> str:
        """获取交易对池地址"""
        try:
            token_a_cs = self.validate_address(token_a)
            token_b_cs = self.validate_address(token_b)
            
            if fee not in self.FEE_TIERS:
                raise ValidationError(f"Invalid fee tier {fee}. Supported tiers: {self.FEE_TIERS}")
                
            pool_address = self.factory_contract.functions.getPool(
                token_a_cs,
                token_b_cs,
                fee
            ).call()
            
            if pool_address == "0x0000000000000000000000000000000000000000":
                logger.warning(f"No pool found for {token_a}/{token_b} with fee {fee}")
                
            return pool_address
        except ValidationError as e:
            # Re-raise validation errors
            raise e
        except Exception as e:
            logger.error(f"Failed to get pool for {token_a}/{token_b}: {str(e)}")
            raise ProviderError(f"Failed to get Uniswap pool: {str(e)}")
    
    def find_best_pool(self, token_a: str, token_b: str) -> Tuple[str, int]:
        """在所有费率档位中寻找流动性最好的池子"""
        best_pool = None
        best_fee = None
        
        for fee in self.FEE_TIERS:
            pool_address = self.get_pool(token_a, token_b, fee)
            if pool_address != "0x0000000000000000000000000000000000000000":
                # 这里可以添加进一步的流动性检查，例如获取池子的 liquidity 或 TVL
                # 现在我们简单地使用第一个找到的非零地址池子
                best_pool = pool_address
                best_fee = fee
                break
                
        if not best_pool:
            raise ProviderError(f"No valid pool found for {token_a}/{token_b} across any fee tier")
            
        return best_pool, best_fee

    def get_quote_for_path(self, token_in: str, token_out: str, amount_in: int, fee: int) -> Dict:
        """获取单一路径的报价"""
        try:
            token_in_cs = self.validate_address(token_in)
            token_out_cs = self.validate_address(token_out)
            
            quote_params = {
                'tokenIn': token_in_cs,
                'tokenOut': token_out_cs,
                'fee': fee,
                'amountIn': amount_in,
                'sqrtPriceLimitX96': 0
            }
            
            # 使用 Quoter 合约获取报价
            quote_result = self.quoter_contract.functions.quoteExactInputSingle(quote_params).call()
            amount_out, _, _, gas_estimate = quote_result

            return {
                "pathId": f"{token_in}-{fee}-{token_out}",
                "fee": fee,
                "toAmount": str(amount_out),
                "estimatedGas": str(gas_estimate)
            }
        except Exception as e:
            logger.warning(f"Failed to get quote for path {token_in}/{token_out} with fee {fee}: {str(e)}")
            return {
                "pathId": f"{token_in}-{fee}-{token_out}",
                "fee": fee,
                "toAmount": "0",
                "estimatedGas": "0",
                "error": str(e)
            }

    def get_quote(self, params: Dict) -> Dict:
        """获取多路径报价信息，并返回最优路径"""
        try:
            token_in = params["fromTokenAddress"]
            token_out = params["toTokenAddress"]
            amount_in = int(params["amount"])
            
            # 验证地址
            self.validate_address(token_in)
            self.validate_address(token_out)
            
            # 如果指定了费率，只查询该费率的路径
            if "fee" in params:
                fee = int(params["fee"])
                if fee not in self.FEE_TIERS:
                    raise ValidationError(f"Invalid fee tier {fee}. Supported tiers: {self.FEE_TIERS}")
                paths = [self.get_quote_for_path(token_in, token_out, amount_in, fee)]
            else:
                # 查询所有费率的路径
                paths = []
                for fee in self.FEE_TIERS:
                    path_quote = self.get_quote_for_path(token_in, token_out, amount_in, fee)
                    if path_quote["toAmount"] != "0":
                        paths.append(path_quote)
            
            if not paths or all(p["toAmount"] == "0" for p in paths):
                raise ProviderError(f"No valid route found for {token_in} to {token_out}")
            
            # 选择产出最高的路径
            best_path = max(paths, key=lambda x: int(x["toAmount"]))
            
            return {
                "fromTokenAddress": token_in,
                "toTokenAddress": token_out,
                "fromAmount": params["amount"],
                "toAmount": best_path["toAmount"],
                "estimatedGas": best_path["estimatedGas"],
                "fee": best_path["fee"],
                "pathId": best_path["pathId"],
                "allPaths": paths  # 返回所有可能的路径，以供参考
            }
        except ValidationError as e:
            # Re-raise validation errors
            raise e
        except Exception as e:
            logger.error(f"Failed to get quote: {str(e)}")
            raise ProviderError(f"Uniswap quote failed: {str(e)}")

    def get_swap_data(self, params: Dict) -> Dict:
        """获取兑换数据"""
        try:
            # 记录输入参数
            logger.info(f"Building swap transaction with parameters: {json.dumps(params)}")
            
            # 参数验证
            required_params = ["fromTokenAddress", "toTokenAddress", "amount", "userWalletAddress"]
            for param in required_params:
                if param not in params:
                    raise ValidationError(f"Missing required parameter: {param}")
            
            token_in = self.validate_address(params["fromTokenAddress"])
            token_out = self.validate_address(params["toTokenAddress"])
            amount_in = int(params["amount"])
            recipient = self.validate_address(
                params.get("recipient", params["userWalletAddress"])
            )
            user_address = self.validate_address(params["userWalletAddress"])
            
            # 使用支持的费率或查找最优费率
            fee = int(params.get("fee", 3000))
            if fee not in self.FEE_TIERS:
                _, fee = self.find_best_pool(token_in, token_out)
                logger.info(f"Using optimal fee tier {fee} for {token_in}/{token_out}")
                
            slippage = float(params.get("slippage", "0.005"))
            if not 0 <= slippage <= 1:
                raise ValidationError(f"Slippage must be between 0 and 1, got {slippage}")

            # 获取报价
            quote_params = {
                'tokenIn': token_in,
                'tokenOut': token_out,
                'fee': fee,
                'amountIn': amount_in,
                'sqrtPriceLimitX96': 0
            }
            logger.info(f"Getting quote with parameters: {json.dumps(quote_params)}")
            
            quote_amount = self.quoter_contract.functions.quoteExactInputSingle(quote_params).call()
            min_amount_out = int(quote_amount[0] * (1 - slippage))  # 使用第一个返回值作为 amountOut
            logger.info(f"Quote result: amountOut={quote_amount[0]}, minAmountOut={min_amount_out}")

            # 构建交易数据
            deadline = self.web3.eth.get_block('latest').timestamp + 1800  # 30分钟后过期
            
            swap_params = {
                'tokenIn': token_in,
                'tokenOut': token_out,
                'fee': fee,
                'recipient': recipient,
                'deadline': deadline,
                'amountIn': amount_in,
                'amountOutMinimum': min_amount_out,
                'sqrtPriceLimitX96': 0
            }
            logger.info(f"Swap parameters: {json.dumps(swap_params)}")

            # 构建基础交易参数
            weth = self.router_contract.functions.WETH9().call()
            is_native_token = token_in.lower() == weth.lower()
            
            # 获取 nonce
            nonce = self.web3.eth.get_transaction_count(user_address)
            logger.info(f"Current nonce for {user_address}: {nonce}")
            
            # 使用 EIP-1559 交易类型 (如果网络支持)
            try:
                # 获取链上当前 gas 费用信息
                base_fee = self.web3.eth.get_block('latest').baseFeePerGas
                priority_fee = self.web3.eth.max_priority_fee
                
                # 使用 EIP-1559 交易
                tx_params = {
                    'from': user_address,
                    'value': amount_in if is_native_token else 0,
                    'nonce': nonce,
                    'chainId': int(self.chain_id),
                    'maxFeePerGas': base_fee * 2 + priority_fee,  # 基础费用的2倍 + 优先费
                    'maxPriorityFeePerGas': priority_fee,
                    'type': 2  # EIP-1559 交易类型
                }
                use_eip1559 = True
                logger.info(f"Using EIP-1559 transaction with parameters: {json.dumps(tx_params)}")
            except Exception as e:
                logger.warning(f"EIP-1559 not supported or error: {str(e)}. Using legacy transaction.")
                # 回退到传统交易类型
                tx_params = {
                    'from': user_address,
                    'value': amount_in if is_native_token else 0,
                    'nonce': nonce,
                    'chainId': int(self.chain_id),
                    'gasPrice': self.web3.eth.gas_price,
                    'type': 0  # 传统交易类型
                }
                use_eip1559 = False
                logger.info(f"Using legacy transaction with parameters: {json.dumps(tx_params)}")

            # 获取交易数据
            tx = self.router_contract.functions.exactInputSingle(
                swap_params
            ).build_transaction(tx_params)
            logger.info(f"Built transaction data: {tx['data'][:100]}...")  # 只记录数据的前100个字符

            # 估算 gas
            try:
                gas_estimate = self.router_contract.functions.exactInputSingle(
                    swap_params
                ).estimate_gas({
                    'from': user_address,
                    'value': amount_in if is_native_token else 0,
                    'type': tx_params['type']
                })
                gas = int(gas_estimate * 1.2)  # 增加 20% gas 余量
                logger.info(f"Estimated gas: {gas_estimate}, With buffer: {gas}")
            except Exception as e:
                logger.warning(f"Failed to estimate gas, using default: {str(e)}")
                gas = 300000  # 使用默认值
                logger.info(f"Using default gas limit: {gas}")

            # 构建最终交易数据
            result = {
                "from": params["userWalletAddress"],
                "to": self.router_address,
                "data": tx["data"],
                "value": amount_in if is_native_token else 0,
                "gas": gas,
                "chainId": int(self.chain_id),
                "type": tx_params['type'],
                "nonce": nonce
            }
            
            # 根据交易类型设置 gas 相关字段
            if use_eip1559:
                result["maxFeePerGas"] = tx_params["maxFeePerGas"]
                result["maxPriorityFeePerGas"] = tx_params["maxPriorityFeePerGas"]
            else:
                result["gasPrice"] = tx_params["gasPrice"]
                
            # 记录最终交易数据（排除 data 字段，因为它太长）
            log_result = result.copy()
            log_result["data"] = f"{result['data'][:100]}..."
            logger.info(f"Final transaction data: {json.dumps(log_result)}")
                
            return result

        except ValidationError as e:
            # Re-raise validation errors
            logger.error(f"Validation error in get_swap_data: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"Failed to get swap data: {str(e)}")
            raise ProviderError(f"Uniswap swap data generation failed: {str(e)}") 