from typing import Dict, Optional
from web3 import Web3
from ...core.interfaces import IDexProvider
from ...utils.web3_helper import Web3Helper
from ...config.settings import WALLET_CONFIG
from ...utils.logger import get_logger
from .client import PancakeSwapClient

logger = get_logger(__name__)

class PancakeSwapProvider(IDexProvider):
    """PancakeSwap DEX Provider 实现"""
    
    SUPPORTED_CHAINS = [
        "1",     # Ethereum
        "56",    # BSC
        "1101",  # zkEVM
        "42161", # Arbitrum
        "59144", # Linea
        "8453",  # Base
        "204",   # opBNB
        "324"    # zkSync
    ]
    
    def __init__(self):
        self.chain_id = "56"  # 默认使用 BSC
        self._web3_helper = Web3Helper.get_instance(self.chain_id)
        self._client = PancakeSwapClient(self._web3_helper.web3, self.chain_id)
        self.wallet_config = WALLET_CONFIG["default"]
    
    @property
    def client(self):
        return self._client
    
    def _get_amount_in_wei(self, token_address: str, amount: str) -> str:
        """将代币金额转换为链上精度"""
        try:
            decimals = self._web3_helper.get_token_decimals(token_address)
            return str(self._web3_helper.parse_token_amount(amount, decimals))
        except Exception as e:
            logger.error(f"Failed to convert amount {amount} for token {token_address}: {str(e)}")
            raise

    def get_quote(self, chain_id: str, from_token: str, to_token: str, amount: str, **kwargs) -> Dict:
        """获取报价"""
        try:
            if chain_id not in self.SUPPORTED_CHAINS:
                raise ValueError(f"Unsupported chain ID for PancakeSwap V3: {chain_id}")

            # 如果链ID变化，重新初始化客户端
            if chain_id != self.chain_id:
                self.chain_id = chain_id
                self._web3_helper = Web3Helper.get_instance(chain_id)
                self._client = PancakeSwapClient(self._web3_helper.web3, chain_id)

            raw_amount = self._get_amount_in_wei(from_token, amount)
            
            params = {
                "fromTokenAddress": from_token,
                "toTokenAddress": to_token,
                "amount": raw_amount,
                **kwargs
            }
            
            quote_result = self.client.get_quote(params)
            
            # 获取代币精度并转换为人类可读的数量
            to_decimals = self._web3_helper.get_token_decimals(to_token)
            human_amount = float(quote_result["toAmount"]) / (10 ** to_decimals)
            
            return {
                "fromTokenAddress": from_token,
                "toTokenAddress": to_token,
                "fromAmount": amount,  # 原始输入金额
                "toAmount": quote_result["toAmount"],  # 链上精度的输出金额
                "humanAmount": f"{human_amount:.8f}",
                "estimatedGas": quote_result["estimatedGas"]
            }
            
        except Exception as e:
            logger.error(f"Failed to get quote: {str(e)}")
            raise

    def check_and_approve(self, chain_id: str, token_address: str, 
                         owner_address: str, amount: int) -> Optional[str]:
        """检查并处理代币授权"""
        try:
            spender_address = self.client.router_address
            current_allowance = self._web3_helper.get_allowance(
                token_address, 
                owner_address, 
                spender_address
            )
            
            if current_allowance < amount:
                logger.info(f"Current allowance {current_allowance} is less than required amount {amount}, approving...")
                
                contract = self._web3_helper.web3.eth.contract(
                    address=self._web3_helper.web3.to_checksum_address(token_address),
                    abi=self._web3_helper.abi_helper.get_abi('erc20')
                )
                
                tx_params = {
                    'from': owner_address,
                    'nonce': self._web3_helper.web3.eth.get_transaction_count(owner_address),
                    'gasPrice': self._web3_helper.web3.eth.gas_price,
                }
                
                # 估算 gas
                gas_estimate = contract.functions.approve(
                    spender_address,
                    amount
                ).estimate_gas(tx_params)
                
                tx_params['gas'] = int(gas_estimate * 1.2)  # 增加 20% gas 余量
                
                approve_tx = contract.functions.approve(
                    spender_address,
                    amount
                ).build_transaction(tx_params)
                
                tx_hash = self._web3_helper.send_transaction(
                    approve_tx, 
                    self.wallet_config["private_key"]
                )
                logger.info(f"Approval transaction sent: {tx_hash}")
                return tx_hash
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check and approve: {str(e)}")
            raise

    def swap(self, chain_id: str, from_token: str, to_token: str, amount: str,
             recipient: Optional[str] = None, slippage: str = "0.005", fee: int = 2500, **kwargs) -> str:
        """执行兑换"""
        try:
            if chain_id not in self.SUPPORTED_CHAINS:
                raise ValueError(f"Unsupported chain ID for PancakeSwap V3: {chain_id}")

            # 如果链ID变化，重新初始化客户端
            if chain_id != self.chain_id:
                self.chain_id = chain_id
                self._web3_helper = Web3Helper.get_instance(chain_id)
                self._client = PancakeSwapClient(self._web3_helper.web3, chain_id)

            user_address = self.wallet_config["address"]
            raw_amount = self._get_amount_in_wei(from_token, amount)
            
            # 检查授权 (仅对非 WETH 代币)
            weth = self._client.router_contract.functions.WETH9().call()
            if from_token.lower() != weth.lower():
                approve_tx = self.check_and_approve(
                    chain_id=chain_id,
                    token_address=from_token,
                    owner_address=user_address,
                    amount=int(raw_amount)
                )
                
                if approve_tx:
                    self._web3_helper.wait_for_transaction(approve_tx)

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
            
            swap_data = self.client.get_swap_data(params)
            
            # 发送交易
            transaction = {
                "from": user_address,
                "to": swap_data["to"],
                "value": int(swap_data["value"]),
                "gas": int(swap_data["gas"]),
                "gasPrice": int(swap_data["gasPrice"]),
                "data": swap_data["data"],
                "chainId": int(chain_id),
                "nonce": self._web3_helper.web3.eth.get_transaction_count(user_address)
            }
            
            tx_hash = self._web3_helper.send_transaction(
                transaction, 
                self.wallet_config["private_key"]
            )
            logger.info(f"Swap transaction sent: {tx_hash}")
            return tx_hash
            
        except Exception as e:
            logger.error(f"Failed to execute swap: {str(e)}")
            raise 