from typing import Type, Dict, Any, List
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from .zapper_base import ZapperBase


class TokenPriceToolInput(BaseModel):
    """Input schema for Token Price Data Tool."""
    token_address: str = Field(..., description="Token contract address to fetch price data for")
    network: str = Field("ethereum", description="Blockchain network to query (default: ethereum)")
    days: int = Field(30, description="Number of days of historical data to fetch (default: 30)")


class TokenPriceTool(BaseTool):
    """Tool to fetch token price data from Zapper API."""
    name: str = "Token Price Analysis Tool"
    description: str = (
        "Fetches current and historical price data for a specific token using its contract address. "
        "Provides price trends, market cap, and trading volume information. "
        "Use this to analyze token performance and market trends."
    )
    args_schema: Type[BaseModel] = TokenPriceToolInput
    
    def __init__(self):
        """Initialize the TokenPriceTool with cache."""
        super().__init__()
        self._cache = {}
    
    def _cache_key(self, token_address: str, network: str, days: int) -> str:
        """Generate a cache key based on input parameters."""
        return f"{token_address.lower()}:{network.lower()}:{days}"
    
    def _run(self, token_address: str, network: str = "ethereum", days: int = 30) -> str:
        """Run the token price data retrieval with caching."""
        # Check cache first
        cache_key = self._cache_key(token_address, network, days)
        if cache_key in self._cache:
            return f"[CACHED] {self._cache[cache_key]}"
        
        try:
            # Convert network name to chain ID
            chain_id = ZapperBase.get_chain_id(network)
            
            # Create GraphQL query for fungibleTokenV2
            query = '''
            query TokenPriceData($address: Address!, $chainId: Int!) {
              fungibleTokenV2(address: $address, chainId: $chainId) {
                # Basic token information
                address
                symbol
                name
                decimals
                network {
                  name
                  chainId
                }
                imageUrlV2
                
                # Current price data
                priceData {
                  price
                  priceChange5m
                  priceChange1h
                  priceChange24h
                  priceChange7d
                  priceChange30d
                  marketCap
                  fullyDilutedValuation
                  totalSupply
                  volume24h
                  ath {
                    price
                    timestamp
                  }
                  atl {
                    price
                    timestamp
                  }
                  # Historical price data for chart
                  priceHistory(interval: DAILY, count: 30) {
                    price
                    timestamp
                  }
                }
              }
            }
            '''
            
            # Prepare variables
            variables = {
                "address": token_address,
                "chainId": chain_id
            }
            
            # Execute GraphQL query
            result = ZapperBase.execute_graphql_query(query, variables)
            
            # Format the response
            formatted_result = self._format_price_data(result, token_address)
            
            # Cache the result
            self._cache[cache_key] = formatted_result
            
            return formatted_result
            
        except Exception as e:
            return f"Error fetching token price data: {str(e)}"
    
    def _format_price_data(self, data: Dict[str, Any], token_address: str) -> str:
        """Format token price data into a readable string."""
        if not data or "data" not in data or "fungibleTokenV2" not in data["data"]:
            return f"No price data found for token {token_address}."
        
        # Extract token information
        token_data = data["data"]["fungibleTokenV2"]
        if not token_data:
            return f"No token information available for {token_address}."
        
        # Basic token information
        symbol = token_data.get("symbol", "Unknown")
        name = token_data.get("name", "Unknown Token")
        network_name = token_data.get("network", {}).get("name", "Unknown Network")
        
        # Price data
        price_data = token_data.get("priceData", {})
        current_price = price_data.get("price", 0)
        price_change_24h = price_data.get("priceChange24h", 0)
        price_change_7d = price_data.get("priceChange7d", 0)
        price_change_30d = price_data.get("priceChange30d", 0)
        market_cap = price_data.get("marketCap", 0)
        volume_24h = price_data.get("volume24h", 0)
        
        # All-time high/low data
        ath = price_data.get("ath", {})
        ath_price = ath.get("price", 0)
        
        atl = price_data.get("atl", {})
        atl_price = atl.get("price", 0)
        
        # Calculate price trend from historical data
        price_history = price_data.get("priceHistory", [])
        price_trend = "No historical data available"
        
        if price_history and len(price_history) >= 2:
            start_price = price_history[0].get("price", 0)
            end_price = price_history[-1].get("price", 0)
            
            if start_price:  # Avoid division by zero
                percent_change = ((end_price - start_price) / start_price * 100)
                direction = "increased" if percent_change > 0 else "decreased"
                price_trend = f"Price {direction} by {abs(percent_change):.2f}% over the last {len(price_history)} days"
        
        # Format the full price summary
        summary = [
            f"Token Price Analysis for {name} ({symbol}) on {network_name}:",
            f"Contract: {token_address}",
            f"Current Price: ${current_price:.6f}",
            f"All-time High: ${ath_price:.6f}",
            f"All-time Low: ${atl_price:.6f}",
            f"Price Changes:",
            f"  24h: {price_change_24h:.2f}%",
            f"  7d: {price_change_7d:.2f}%",
            f"  30d: {price_change_30d:.2f}%",
            f"Market Cap: ${market_cap:,.2f}",
            f"24h Trading Volume: ${volume_24h:,.2f}",
            f"Trend: {price_trend}"
        ]
        
        return "\n".join(summary)
