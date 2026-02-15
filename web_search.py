"""
VIVOHOME AI - Web Search (Tavily API)
Fallback search when products are not found in the local database.
"""

import requests
from typing import Dict, List

from app_config import TAVILY_API_KEY, TAVILY_SEARCH_URL, WEB_SEARCH_TIMEOUT
from logger import get_logger

logger = get_logger("web_search")


def web_search(query: str, max_results: int = 3) -> Dict:
    """
    Search the web using Tavily API.

    Args:
        query: Natural-language search query.
        max_results: Maximum number of results to return.

    Returns:
        {"found": bool, "count": int, "results": [...]}
    """
    try:
        logger.info("Web search: '%s'", query[:80])

        payload = {
            "api_key": TAVILY_API_KEY,
            "query": f"{query} giá",
            "search_depth": "basic",
            "include_answer": True,
            "include_images": False,
            "max_results": max_results,
        }

        response = requests.post(
            TAVILY_SEARCH_URL, json=payload, timeout=WEB_SEARCH_TIMEOUT
        )

        if response.status_code != 200:
            logger.warning("Tavily API error: HTTP %d", response.status_code)
            return {"found": False, "error": f"API error: {response.status_code}"}

        data = response.json()
        results: List[Dict] = []

        # AI-generated answer
        if data.get("answer"):
            results.append({
                "type": "answer",
                "content": data["answer"],
                "source": "tavily_ai",
            })

        # Individual search results
        for item in data.get("results", [])[:max_results]:
            results.append({
                "type": "web_result",
                "title": item.get("title", ""),
                "content": item.get("content", "")[:300],
                "url": item.get("url", ""),
                "source": "web_search",
            })

        logger.info("Web search found %d results", len(results))
        return {"found": len(results) > 0, "count": len(results), "results": results}

    except requests.exceptions.Timeout:
        logger.warning("Web search timed out after %ds", WEB_SEARCH_TIMEOUT)
        return {"found": False, "error": "Search timeout"}
    except Exception as exc:
        logger.error("Web search error: %s", exc)
        return {"found": False, "error": str(exc)}


def search_product_info(product_name: str) -> Dict:
    """Search for detailed product specifications and pricing."""
    return web_search(f"{product_name} giá bán thông số kỹ thuật", max_results=3)


def search_price_comparison(product_name: str) -> Dict:
    """Search for price comparison across retailers."""
    return web_search(f"{product_name} so sánh giá mua ở đâu", max_results=5)


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 50)
    print("VIVOHOME AI - Web Search Test")
    print("=" * 50)

    for q in ["tủ lạnh Samsung inverter", "iPhone 15 Pro Max giá"]:
        print(f"\nQuery: '{q}'")
        result = web_search(q)
        if result.get("found"):
            for r in result["results"]:
                if r["type"] == "answer":
                    print(f"  AI: {r['content'][:100]}...")
                else:
                    print(f"  🔗 {r['title'][:60]}")
        else:
            print(f"  No results: {result.get('error')}")
