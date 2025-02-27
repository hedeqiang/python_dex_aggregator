from typing import Dict, Optional
from web3 import Web3
from ...core.exceptions import ProviderError
from ...utils.logger import get_logger
from ...config.contracts import UNISWAP_V3_CONTRACTS

logger = get_logger(__name__)

class UniswapClient:
    """Uniswap API 客户端"""
    
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

    def get_pool(self, token_a: str, token_b: str, fee: int = 3000) -> str:
        """获取交易对池地址"""
        try:
            pool_address = self.factory_contract.functions.getPool(
                self.web3.to_checksum_address(token_a),
                self.web3.to_checksum_address(token_b),
                fee
            ).call()
            return pool_address
        except Exception as e:
            logger.error(f"Failed to get pool for {token_a}/{token_b}: {str(e)}")
            raise ProviderError(f"Failed to get Uniswap pool: {str(e)}")

    def get_quote(self, params: Dict) -> Dict:
        """获取报价信息"""
        try:
            token_in = self.web3.to_checksum_address(params["fromTokenAddress"])
            token_out = self.web3.to_checksum_address(params["toTokenAddress"])
            amount_in = int(params["amount"])
            fee = params.get("fee", 3000)

            quote_params = {
                'tokenIn': token_in,
                'tokenOut': token_out,
                'fee': fee,
                'amountIn': amount_in,
                'sqrtPriceLimitX96': 0
            }
            
            # 使用 Quoter 合约获取报价
            quote_result = self.quoter_contract.functions.quoteExactInputSingle(quote_params).call()
            amount_out, _, _, gas_estimate = quote_result

            return {
                "fromTokenAddress": token_in,
                "toTokenAddress": token_out,
                "fromAmount": params["amount"],
                "toAmount": str(amount_out),
                "estimatedGas": str(gas_estimate)
            }
        except Exception as e:
            logger.error(f"Failed to get quote: {str(e)}")
            raise ProviderError(f"Uniswap quote failed: {str(e)}")

    def get_swap_data(self, params: Dict) -> Dict:
        """获取兑换数据"""
        try:
            token_in = self.web3.to_checksum_address(params["fromTokenAddress"])
            token_out = self.web3.to_checksum_address(params["toTokenAddress"])
            amount_in = int(params["amount"])
            recipient = self.web3.to_checksum_address(
                params.get("recipient", params["userWalletAddress"])
            )
            fee = params.get("fee", 3000)
            slippage = float(params.get("slippage", "0.005"))

            # 获取报价
            quote_params = {
                'tokenIn': token_in,
                'tokenOut': token_out,
                'fee': fee,
                'amountIn': amount_in,
                'sqrtPriceLimitX96': 0
            }
            quote_amount = self.quoter_contract.functions.quoteExactInputSingle(quote_params).call()
            min_amount_out = int(quote_amount[0] * (1 - slippage))  # 使用第一个返回值作为 amountOut

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

            # 构建交易
            tx_params = {
                'from': self.web3.to_checksum_address(params["userWalletAddress"]),
                'value': amount_in if token_in == self.router_contract.functions.WETH9().call() else 0,
                'nonce': self.web3.eth.get_transaction_count(params["userWalletAddress"]),
                'gas': 300000,  # TODO: 优化 gas
                'gasPrice': self.web3.eth.gas_price
            }

            # 获取交易数据
            tx = self.router_contract.functions.exactInputSingle(
                swap_params
            ).build_transaction(tx_params)

            return tx

        except Exception as e:
            logger.error(f"Failed to get swap data: {str(e)}")
            raise ProviderError(f"Uniswap swap data generation failed: {str(e)}") 