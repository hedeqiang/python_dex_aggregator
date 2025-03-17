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

class RaydiumProvider(IDexProvider):
    """Raydium DEX Provider implementation"""
    
    SOLANA_CHAIN_ID = "501"
    
    def __init__(self):
        self.wallet_config = WALLET_CONFIG.get("solana", WALLET_CONFIG["default"])
        self.solana_client = Client(WEB3_CONFIG['providers'][self.SOLANA_CHAIN_ID])
        self._client = RaydiumClient(self.solana_client)
    
    @property
    def client(self):
        return self._client
    
    def _convert_sol_to_wsol(self, token_address: str) -> str:
        """Convert SOL address to wSOL address"""
        return WSOL_MINT if token_address.lower() == "11111111111111111111111111111111" else token_address
    
    def _get_token_decimals(self, token_address: str) -> int:
        """Get token decimals"""
        chain_id = self.SOLANA_CHAIN_ID
        
        # Handle native token (SOL)
        if token_address.lower() == "11111111111111111111111111111111":
            if chain_id not in NATIVE_TOKENS:
                raise ValueError(f"Unsupported chain ID: {chain_id}")
            return NATIVE_TOKENS[chain_id]["decimals"]
        
        # Get SPL token decimals
        token_pubkey = Pubkey.from_string(token_address)
        token_info = self.solana_client.get_token_supply(token_pubkey)
        if not token_info.value:
            raise ValueError(f"Token {token_address} not found")
        return token_info.value.decimals
    
    def get_quote(self, chain_id: str, from_token: str, to_token: str, amount: str, **kwargs) -> Dict:
        """Get swap quote"""
        if chain_id != self.SOLANA_CHAIN_ID:
            raise ValueError(f"Unsupported chain ID: {chain_id}")
        
        try:
            # Get token decimals
            from_decimals = self._get_token_decimals(from_token)
            to_decimals = self._get_token_decimals(to_token)
            
            # Convert to on-chain precision
            raw_amount = str(int(float(amount) * (10 ** from_decimals)))
            
            # Convert SOL to wSOL
            input_mint = self._convert_sol_to_wsol(from_token)
            output_mint = self._convert_sol_to_wsol(to_token)
            
            # Calculate slippage in basis points
            slippage_bps = int(float(kwargs.get("slippage", "0.5")) * 100)
            
            # Get raw quote from API
            quote_response = self.client.get_quote_response(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=raw_amount,
                slippage_bps=slippage_bps
            )
            
            swap_response = quote_response["data"]
            
            # Calculate human-readable amount
            human_amount = float(swap_response["outputAmount"]) / (10 ** to_decimals)
            
            return {
                "fromTokenAddress": from_token,
                "toTokenAddress": to_token,
                "fromAmount": amount,
                "toAmount": swap_response["outputAmount"],
                "humanAmount": f"{human_amount:.8f}",
                "estimatedGas": "300000",  # Fixed gas for Solana
                "priceImpact": str(swap_response.get("priceImpactPct", "0")),
                "quoteResponse": quote_response
            }
        except Exception as e:
            logger.error(f"Failed to get quote: {str(e)}")
            raise ProviderError(f"Failed to get quote: {str(e)}")
    
    def check_and_approve(self, chain_id: str, token_address: str, 
                         owner_address: str, amount: int) -> Optional[str]:
        """Check and handle token approval
        Not needed on Solana, return None
        """
        return None
    
    def _prepare_swap_params(self, from_token: str, to_token: str, amount: str, quote_response: Dict, **kwargs) -> Dict:
        """Prepare parameters for swap transaction"""
        # Get priority fee
        priority_fee = self.client.get_priority_fee()
        
        # Check if tokens are SOL
        is_input_sol = from_token.lower() == "11111111111111111111111111111111"
        is_output_sol = to_token.lower() == "11111111111111111111111111111111"
        
        # Convert SOL to wSOL for finding token accounts
        input_mint = self._convert_sol_to_wsol(from_token)

        user_address = self.wallet_config["address"]
        # Build transaction parameters
        tx_params = {
            "computeUnitPriceMicroLamports": str(priority_fee["h"]),
            "swapResponse": quote_response,
            "txVersion": "V0",
            # "wallet" : kwargs['recipient_address']
            "wallet" : user_address  # TODO: 不理解
        }
        
        # Handle input account
        if not is_input_sol:
            if kwargs.get("inputAccount"):
                tx_params["inputAccount"] = kwargs["inputAccount"]
            else:
                input_account = self.client.get_token_accounts(user_address, input_mint)
                if input_account:
                    tx_params["inputAccount"] = input_account
                else:
                    raise ProviderError(f"No input token account found for {input_mint}")
        else:
            tx_params["wrapSol"] = True

        # Handle output account
        if not is_output_sol:
            if kwargs.get("outputAccount"):
                tx_params["outputAccount"] = kwargs["outputAccount"]
            else:
                output_account = self.client.get_token_accounts(kwargs['recipient_address'], to_token)
                if output_account:
                    tx_params["outputAccount"] = output_account
                else:
                    raise ProviderError(f"No output token account found for {to_token}")
        else:
            tx_params["unwrapSol"] = True
            
        return tx_params
    
    def swap(self, chain_id: str, from_token: str, to_token: str, amount: str,
             recipient_address: Optional[str] = None, slippage: str = "0.5", **kwargs) -> Signature:
        """Execute swap"""
        try:
            if chain_id != self.SOLANA_CHAIN_ID:
                raise ValueError(f"Unsupported chain ID: {chain_id}")
            
            # Get quote with pricing info
            quote_result = self.get_quote(
                chain_id=chain_id, 
                from_token=from_token, 
                to_token=to_token, 
                amount=amount, 
                slippage=slippage
            )
            
            # Get token decimals and convert amount
            from_decimals = self._get_token_decimals(from_token)
            raw_amount = str(int(float(amount) * (10 ** from_decimals)))
            
            # Prepare transaction parameters

            tx_params = self._prepare_swap_params(
                from_token=from_token,
                to_token=to_token,
                amount=raw_amount,
                quote_response=quote_result["quoteResponse"],
                recipient_address=recipient_address,
                **kwargs
            )
            
            # Determine swap type
            swap_type = "swap-base-in"  # Always use swap-base-in for now
            
            # Get transaction data
            tx_data = self.client.get_swap_transaction(tx_params, swap_type)
            
            if not tx_data["success"]:
                raise ValueError("Failed to get swap transaction data")
                
            # Extract transaction information
            transactions = [tx["transaction"] for tx in tx_data["data"]]
            version = tx_data["version"]

            # Create and sign transaction
            keypair = Keypair.from_bytes(base58.b58decode(self.wallet_config["private_key"]))

            # Process all transactions
            tx_ids = []
            for tx_base64 in transactions:
                # Decode transaction data
                tx_bytes = base64.b64decode(tx_base64)

                # Create transaction based on version
                if version in ["V1", "V0"]:
                    unsigned_tx = VersionedTransaction.from_bytes(tx_bytes)
                    message = unsigned_tx.message
                    signed_tx = VersionedTransaction(message, [keypair])
                    tx_id = self.solana_client.send_transaction(signed_tx)
                else:
                    raise ValueError(f"Unsupported transaction version: {version}")

                if not tx_id.value:
                    raise ValueError("Failed to send transaction")

                tx_ids.append(tx_id.value)

            # Return the last transaction ID
            return tx_ids[-1]
        except Exception as e:
            logger.error(f"Failed to execute swap: {str(e)}")
            raise ProviderError(f"Failed to execute swap: {str(e)}") 