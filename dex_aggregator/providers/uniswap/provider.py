from typing import Dict, Optional, List, Union, Any
from decimal import Decimal
from eth_typing import ChecksumAddress

from web3 import Web3
from ...core.interfaces import IDexProvider
from ...core.exceptions import ValidationError, ProviderError
from ...utils.logger import get_logger
from ...utils.web3_helper import Web3Helper
from ...config.settings import WALLET_CONFIG, NATIVE_TOKENS
from .client import UniswapClient

logger = get_logger(__name__)

class UniswapProvider(IDexProvider):
    """Uniswap DEX Provider 实现"""

    SUPPORTED_CHAINS = ["1", "56", "137", "42161", "10", "43114", "8453", "81457", "42220", "480", "324", "7777777"]  # 支持的链ID
    MAX_UINT256 = 2**256 - 1
    
    def __init__(self):
        self._client = None
        self._web3_helper = None
        self.wallet_config = {}
        
    def init_provider(self, chain_id: str) -> None:
        """初始化Uniswap提供者

        Args:
            chain_id (str): 链ID
        """
        try:
            if chain_id not in self.SUPPORTED_CHAINS:
                raise ValidationError(f"Unsupported chain_id: {chain_id}. Must be one of {self.SUPPORTED_CHAINS}")
                
            logger.info(f"Initializing Uniswap provider for chain ID: {chain_id}")
            
            # 初始化Web3Helper
            self._web3_helper = Web3Helper.get_instance(chain_id)
            
            # 初始化UniswapClient
            self._client = UniswapClient(self._web3_helper.web3, chain_id)
            
            # 设置钱包配置
            self.wallet_config = WALLET_CONFIG.get("default", {})
            
            logger.info(f"Uniswap provider initialized successfully for chain ID: {chain_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Uniswap provider: {str(e)}")
            raise ProviderError(f"Provider initialization failed: {str(e)}")
        
    @property
    def client(self):
        if not self._client:
            raise ProviderError("Provider not initialized, call init_provider first")
        return self._client
        
    def _validate_chain_id(self, chain_id: str) -> str:
        """验证链ID并更新客户端"""
        if not chain_id:
            raise ValidationError("chain_id cannot be empty")
            
        if chain_id not in self.SUPPORTED_CHAINS:
            raise ValidationError(f"Unsupported chain_id: {chain_id}. Must be one of {self.SUPPORTED_CHAINS}")
            
        # 如果客户端不存在或链ID改变，重新初始化客户端
        if not self._client or self._client.chain_id != chain_id:
            self.init_provider(chain_id)
            
        return chain_id
        
    def _validate_address(self, address: str, param_name: str) -> str:
        """验证地址格式"""
        if not address:
            raise ValidationError(f"{param_name} cannot be empty")
            
        try:
            return self.client.validate_address(address)
        except Exception as e:
            raise ValidationError(f"Invalid {param_name}: {str(e)}")
            
    def _validate_amount(self, amount: str) -> str:
        """验证金额格式"""
        if not amount:
            raise ValidationError("amount cannot be empty")
            
        try:
            float_amount = float(amount)
            if float_amount <= 0:
                raise ValidationError(f"Amount must be positive, got {amount}")
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid amount format: {amount}. Must be a positive number.")
            
        return amount
        
    def _get_amount_in_wei(self, token_address: str, amount: str) -> str:
        """获取以 wei 为单位的金额"""
        try:
            # 验证输入
            token_address = self._validate_address(token_address, "token_address")
            amount = self._validate_amount(amount)
            weth = self.client.router_contract.functions.WETH9().call()
            # 获取代币精度
            if token_address.lower() == "0x0000000000000000000000000000000000000000" or token_address.lower() == weth.lower():
                # 处理原生代币
                if self._client.chain_id not in NATIVE_TOKENS:
                    raise ValidationError(f"Native token configuration not found for chain {self._client.chain_id}")
                decimals = NATIVE_TOKENS[self._client.chain_id]["decimals"]
            else:
                # 获取 ERC20 代币的精度
                decimals = self._web3_helper.get_token_decimals(token_address)

            # 转换为 wei 单位
            float_amount = float(amount)
            raw_amount = str(int(float_amount * (10 ** decimals)))
            return raw_amount
        except ValidationError as e:
            # Re-raise validation errors
            raise e
        except Exception as e:
            logger.error(f"Failed to get amount in wei: {str(e)}")
            raise ProviderError(f"Amount conversion failed: {str(e)}")

    def get_quote(self, chain_id: str, from_token: str, to_token: str, amount: str, **kwargs) -> Dict:
        """获取兑换报价"""
        try:
            # 验证输入
            chain_id = self._validate_chain_id(chain_id)
            from_token = self._validate_address(from_token, "from_token")
            to_token = self._validate_address(to_token, "to_token")
            amount = self._validate_amount(amount)

            # 验证 from_token 和 to_token 不是相同的
            if from_token.lower() == to_token.lower():
                raise ValidationError("from_token and to_token cannot be the same")

            raw_amount = self._get_amount_in_wei(from_token, amount)

            params = {
                "chainId": chain_id,
                "fromTokenAddress": from_token,
                "toTokenAddress": to_token,
                "amount": raw_amount
            }

            # 处理可选参数
            # 如果提供了特定费率，则使用该费率
            if "fee" in kwargs:
                fee = kwargs.get("fee")
                try:
                    fee = int(fee)
                    if fee not in self.client.FEE_TIERS:
                        raise ValidationError(f"Invalid fee: {fee}. Must be one of {self.client.FEE_TIERS}")
                    params["fee"] = fee
                except (ValueError, TypeError):
                    raise ValidationError(f"Invalid fee format: {fee}. Must be an integer.")

            # 如果提供了特定路径ID，则使用该路径
            if "pathId" in kwargs:
                params["pathId"] = kwargs.get("pathId")

            # 设置最大跳数
            if "maxHops" in kwargs:
                try:
                    max_hops = int(kwargs.get("maxHops"))
                    if max_hops < 1 or max_hops > self.client.MAX_HOPS:
                        raise ValidationError(f"maxHops must be between 1 and {self.client.MAX_HOPS}")
                    params["maxHops"] = max_hops
                except (ValueError, TypeError):
                    raise ValidationError(f"Invalid maxHops format: {kwargs.get('maxHops')}. Must be an integer.")

            # 获取多路径报价
            quote_result = self.client.get_quote(params)
            weth = self.client.router_contract.functions.WETH9().call()

            # 获取代币精度并转换为人类可读的数量
            if to_token.lower() == "0x0000000000000000000000000000000000000000" or to_token.lower() == weth.lower():
                if chain_id not in NATIVE_TOKENS:
                    raise ValidationError(f"Native token configuration not found for chain {chain_id}")
                to_decimals = NATIVE_TOKENS[chain_id]["decimals"]
            else:
                to_decimals = self._web3_helper.get_token_decimals(to_token)

            # 计算可读金额
            human_amount = float(quote_result["toAmount"]) / (10 ** to_decimals)

            # 构建增强的返回结果
            result = {
                "fromTokenAddress": from_token,
                "toTokenAddress": to_token,
                "fromAmount": amount,
                "toAmount": quote_result["toAmount"],
                "humanAmount": f"{human_amount:.8f}",
                "estimatedGas": quote_result["estimatedGas"],
                "pathId": quote_result["pathId"],
                "path": quote_result["path"],
                "fees": quote_result["fees"],
                "pathType": quote_result["type"]
            }

            # 如果存在多路径结果，添加到结果中
            if "allPaths" in quote_result:
                paths_info = []
                for path in quote_result["allPaths"]:
                    if path["toAmount"] != "0":
                        path_human_amount = float(path["toAmount"]) / (10 ** to_decimals)
                        paths_info.append({
                            "pathId": path["pathId"],
                            "path": path["path"],
                            "fees": path["fees"],
                            "toAmount": path["toAmount"],
                            "humanAmount": f"{path_human_amount:.8f}",
                            "estimatedGas": path["estimatedGas"],
                            "pathType": path["type"]
                        })
                if paths_info:
                    result["availablePaths"] = paths_info

            return result

        except ValidationError as e:
            # Re-raise validation errors for better handling
            raise e
        except Exception as e:
            logger.error(f"Failed to get quote: {str(e)}")
            raise ProviderError(f"Quote retrieval failed: {str(e)}")

    def check_and_approve(self, chain_id: str, token_address: str,
                          owner_address: str, amount: int, infinite_approval: bool = False) -> Optional[str]:
        """检查并处理代币授权

        Args:
            chain_id (str): 链ID
            token_address (str): 代币合约地址
            owner_address (str): 代币持有者地址
            amount (int): 需要授权的金额（最小授权金额）
            infinite_approval (bool): 是否进行无限授权，默认为 False

        Returns:
            Optional[str]: 如果进行了授权操作，返回交易哈希，否则返回 None
        """
        try:
            # 验证输入
            chain_id = self._validate_chain_id(chain_id)
            token_address = self._validate_address(token_address, "token_address")
            owner_address = self._validate_address(owner_address, "owner_address")

            weth = self.client.router_contract.functions.WETH9().call()
            # 如果是原生代币，不需要授权
            if token_address.lower() == "0x0000000000000000000000000000000000000000" or token_address.lower() == weth.lower():
                return None

            # 获取路由合约地址
            spender_address = self.client.router_address

            # 获取当前授权额度
            current_allowance = self._web3_helper.get_allowance(
                token_address,
                owner_address,
                spender_address
            )

            # 如果无限授权参数为 True，则将 amount 设置为 MAX_UINT256
            required_amount = self.MAX_UINT256 if infinite_approval else amount

            if current_allowance < required_amount:
                logger.info(f"Current allowance {current_allowance} is less than required amount {required_amount}, approving...")

                # 获取 ERC20 合约
                contract = self._web3_helper.web3.eth.contract(
                    address=self._web3_helper.web3.to_checksum_address(token_address),
                    abi=self._web3_helper.abi_helper.get_abi('erc20')
                )

                # 构建交易参数
                tx_params = self._build_tx_params(owner_address)

                # 估算 gas
                gas_estimate = contract.functions.approve(
                    spender_address,
                    required_amount
                ).estimate_gas({
                    'from': owner_address,
                    'type': tx_params.get('type', 0)  # 确保使用相同的交易类型
                })

                tx_params['gas'] = int(gas_estimate * 1.2)  # 增加 20% gas 余量

                approve_tx = contract.functions.approve(
                    spender_address,
                    required_amount
                ).build_transaction(tx_params)

                tx_hash = self._web3_helper.send_transaction(
                    approve_tx,
                    self.wallet_config["private_key"]
                )
                logger.info(f"Approval transaction sent: {tx_hash}")
                return tx_hash

            logger.info(f"Current allowance {current_allowance} is enough for required amount {required_amount}, no approval needed.")
            return None

        except ValidationError as e:
            # Re-raise validation errors
            raise e
        except Exception as e:
            logger.error(f"Failed to check and approve: {str(e)}")
            raise ProviderError(f"Token approval failed: {str(e)}")

    def swap(self, chain_id: str, from_token: str, to_token: str, amount: str,
             recipient: Optional[str] = None, slippage: str = "0.005",
             infinite_approval: bool = False, **kwargs) -> str:
        """执行兑换，支持多费率层级和多跳路径

        Args:
            chain_id (str): 链ID
            from_token (str): 源代币地址
            to_token (str): 目标代币地址
            amount (str): 兑换金额
            recipient (Optional[str]): 收款地址，默认为 None
            slippage (str): 滑点，默认为"0.005"
            infinite_approval (bool): 是否进行无限授权，默认为 False

        Returns:
            str: 交易哈希
        """
        try:
            # 验证输入参数
            chain_id = self._validate_chain_id(chain_id)
            from_token = self._validate_address(from_token, "from_token")
            to_token = self._validate_address(to_token, "to_token")
            amount = self._validate_amount(amount)

            # 验证收款地址
            if recipient:
                recipient = self._validate_address(recipient, "recipient")

            # 验证滑点
            try:
                slippage_float = float(slippage)
                if not 0 <= slippage_float <= 1:
                    raise ValidationError(f"Slippage must be between 0 and 1, got {slippage}")
            except (ValueError, TypeError):
                raise ValidationError(f"Invalid slippage format: {slippage}. Must be a number between 0 and 1.")

            # 验证 from_token 和 to_token 不是相同的
            if from_token.lower() == to_token.lower():
                raise ValidationError("from_token and to_token cannot be the same")

            user_address = self.wallet_config["address"]
            raw_amount = self._get_amount_in_wei(from_token, amount)
            
            swap_params = {
                'fromTokenAddress': from_token,
                'toTokenAddress': to_token,
                'amount': raw_amount,
                'userWalletAddress': user_address,
                'slippage': slippage
            }
            
            # 处理可选参数
            # 如果提供了特定费率，则使用该费率
            if "fee" in kwargs:
                try:
                    fee = int(kwargs["fee"])
                    if fee not in self.client.FEE_TIERS:
                        raise ValidationError(f"Invalid fee: {fee}. Must be one of {self.client.FEE_TIERS}")
                    swap_params["fee"] = fee
                except (ValueError, TypeError):
                    raise ValidationError(f"Invalid fee format: {kwargs['fee']}. Must be an integer.")
                    
            # 如果提供了特定路径ID，则使用该路径
            if "pathId" in kwargs:
                swap_params["pathId"] = kwargs["pathId"]
                logger.info(f"Using specified path ID: {kwargs['pathId']}")
                
            # 如果提供了最大跳数限制
            if "maxHops" in kwargs:
                try:
                    max_hops = int(kwargs["maxHops"])
                    if max_hops < 1 or max_hops > self.client.MAX_HOPS:
                        raise ValidationError(f"maxHops must be between 1 and {self.client.MAX_HOPS}")
                    swap_params["maxHops"] = max_hops
                except (ValueError, TypeError):
                    raise ValidationError(f"Invalid maxHops format: {kwargs['maxHops']}. Must be an integer.")

            if recipient:
                swap_params['recipient'] = recipient

            # 检查授权 (仅对非原生代币)
            weth = self.client.router_contract.functions.WETH9().call()
            if from_token.lower() != weth.lower():
                approve_tx = self.check_and_approve(
                    chain_id=chain_id,
                    token_address=from_token,
                    owner_address=user_address,
                    amount=int(raw_amount),
                    infinite_approval=infinite_approval  # 传递参数
                )

                if approve_tx:
                    # 等待授权交易完成
                    receipt = self._web3_helper.wait_for_transaction(approve_tx)
                    if not receipt or receipt.get('status', 0) != 1:
                        raise ProviderError(f"Approval transaction failed: {approve_tx}")
                    logger.info(f"Approval transaction confirmed: {approve_tx}")

            # 获取兑换数据
            try:
                swap_data = self.client.get_swap_data(swap_params)
                # 记录与交易相关的路径信息
                logger.info(f"Swapping with path: {swap_data.get('path')} using fees: {swap_data.get('fees')}")
                logger.info(f"Path type: {swap_data.get('pathType', 'single')}")
            except Exception as e:
                logger.error(f"Failed to get swap data: {str(e)}")
                raise ProviderError(f"Swap data generation failed: {str(e)}")

            # 发送交易
            try:
                # 保存交易类型相关字段
                tx_type = swap_data.pop('type', None)
                path_type = swap_data.pop('pathType', None)
                path = swap_data.pop('path', None)
                fees = swap_data.pop('fees', None)
                
                # 记录类型信息
                logger.info(f"Transaction type: {tx_type}, path type: {path_type}")
                if path:
                    logger.info(f"Path: {path}")
                if fees:
                    logger.info(f"Fees: {fees}")
                
                # 使用相同的交易类型
                if tx_type is not None:
                    swap_data['type'] = tx_type
                
                tx_hash = self._web3_helper.send_transaction(
                    swap_data,
                    self.wallet_config["private_key"]
                )
                logger.info(f"Swap transaction sent: {tx_hash}")
                return tx_hash
            except Exception as e:
                logger.error(f"Failed to send swap transaction: {str(e)}")
                if "gas required exceeds allowance" in str(e):
                    raise ProviderError(f"Insufficient gas: {str(e)}")
                raise ProviderError(f"Swap transaction failed: {str(e)}")

        except ValidationError as e:
            # Re-raise validation errors
            raise e
        except Exception as e:
            logger.error(f"Failed to swap: {str(e)}")
            raise ProviderError(f"Swap operation failed: {str(e)}")

    def _build_tx_params(self, owner_address: str) -> Dict[str, Any]:
        """构建交易参数，支持 EIP-1559 和传统交易类型

        Args:
            owner_address (str): 交易发起者地址

        Returns:
            Dict[str, Any]: 交易参数字典
        """
        try:
            # 获取链上当前 gas 费用信息
            base_fee = self._web3_helper.web3.eth.get_block('latest').baseFeePerGas
            priority_fee = self._web3_helper.web3.eth.max_priority_fee

            # 使用 EIP-1559 交易
            tx_params = {
                'from': owner_address,
                'nonce': self._web3_helper.web3.eth.get_transaction_count(owner_address),
                'maxFeePerGas': base_fee * 1.2 + priority_fee,  # 基础费用的 1.2 倍 + 优先费
                'maxPriorityFeePerGas': priority_fee,
                'type': 2  # EIP-1559 交易类型
            }
        except Exception as e:
            logger.warning(f"EIP-1559 not supported or error: {str(e)}. Using legacy transaction.")
            # 回退到传统交易类型
            tx_params = {
                'from': owner_address,
                'nonce': self._web3_helper.web3.eth.get_transaction_count(owner_address),
                'gasPrice': self._web3_helper.web3.eth.gas_price,
                'type': 0  # 传统交易类型
            }
        return tx_params