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
from .client import RaydiumClient
from .constants import WSOL_MINT

logger = get_logger(__name__)

# 常量定义
SOLANA_CHAIN_ID = "501"
SOL_ADDRESS = "11111111111111111111111111111111"
FIXED_GAS_ESTIMATE = "300000"  # Solana固定gas估计值
TX_VERSION_V0 = "V0"
TX_VERSION_V1 = "V1"
SWAP_TYPE_BASE_IN = "swap-base-in"

class RaydiumProvider(IDexProvider):
    """Raydium DEX 交易提供者实现"""
    
    def __init__(self):
        self.wallet_config = WALLET_CONFIG.get("solana", WALLET_CONFIG["default"])
        self.solana_client = Client(WEB3_CONFIG['providers'][SOLANA_CHAIN_ID])
        self._client = RaydiumClient(self.solana_client)
    
    @property
    def client(self):
        return self._client
    
    def _convert_sol_to_wsol(self, token_address: str) -> str:
        """将 SOL 地址转换为 wSOL 地址"""
        return WSOL_MINT if token_address.lower() == SOL_ADDRESS else token_address
    
    def _get_token_decimals(self, token_address: str) -> int:
        """获取代币精度"""
        chain_id = SOLANA_CHAIN_ID
        
        # 处理原生代币 (SOL)
        if token_address.lower() == SOL_ADDRESS:
            if chain_id not in NATIVE_TOKENS:
                raise ValueError(f"不支持的链 ID: {chain_id}")
            return NATIVE_TOKENS[chain_id]["decimals"]
        
        # 获取 SPL 代币精度
        token_pubkey = Pubkey.from_string(token_address)
        token_info = self.solana_client.get_token_supply(token_pubkey)
        if not token_info.value:
            raise ValueError(f"未找到代币 {token_address}")
        return token_info.value.decimals
    
    def get_quote(self, chain_id: str, from_token: str, to_token: str, amount: str, **kwargs) -> Dict:
        """获取兑换报价"""
        if chain_id != SOLANA_CHAIN_ID:
            raise ValueError(f"不支持的链 ID: {chain_id}")
        
        try:
            # 获取代币精度
            from_decimals = self._get_token_decimals(from_token)
            to_decimals = self._get_token_decimals(to_token)
            
            # 转换为链上精度
            raw_amount = str(int(float(amount) * (10 ** from_decimals)))
            
            # 将 SOL 转换为 wSOL
            input_mint = self._convert_sol_to_wsol(from_token)
            output_mint = self._convert_sol_to_wsol(to_token)
            
            # 计算滑点（基点）
            slippage_bps = int(float(kwargs.get("slippage", "0.5")) * 100)
            
            # 从 API 获取原始报价
            quote_response = self.client.get_quote_response(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=raw_amount,
                slippage_bps=slippage_bps
            )
            
            swap_response = quote_response["data"]
            
            # 计算人类可读金额
            human_amount = float(swap_response["outputAmount"]) / (10 ** to_decimals)
            
            return {
                "fromTokenAddress": from_token,
                "toTokenAddress": to_token,
                "fromAmount": amount,
                "toAmount": swap_response["outputAmount"],
                "humanAmount": f"{human_amount:.8f}",
                "estimatedGas": FIXED_GAS_ESTIMATE,  # Solana 固定 gas
                "priceImpact": str(swap_response.get("priceImpactPct", "0")),
                "quoteResponse": quote_response
            }
        except Exception as e:
            logger.error(f"获取报价失败: {str(e)}")
            raise ProviderError(f"获取报价失败: {str(e)}")
    
    def check_and_approve(self, chain_id: str, token_address: str, 
                         owner_address: str, amount: int) -> Optional[str]:
        """检查并处理代币授权
        在 Solana 上不需要，返回 None
        """
        return None
    
    def _prepare_swap_params(self, from_token: str, to_token: str, amount: str, quote_response: Dict, **kwargs) -> Dict:
        """准备兑换交易参数"""
        # 获取优先级费用
        priority_fee = self.client.get_priority_fee()
        
        # 检查代币是否为 SOL
        is_input_sol = from_token.lower() == SOL_ADDRESS
        is_output_sol = to_token.lower() == SOL_ADDRESS
        
        # 将 SOL 转换为 wSOL 以查找代币账户
        input_mint = self._convert_sol_to_wsol(from_token)

        user_address = self.wallet_config["address"]
        # 构建交易参数
        tx_params = {
            "computeUnitPriceMicroLamports": str(priority_fee["h"]),
            "swapResponse": quote_response,
            "txVersion": TX_VERSION_V0,
            "wallet" : user_address
        }
        
        # 处理输入账户
        if not is_input_sol:
            if kwargs.get("inputAccount"):
                tx_params["inputAccount"] = kwargs["inputAccount"]
            else:
                input_account = self.client.get_token_accounts(user_address, input_mint)
                if input_account:
                    tx_params["inputAccount"] = input_account
                else:
                    raise ProviderError(f"未找到 {input_mint} 的输入代币账户")
        else:
            tx_params["wrapSol"] = True

        # 处理输出账户
        if not is_output_sol:
            if kwargs.get("outputAccount"):
                tx_params["outputAccount"] = kwargs["outputAccount"]
        else:
            tx_params["unwrapSol"] = True
            
        return tx_params
    
    def swap(self, chain_id: str, from_token: str, to_token: str, amount: str,
             recipient_address: Optional[str] = None, slippage: str = "0.5", **kwargs) -> Signature:
        """执行兑换交易"""
        try:
            if chain_id != SOLANA_CHAIN_ID:
                raise ValueError(f"不支持的链 ID: {chain_id}")
            
            # 获取带有价格信息的报价
            quote_result = self.get_quote(
                chain_id=chain_id, 
                from_token=from_token, 
                to_token=to_token, 
                amount=amount, 
                slippage=slippage
            )
            
            # 获取代币精度并转换金额
            from_decimals = self._get_token_decimals(from_token)
            raw_amount = str(int(float(amount) * (10 ** from_decimals)))
            
            # 确定是否需要转账到其他地址
            needs_transfer = recipient_address and recipient_address.lower() != self.wallet_config["address"].lower()
            
            # 如果不需要额外转账，使用raydium原生支持的recipient
            if recipient_address and not needs_transfer:
                kwargs["recipient"] = recipient_address
            
            # 准备交易参数
            tx_params = self._prepare_swap_params(
                from_token=from_token,
                to_token=to_token,
                amount=raw_amount,
                quote_response=quote_result["quoteResponse"],
                **kwargs
            )
            
            # 确定兑换类型
            swap_type = SWAP_TYPE_BASE_IN  # 目前始终使用 swap-base-in
            
            # 获取交易数据
            tx_data = self.client.get_swap_transaction(tx_params, swap_type)
            
            if not tx_data["success"]:
                raise ValueError("获取兑换交易数据失败")
                
            # 提取交易信息
            transactions = [tx["transaction"] for tx in tx_data["data"]]
            version = tx_data["version"]

            # 创建并签名交易
            keypair = Keypair.from_bytes(base58.b58decode(self.wallet_config["private_key"]))

            # 处理所有交易
            tx_ids = []
            for tx_base64 in transactions:
                # 解码交易数据
                tx_bytes = base64.b64decode(tx_base64)

                # 根据版本创建交易
                if version in [TX_VERSION_V1, TX_VERSION_V0]:
                    # 创建并签名交易
                    unsigned_tx = VersionedTransaction.from_bytes(tx_bytes)
                    message = unsigned_tx.message
                    signed_tx = VersionedTransaction(message, [keypair])
                    
                    # 发送交易
                    tx_id = self.solana_client.send_transaction(signed_tx)
                    
                    if not tx_id.value:
                        raise ValueError("发送交易失败")
                    
                    tx_ids.append(tx_id.value)
                    
                    # 如果需要转账到其他地址，执行额外的转账交易
                    if needs_transfer and to_token != SOL_ADDRESS:  # 对非SOL代币添加转账指令
                        transfer_tx_id = self._send_transfer_transaction(
                            keypair, 
                            to_token, 
                            recipient_address,
                            quote_result["toAmount"]  # 传递交换得到的金额
                        )
                        if transfer_tx_id:
                            tx_ids.append(transfer_tx_id)
                else:
                    raise ValueError(f"不支持的交易版本: {version}")

            # 返回最后一个交易 ID
            return tx_ids[-1]
        except Exception as e:
            logger.error(f"执行兑换失败: {str(e)}")
            raise ProviderError(f"执行兑换失败: {str(e)}")
            
    def _send_transfer_transaction(self, keypair, token_address, recipient_address, amount):
        """创建并发送单独的转账交易"""
        from spl.token.instructions import get_associated_token_address, transfer, TransferParams, create_associated_token_account
        from solders.message import Message
        import time
        
        try:
            # 获取或创建发送者的token账户
            sender_pubkey = keypair.pubkey()
            token_pubkey = Pubkey.from_string(self._convert_sol_to_wsol(token_address))
            recipient_pubkey = Pubkey.from_string(recipient_address)
            
            # 获取发送者的token账户
            sender_token_account = get_associated_token_address(sender_pubkey, token_pubkey)
            
            # 获取接收者的token账户
            recipient_token_account = get_associated_token_address(recipient_pubkey, token_pubkey)
            
            # 查询token账户是否存在，如果不存在需要先创建
            recipient_account_info = self.solana_client.get_account_info(
                recipient_token_account,
                commitment=None,
                encoding="base64"
            )
            
            # 获取最新的区块哈希
            recent_blockhash = self.solana_client.get_latest_blockhash().value.blockhash
            
            # 创建指令
            instructions = []
            
            # 如果接收者账户不存在，添加创建账户的指令
            if not recipient_account_info.value:
                create_ata_ix = create_associated_token_account(
                    payer=sender_pubkey,
                    owner=recipient_pubkey,
                    mint=token_pubkey
                )
                instructions.append(create_ata_ix)
            
            # 添加转账指令
            token_program_id = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
            
            # 使用TransferParams对象创建转账指令
            transfer_params = TransferParams(
                source=sender_token_account,
                dest=recipient_token_account,
                owner=sender_pubkey,
                amount=int(amount),
                program_id=token_program_id,
                signers=[]
            )
            
            transfer_ix = transfer(transfer_params)
            instructions.append(transfer_ix)
            
            # 创建一个legacy Message
            message = Message.new_with_blockhash(
                instructions=instructions,
                payer=sender_pubkey,
                blockhash=recent_blockhash
            )
            
            # 创建一个VersionedTransaction
            signed_tx = VersionedTransaction(message, [keypair])
            
            # 稍微等待一下，确保前一个交易已经处理
            time.sleep(0.5)
            
            # 发送交易
            tx_id = self.solana_client.send_transaction(signed_tx)
            
            return tx_id.value
            
        except Exception as e:
            logger.error(f"发送转账交易失败: {str(e)}")
            return None 