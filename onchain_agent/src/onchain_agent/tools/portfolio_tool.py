from typing import Type, Dict, Any, List
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from .zapper_base import ZapperBase


class PortfolioToolInput(BaseModel):
    """Input schema for Portfolio Data Tool."""
    address: str = Field(..., description="Blockchain address to fetch portfolio data for")
    network: str = Field("ethereum", description="Blockchain network to query (default: ethereum)")


class PortfolioTool(BaseTool):
    """Tool to fetch comprehensive portfolio data from Zapper API."""
    name: str = "Portfolio Analysis Tool"
    description: str = (
        "Fetches comprehensive portfolio data for a blockchain address including token balances, "
        "DeFi positions, NFT holdings, and total portfolio value. Use this to analyze wallet "
        "holdings and assess portfolio composition."
    )
    args_schema: Type[BaseModel] = PortfolioToolInput
    
    def __init__(self):
        """Initialize the PortfolioTool with cache."""
        super().__init__()
        self._cache = {}
    
    def _cache_key(self, address: str, network: str) -> str:
        """Generate a cache key based on input parameters."""
        return f"{address.lower()}:{network.lower()}"
    
    def _run(self, address: str, network: str = "ethereum") -> str:
        """Run the portfolio data retrieval with caching."""
        # Generate cache key
        cache_key = self._cache_key(address, network)
        
        # Return cached result if available
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Map network string to Zapper network slug if needed
            network_params = None
            network_map = {
                "ethereum": "ethereum",
                "polygon": "polygon",
                "optimism": "optimism",
                "arbitrum": "arbitrum",
                "base": "base",
                "bsc": "binance-smart-chain",
                "avalanche": "avalanche",
                "gnosis": "gnosis",
                "fantom": "fantom"
            }
            
            if network in network_map:
                network_params = network_map[network]
            
            # Define GraphQL query using current Zapper API structure
            query = '''
            query PortfolioData($addresses: [Address!]!) {
              portfolioV2(addresses: $addresses) {
                # Token balances
                tokenBalances {
                  totalBalanceUSD
                  byToken(first: 10) {
                    totalCount
                    edges {
                      node {
                        symbol
                        tokenAddress
                        balance
                        balanceUSD
                        price
                        name
                        network {
                          name
                        }
                      }
                    }
                  }
                }
                
                # App balances
                appBalances {
                  totalBalanceUSD
                  byApp(first: 10) {
                    totalCount
                    edges {
                      node {
                        balanceUSD
                        app {
                          displayName
                          imgUrl
                        }
                        network {
                          name
                        }
                        positionBalances(first: 10) {
                          edges {
                            node {
                              # App token positions (e.g. LP tokens)
                              ... on AppTokenPositionBalance {
                                type
                                symbol
                                balance
                                balanceUSD
                                price
                                appId
                                # Display properties
                                displayProps {
                                  label
                                }
                                # Underlying tokens
                                tokens {
                                  ... on BaseTokenPositionBalance {
                                    symbol
                                    balance
                                    balanceUSD
                                  }
                                }
                              }
                              # Contract positions (e.g. lending positions)
                              ... on ContractPositionBalance {
                                type
                                balanceUSD
                                # Underlying tokens with meta-types
                                tokens {
                                  metaType
                                  token {
                                    ... on BaseTokenPositionBalance {
                                      symbol
                                      balance
                                      balanceUSD
                                    }
                                  }
                                }
                                # Display properties
                                displayProps {
                                  label
                                }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
                
                # NFT balances
                nftBalances {
                  totalCount
                  totalFloorValueUSD
                  byCollection(first: 5) {
                    edges {
                      node {
                        collection {
                          name
                          floorPrice
                        }
                        items(first: 3) {
                          edges {
                            node {
                              name
                              tokenId
                              image {
                                url
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
            '''
            
            # Prepare variables - API now expects 'Address' type, not networks array
            variables = {
                "addresses": [address]
            }
                
            # Execute GraphQL query
            result = ZapperBase.execute_graphql_query(query, variables)
            
            # Format the response
            formatted_result = self._format_portfolio_data(result, address)
            
            # Cache the result
            self._cache[cache_key] = formatted_result
            
            return formatted_result
            
        except Exception as e:
            return f"Error fetching portfolio data: {str(e)}"
    
    def _format_portfolio_data(self, data: Dict[str, Any], address: str) -> str:
        """Format portfolio data into a readable string."""
        if not data or "data" not in data or "portfolioV2" not in data["data"]:
            return "No portfolio data found."
        
        # Get portfolio data from GraphQL response with new structure
        portfolio = data["data"]["portfolioV2"]
        
        # Extract data from new structure
        token_balances = portfolio.get("tokenBalances", {})
        app_balances = portfolio.get("appBalances", {})
        nft_balances = portfolio.get("nftBalances", {})
        
        # Extract totals
        total_value = (
            token_balances.get("totalBalanceUSD", 0) + 
            app_balances.get("totalBalanceUSD", 0) + 
            nft_balances.get("totalFloorValueUSD", 0)
        )
        
        # Get token count
        token_count = token_balances.get("byToken", {}).get("totalCount", 0)
        
        # Get NFT count and value
        nft_count = nft_balances.get("totalCount", 0)
        nft_value = nft_balances.get("totalFloorValueUSD", 0)
        
        # Get app count
        app_count = app_balances.get("byApp", {}).get("totalCount", 0)
        
        # Extract token data from new structure
        tokens = []
        token_edges = token_balances.get("byToken", {}).get("edges", [])
        for edge in token_edges:
            if edge and "node" in edge:
                tokens.append(edge["node"])
        
        # Extract app data from new structure
        apps = []
        app_positions = []
        app_edges = app_balances.get("byApp", {}).get("edges", [])
        
        for app_edge in app_edges:
            if not app_edge or "node" not in app_edge:
                continue
                
            app_node = app_edge["node"]
            app_info = {
                "app": {
                    "name": app_node.get("app", {}).get("displayName", "Unknown")
                },
                "balanceUSD": app_node.get("balanceUSD", 0),
                "network": app_node.get("network", {})            
            }
            apps.append(app_info)
            
            # Extract position balances
            position_edges = app_node.get("positionBalances", {}).get("edges", [])
            for pos_edge in position_edges:
                if not pos_edge or "node" not in pos_edge:
                    continue
                    
                pos_node = pos_edge["node"]
                pos_info = {
                    "type": pos_node.get("type", "unknown"),
                    "balanceUSD": pos_node.get("balanceUSD", 0),
                    "app": app_info["app"],
                    "network": app_info["network"],
                    "displayProps": pos_node.get("displayProps", []),
                    "name": ""
                }
                
                # Set position name based on type
                if pos_node.get("type") == "app-token":
                    pos_info["symbol"] = pos_node.get("symbol", "")
                    pos_info["balance"] = pos_node.get("balance", 0)
                    pos_info["name"] = pos_node.get("displayProps", {}).get("label", "Unknown Position")
                else:  # contract-position
                    pos_info["name"] = pos_node.get("displayProps", {}).get("label", "Unknown Position")
                
                app_positions.append(pos_info)
        
        # Extract NFT data from new structure
        nft_items = []
        collection_edges = nft_balances.get("byCollection", {}).get("edges", [])
        
        for collection_edge in collection_edges:
            if not collection_edge or "node" not in collection_edge:
                continue
                
            collection_node = collection_edge["node"]
            collection_info = collection_node.get("collection", {})
            
            item_edges = collection_node.get("items", {}).get("edges", [])
            for item_edge in item_edges:
                if not item_edge or "node" not in item_edge:
                    continue
                    
                item_node = item_edge["node"]
                nft_items.append({
                    "name": item_node.get("name", "Unnamed"),
                    "tokenId": item_node.get("tokenId", "Unknown ID"),
                    "collection": {
                        "name": collection_info.get("name", "Unknown Collection"),
                        "floorPrice": collection_info.get("floorPrice", 0)
                    }
                })
        
        # Format top tokens by value
        top_tokens = []
        sorted_tokens = sorted(tokens, key=lambda x: x.get("balanceUSD", 0), reverse=True)
        for token in sorted_tokens[:5]:  # Get top 5 tokens
            symbol = token.get("symbol", "Unknown")
            balance = token.get("balance", 0)
            value = token.get("balanceUSD", 0)
            price = token.get("price", 0)
            network_name = token.get("network", {}).get("name", "Unknown")
            token_str = f"{symbol}: {balance:.4f} @ ${price:.6f} = ${value:.2f} on {network_name}"
            top_tokens.append(token_str)
        
        # Format top apps by value
        top_apps = []
        sorted_positions = sorted(app_positions, key=lambda x: x.get("balanceUSD", 0), reverse=True)
        for position in sorted_positions[:3]:  # Get top 3 positions
            app_name = position.get("app", {}).get("name", "Unknown")
            position_name = position.get("name", "Unknown Position")
            value = position.get("balanceUSD", 0)
            network_name = position.get("network", {}).get("name", "Unknown")
            
            # Handle different app position types
            if position.get("type") == "app-token":
                symbol = position.get("symbol", "")
                balance = position.get("balance", 0)
                app_str = f"{app_name} - {position_name} ({symbol}): {balance:.4f} = ${value:.2f} on {network_name}"
            else:  # contract-position
                display_props = position.get("displayProps", [])
                if isinstance(display_props, dict):
                    props_str = display_props.get("label", "")
                else:
                    props_str = ", ".join([f"{prop.get('label', '')}" for prop in display_props[:2] if prop])
                app_str = f"{app_name} - {position_name}: ${value:.2f} ({props_str}) on {network_name}"
            
            top_apps.append(app_str)
        
        # Format top NFTs
        top_nfts = []
        for nft in nft_items[:3]:  # Get top 3 NFTs
            collection = nft.get("collection", {})
            collection_name = collection.get("name", "Unknown Collection")
            nft_name = nft.get("name", "Unnamed")
            token_id = nft.get("tokenId", "Unknown ID")
            floor_price = collection.get("floorPrice", 0)
            nft_str = f"{collection_name} - {nft_name} (#{token_id}) - Floor: ${floor_price:.4f}"
            top_nfts.append(nft_str)
        
        # Format the full portfolio summary
        summary = [
            f"Portfolio Summary for {address}:",
            f"Total Value: ${total_value:.2f}",
            f"Assets: {token_count} tokens, {nft_count} NFTs, {app_count} DeFi positions",
            ""
        ]
        
        # Add token section
        summary.append("Top Tokens by Value:")
        if top_tokens:
            summary.extend(top_tokens)
        else:
            summary.append("No token data available")
        
        summary.append("")  # Add spacing
        
        # Add DeFi app section
        if app_count > 0:
            summary.append("Top DeFi Positions:")
            if top_apps:
                summary.extend(top_apps)
            else:
                summary.append("No DeFi position data available")
        
        summary.append("")  # Add spacing
        
        # Add NFT section if there are NFTs
        if nft_count > 0:
            summary.append(f"NFT Holdings: {nft_count} NFTs - Total Floor Value: ${nft_value:.2f}")
            if top_nfts:
                summary.append("Top NFTs:")
                summary.extend(top_nfts)
        
        return "\n".join(summary)
