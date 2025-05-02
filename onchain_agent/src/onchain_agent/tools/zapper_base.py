import os
import requests
import json
from typing import Dict, Any, Optional, Union, List

class ZapperBase:
    """Base class for Zapper API tools with common functionality."""
    
    # GraphQL API endpoint
    GRAPHQL_API_URL = "https://public.zapper.xyz/graphql"
    
    # Network ID mapping (network name to chain ID)
    NETWORK_IDS = {
        "ethereum": 1,
        "polygon": 137,
        "optimism": 10,
        "arbitrum": 42161,
        "base": 8453,
        "zora": 7777777,
        "bsc": 56,
        "avalanche": 43114,
        "fantom": 250,
        "gnosis": 100
    }
    
    @staticmethod
    def get_api_key() -> str:
        """Get the Zapper API key from environment variables."""
        api_key = os.getenv("ZAPPER_API_KEY")
        if not api_key:
            raise ValueError("ZAPPER_API_KEY environment variable not set")
        return api_key
    
    @staticmethod
    def get_chain_id(network: str) -> int:
        """Convert network name to chain ID."""
        network = network.lower()
        if network in ZapperBase.NETWORK_IDS:
            return ZapperBase.NETWORK_IDS[network]
        raise ValueError(f"Unknown network: {network}. Supported networks: {', '.join(ZapperBase.NETWORK_IDS.keys())}")
    
    @staticmethod
    def execute_graphql_query(query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a GraphQL query against the Zapper API."""
        api_key = ZapperBase.get_api_key()
        
        headers = {
            "x-zapper-api-key": api_key,
            "accept": "application/json",
            "content-type": "application/json"
        }
        
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        try:
            response = requests.post(ZapperBase.GRAPHQL_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_details = e.response.json()
                    error_msg += f". Details: {json.dumps(error_details)}"
                except:
                    error_msg += f". Status code: {e.response.status_code}"
            raise RuntimeError(error_msg)
    
    @staticmethod
    def make_request(url: str, method: str = "POST", params: Optional[Dict[str, Any]] = None, 
                     data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Legacy method for backward compatibility. 
        Note: This method is deprecated. Use execute_graphql_query instead."""
        
        if "graphql" in url:
            # Handle GraphQL request
            return ZapperBase.execute_graphql_query(data.get("query", ""), data.get("variables", {}))
        
        # For legacy REST requests (which will likely fail)
        api_key = ZapperBase.get_api_key()
        
        headers = {
            "x-zapper-api-key": api_key,
            "accept": "application/json"
        }
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                headers["content-type"] = "application/json"
                response = requests.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_details = e.response.json()
                    error_msg += f". Details: {json.dumps(error_details)}"
                except:
                    error_msg += f". Status code: {e.response.status_code}"
            raise RuntimeError(error_msg)
