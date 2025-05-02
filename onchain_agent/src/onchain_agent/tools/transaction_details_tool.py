from typing import Type, Dict, Any, List, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from .zapper_base import ZapperBase
from datetime import datetime


class TransactionDetailsToolInput(BaseModel):
    """Input schema for Transaction Details Tool."""
    transaction_hash: str = Field(..., description="Transaction hash to fetch details for")
    network: str = Field("ethereum", description="Blockchain network to query (default: ethereum)")


class TransactionDetailsTool(BaseTool):
    """Tool to fetch detailed transaction data from Zapper API."""
    name: str = "Transaction Details Tool"
    description: str = (
        "Fetches detailed information about a specific transaction including metadata, "
        "asset transfers, and human-readable descriptions. Use this to deeply analyze "
        "individual transactions and understand complex DeFi operations."
    )
    args_schema: Type[BaseModel] = TransactionDetailsToolInput
    
    def __init__(self):
        """Initialize the TransactionDetailsTool with cache."""
        super().__init__()
        self._cache = {}
    
    def _cache_key(self, transaction_hash: str, network: str) -> str:
        """Generate a cache key based on input parameters."""
        return f"{transaction_hash.lower()}:{network.lower()}"
    
    def _run(self, transaction_hash: str, network: str = "ethereum") -> str:
        """Run the transaction details retrieval with caching."""
        # Check cache first
        cache_key = self._cache_key(transaction_hash, network)
        if cache_key in self._cache:
            return f"[CACHED] {self._cache[cache_key]}"
        
        try:
            # Convert network name to chain ID
            chain_id = ZapperBase.get_chain_id(network)
            
            # Create GraphQL query for transactionV2
            query = '''
            query TransactionDetails($hash: String!, $chainId: Int!) {
              transactionV2(hash: $hash, chainId: $chainId) {
                # Basic transaction information
                hash
                status
                blockNumber
                timestamp
                nonce
                gasUsed
                gasPrice
                maxFeePerGas
                maxPriorityFeePerGas
                from {
                  address
                }
                to {
                  address
                }
                
                # Transaction fee
                fee {
                  value
                  currency
                }
                
                # Human-readable description
                processedData {
                  description
                  actionCategory
                }
                
                # Token transfers
                transfers {
                  from
                  to
                  type
                  token {
                    address
                    name
                    symbol
                    decimals
                  }
                  value
                  valueUSD
                }
              }
            }
            '''
            
            # Prepare variables
            variables = {
                "hash": transaction_hash,
                "chainId": chain_id
            }
            
            # Execute GraphQL query
            result = ZapperBase.execute_graphql_query(query, variables)
            
            # Format the response
            formatted_result = self._format_transaction_details(result, transaction_hash, network)
            
            # Cache the result
            self._cache[cache_key] = formatted_result
            
            return formatted_result
            
        except Exception as e:
            return f"Error fetching transaction details: {str(e)}"
    
    def _format_timestamp(self, timestamp: Optional[int]) -> str:
        """Format a Unix timestamp to a human-readable date and time."""
        if not timestamp:
            return "Unknown time"
        
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return "Invalid timestamp"
    
    def _format_transaction_details(self, data: Dict[str, Any], transaction_hash: str, network: str) -> str:
        """Format transaction details into a readable string."""
        if not data or "data" not in data or "transactionV2" not in data["data"] or not data["data"]["transactionV2"]:
            return f"No details found for transaction {transaction_hash} on {network}."
        
        tx_data = data["data"]["transactionV2"]
        
        # Extract basic transaction information
        status = tx_data.get("status", "Unknown")
        block_number = tx_data.get("blockNumber")
        timestamp = self._format_timestamp(tx_data.get("timestamp"))
        nonce = tx_data.get("nonce", "Unknown")
        
        from_address = tx_data.get("from", {}).get("address", "Unknown")
        to_address = tx_data.get("to", {}).get("address", "Unknown")
        
        # Gas information
        gas_used = tx_data.get("gasUsed", 0)
        gas_price = tx_data.get("gasPrice", 0)
        
        # Transaction fee
        fee_data = tx_data.get("fee", {})
        fee_value = fee_data.get("value", 0)
        fee_currency = fee_data.get("currency", "ETH")
        
        # Description
        processed_data = tx_data.get("processedData", {})
        description = processed_data.get("description", "Unknown transaction")
        action_category = processed_data.get("actionCategory", "Unknown action")
        
        # Extract asset transfers if available
        transfers = tx_data.get("transfers", [])
        transfer_details = []
        
        for transfer in transfers:
            token = transfer.get("token", {})
            token_name = token.get("name", "Unknown Token")
            token_symbol = token.get("symbol", "")
            value = transfer.get("value", 0)
            value_usd = transfer.get("valueUSD", 0)
            transfer_type = transfer.get("type", "Unknown")
            from_addr = transfer.get("from", "Unknown")
            to_addr = transfer.get("to", "Unknown")
            
            # Format the transfer details
            transfer_str = f"{transfer_type}: {value} {token_name}"
            if token_symbol:
                transfer_str += f" ({token_symbol})"
            
            if value_usd:
                transfer_str += f" (${value_usd:.2f})"
                
            transfer_str += f" from {from_addr[:8]}... to {to_addr[:8]}..."
            transfer_details.append(transfer_str)
        
        # Format the full transaction details
        summary = [
            f"Transaction Details for {transaction_hash} on {network.upper()}:\n",
            f"Status: {status}",
            f"Block: {block_number}",
            f"Time: {timestamp}",
            f"From: {from_address}",
            f"To: {to_address}",
            f"Nonce: {nonce}",
            f"Action: {action_category}",
            f"Description: {description}",
            f"Gas Used: {gas_used:,}",
            f"Gas Price: {float(gas_price) / 1e9:.2f} Gwei",
            f"Transaction Fee: {fee_value} {fee_currency}",
            "\nToken Transfers:"
        ]
        
        if transfer_details:
            summary.extend(transfer_details)
        else:
            summary.append("No token transfers found in this transaction")
        
        return "\n".join(summary)
