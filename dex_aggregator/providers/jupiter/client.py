from typing import Dict, Optional, List, Any
import requests
from solana.rpc.api import Client
from solana.rpc.types import TokenAccountOpts
from solders.pubkey import Pubkey
from ...core.exceptions import ProviderError
from ...utils.logger import get_logger
from .constants import API_URLS, WSOL_MINT

logger = get_logger(__name__)

class JupiterClient:
    """Jupiter API Client - Handles HTTP requests"""
    
    def __init__(self, solana_client: Client):
        self.solana_client = solana_client
        self.session = requests.Session()
        
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict:
        """Send HTTP request to Jupiter API"""
        try:
            url = f"{API_URLS['BASE_HOST']}{endpoint}"
            logger.info(f"Making request to {url} with params: {params}")
            
            if method.upper() == "GET":
                response = self.session.get(url, params=params)
            else:
                response = self.session.post(url, json=data)
            
            # 先记录响应，再检查状态码
            logger.info(f"Response: {response.text}")
            
            # 检查 HTTP 状态码
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Jupiter API request failed: {str(e)}")
            raise ProviderError(f"Jupiter API request failed: {str(e)}")
    
    def get_quote(self, input_mint: str, output_mint: str, amount: str, 
                  slippage_bps: int = 50, restrict_intermediate_tokens: bool = True) -> Dict:
        """Get quote from Jupiter API"""
        query_params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
            "slippageBps": slippage_bps
        }
        
        # Jupiter API 期望的是小写字符串形式的布尔值
        query_params["restrictIntermediateTokens"] = "true" if restrict_intermediate_tokens else "false"
        
        quote = self._make_request(
            "GET", 
            API_URLS['QUOTE_API'], 
            params=query_params
        )
        
        logger.info(f"Quote response: {quote}")
        
        if not quote or "outAmount" not in quote:
            raise ProviderError("Failed to get Jupiter quote")
            
        return quote
    
    def build_swap_transaction(self, quote_response: Dict, tx_params: Dict) -> Dict:
        """Build swap transaction using Jupiter API"""
        # 必须传递 quoteResponse 参数
        tx_data = {
            "quoteResponse": quote_response,
            **tx_params
        }
        
        logger.info(f"Building swap transaction with data: {tx_data}")
        
        # Get transaction data from Jupiter API
        response = self._make_request(
            "POST", 
            API_URLS['SWAP_API'], 
            data=tx_data
        )
        
        if not response or "swapTransaction" not in response:
            raise ProviderError("Failed to build Jupiter swap transaction")
            
        return response
    
    def get_token_accounts(self, wallet_address: str, token_mint: str) -> Optional[str]:
        """Get token account address for a wallet"""
        try:
            response = self.solana_client.get_token_accounts_by_owner(
                Pubkey.from_string(wallet_address),
                TokenAccountOpts(mint=Pubkey.from_string(token_mint))
            )
            
            if not response.value or len(response.value) == 0:
                logger.info(f"No token account found for mint {token_mint}")
                return None
            
            return str(response.value[0].pubkey)
        except Exception as e:
            logger.error(f"Failed to get token account: {str(e)}")
            return None
    
    def get_token_decimals(self, token_mint: str) -> int:
        """Get token decimals from Solana RPC"""
        try:
            # For WSOL, we know it's 9 decimals
            if token_mint == WSOL_MINT:
                return 9
                
            token_pubkey = Pubkey.from_string(token_mint)
            token_info = self.solana_client.get_token_supply(token_pubkey)
            
            if not token_info.value:
                raise ValueError(f"Token info not found for {token_mint}")
                
            return token_info.value.decimals
            
        except Exception as e:
            logger.error(f"Failed to get token decimals for {token_mint}: {str(e)}")
            raise ProviderError(f"Failed to get token decimals: {str(e)}") 