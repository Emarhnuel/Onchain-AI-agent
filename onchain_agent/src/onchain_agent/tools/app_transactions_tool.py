from typing import Type, Dict, Any, List
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from .zapper_base import ZapperBase
from datetime import datetime


class AppTransactionsToolInput(BaseModel):
    """Input schema for App Transactions Tool."""
    app_id: str = Field(..., description="App identifier (slug) to fetch transactions for")
    network: str = Field("ethereum", description="Blockchain network to query (default: ethereum)")
    limit: int = Field(10, description="Maximum number of transactions to return (default: 10)")


class AppTransactionsTool(BaseTool):
    """Tool to fetch app-specific transaction data from Zapper API."""
    name: str = "App Transactions Tool"
    description: str = (
        "Fetches transactions interacting with a specific protocol or dapp. "
        "Provides insights into how users are interacting with particular blockchain applications. "
        "Use this to monitor activity patterns on specific protocols."
    )
    args_schema: Type[BaseModel] = AppTransactionsToolInput
    
    def __init__(self):
        """Initialize the AppTransactionsTool with cache."""
        super().__init__()
        self._cache = {}
    
    def _cache_key(self, app_id: str, network: str, limit: int) -> str:
        """Generate a cache key based on input parameters."""
        return f"{app_id.lower()}:{network.lower()}:{limit}"
    
    def _run(self, app_id: str, network: str = "ethereum", limit: int = 10) -> str:
        """Run the app transactions retrieval with caching."""
        # Check cache first
        cache_key = self._cache_key(app_id, network, limit)
        if cache_key in self._cache:
            return f"[CACHED] {self._cache[cache_key]}"
        
        try:
            # Convert network name to chain ID (if needed)
            chain_id = None
            if network:  # Only include chainId if network is specified
                chain_id = ZapperBase.get_chain_id(network)

            # Create GraphQL query for transactionsForAppV2
            query = '''
            query TransactionsForAppV2($slug: String!, $chainId: Int, $first: Int) {
              transactionsForAppV2(slug: $slug, chainId: $chainId, first: $first) {
                edges {
                  node {
                    transaction {
                      hash
                      timestamp
                      blockNumber
                      fromUser {
                        address
                        displayName {
                          value
                        }
                      }
                      toUser {
                        address
                        displayName {
                          value
                        }
                      }
                    }
                    app {
                      name
                      imgUrl
                    }
                    interpretation {
                      processedDescription
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
                "slug": app_id,
                "first": limit
            }
            
            # Add chainId if specified
            if chain_id is not None:
                variables["chainId"] = chain_id
            
            # Execute GraphQL query
            result = ZapperBase.execute_graphql_query(query, variables)
            
            # Format the response
            formatted_result = self._format_app_transactions(result, app_id)
            
            # Cache the result
            self._cache[cache_key] = formatted_result
            
            return formatted_result
            
        except Exception as e:
            return f"Error fetching app transactions: {str(e)}"
    
    def _format_app_transactions(self, data: Dict[str, Any], app_id: str) -> str:
        """Format app transactions data into a readable string."""
        if not data or "data" not in data or "transactionsForAppV2" not in data["data"] or not data["data"]["transactionsForAppV2"]["edges"]:
            return f"No transactions found for app {app_id}."
        
        edges = data["data"]["transactionsForAppV2"]["edges"]
        if not edges:
            return f"No recent transactions found for app {app_id}."
        
        # Format the app transactions
        summary = [f"Recent Transactions for App {app_id}:\n"]
        
        for idx, edge in enumerate(edges, 1):
            node = edge["node"]
            tx = node["transaction"]
            interpretation = node["interpretation"]
            
            tx_hash = tx.get("hash", "Unknown")
            
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
                
            description = interpretation.get("processedDescription", "Unknown transaction")
            
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
                f"Time: {time_str}",
                f"From: {from_display}",
                f"To: {to_display}",
                f"Description: {description}",
                ""
            ]
            
            summary.extend(tx_summary)
        
        # Add pagination info if available
        page_info = data["data"]["transactionsForAppV2"].get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        if has_next:
            summary.append("\nMore transactions are available. Increase the limit parameter to see more.")
        
        return "\n".join(summary)
