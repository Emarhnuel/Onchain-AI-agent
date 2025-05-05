from typing import Type, Dict, Any, List
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from .zapper_base import ZapperBase
from datetime import datetime


class TransactionHistoryToolInput(BaseModel):
    """Input schema for Transaction History Tool."""
    address: str = Field(..., description="Blockchain address to fetch transaction history for")
    network: str = Field("ethereum", description="Blockchain network to query (default: ethereum)")
    limit: int = Field(10, description="Maximum number of transactions to return (default: 10)")


class TransactionHistoryTool(BaseTool):
    """Tool to fetch transaction history data from Zapper API."""
    name: str = "Transaction History Tool"
    description: str = (
        "Fetches human-readable transaction history for a blockchain address, providing "
        "simplified descriptions of complex onchain transactions. Use this to analyze "
        "past activities and identify transaction patterns."
    )
    args_schema: Type[BaseModel] = TransactionHistoryToolInput
    
    def __init__(self):
        """Initialize the TransactionHistoryTool with cache."""
        super().__init__()
        self._cache = {}
    
    def _cache_key(self, address: str, network: str, limit: int) -> str:
        """Generate a cache key based on input parameters."""
        return f"{address.lower()}:{network.lower()}:{limit}"
    
    def _run(self, address: str, network: str = "ethereum", limit: int = 10) -> str:
        """Run the transaction history retrieval with caching."""
        # Check cache first
        cache_key = self._cache_key(address, network, limit)
        if cache_key in self._cache:
            return f"[CACHED] {self._cache[cache_key]}"
        
        try:
            # Convert network name to chain ID (if needed)
            chain_id = None
            if network:  # Only include chainId if network is specified
                chain_id = ZapperBase.get_chain_id(network)
                
            # Create GraphQL query for transactionHistoryV2
            query = '''
            query TransactionHistoryV2($subjects: [Address!]!, $perspective: TransactionHistoryV2Perspective, $first: Int, $filters: TransactionHistoryV2FiltersArgs) {
              transactionHistoryV2(subjects: $subjects, perspective: $perspective, first: $first, filters: $filters) {
                edges {
                  node {
                    ... on TimelineEventV2 {
                      # Transaction metadata
                      transaction {
                        hash
                        network
                        timestamp
                        blockNumber
                        # Sender details with identity
                        fromUser {
                          address
                          displayName {
                            value
                          }
                        }
                        # Recipient details with identity
                        toUser {
                          address
                          displayName {
                            value
                          }
                        }
                      }
                      # Human-readable transaction information
                      interpretation {
                        processedDescription
                      }
                      # Balance changes for the perspective account
                      perspectiveDelta {
                        account {
                          address
                        }
                        # Token balance changes
                        tokenDeltasV2(first: 3) {
                          edges {
                            node {
                              address
                              amount
                              amountRaw
                              token {
                                symbol
                                imageUrlV2
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
            '''
            
            # Prepare variables
            variables = {
                "subjects": [address],
                "perspective": "SIGNER",  # View from the signer's perspective
                "first": limit
            }
            
            # Add filters if a specific network is selected
            if chain_id:
                variables["filters"] = {
                    "networks": [chain_id]
                }
            
            # Execute GraphQL query
            result = ZapperBase.execute_graphql_query(query, variables)
            
            # Format the response
            formatted_result = self._format_transaction_history(result, address)
            
            # Cache the result
            self._cache[cache_key] = formatted_result
            
            return formatted_result
            
        except Exception as e:
            return f"Error fetching transaction history: {str(e)}"
    
    def _format_transaction_history(self, data: Dict[str, Any], address: str) -> str:
        """Format transaction history data into a readable string."""
        if not data or "data" not in data or "transactionHistoryV2" not in data["data"] or not data["data"]["transactionHistoryV2"]["edges"]:
            return "No transaction history found."
        
        edges = data["data"]["transactionHistoryV2"]["edges"]
        if not edges:
            return "No transactions found for this address."
        
        # Format the transaction history
        summary = [f"Transaction History for {address}:\n"]
        
        for idx, edge in enumerate(edges, 1):
            node = edge["node"]
            
            # Extract transaction data
            tx = node.get("transaction", {})
            interpretation = node.get("interpretation", {})
            perspective_delta = node.get("perspectiveDelta", {})
            
            tx_hash = tx.get("hash", "Unknown")
            network_name = tx.get("network", "Unknown")
            
            # Convert timestamp to readable format if it's a millisecond timestamp
            timestamp = tx.get("timestamp")
            if timestamp:
                try:
                    # Convert milliseconds to seconds for datetime
                    time_str = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    time_str = str(timestamp)
            else:
                time_str = "Unknown time"
            
            # Get human-readable description
            description = interpretation.get("processedDescription", "Unknown transaction")
            
            # Extract token deltas if available
            token_deltas = []
            if perspective_delta and "tokenDeltasV2" in perspective_delta and "edges" in perspective_delta["tokenDeltasV2"]:
                for delta_edge in perspective_delta["tokenDeltasV2"]["edges"]:
                    delta_node = delta_edge["node"]
                    symbol = delta_node.get("token", {}).get("symbol", "Unknown")
                    amount = delta_node.get("amount", 0)
                    # Use amount instead of amountUSD since the API schema changed
                    sign = "+" if amount > 0 else ""  # Add plus sign for positive values
                    token_deltas.append(f"{sign}{amount} {symbol}")
            
            # Get from and to addresses with display names if available
            from_address = tx.get("fromUser", {}).get("address", "Unknown")
            from_name = tx.get("fromUser", {}).get("displayName", {}).get("value")
            from_display = f"{from_name} ({from_address})" if from_name else from_address
            
            to_address = tx.get("toUser", {}).get("address", "Unknown")
            to_name = tx.get("toUser", {}).get("displayName", {}).get("value")
            to_display = f"{to_name} ({to_address})" if to_name else to_address
            
            tx_summary = [
                f"Transaction {idx}:",
                f"Hash: {tx_hash}",
                f"Network: {network_name}",
                f"Time: {time_str}",
                f"From: {from_display}",
                f"To: {to_display}",
                f"Description: {description}"
            ]
            
            # Add token changes if available
            if token_deltas:
                tx_summary.append("Token Changes:")
                for delta in token_deltas:
                    tx_summary.append(f"  {delta}")
            
            tx_summary.append("")  # Add a blank line between transactions
            summary.extend(tx_summary)
        
        # Add pagination info if available
        page_info = data["data"]["transactionHistoryV2"].get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        if has_next:
            summary.append("\nMore transactions are available. Increase the limit parameter to see more.")
        
        return "\n".join(summary)
