from typing import Dict, Optional
import base58
from solders.transaction import VersionedTransaction, Transaction
from solders.message import MessageV0
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from spl.token.client import Token
from spl.token.constants import TOKEN_PROGRAM_ID
from ...core.interfaces import IDexProvider
from ...config.settings import WALLET_CONFIG, NATIVE_TOKENS, WEB3_CONFIG
from ...utils.logger import get_logger
from .client import OKXClient

logger = get_logger(__name__)

class OKXSolanaProvider(IDexProvider):
    """OKX Solana 提供商实现"""

    SOLANA_CHAIN_ID = "501"
    MAX_RETRIES = 3

    def __init__(self):
        self._client = OKXClient()
        self.wallet_config = WALLET_CONFIG.get("solana", WALLET_CONFIG["default"])
        self.solana_client = Client(WEB3_CONFIG['providers'][self.SOLANA_CHAIN_ID])

    @property
    def client(self):
        return self._client

    def _get_token_decimals(self, token_address: str) -> int:
        """获取 token 精度"""
        try:
            chain_id = self.SOLANA_CHAIN_ID
            # 处理原生 token
            if token_address.lower() == "11111111111111111111111111111111":
                if chain_id not in NATIVE_TOKENS:
                    raise ValueError(f"Unsupported chain ID: {chain_id}")
                return NATIVE_TOKENS[chain_id]["decimals"]

            # 处理 SPL token
            token = Token(
                conn=self.solana_client,
                pubkey=Pubkey.from_string(token_address),
                program_id=TOKEN_PROGRAM_ID,
                payer=None
            )
            mint_info = token.get_mint_info()
            return mint_info.decimals

        except Exception as e:
            logger.error(f"Failed to get token decimals for {token_address}: {str(e)}")
            raise

    def _convert_amount(self, amount: str, token_address: str) -> str:
        """将金额转换为链上小数"""
        try:
            value = float(amount)
            if value <= 0:
                raise ValueError("Amount must be greater than 0")
            decimals = self._get_token_decimals(token_address)
            return str(int(value * (10 ** decimals)))
        except (ValueError, TypeError) as e:
            logger.error(f"Amount conversion error: {str(e)}")
            raise ValueError("Invalid amount format")

    def get_quote(self, chain_id: str, from_token: str, to_token: str, amount: str, **kwargs) -> Dict:
        """获取兑换参数"""
        try:
            if chain_id != self.SOLANA_CHAIN_ID:
                raise ValueError(f"Invalid chain ID for Solana: {chain_id}")

            raw_amount = self._convert_amount(amount, from_token)
            params = {
                "chainId": chain_id,
                "fromTokenAddress": from_token,
                "toTokenAddress": to_token,
                "amount": raw_amount,
                **kwargs
            }

            quote_result = self.client.get_quote(params)
            logger.info(f"Got quote for {amount} from {from_token} to {to_token}")
            return quote_result

        except Exception as e:
            logger.error(f"Failed to get quote: {str(e)}")
            raise

    def check_and_approve(self, chain_id: str, token_address: str, owner_address: str, amount: int) -> Optional[str]:
        """Solana 不需要授权"""
        return None

    def swap(self, chain_id: str, from_token: str, to_token: str, amount: str,
             recipient_address: Optional[str] = None,slippage: str = "0.03", **kwargs) -> str:
        """在 Solana 上执行兑换交易"""
        try:
            if chain_id != self.SOLANA_CHAIN_ID:
                raise ValueError(f"Invalid chain ID for Solana: {chain_id}")

            # 检查是否为原生 SOL 并验证余额
            if from_token.lower() == "11111111111111111111111111111111":
                balance = self.solana_client.get_balance(
                    Pubkey.from_string(self.wallet_config["address"])
                ).value
                raw_amount = int(self._convert_amount(amount, from_token))
                if balance < raw_amount:
                    raise ValueError(
                        f"SOL 余额不足。需要: {amount}, 可用: {balance / 1e9}"
                    )
                logger.info(f"SOL 余额检查通过。余额: {balance / 1e9} SOL")

            # 获取兑换数据
            params = {
                "chainId": chain_id,
                "fromTokenAddress": from_token,
                "toTokenAddress": to_token,
                "amount": self._convert_amount(amount, from_token),
                "userWalletAddress": self.wallet_config["address"],
                "slippage": slippage,
            }

            if recipient_address:
                params["swapReceiverAddress"] = recipient_address

            swap_data = self.client.get_swap(params)
            logger.info(f"获取兑换数据 {amount} 从 {from_token} 到 {to_token}")

            if "data" not in swap_data or not swap_data["data"]:
                raise ValueError("收到无效的兑换数据")

            tx_data = swap_data["data"][0]["tx"]["data"]

            # 解码交易数据
            try:
                decoded_tx = base58.b58decode(tx_data)
            except Exception as e:
                logger.error(f"解码交易数据失败: {e}")
                raise

            # 获取密钥对
            keypair = Keypair.from_bytes(base58.b58decode(self.wallet_config["private_key"]))
            logger.info(f"使用钱包地址: {self.wallet_config['address']}")

            # 获取最新的区块哈希
            latest_blockhash = self.solana_client.get_latest_blockhash().value.blockhash
            logger.info(f"获取最新区块哈希: {latest_blockhash}")

            try:
                # 尝试创建并签名版本化交易
                tx = VersionedTransaction.from_bytes(decoded_tx)
                
                # 使用更新的区块哈希创建新消息
                message = MessageV0(
                    header=tx.message.header,
                    account_keys=tx.message.account_keys,
                    recent_blockhash=latest_blockhash,
                    instructions=tx.message.instructions,
                    address_table_lookups=tx.message.address_table_lookups
                )
                
                # 创建并签名交易
                signed_tx = VersionedTransaction(message, [keypair])
                try:
                    serialized_tx = bytes(signed_tx)  # 序列化已签名的交易
                    signature = self.solana_client.send_raw_transaction(serialized_tx).value
                    tx_hash = str(signature)

                    logger.info(f"兑换交易已发送: {tx_hash}")
                    return tx_hash

                except Exception as e:
                    logger.error(f"发送交易失败: {e}")
                    raise

            except Exception as e:
                logger.error(f"创建和签名交易失败: {e}")
                raise

        except Exception as e:
            logger.error(f"执行兑换失败: {str(e)}")
            raise