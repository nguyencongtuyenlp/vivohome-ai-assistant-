"""
VIVOHOME AI - Web Search with Tavily
Fallback search when product not found in database
"""

import requests
from logger import app_logger

# Tavily API Configuration
TAVILY_API_KEY = "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"
TAVILY_SEARCH_URL = "https://api.tavily.com/search"

def web_search(query: str, max_results: int = 3):
    """
    Search the web using Tavily API
    
    Args:
        query: Search query
        max_results: Maximum results to return
        
    Returns:
        Search results with title, content, and URL
    """
    try:
        app_logger.info(f"🌐 Web search: {query}")
        
        # Prepare request
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": f"VIVOHOME {query} giá",  # Add context for product search
            "search_depth": "basic",
            "include_answer": True,
            "include_images": False,
            "max_results": max_results
        }
        
        # Make request
        response = requests.post(
            TAVILY_SEARCH_URL,
            json=payload,
            timeout=10
        )
        
        if response.status_code != 200:
            app_logger.warning(f"⚠️ Tavily API error: {response.status_code}")
            return {"found": False, "error": f"API error: {response.status_code}"}
        
        data = response.json()
        
        # Extract results
        results = []
        
        # Add AI answer if available
        if data.get("answer"):
            results.append({
                "type": "answer",
                "content": data["answer"],
                "source": "tavily_ai"
            })
        
        # Add search results
        for item in data.get("results", [])[:max_results]:
            results.append({
                "type": "web_result",
                "title": item.get("title", ""),
                "content": item.get("content", "")[:300],  # Limit content length
                "url": item.get("url", ""),
                "source": "web_search"
            })
        
        app_logger.info(f"✅ Web search found {len(results)} results")
        return {
            "found": len(results) > 0,
            "count": len(results),
            "results": results
        }
        
    except requests.exceptions.Timeout:
        app_logger.warning("⚠️ Web search timeout")
        return {"found": False, "error": "Search timeout"}
    except Exception as e:
        app_logger.error(f"❌ Web search error: {e}")
        return {"found": False, "error": str(e)}

def search_product_info(product_name: str):
    """
    Search for specific product information
    
    Args:
        product_name: Name of the product to search
        
    Returns:
        Product information from web
    """
    query = f"{product_name} giá bán thông số kỹ thuật"
    return web_search(query, max_results=3)

def search_price_comparison(product_name: str):
    """
    Search for price comparison
    
    Args:
        product_name: Product to compare prices
        
    Returns:
        Price information from different sources
    """
    query = f"{product_name} so sánh giá mua ở đâu"
    return web_search(query, max_results=5)

# Test
if __name__ == "__main__":
    print("=" * 50)
    print("🌐 VIVOHOME AI - Web Search Test")
    print("=" * 50)
    
    # Test queries
    test_queries = [
        "tủ lạnh Samsung inverter",
        "máy giặt LG 9kg",
        "điều hòa Daikin 1HP"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        result = web_search(query)
        
        if result.get("found"):
            print(f"   Found {result['count']} results:")
            for r in result["results"]:
                if r["type"] == "answer":
                    print(f"   💡 AI Answer: {r['content'][:100]}...")
                else:
                    print(f"   🔗 {r['title'][:50]}...")
        else:
            print(f"   ❌ No results: {result.get('error', 'Unknown')}")
