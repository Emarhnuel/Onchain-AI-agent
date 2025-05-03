from typing import Type, Dict, Any, List, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from .zapper_base import ZapperBase


class SearchToolInput(BaseModel):
    """Input schema for Zapper Search Tool."""
    query: str = Field(..., description="Search query string")
    entity_types: str = Field("all", description="Comma-separated list of entity types to search (default: all)")
    networks: Optional[str] = Field(None, description="Optional comma-separated list of networks to search")
    limit: int = Field(10, description="Maximum number of results to return (default: 10)")


class SearchTool(BaseTool):
    """Tool to search across multiple entity types and networks using Zapper API."""
    name: str = "Onchain Search Tool"
    description: str = (
        "Performs a unified search across tokens, NFTs, apps, and accounts across multiple blockchain networks. "
        "Use this to find specific entities when you have partial information. Supports searching by name, "
        "symbol, or address fragments."
    )
    args_schema: Type[BaseModel] = SearchToolInput
    
    def __init__(self):
        """Initialize the SearchTool with cache."""
        super().__init__()
        self._cache = {}
    
    def _cache_key(self, query: str, entity_types: str, networks: Optional[str], limit: int) -> str:
        """Generate a cache key based on input parameters."""
        networks_key = networks or "all"
        return f"{query.lower()}:{entity_types}:{networks_key}:{limit}"
    
    def _run(self, query: str, entity_types: str = "all", networks: Optional[str] = None, limit: int = 10) -> str:
        """Run the search with caching."""
        # Check cache first
        cache_key = self._cache_key(query, entity_types, networks, limit)
        if cache_key in self._cache:
            return f"[CACHED] {self._cache[cache_key]}"
        
        try:
            # Prepare entity types list
            entity_types_list = []
            if entity_types.lower() != "all":
                # Convert entity types to uppercase for API
                for entity_type in entity_types.split(","):
                    et = entity_type.strip().upper()
                    if et == "TOKEN" or et == "TOKENS":
                        entity_types_list.append("UNIFIED_ERC20_TOKEN")
                    elif et == "NFT" or et == "NFTS":
                        entity_types_list.append("NFT_COLLECTION")
                    elif et == "APP" or et == "APPS" or et == "PROTOCOL" or et == "PROTOCOLS":
                        entity_types_list.append("APP")
                    elif et == "ACCOUNT" or et == "ACCOUNTS" or et == "WALLET" or et == "WALLETS":
                        entity_types_list.append("USER")
            else:
                # If "all", include all valid entity types
                entity_types_list = ["UNIFIED_ERC20_TOKEN", "USER", "APP", "NFT_COLLECTION"]
            
            # Prepare network IDs if specified
            network_ids = []
            if networks:
                network_list = [n.strip() for n in networks.split(",")]
                for network in network_list:
                    chain_id = ZapperBase.get_chain_id(network)
                    network_ids.append(chain_id)
            
            # Create GraphQL query for searchV2 using the correct structure
            query_str = '''
            query SearchV2($input: SearchInputV2!) {
              searchV2(input: $input) {
                results {
                  __typename
                  # Token fields
                  ... on UnifiedErc20TokenResult {
                    category
                    name
                    symbol
                    imageUrl
                    groupedFungibleTokens {
                      address
                      networkV2 {
                        chainId
                        name
                      }
                      priceData {
                        price
                        priceChange24h
                      }
                    }
                  }
                  # User fields
                  ... on UserResult {
                    category
                    address
                    account {
                      displayName {
                        value
                      }
                      # Balance field removed as it's no longer available
                    }
                  }
                  # App fields
                  ... on AppResult {
                    category
                    appId
                    app {
                      displayName
                      url
                      imgUrl
                    }
                  }
                  # NFT fields
                  ... on NftCollectionResult {
                    category
                    address
                    network
                    collection {
                      displayName
                      symbol
                      floorPrice {
                        valueUsd
                      }
                    }
                  }
                }
              }
            }
            '''
            
            # Prepare input variables for the query
            variables = {
                "input": {
                    "search": query,
                    "categories": entity_types_list,
                    "maxResultsPerCategory": limit
                }
            }
            
            # Add networks to filter if specified
            if network_ids:
                variables["input"]["chainIds"] = network_ids
            
            # Execute GraphQL query
            result = ZapperBase.execute_graphql_query(query_str, variables)
            
            # Format the response
            formatted_result = self._format_search_results(result, query)
            
            # Cache the result
            self._cache[cache_key] = formatted_result
            
            return formatted_result
            
        except Exception as e:
            error_details = f"Error type: {type(e).__name__}, Error message: {str(e)}"
            return f"Error performing search: {error_details}"
    
    def _format_search_results(self, data: Dict[str, Any], query: str) -> str:
        """Format search results into a readable string."""
        if not data or "data" not in data or "searchV2" not in data["data"] or not data["data"]["searchV2"]["results"]:
            return f"No search results found for query: {query}"
        
        results = data["data"]["searchV2"]["results"]
        
        # Format the search results
        summary = [f"Search Results for '{query}':\n"]
        results_found = False
        
        # Group results by type using __typename
        tokens = []
        users = []
        apps = []
        nfts = []
        
        for result in results:
            # Use __typename for primary type identification
            result_type = result.get("__typename")
            # Fall back to category if available
            category = result.get("category")
            
            if result_type == "UnifiedErc20TokenResult":
                tokens.append(result)
            elif result_type == "UserResult":
                users.append(result)
            elif result_type == "AppResult":
                apps.append(result)
            elif result_type == "NftCollectionResult":
                nfts.append(result)
        
        # Process token results
        if tokens:
            results_found = True
            summary.append("TOKENS:")
            for idx, token in enumerate(tokens, 1):
                name = token.get("name", "Unknown")
                symbol = token.get("symbol", "")
                grouped_tokens = token.get("groupedFungibleTokens", [])
                
                if grouped_tokens:
                    token_data = grouped_tokens[0]  # Get first token instance
                    address = token_data.get("address", "Unknown")
                    network_info = token_data.get("networkV2", {})
                    network_name = network_info.get("name", "Unknown")
                    price_data = token_data.get("priceData", {})
                    price = price_data.get("price", 0)
                    price_change = price_data.get("priceChange24h", 0)
                    
                    # Ensure values are properly converted to float
                    price = float(price) if price is not None else 0.0
                    price_change = float(price_change) if price_change is not None else 0.0
                    
                    summary.append(f"{idx}. {name} ({symbol})")
                    summary.append(f"   Price: ${price:.6f} (24h change: {price_change:.2f}%)")
                    summary.append(f"   Address: {address} on {network_name}")
                    summary.append("")
                else:
                    summary.append(f"{idx}. {name} ({symbol})")
                    summary.append(f"   No detailed price data available")
                    summary.append("")
            
            summary.append("")
        
        # Process user results
        if users:
            results_found = True
            summary.append("ACCOUNTS:")
            for idx, user in enumerate(users, 1):
                address = user.get("address", "Unknown")
                account_info = user.get("account", {})
                display_name_info = account_info.get("displayName", {})
                display_name = display_name_info.get("value", address)
                
                summary.append(f"{idx}. {display_name}")
                summary.append(f"   Address: {address}")
                summary.append("")
            
            summary.append("")
        
        # Process app results
        if apps:
            results_found = True
            summary.append("APPS/PROTOCOLS:")
            for idx, app_result in enumerate(apps, 1):
                app_id = app_result.get("appId", "")
                app_info = app_result.get("app", {})
                name = app_info.get("displayName", "Unknown")
                url = app_info.get("url", "")
                
                summary.append(f"{idx}. {name}")
                summary.append(f"   ID: {app_id}")
                if url:
                    summary.append(f"   URL: {url}")
                summary.append("")
            
            summary.append("")
        
        # Process NFT results
        if nfts:
            results_found = True
            summary.append("NFTs:")
            for idx, nft in enumerate(nfts, 1):
                address = nft.get("address", "Unknown")
                network_name = nft.get("network", "Unknown")
                collection = nft.get("collection", {})
                name = collection.get("displayName", "Unknown Collection")
                symbol = collection.get("symbol", "")
                floor_price_info = collection.get("floorPrice", {})
                floor_price = floor_price_info.get("valueUsd", 0) if floor_price_info else 0
                
                # Ensure value is properly converted to float
                floor_price = float(floor_price) if floor_price is not None else 0.0
                
                summary.append(f"{idx}. {name} ({symbol})")
                summary.append(f"   Floor Price: ${floor_price:.4f}")
                summary.append(f"   Address: {address} on {network_name}")
                summary.append("")
        
        if not results_found:
            return f"No matches found for query: {query}"
        
        return "\n".join(summary)
