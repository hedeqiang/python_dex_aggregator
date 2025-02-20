from typing import Dict, Optional
from dex_aggregator.providers.okx.client import OKXClient
from dex_aggregator.utils.web3_helper import Web3Helper
from dex_aggregator.utils.logger import get_logger
from dex_aggregator.config.settings import WALLET_CONFIG, NATIVE_TOKENS

logger = get_logger(__name__)


class SwapService:
    def __init__(self):
        self.okx_client = OKXClient()
        self.wallet_config = WALLET_CONFIG["default"]  # 使用默认钱包配置

    def check_and_approve(self, chain_id: str, token_address: str, owner_address: str, amount: str) -> Optional[str]:
        """检查授权额度并在需要时发起授权"""
        try:
            web3_helper = Web3Helper.get_instance(chain_id)

            # 1. 获取授权地址
            approve_data = self.okx_client.get_approve_transaction({
                "chainId": chain_id,
                "tokenContractAddress": token_address,
                "approveAmount": amount
            })

            spender_address = approve_data["data"][0]["spenderAddress"]

            # 2. 检查当前授权额度
            current_allowance = web3_helper.get_allowance(
                token_address=token_address,
                owner_address=owner_address,
                spender_address=spender_address
            )

            # 3. 如果授权额度不足，发起授权交易
            if current_allowance < int(amount):
                logger.info(f"Current allowance {current_allowance} is less than required amount {amount}, approving...")

                tx_data = approve_data["data"][0]
                gas_price = web3_helper.web3.eth.gas_price
                nonce = web3_helper.web3.eth.get_transaction_count(owner_address)

                transaction = {
                    "nonce": nonce,
                    "to": token_address,
                    "gasPrice": int(gas_price * 1.5),
                    "gas": int(int(tx_data["gasLimit"]) * 1.5),
                    "data": tx_data["data"],
                    "value": 0,
                    "chainId": int(chain_id)
                }

                tx_hash = web3_helper.send_transaction(transaction, self.wallet_config["private_key"])
                logger.info(f"Approval transaction sent: {tx_hash}")
                return tx_hash

            return None

        except Exception as e:
            logger.error(f"Failed to check and approve: {str(e)}")
            raise

    def _get_amount_in_wei(self, web3_helper: Web3Helper, token_address: str, amount: str) -> str:
        """
        将代币金额转换为链上精度
        
        Args:
            web3_helper: Web3Helper实例
            token_address: 代币地址
            amount: 原始金额（带小数点的字符串）
            
        Returns:
            str: 转换后的金额（wei格式）
        """
        try:
            chain_id = web3_helper.chain_id
            if token_address.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
                if chain_id not in NATIVE_TOKENS:
                    raise ValueError(f"Unsupported chain ID: {chain_id}")
                decimals = NATIVE_TOKENS[chain_id]["decimals"]
            else:
                decimals = web3_helper.get_token_decimals(token_address)
            
            return str(web3_helper.parse_token_amount(amount, decimals))
        except Exception as e:
            logger.error(f"Failed to convert amount {amount} for token {token_address}: {str(e)}")
            raise

    def create_swap_transaction(self, chain_id: str, from_token: str, to_token: str, amount: str, 
                              user_address: str, recipient_address: Optional[str] = None, 
                              slippage: str = "0.03", **kwargs) -> Dict:
        """创建兑换交易"""
        try:
            web3_helper = Web3Helper.get_instance(chain_id)
            
            # 转换金额精度
            raw_amount = self._get_amount_in_wei(web3_helper, from_token, amount)
            
            params = {
                "chainId": chain_id,
                "fromTokenAddress": from_token,
                "toTokenAddress": to_token,
                "amount": raw_amount,
                "userWalletAddress": user_address,
                "slippage": slippage,
                **kwargs
            }
            
            if recipient_address:
                params["swapReceiverAddress"] = recipient_address
            
            print(f"create_swap_transaction params: {params}")
            swap_data = self.okx_client.get_swap(params)
            logger.info(f"Created swap transaction for {amount} of {from_token} to {to_token}")
            logger.info(f"Recipient address: {recipient_address or user_address}")
            return swap_data

        except Exception as e:
            logger.error(f"Failed to create swap transaction: {str(e)}")
            raise

    def execute_swap(self, chain_id: str, from_token: str, to_token: str, amount: str,
                    recipient_address: Optional[str] = None, slippage: str = "0.03",
                    wallet_name: str = "default", **kwargs) -> str:
        """执行完整的兑换流程"""
        try:
            wallet = WALLET_CONFIG.get(wallet_name, WALLET_CONFIG["default"])
            user_address = wallet["address"]
            
            web3_helper = Web3Helper.get_instance(chain_id)
            
            # 转换金额精度
            raw_amount = self._get_amount_in_wei(web3_helper, from_token, amount)

            # 1. 如果是ERC20代币，检查并处理授权
            if from_token.lower() != "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
                approve_tx = self.check_and_approve(
                    chain_id=chain_id,
                    token_address=from_token,
                    owner_address=user_address,
                    amount=raw_amount
                )

                if approve_tx:
                    web3_helper.web3.eth.wait_for_transaction_receipt(approve_tx)

            # 2. 创建兑换交易
            swap_data = self.create_swap_transaction(
                chain_id=chain_id,
                from_token=from_token,
                to_token=to_token,
                amount=amount,
                user_address=user_address,
                recipient_address=recipient_address,
                slippage=slippage,
                **kwargs
            )

            logger.info(f"Swap data: {swap_data}")

            # 3. 准备交易参数
            tx_info = swap_data["data"][0]["tx"]
            nonce = web3_helper.web3.eth.get_transaction_count(user_address)

            transaction = {
                "nonce": nonce,
                "to": tx_info["to"],
                "gasPrice": int(int(tx_info["gasPrice"]) * 1.5),
                "gas": int(int(tx_info["gas"]) * 1.5),
                "data": tx_info["data"],
                "value": int(tx_info["value"]),
                "chainId": int(chain_id)
            }

            # 4. 发送兑换交易
            tx_hash = web3_helper.send_transaction(transaction, wallet["private_key"])
            logger.info(f"Swap transaction sent: {tx_hash}")
            return tx_hash

        except Exception as e:
            logger.error(f"Failed to execute swap: {str(e)}")
            raise
