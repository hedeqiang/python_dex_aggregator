from typing import Dict, Optional
from ...core.interfaces import IDexProvider
from ...utils.web3_helper import Web3Helper
from ...config.settings import WALLET_CONFIG, NATIVE_TOKENS
from ...utils.logger import get_logger
from .client import OKXClient

logger = get_logger(__name__)

class OKXProvider(IDexProvider):
    """OKX DEX Provider 实现"""
    
    def __init__(self):
        self._client = OKXClient()
        self.wallet_config = WALLET_CONFIG["default"]
    
    @property
    def client(self):
        return self._client
    
    def _get_web3_helper(self, chain_id: str) -> Web3Helper:
        return Web3Helper.get_instance(chain_id)
    
    def _get_amount_in_wei(self, web3_helper: Web3Helper, token_address: str, amount: str) -> str:
        """将代币金额转换为链上精度"""
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

    def get_quote(self, chain_id: str, from_token: str,  to_token: str, amount: str, **kwargs) -> Dict:
        """获取报价"""
        try:
            web3_helper = self._get_web3_helper(chain_id)
            raw_amount = self._get_amount_in_wei(web3_helper, from_token, amount)
            
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

    def check_and_approve(self, chain_id: str, token_address: str, 
                         owner_address: str, amount: int) -> Optional[str]:
        """检查并处理代币授权"""
        try:
            web3_helper = self._get_web3_helper(chain_id)
            
            approve_data = self.client.get_approve_transaction({
                "chainId": chain_id,
                "tokenContractAddress": token_address,
                "approveAmount": str(amount)
            })
            
            spender_address = approve_data["data"][0]["dexContractAddress"]
            current_allowance = web3_helper.get_allowance(token_address, owner_address, spender_address)
            
            if current_allowance < amount:
                logger.info(f"Current allowance {current_allowance} is less than required amount {amount}, approving...")
                
                contract = web3_helper.web3.eth.contract(
                    address=web3_helper.web3.to_checksum_address(token_address),
                    abi=web3_helper.abi_helper.get_abi('erc20')
                )
                
                tx_params = {
                    'from': owner_address,
                    'nonce': web3_helper.web3.eth.get_transaction_count(owner_address),
                    'gasPrice': int(approve_data["data"][0]["gasPrice"]),
                    'gas': int(approve_data["data"][0]["gasLimit"]),
                }
                
                approve_tx = contract.functions.approve(
                    web3_helper.web3.to_checksum_address(spender_address),
                    amount
                ).build_transaction(tx_params)
                
                tx_hash = web3_helper.send_transaction(approve_tx, self.wallet_config["private_key"])
                logger.info(f"Approval transaction sent: {tx_hash}")
                return tx_hash
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check and approve: {str(e)}")
            raise

    def swap(self, chain_id: str, from_token: str, to_token: str, amount: str,
             recipient_address: Optional[str] = None,slippage: str = "0.03", **kwargs) -> str:
        """执行兑换"""
        try:
            web3_helper = self._get_web3_helper(chain_id)
            user_address = self.wallet_config["address"]
            
            raw_amount = self._get_amount_in_wei(web3_helper, from_token, amount)
            
            if from_token.lower() != "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
                approve_tx = self.check_and_approve(
                    chain_id=chain_id,
                    token_address=from_token,
                    owner_address=user_address,
                    amount=int(raw_amount)
                )
                
                if approve_tx:
                    web3_helper.web3.eth.wait_for_transaction_receipt(approve_tx)
            
            params = {
                "chainId": chain_id,
                "fromTokenAddress": from_token,
                "toTokenAddress": to_token,
                "amount": raw_amount,
                "userWalletAddress": user_address,
                **kwargs
            }

            if recipient_address:
                params["swapReceiverAddress"] = recipient_address
            
            swap_data = self.client.get_swap(params)
            tx_info = swap_data["data"][0]["tx"]
            
            transaction = {
                "nonce": web3_helper.web3.eth.get_transaction_count(user_address),
                "to": tx_info["to"],
                "gasPrice": int(int(tx_info["gasPrice"]) * 1.5),
                "gas": int(int(tx_info["gas"]) * 1.5),
                "data": tx_info["data"],
                "value": int(tx_info["value"]),
                "chainId": int(chain_id)
            }
            
            tx_hash = web3_helper.send_transaction(transaction, self.wallet_config["private_key"])
            logger.info(f"Swap transaction sent: {tx_hash}")
            return tx_hash
            
        except Exception as e:
            logger.error(f"Failed to execute swap: {str(e)}")
            raise 