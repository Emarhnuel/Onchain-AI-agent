from typing import Type, Dict, Any, List
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from .zapper_base import ZapperBase


class TokenPriceToolInput(BaseModel):
    """Input schema for Token Price Data Tool."""
    token_address: str = Field(..., description="Token contract address to fetch price data for")
    network: str = Field("ethereum", description="Blockchain network to query (default: ethereum)")
    days: int = Field(30, description="Number of days of historical data to fetch (default: 30)")
    currency: str = Field("USD", description="Currency for price data (default: USD)")


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
    
    def _map_days_to_timeframe(self, days: int) -> str:
        """Maps number of days to the appropriate TimeFrame enum value."""
        if days <= 1:
            return "HOUR"
        elif days <= 7:
            return "DAY"
        elif days <= 30:
            return "WEEK"
        elif days <= 365:
            return "MONTH"
        else:
            return "YEAR"
    
    def _run(self, token_address: str, network: str = "ethereum", days: int = 30, currency: str = "USD") -> str:
        """Run the token price data retrieval with caching."""
        # Check cache first
        cache_key = self._cache_key(token_address, network, days)
        if cache_key in self._cache:
            return f"[CACHED] {self._cache[cache_key]}"
        
        try:
            # Convert network name to chain ID
            chain_id = ZapperBase.get_chain_id(network)
            
            # Map days to appropriate timeframe
            time_frame = self._map_days_to_timeframe(days)
            
            # Create GraphQL query for fungibleTokenV2
            query = '''
            query TokenPriceData($address: Address!, $chainId: Int!, $currency: Currency!, $timeFrame: TimeFrame!) {
              fungibleTokenV2(address: $address, chainId: $chainId) {
                # Basic token information
                address
                symbol
                name
                decimals
                imageUrlV2
                
                # Market data and pricing information
                priceData {
                  marketCap
                  price
                  priceChange5m
                  priceChange1h
                  priceChange24h
                  volume24h
                  totalGasTokenLiquidity
                  totalLiquidity
                  
                  # Historical price data for charts
                  priceTicks(currency: $currency, timeFrame: $timeFrame) {
                    open
                    median
                    close
                    timestamp
                  }
                }
              }
            }
            '''
            
            # Prepare variables
            variables = {
                "address": token_address,
                "chainId": chain_id,
                "currency": currency.upper(),
                "timeFrame": time_frame
            }
            
            # Execute GraphQL query
            result = ZapperBase.execute_graphql_query(query, variables)
            
            # Format the response
            formatted_result = self._format_price_data(result, token_address)
            
            # Cache the result
            self._cache[cache_key] = formatted_result
            
            return formatted_result
            
        except Exception as e:
            error_details = f"Error type: {type(e).__name__}, Error message: {str(e)}"
            return f"Error fetching token price data: {error_details}"
    
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
        
        # Extract chain/network from the response or use address format
        chain_info = ""
        if token_address.startswith("0x"):
            chain_info = "on Ethereum"  # Default if can't determine
        
        # Price data
        price_data = token_data.get("priceData", {})
        current_price = float(price_data.get("price", 0))
        price_change_24h = float(price_data.get("priceChange24h", 0))
        price_change_1h = float(price_data.get("priceChange1h", 0))
        price_change_5m = float(price_data.get("priceChange5m", 0))
        market_cap = float(price_data.get("marketCap", 0))
        volume_24h = float(price_data.get("volume24h", 0))
        total_liquidity = float(price_data.get("totalLiquidity", 0))
        
        # Calculate price trend from price ticks
        price_ticks = price_data.get("priceTicks", [])
        price_trend = "No historical data available"
        
        if price_ticks and len(price_ticks) >= 2:
            start_price = float(price_ticks[0].get("close", 0))
            end_price = float(price_ticks[-1].get("close", 0))
            
            if start_price > 0:  # Avoid division by zero
                percent_change = ((end_price - start_price) / start_price * 100)
                direction = "increased" if percent_change > 0 else "decreased"
                price_trend = f"Price {direction} by {abs(percent_change):.2f}% over the analyzed period"
        
        # Format the full price summary
        summary = [
            f"Token Price Analysis for {name} ({symbol}) {chain_info}:",
            f"Contract: {token_address}",
            f"Current Price: ${current_price:.6f}",
            f"Price Changes:",
            f"  5min: {price_change_5m:.2f}%",
            f"  1h: {price_change_1h:.2f}%",
            f"  24h: {price_change_24h:.2f}%",
            f"Market Cap: ${market_cap:,.2f}",
            f"24h Trading Volume: ${volume_24h:,.2f}",
            f"Total Liquidity: ${total_liquidity:,.2f}",
            f"Trend: {price_trend}"
        ]
        
        return "\n".join(summary)
