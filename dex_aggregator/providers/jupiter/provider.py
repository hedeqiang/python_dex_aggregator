from typing import Dict, Optional, List
import base64
import base58

from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.solders import Signature
from solders.transaction import VersionedTransaction
from ...core.interfaces import IDexProvider
from ...core.exceptions import ProviderError
from ...config.settings import WALLET_CONFIG, NATIVE_TOKENS, WEB3_CONFIG
from ...utils.logger import get_logger
from .client import JupiterClient
from .constants import WSOL_MINT, SOL_ADDRESS, SOLANA_CHAIN_ID, FIXED_GAS_ESTIMATE

logger = get_logger(__name__)

class JupiterProvider(IDexProvider):
    """Jupiter DEX provider implementation"""
    
    def __init__(self):
        self.wallet_config = WALLET_CONFIG.get("solana", WALLET_CONFIG["default"])
        self.solana_client = Client(WEB3_CONFIG['providers'][SOLANA_CHAIN_ID])
        self._client = JupiterClient(self.solana_client)
    
    @property
    def client(self):
        return self._client
    
    def _convert_sol_to_wsol(self, token_address: str) -> str:
        """Convert SOL address to wSOL address for Solana"""
        return WSOL_MINT if token_address.lower() == SOL_ADDRESS else token_address
    
    def _get_token_decimals(self, token_address: str) -> int:
        """Get token decimals"""
        chain_id = SOLANA_CHAIN_ID
        
        # Handle native token (SOL)
        if token_address.lower() == SOL_ADDRESS:
            if chain_id not in NATIVE_TOKENS:
                raise ValueError(f"Unsupported chain ID: {chain_id}")
            return NATIVE_TOKENS[chain_id]["decimals"]
        
        # Get token decimals via client
        return self.client.get_token_decimals(token_address)
    
    def get_quote(self, chain_id: str, from_token: str, to_token: str, amount: str, **kwargs) -> Dict:
        """Get swap quote from Jupiter"""
        if chain_id != SOLANA_CHAIN_ID:
            raise ValueError(f"Unsupported chain ID: {chain_id}")
        
        try:
            # Get token decimals
            from_decimals = self._get_token_decimals(from_token)
            to_decimals = self._get_token_decimals(to_token)
            
            # Convert to chain representation
            raw_amount = str(int(float(amount) * (10 ** from_decimals)))
            
            # Convert SOL to wSOL
            input_mint = self._convert_sol_to_wsol(from_token)
            output_mint = self._convert_sol_to_wsol(to_token)
            
            # Calculate slippage in basis points
            slippage_bps = int(float(kwargs.get("slippage", "0.5")) * 100)
            
            # Get quote from API
            quote_response = self.client.get_quote(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=raw_amount,
                slippage_bps=slippage_bps,
                restrict_intermediate_tokens=kwargs.get("restrictIntermediateTokens", True)
            )
            
            # Calculate human-readable amount
            human_amount = float(quote_response["outAmount"]) / (10 ** to_decimals)
            
            return {
                "fromTokenAddress": from_token,
                "toTokenAddress": to_token,
                "fromAmount": amount,
                "toAmount": quote_response["outAmount"],
                "humanAmount": f"{human_amount:.8f}",
                "estimatedGas": FIXED_GAS_ESTIMATE,  # Fixed gas for Solana
                "priceImpact": str(quote_response.get("priceImpactPct", "0")),
                "quoteResponse": quote_response
            }
        except Exception as e:
            logger.error(f"Failed to get quote: {str(e)}")
            raise ProviderError(f"Failed to get Jupiter quote: {str(e)}")
    
    def check_and_approve(self, chain_id: str, token_address: str, 
                        owner_address: str, amount: int) -> Optional[str]:
        """Check and handle token approval
        Not needed for Solana, returns None
        """
        return None
        
    def _prepare_swap_transaction(self, from_token: str, to_token: str, quote_response: Dict, recipient_address: Optional[str] = None, **kwargs) -> Dict:
        """Prepare swap transaction parameters"""
        # Get user wallet address
        user_address = self.wallet_config["address"]
        
        # Check if tokens are native SOL
        is_input_sol = from_token.lower() == SOL_ADDRESS
        is_output_sol = to_token.lower() == SOL_ADDRESS
        
        # 准备交易参数
        tx_params = {
            "userPublicKey": user_address,
            "wrapAndUnwrapSol": True,  # 默认自动处理SOL的包装和解包
            "dynamicComputeUnitLimit": True,  # 启用动态计算单元限制以获得更准确的费用估算
        }
        
        # 如果提供了接收者地址并且不是发送者自己
        if recipient_address and recipient_address.lower() != user_address.lower():
            logger.info(f"Setting recipient address: {recipient_address}")
            
            # 如果指定了token账户，直接使用它
            if kwargs.get("destinationTokenAccount"):
                tx_params["destinationTokenAccount"] = kwargs["destinationTokenAccount"]
                logger.info(f"Using provided destination token account: {kwargs['destinationTokenAccount']}")
            else:
                # 处理SOL接收情况
                if is_output_sol:
                    # 如果是SOL，我们可以直接使用接收者的地址，但需要明确设置 skipUserAccountsRpcCalls=true
                    tx_params["destinationWallet"] = recipient_address
                    tx_params["skipUserAccountsRpcCalls"] = True
                    logger.info(f"Setting destination wallet for SOL: {recipient_address}")
                else:
                    # 对于SPL代币，我们需要找到接收者的关联代币账户
                    try:
                        # 先从WSOL转回代币实际地址
                        to_token_mint = self._convert_sol_to_wsol(to_token)
                        
                        # 查找接收者的关联代币账户
                        token_account = self.client.get_token_accounts(
                            wallet_address=recipient_address, 
                            token_mint=to_token_mint
                        )
                        
                        if token_account:
                            # 如果找到代币账户，使用它
                            tx_params["destinationTokenAccount"] = token_account
                            logger.info(f"Found destination token account: {token_account}")
                        else:
                            # 如果没找到代币账户，设置目标钱包地址
                            # Jupiter API 将创建关联代币账户
                            tx_params["destinationWallet"] = recipient_address
                            tx_params["skipUserAccountsRpcCalls"] = False  # 确保 Jupiter 会检查和创建账户
                            logger.info(f"No token account found, setting destination wallet: {recipient_address}")
                    except Exception as e:
                        logger.warning(f"Error getting token account, using destination wallet instead: {str(e)}")
                        tx_params["destinationWallet"] = recipient_address
                        tx_params["skipUserAccountsRpcCalls"] = False
        
        # 其他可选参数
        if kwargs.get("useSharedAccounts") is not None:
            tx_params["useSharedAccounts"] = kwargs["useSharedAccounts"]
        else:
            # 默认启用共享账户，提高交易成功率
            tx_params["useSharedAccounts"] = True
        
        if kwargs.get("asLegacyTransaction") is not None:
            tx_params["asLegacyTransaction"] = kwargs["asLegacyTransaction"]
            
        if kwargs.get("dynamicSlippage") is not None:
            tx_params["dynamicSlippage"] = kwargs["dynamicSlippage"]
        
        # 添加引用跟踪账户，如果有的话
        if kwargs.get("trackingAccount"):
            tx_params["trackingAccount"] = kwargs["trackingAccount"]
            
        # 添加优先级费用，如果有的话
        if kwargs.get("prioritizationFeeLamports"):
            tx_params["prioritizationFeeLamports"] = kwargs["prioritizationFeeLamports"]
            
        # 添加计算单元价格，如果有的话
        if kwargs.get("computeUnitPriceMicroLamports"):
            tx_params["computeUnitPriceMicroLamports"] = kwargs["computeUnitPriceMicroLamports"]
            
        # 构建交易
        tx_data = self.client.build_swap_transaction(
            quote_response=quote_response,
            tx_params=tx_params
        )
        
        return tx_data
    
    def _confirm_transaction(self, signature: str, timeout: int = 60) -> Dict:
        """确认交易是否成功执行
        
        Args:
            signature: 交易签名
            timeout: 超时时间（秒）
            
        Returns:
            交易确认结果
        """
        import time
        
        logger.info(f"等待交易确认: {signature}, 超时时间: {timeout}秒")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 获取交易状态
                tx_info = self.solana_client.get_transaction(
                    signature, 
                    commitment="confirmed"
                )
                
                if tx_info:
                    # 判断交易状态
                    if hasattr(tx_info, 'result') and tx_info.result:
                        if tx_info.result.meta and hasattr(tx_info.result.meta, 'err') and not tx_info.result.meta.err:
                            logger.info(f"交易确认成功: {signature}")
                            return {
                                "status": "confirmed", 
                                "signature": signature, 
                                "info": tx_info.to_json() if hasattr(tx_info, 'to_json') else str(tx_info)
                            }
                        else:
                            error_info = tx_info.result.meta.err if (tx_info.result.meta and hasattr(tx_info.result.meta, 'err')) else "Unknown error"
                            logger.error(f"交易执行失败: {error_info}")
                            return {"status": "failed", "signature": signature, "error": str(error_info)}
                    elif hasattr(tx_info, 'value') and tx_info.value:
                        # 新版API返回格式
                        if tx_info.value.err:
                            logger.error(f"交易执行失败: {tx_info.value.err}")
                            return {"status": "failed", "signature": signature, "error": str(tx_info.value.err)}
                        else:
                            logger.info(f"交易确认成功: {signature}")
                            return {"status": "confirmed", "signature": signature}
                
                # 等待1秒再次查询
                time.sleep(1)
                
            except Exception as e:
                logger.warning(f"查询交易状态出错: {str(e)}")
                time.sleep(2)  # 出错时等待时间略长
                
        # 超时情况下，最后再尝试查询一次
        try:
            final_status = self.solana_client.get_transaction(signature)
            if final_status and ((hasattr(final_status, 'result') and final_status.result) or (hasattr(final_status, 'value') and final_status.value)):
                logger.info(f"最终查询结果: 交易已确认")
                return {"status": "confirmed", "signature": signature}
        except Exception:
            pass
            
        logger.warning(f"交易确认超时: {signature}")
        return {"status": "timeout", "signature": signature}
        
    def swap(self, chain_id: str, from_token: str, to_token: str, amount: str,
            recipient_address: Optional[str] = None, slippage: str = "0.5", **kwargs) -> str:
        """Execute swap transaction"""
        try:
            if chain_id != SOLANA_CHAIN_ID:
                raise ValueError(f"Unsupported chain ID: {chain_id}")
            
            # 记录交易参数
            logger.info(f"Swap request: {from_token} -> {to_token}, amount: {amount}, recipient: {recipient_address}")
            
            # Get quote with pricing info
            quote_result = self.get_quote(
                chain_id=chain_id, 
                from_token=from_token, 
                to_token=to_token, 
                amount=amount, 
                slippage=slippage,
                **kwargs
            )
            
            # 记录报价结果
            logger.info(f"Quote result: {amount} {from_token} -> {quote_result['humanAmount']} {to_token} (Price impact: {quote_result['priceImpact']}%)")
            
            # Get token decimals and convert amount
            from_decimals = self._get_token_decimals(from_token)
            raw_amount = str(int(float(amount) * (10 ** from_decimals)))
            
            # Prepare transaction with recipient address
            tx_data = self._prepare_swap_transaction(
                from_token=from_token,
                to_token=to_token,
                quote_response=quote_result["quoteResponse"],
                recipient_address=recipient_address,
                **kwargs
            )
            
            # 记录交易构建结果
            logger.info(f"Transaction prepared, params: {tx_data.get('inputAddress', 'N/A')} -> {tx_data.get('outputAddress', 'N/A')}")
            
            # Get swap transaction data
            swap_transaction_base64 = tx_data.get("swapTransaction")
            if not swap_transaction_base64:
                raise ValueError("Failed to get swap transaction data")
            
            # 获取钱包密钥对
            secret_key = base58.b58decode(self.wallet_config["private_key"])
            keypair = Keypair.from_bytes(secret_key)
            
            # 记录使用的钱包地址
            logger.info(f"Using wallet address: {keypair.pubkey()}")
            
            # 解码 Jupiter 给我们的交易
            tx_bytes = base64.b64decode(swap_transaction_base64)
            
            # 从字节创建未签名的交易
            unsigned_tx = VersionedTransaction.from_bytes(tx_bytes)
            
            # 记录交易信息
            logger.info(f"Transaction created, account keys count: {len(unsigned_tx.message.account_keys)}")
            
            # 获取交易消息
            message = unsigned_tx.message
            
            # 使用钱包密钥对创建已签名的交易
            # VersionedTransaction 构造函数接受消息和签名者数组
            signed_tx = VersionedTransaction(message, [keypair])
            
            # 发送交易到 Solana 网络
            logger.info("Sending transaction to Solana network...")
            tx_signature = self.solana_client.send_transaction(signed_tx)
            
            if not tx_signature:
                raise ValueError("Failed to send transaction")
            
            # 提取交易签名的值
            tx_sig_value = tx_signature.value if hasattr(tx_signature, 'value') else str(tx_signature)
            
            logger.info(f"Swap transaction sent: {tx_sig_value}")
            
            # 确认交易结果（如果需要）
            if kwargs.get("wait_for_confirmation", False):
                confirmation_timeout = kwargs.get("confirmation_timeout", 60)  # 默认超时时间为60秒
                confirmation_result = self._confirm_transaction(tx_sig_value, timeout=confirmation_timeout)
                
                if confirmation_result["status"] != "confirmed":
                    logger.warning(f"Transaction might not be confirmed: {confirmation_result}")
            
            # 返回交易签名作为字符串
            return str(tx_sig_value)
            
        except Exception as e:
            logger.error(f"Swap transaction failed: {str(e)}")
            raise ProviderError(f"Jupiter swap failed: {str(e)}") 