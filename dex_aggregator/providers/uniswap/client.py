from typing import Dict, Optional, List, Tuple, Any, Set
from web3 import Web3
from eth_typing import ChecksumAddress
from ...core.exceptions import ProviderError, ValidationError
from ...utils.logger import get_logger
from ...config.contracts import UNISWAP_V3_CONTRACTS, COMMON_BASES
import re
import json
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = get_logger(__name__)

class UniswapClient:
    """Uniswap API 客户端"""
    
    # Uniswap V3 支持的费率档位
    FEE_TIERS = [100, 500, 3000, 10000]  # 0.01%, 0.05%, 0.3%, 1%
    
    # 最大跳数限制
    MAX_HOPS = 3
    
    # 缓存过期时间（秒）
    CACHE_TTL = 300  # 5分钟
    
    def __init__(self, web3: Web3, chain_id: str):
        if chain_id not in UNISWAP_V3_CONTRACTS:
            raise ValueError(f"Unsupported chain ID for Uniswap V3: {chain_id}")
            
        self.web3 = web3
        self.chain_id = chain_id
        self.contracts = UNISWAP_V3_CONTRACTS[chain_id]
        
        # 初始化缓存
        self._pool_cache = {}  # 池子地址缓存
        self._pool_cache_timestamp = {}  # 缓存时间戳
        self._path_cache = {}  # 路径缓存
        self._path_cache_timestamp = {}  # 路径缓存时间戳
        
        self.factory_contract = self._get_factory_contract()
        self.router_contract = self._get_router_contract()
        self.quoter_contract = self._get_quoter_contract()

    def _get_cached_pool(self, token_a: str, token_b: str, fee: int) -> Optional[str]:
        """从缓存中获取池子地址"""
        cache_key = f"{token_a.lower()}-{token_b.lower()}-{fee}"
        current_time = time.time()
        
        # 检查缓存是否存在且未过期
        if cache_key in self._pool_cache:
            if current_time - self._pool_cache_timestamp[cache_key] < self.CACHE_TTL:
                return self._pool_cache[cache_key]
        
        return None

    def _set_pool_cache(self, token_a: str, token_b: str, fee: int, pool_address: str):
        """设置池子地址缓存"""
        cache_key = f"{token_a.lower()}-{token_b.lower()}-{fee}"
        self._pool_cache[cache_key] = pool_address
        self._pool_cache_timestamp[cache_key] = time.time()

    def _get_cached_paths(self, token_in: str, token_out: str, max_hops: int) -> Optional[List[Dict]]:
        """从缓存中获取路径"""
        cache_key = f"{token_in.lower()}-{token_out.lower()}-{max_hops}"
        current_time = time.time()
        
        if cache_key in self._path_cache:
            if current_time - self._path_cache_timestamp[cache_key] < self.CACHE_TTL:
                return self._path_cache[cache_key]
        
        return None

    def _set_path_cache(self, token_in: str, token_out: str, max_hops: int, paths: List[Dict]):
        """设置路径缓存"""
        cache_key = f"{token_in.lower()}-{token_out.lower()}-{max_hops}"
        self._path_cache[cache_key] = paths
        self._path_cache_timestamp[cache_key] = time.time()

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

    @lru_cache(maxsize=1000)
    def get_pool(self, token_a: str, token_b: str, fee: int = 3000) -> str:
        """获取交易对池地址（带缓存）"""
        try:
            # 检查缓存
            cached_pool = self._get_cached_pool(token_a, token_b, fee)
            if cached_pool is not None:
                return cached_pool

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
            else:
                # 设置缓存
                self._set_pool_cache(token_a, token_b, fee, pool_address)
                
            return pool_address
        except ValidationError as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to get pool for {token_a}/{token_b}: {str(e)}")
            raise ProviderError(f"Failed to get Uniswap pool: {str(e)}")

    def _parallel_get_pool(self, token_a: str, token_b: str, fee: int) -> Tuple[int, str]:
        """并行获取池子地址"""
        return fee, self.get_pool(token_a, token_b, fee)

    def find_best_pool(self, token_a: str, token_b: str) -> Tuple[str, int]:
        """并行在所有费率档位中寻找流动性最好的池子"""
        with ThreadPoolExecutor(max_workers=len(self.FEE_TIERS)) as executor:
            future_to_fee = {
                executor.submit(self._parallel_get_pool, token_a, token_b, fee): fee
                for fee in self.FEE_TIERS
            }
            
            best_pool = None
            best_fee = None
            
            for future in as_completed(future_to_fee):
                fee, pool_address = future.result()
                if pool_address != "0x0000000000000000000000000000000000000000":
                    best_pool = pool_address
                    best_fee = fee
                    break
                    
            if not best_pool:
                raise ProviderError(f"No valid pool found for {token_a}/{token_b} across any fee tier")
                
            return best_pool, best_fee

    def encode_path(self, tokens: List[str], fees: List[int]) -> bytes:
        """
        将路径编码为Uniswap V3路径格式
        例如：[tokenA, tokenB, tokenC] 和 [fee1, fee2] 编码为 tokenA + fee1 + tokenB + fee2 + tokenC
        """
        if len(tokens) != len(fees) + 1:
            raise ValidationError(f"Tokens length ({len(tokens)}) should be fees length ({len(fees)}) + 1")
            
        path = b''
        for i in range(len(tokens) - 1):
            token_in = self.validate_address(tokens[i])
            fee = fees[i]
            
            # 添加当前token (20字节) 和 fee (3字节)
            path += Web3.to_bytes(hexstr=token_in[2:]).rjust(20, b'\0')
            path += fee.to_bytes(3, 'big')
            
        # 添加最后一个token
        last_token = self.validate_address(tokens[-1])
        path += Web3.to_bytes(hexstr=last_token[2:]).rjust(20, b'\0')
        
        return path

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
                "path": [token_in, token_out],
                "fees": [fee],
                "toAmount": str(amount_out),
                "estimatedGas": str(gas_estimate),
                "type": "single"
            }
        except Exception as e:
            logger.warning(f"Failed to get quote for path {token_in}/{token_out} with fee {fee}: {str(e)}")
            return {
                "pathId": f"{token_in}-{fee}-{token_out}",
                "path": [token_in, token_out],
                "fees": [fee],
                "toAmount": "0",
                "estimatedGas": "0",
                "error": str(e),
                "type": "single"
            }

    def get_quote_for_multi_path(self, path: List[str], fees: List[int], amount_in: int) -> Dict:
        """获取多跳路径的报价"""
        try:
            # 验证所有地址
            validated_path = [self.validate_address(token) for token in path]
            
            # 验证所有费率
            for fee in fees:
                if fee not in self.FEE_TIERS:
                    raise ValidationError(f"Invalid fee tier {fee}. Supported tiers: {self.FEE_TIERS}")
                    
            # 编码路径
            encoded_path = self.encode_path(validated_path, fees)
            
            # 获取报价
            try:
                quote_result = self.quoter_contract.functions.quoteExactInput(
                    encoded_path,
                    amount_in
                ).call()
                
                amount_out = quote_result[0]  # 第一个返回值是输出金额
                gas_estimate = 300000  # 多跳路径的 gas 消耗通常较高，使用固定值
                
                path_id = "-".join([f"{path[i]}-{fees[i]}" for i in range(len(fees))] + [path[-1]])
                
                return {
                    "pathId": path_id,
                    "path": path,
                    "fees": fees,
                    "toAmount": str(amount_out),
                    "estimatedGas": str(gas_estimate),
                    "type": "multi"
                }
            except Exception as e:
                logger.warning(f"Failed to get quote for multi-hop path: {str(e)}")
                path_id = "-".join([f"{path[i]}-{fees[i]}" for i in range(len(fees))] + [path[-1]])
                
                return {
                    "pathId": path_id,
                    "path": path,
                    "fees": fees,
                    "toAmount": "0",
                    "estimatedGas": "0",
                    "error": str(e),
                    "type": "multi"
                }
                
        except Exception as e:
            logger.error(f"Failed to get quote for multi-hop path: {str(e)}")
            return {
                "pathId": f"multi-path-error",
                "path": path,
                "fees": fees,
                "toAmount": "0",
                "estimatedGas": "0",
                "error": str(e),
                "type": "multi"
            }

    def _parallel_get_quote(self, path_info: Dict, amount_in: int) -> Dict:
        """并行获取路径报价"""
        if len(path_info["tokens"]) == 2:
            return self.get_quote_for_path(
                path_info["tokens"][0],
                path_info["tokens"][1],
                amount_in,
                path_info["fees"][0]
            )
        else:
            return self.get_quote_for_multi_path(
                path_info["tokens"],
                path_info["fees"],
                amount_in
            )

    def find_possible_paths(self, token_in: str, token_out: str, max_hops: int = 2) -> List[Dict]:
        """寻找从token_in到token_out的所有可能路径（带缓存）"""
        # 检查缓存
        cached_paths = self._get_cached_paths(token_in, token_out, max_hops)
        if cached_paths is not None:
            return cached_paths

        # 获取当前链的常用中间代币
        common_bases = COMMON_BASES.get(self.chain_id, [])
        paths = []
        
        # 并行获取直接路径
        with ThreadPoolExecutor(max_workers=len(self.FEE_TIERS)) as executor:
            future_to_fee = {
                executor.submit(self._parallel_get_pool, token_in, token_out, fee): fee
                for fee in self.FEE_TIERS
            }
            
            for future in as_completed(future_to_fee):
                fee, pool = future.result()
                if pool != "0x0000000000000000000000000000000000000000":
                    paths.append({
                        "tokens": [token_in, token_out],
                        "fees": [fee]
                    })
        
        # 如果需要探索更多跳数，且有常用代币可用
        if max_hops >= 2 and common_bases:
            # 并行处理一跳路径
            with ThreadPoolExecutor(max_workers=min(len(common_bases), 10)) as executor:
                future_to_base = {}
                for base in common_bases:
                    if base.lower() in [token_in.lower(), token_out.lower()]:
                        continue
                    future_to_base[executor.submit(self._find_two_hop_path, token_in, token_out, base)] = base
                
                for future in as_completed(future_to_base):
                    path = future.result()
                    if path:
                        paths.append(path)
        
        # 如果需要探索3跳路径且有足够的常用代币
        if max_hops >= 3 and len(common_bases) >= 2:
            # 并行处理两跳路径
            with ThreadPoolExecutor(max_workers=min(len(common_bases), 5)) as executor:
                future_to_bases = {}
                for base1 in common_bases:
                    if base1.lower() in [token_in.lower(), token_out.lower()]:
                        continue
                    for base2 in common_bases:
                        if base2.lower() in [token_in.lower(), token_out.lower(), base1.lower()]:
                            continue
                        future_to_bases[executor.submit(self._find_three_hop_path, token_in, token_out, base1, base2)] = (base1, base2)
                
                for future in as_completed(future_to_bases):
                    path = future.result()
                    if path:
                        paths.append(path)
        
        # 设置缓存
        self._set_path_cache(token_in, token_out, max_hops, paths)
        return paths

    def _find_two_hop_path(self, token_in: str, token_out: str, base: str) -> Optional[Dict]:
        """查找两跳路径"""
        # 检查第一跳 (A->C)
        fee1 = None
        for f in self.FEE_TIERS:
            if self.get_pool(token_in, base, f) != "0x0000000000000000000000000000000000000000":
                fee1 = f
                break
        
        # 检查第二跳 (C->B)
        fee2 = None
        for f in self.FEE_TIERS:
            if self.get_pool(base, token_out, f) != "0x0000000000000000000000000000000000000000":
                fee2 = f
                break
        
        if fee1 and fee2:
            return {
                "tokens": [token_in, base, token_out],
                "fees": [fee1, fee2]
            }
        return None

    def _find_three_hop_path(self, token_in: str, token_out: str, base1: str, base2: str) -> Optional[Dict]:
        """查找三跳路径"""
        # 检查所有跳数
        fee1 = None
        for f in self.FEE_TIERS:
            if self.get_pool(token_in, base1, f) != "0x0000000000000000000000000000000000000000":
                fee1 = f
                break
        
        fee2 = None
        for f in self.FEE_TIERS:
            if self.get_pool(base1, base2, f) != "0x0000000000000000000000000000000000000000":
                fee2 = f
                break
        
        fee3 = None
        for f in self.FEE_TIERS:
            if self.get_pool(base2, token_out, f) != "0x0000000000000000000000000000000000000000":
                fee3 = f
                break
        
        if fee1 and fee2 and fee3:
            return {
                "tokens": [token_in, base1, base2, token_out],
                "fees": [fee1, fee2, fee3]
            }
        return None

    def get_quote(self, params: Dict) -> Dict:
        """获取多路径报价信息，并返回最优路径（并行处理）"""
        try:
            token_in = params["fromTokenAddress"]
            token_out = params["toTokenAddress"]
            amount_in = int(params["amount"])
            
            # 验证地址
            token_in_cs = self.validate_address(token_in)
            token_out_cs = self.validate_address(token_out)
            
            # 查找所有可能的路径
            max_hops = min(int(params.get("maxHops", 2)), self.MAX_HOPS)
            all_possible_paths = self.find_possible_paths(token_in_cs, token_out_cs, max_hops)
            
            logger.info(f"Found {len(all_possible_paths)} possible paths for {token_in} to {token_out}")
            
            # 如果指定了特定路径，只查询该路径
            if "pathId" in params:
                path_id = params["pathId"]
                matching_paths = [p for p in all_possible_paths if "-".join([f"{p['tokens'][i]}-{p['fees'][i]}" for i in range(len(p['fees']))] + [p['tokens'][-1]]) == path_id]
                if matching_paths:
                    selected_path = matching_paths[0]
                    path_quote = self._parallel_get_quote(selected_path, amount_in)
                    paths = [path_quote]
                else:
                    raise ValidationError(f"Invalid path ID: {path_id}")
            
            # 如果指定了费率，只查询直接路径
            elif "fee" in params:
                fee = int(params["fee"])
                if fee not in self.FEE_TIERS:
                    raise ValidationError(f"Invalid fee tier {fee}. Supported tiers: {self.FEE_TIERS}")
                paths = [self.get_quote_for_path(token_in, token_out, amount_in, fee)]
            
            # 否则，并行查询所有可能的路径
            else:
                with ThreadPoolExecutor(max_workers=min(len(all_possible_paths), 10)) as executor:
                    future_to_path = {
                        executor.submit(self._parallel_get_quote, path_info, amount_in): path_info
                        for path_info in all_possible_paths
                    }
                    
                    paths = []
                    for future in as_completed(future_to_path):
                        quote = future.result()
                        if quote["toAmount"] != "0":
                            paths.append(quote)
            
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
                "pathId": best_path["pathId"],
                "path": best_path["path"],
                "fees": best_path["fees"],
                "type": best_path["type"],
                "allPaths": paths  # 返回所有可能的路径，以供参考
            }
        except ValidationError as e:
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
            
            slippage = float(params.get("slippage", "0.005"))
            if not 0 <= slippage <= 1:
                raise ValidationError(f"Slippage must be between 0 and 1, got {slippage}")
            
            # 确定使用的路径
            path_type = "single"  # 默认为单跳路径
            
            # 如果指定了路径ID，使用该路径
            if "pathId" in params:
                # 先获取报价来确认路径类型和详情
                quote_result = self.get_quote({
                    "fromTokenAddress": token_in,
                    "toTokenAddress": token_out,
                    "amount": str(amount_in),
                    "pathId": params["pathId"]
                })
                
                path_tokens = quote_result["path"]
                path_fees = quote_result["fees"]
                path_type = quote_result["type"]
                logger.info(f"Using specified path: {quote_result['pathId']}, type: {path_type}")
            else:
                # 否则，获取最优路径
                quote_result = self.get_quote({
                    "fromTokenAddress": token_in,
                    "toTokenAddress": token_out,
                    "amount": str(amount_in),
                    "maxHops": int(params.get("maxHops", 2))
                })
                
                path_tokens = quote_result["path"]
                path_fees = quote_result["fees"]
                path_type = quote_result["type"]
                logger.info(f"Using best path: {quote_result['pathId']}, type: {path_type}")
            
            # 获取输出金额和最小输出金额
            quote_amount = int(quote_result["toAmount"])
            min_amount_out = int(quote_amount * (1 - slippage))
            logger.info(f"Quote result: amountOut={quote_amount}, minAmountOut={min_amount_out}")

            # 构建交易数据
            deadline = self.web3.eth.get_block('latest').timestamp + 1800  # 30分钟后过期
            
            # 获取 nonce
            nonce = self.web3.eth.get_transaction_count(user_address)
            logger.info(f"Current nonce for {user_address}: {nonce}")
            
            # 构建基础交易参数
            weth = self.router_contract.functions.WETH9().call()
            is_native_token = token_in.lower() == weth.lower()
            
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
                    'maxFeePerGas': base_fee * 1.2 + priority_fee,  # 基础费用 + 优先费用
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

            # 根据路径类型构建交易
            if path_type == "single":
                # 单跳路径使用 exactInputSingle
                swap_params = {
                    'tokenIn': path_tokens[0],
                    'tokenOut': path_tokens[1],
                    'fee': path_fees[0],
                    'recipient': recipient,
                    'deadline': deadline,
                    'amountIn': amount_in,
                    'amountOutMinimum': min_amount_out,
                    'sqrtPriceLimitX96': 0
                }
                logger.info(f"Single-hop swap parameters: {json.dumps(swap_params)}")
                
                # 获取交易数据
                tx = self.router_contract.functions.exactInputSingle(
                    swap_params
                ).build_transaction(tx_params)
                
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
                    logger.info(f"Estimated gas for single-hop: {gas_estimate}, With buffer: {gas}")
                except Exception as e:
                    logger.warning(f"Failed to estimate gas for single-hop, using default: {str(e)}")
                    gas = 300000  # 使用默认值
                    logger.info(f"Using default gas limit: {gas}")
                
            else:
                # 多跳路径使用 exactInput
                encoded_path = self.encode_path(path_tokens, path_fees)
                
                swap_params = {
                    'path': encoded_path,
                    'recipient': recipient,
                    'deadline': deadline,
                    'amountIn': amount_in,
                    'amountOutMinimum': min_amount_out
                }
                logger.info(f"Multi-hop swap parameters: path={path_tokens}, fees={path_fees}")
                
                # 获取交易数据
                tx = self.router_contract.functions.exactInput(
                    swap_params
                ).build_transaction(tx_params)
                
                # 估算 gas (多跳路径通常需要更多 gas)
                try:
                    gas_estimate = self.router_contract.functions.exactInput(
                        swap_params
                    ).estimate_gas({
                        'from': user_address,
                        'value': amount_in if is_native_token else 0,
                        'type': tx_params['type']
                    })
                    gas = int(gas_estimate * 1.3)  # 增加 30% gas 余量，因为多跳路径
                    logger.info(f"Estimated gas for multi-hop: {gas_estimate}, With buffer: {gas}")
                except Exception as e:
                    logger.warning(f"Failed to estimate gas for multi-hop, using default: {str(e)}")
                    gas = 500000  # 使用更高的默认值，因为多跳路径
                    logger.info(f"Using default gas limit for multi-hop: {gas}")

            logger.info(f"Built transaction data: {tx['data'][:100]}...")  # 只记录数据的前100个字符

            # 构建最终交易数据
            result = {
                "from": params["userWalletAddress"],
                "to": self.router_address,
                "data": tx["data"],
                "value": amount_in if is_native_token else 0,
                "gas": gas,
                "chainId": int(self.chain_id),
                "type": tx_params['type'],
                "nonce": nonce,
                "pathType": path_type,
                "path": path_tokens,
                "fees": path_fees
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