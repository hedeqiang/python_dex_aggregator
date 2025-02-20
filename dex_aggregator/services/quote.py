from typing import Dict
from dex_aggregator.providers.okx.client import OKXClient
from dex_aggregator.utils.web3_helper import Web3Helper
from dex_aggregator.utils.logger import get_logger
from dex_aggregator.config.settings import NATIVE_TOKENS

logger = get_logger(__name__)


class QuoteService:
    def __init__(self):
        self.okx_client = OKXClient()

    def get_quote(self, chain_id: str, from_token: str, to_token: str, amount: str, **kwargs) -> Dict:
        """
        获取兑换询价
        
        Args:
            chain_id: 链ID
            from_token: 源代币地址
            to_token: 目标代币地址
            amount: 兑换数量（带精度的字符串，如"0.001"）
            **kwargs: 其他参数
            
        Returns:
            Dict: 询价结果
        """
        try:
            web3_helper = Web3Helper.get_instance(chain_id)
            
            # 处理原生代币的情况
            if from_token.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
                if chain_id not in NATIVE_TOKENS:
                    raise ValueError(f"Unsupported chain ID: {chain_id}")
                token_info = NATIVE_TOKENS[chain_id]
                decimals = token_info["decimals"]
                symbol = token_info["symbol"]
            else:
                # 只获取decimals
                decimals = web3_helper.get_token_decimals(from_token)
                try:
                    contract = web3_helper.web3.eth.contract(
                        address=web3_helper.web3.to_checksum_address(from_token),
                        abi=web3_helper.abi_helper.get_abi('erc20')
                    )
                    symbol = contract.functions.symbol().call()
                except:
                    symbol = from_token[:8]
            
            raw_amount = web3_helper.parse_token_amount(amount, decimals)
            
            params = {
                "chainId": chain_id,
                "fromTokenAddress": from_token,
                "toTokenAddress": to_token,
                "amount": str(raw_amount),
                **kwargs
            }

            quote_result = self.okx_client.get_quote(params)
            logger.info(f"Got quote for {amount} {symbol} to {to_token}")
            return quote_result

        except Exception as e:
            logger.error(f"Failed to get quote: {str(e)}")
            raise
