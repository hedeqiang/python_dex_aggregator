from typing import Dict, Optional
import requests
from solana.rpc.api import Client
from solana.rpc.types import TokenAccountOpts
from solders.pubkey import Pubkey
from ...core.exceptions import ProviderError
from ...utils.logger import get_logger
from .constants import API_URLS

logger = get_logger(__name__)

class RaydiumClient:
    """Raydium API Client - Handles HTTP requests only"""
    
    def __init__(self, solana_client: Client):
        self.solana_client = solana_client
        self.session = requests.Session()
        
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Send HTTP request to Raydium API"""
        try:
            base_url = API_URLS["SWAP_HOST"] if endpoint.startswith(("/compute", "/transaction")) else API_URLS["BASE_HOST"]
            url = f"{base_url}{endpoint}"
            
            if method.upper() == "GET":
                response = self.session.get(url, params=params)
            else:
                response = self.session.post(url, json=params)
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise ProviderError(f"API request failed: {str(e)}")

    def get_priority_fee(self) -> Dict:
        """Get priority fee"""
        response = self._make_request("GET", API_URLS["PRIORITY_FEE"])
        if not response or "data" not in response:
            raise ProviderError("Failed to get priority fee")
        return response["data"]["default"]
    
    def get_pool_info(self, pool_id: str) -> Dict:
        """Get liquidity pool info"""
        response = self._make_request("GET", API_URLS["POOL_SEARCH_BY_ID"], {"ids": pool_id})
        if not response or "data" not in response:
            raise ProviderError(f"Pool {pool_id} not found")
        return response["data"][0]
            
    def get_quote_response(self, input_mint: str, output_mint: str, amount: str, slippage_bps: int, tx_version: str = "V0") -> Dict:
        """Get raw quote API response"""
        query_params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
            "slippageBps": slippage_bps,
            "txVersion": tx_version
        }
        
        # Determine transaction type based on params
        swap_type = "swap-base-in"  # Default to swap-base-in
        
        # Get quote
        quote = self._make_request("GET", f"/compute/{swap_type}", query_params)
        logger.info(f"Quote response: {quote}")
        
        if not quote or "data" not in quote:
            raise ProviderError("Failed to get quote")
            
        return quote
            
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

    def get_swap_transaction(self, tx_params: Dict, swap_type: str = "swap-base-in") -> Dict:
        """Get raw swap transaction data"""
        logger.info(f"Sending swap request: {swap_type} {tx_params}")
        tx_data = self._make_request("POST", f"/transaction/{swap_type}", tx_params)
        logger.info(f"Transaction response: {tx_data}")
        
        if not tx_data or not tx_data.get("success", False):
            error_msg = tx_data.get("msg", "Unknown error") if tx_data else "No response"
            raise ProviderError(f"Failed to get transaction data: {error_msg}")
            
        return tx_data 