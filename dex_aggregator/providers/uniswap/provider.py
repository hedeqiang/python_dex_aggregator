from typing import Dict, Optional, Any
from decimal import Decimal
import re
from ...core.interfaces import IDexProvider
from ...core.exceptions import ValidationError, ProviderError
from ...utils.web3_helper import Web3Helper
from ...config.settings import WALLET_CONFIG, NATIVE_TOKENS
from ...utils.logger import get_logger
from .client import UniswapClient

logger = get_logger(__name__)

class UniswapProvider(IDexProvider):
    """Uniswap DEX Provider 实现"""

    SUPPORTED_CHAINS = ["1", "56", "137", "42161", "10"]  # 支持的链ID
    MAX_UINT256 = 2**256 - 1

    def __init__(self):
        self.chain_id = "1"  # 默认使用以太坊主网
        self._web3_helper = Web3Helper.get_instance(self.chain_id)
        self._client = UniswapClient(self._web3_helper.web3, self.chain_id)
        self.wallet_config = WALLET_CONFIG["default"]

    @property
    def client(self):
        return self._client

    def _validate_chain_id(self, chain_id: str) -> str:
        """验证链ID并在必要时更新客户端"""
        if not chain_id or chain_id not in self.SUPPORTED_CHAINS:
            supported_chains = ", ".join(self.SUPPORTED_CHAINS)
            raise ValidationError(f"Unsupported chain ID: {chain_id}. Supported chains: {supported_chains}")

        # 如果链ID变化，重新初始化客户端
        if chain_id != self.chain_id:
            self.chain_id = chain_id
            self._web3_helper = Web3Helper.get_instance(chain_id)
            self._client = UniswapClient(self._web3_helper.web3, chain_id)

        return chain_id

    def _validate_address(self, address: str, param_name: str) -> str:
        """验证地址格式"""
        if not address or not isinstance(address, str):
            raise ValidationError(f"Invalid {param_name}: {address}. Must be a non-empty string.")

        if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
            raise ValidationError(f"Invalid {param_name} format: {address}. Must be a valid Ethereum address.")

        return address

    def _validate_amount(self, amount: str) -> str:
        """验证金额格式"""
        try:
            # 尝试转换为 Decimal 确保是有效数字
            amount_decimal = Decimal(amount)
            if amount_decimal <= 0:
                raise ValidationError(f"Amount must be greater than 0, got {amount}")
            return amount
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid amount format: {amount}. Must be a valid positive number.")

    def _get_amount_in_wei(self, token_address: str, amount: str) -> str:
        """将代币金额转换为链上精度"""
        try:
            # 验证输入
            token_address = self._validate_address(token_address, "token_address")
            amount = self._validate_amount(amount)

            # 获取代币精度
            if token_address.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
                if self.chain_id not in NATIVE_TOKENS:
                    raise ValidationError(f"Native token configuration not found for chain {self.chain_id}")
                decimals = NATIVE_TOKENS[self.chain_id]["decimals"]
            else:
                decimals = self._web3_helper.get_token_decimals(token_address)

            return str(self._web3_helper.parse_token_amount(amount, decimals))
        except ValidationError as e:
            # Re-raise validation errors
            raise e
        except Exception as e:
            logger.error(f"Failed to convert amount {amount} for token {token_address}: {str(e)}")
            raise ProviderError(f"Amount conversion failed: {str(e)}")

    def get_quote(self, chain_id: str, from_token: str, to_token: str, amount: str, **kwargs) -> Dict:
        """获取报价，支持多费率层级"""
        try:
            # 验证输入参数
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

            # 获取多路径报价
            quote_result = self.client.get_quote(params)

            # 获取代币精度并转换为人类可读的数量
            if to_token.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
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
                "fee": quote_result["fee"],
                "pathId": quote_result["pathId"]
            }

            # 如果存在多路径结果，添加到结果中
            if "allPaths" in quote_result:
                paths_info = []
                for path in quote_result["allPaths"]:
                    if path["toAmount"] != "0":
                        path_human_amount = float(path["toAmount"]) / (10 ** to_decimals)
                        paths_info.append({
                            "fee": path["fee"],
                            "toAmount": path["toAmount"],
                            "humanAmount": f"{path_human_amount:.8f}",
                            "estimatedGas": path["estimatedGas"],
                            "pathId": path["pathId"]
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

            # 如果是原生代币，不需要授权
            if token_address.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
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
        """执行兑换，支持多费率层级

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

            # 处理费率参数
            fee = None
            if "fee" in kwargs:
                try:
                    fee = int(kwargs["fee"])
                    if fee not in self.client.FEE_TIERS:
                        raise ValidationError(f"Invalid fee: {fee}. Must be one of {self.client.FEE_TIERS}")
                except (ValueError, TypeError):
                    raise ValidationError(f"Invalid fee format: {kwargs['fee']}. Must be an integer.")

            # 如果没有指定费率，先获取报价以确定最佳费率
            if fee is None:
                quote = self.get_quote(
                    chain_id=chain_id,
                    from_token=from_token,
                    to_token=to_token,
                    amount=amount
                )
                fee = quote["fee"]
                logger.info(f"Using optimal fee tier {fee} for {from_token}/{to_token}")

            # 检查授权 (仅对非原生代币)
            weth = self._client.router_contract.functions.WETH9().call()
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

            # 构建兑换参数
            params = {
                'fromTokenAddress': from_token,
                'toTokenAddress': to_token,
                'amount': raw_amount,
                'userWalletAddress': user_address,
                'fee': fee,
                'slippage': slippage
            }

            if recipient:
                params['recipient'] = recipient

            # 获取兑换数据
            try:
                swap_data = self.client.get_swap_data(params)
            except Exception as e:
                logger.error(f"Failed to get swap data: {str(e)}")
                raise ProviderError(f"Failed to generate swap transaction: {str(e)}")

            # 发送交易
            try:
                tx_hash = self._web3_helper.send_transaction(
                    swap_data,
                    self.wallet_config["private_key"]
                )
                logger.info(f"Swap transaction sent: {tx_hash}")
                return tx_hash
            except Exception as e:
                logger.error(f"Failed to send swap transaction: {str(e)}")
                raise ProviderError(f"Failed to execute swap transaction: {str(e)}")

        except ValidationError as e:
            # Re-raise validation errors for better handling
            raise e
        except Exception as e:
            logger.error(f"Failed to execute swap: {str(e)}")
            raise ProviderError(f"Swap execution failed: {str(e)}")

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
                'maxFeePerGas': base_fee * 2 + priority_fee,  # 基础费用的2倍 + 优先费
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