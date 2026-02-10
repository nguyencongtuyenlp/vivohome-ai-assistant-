"""
VIVOHOME AI - RAG Engine
Orchestrates: Intent Parsing → Semantic Search → Database Search → Web Fallback.
"""

from typing import Dict, List, Optional

from config import SIMILARITY_THRESHOLD, MAX_SEARCH_RESULTS
from query_parser import parse_query
from database import search_with_intent
from vector_store import semantic_search
from web_search import web_search
from logger import get_logger

logger = get_logger("rag")


class RAGEngine:
    """
    Full RAG pipeline for VIVOHOME AI.

    Pipeline order:
        1. Parse intent (rule-based)
        2. Semantic search (ChromaDB embeddings)
        3. Database search (SQLite keyword/intent)
        4. Web search fallback (Tavily API)
        5. Format response
    """

    def __init__(self, *, use_web_fallback: bool = True, use_semantic: bool = True):
        self.use_web_fallback = use_web_fallback
        self.use_semantic = use_semantic
        logger.info("RAG Engine initialized (semantic=%s, web=%s)",
                     use_semantic, use_web_fallback)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, max_results: int = MAX_SEARCH_RESULTS) -> Dict:
        """Run the full search pipeline and return raw results."""
        logger.info("RAG search: '%s'", query[:80])

        intent = parse_query(query)
        logger.info("  Intent=%s  Category=%s  Brands=%s",
                     intent["intent"], intent["category"], intent.get("brands"))

        results: List[Dict] = []
        sources: List[str] = []

        # Strategy: if intent has category/brands/compare → DB first, semantic fallback
        #           if generic query → keyword check first, web fallback if not found
        use_db_first = (
            intent["intent"] in ("compare", "highest_price", "lowest_price")
            or intent.get("category")
            or intent.get("brands")
        )

        if use_db_first:
            # 1a. Database search (structured, precise)
            results, sources = self._database_search(query, intent, max_results)
            # 1b. Semantic fallback if DB found nothing
            if not results and self.use_semantic:
                results, sources = self._semantic_search(query, max_results)
        else:
            # Generic query — check if product exists in DB first
            from database import search_by_keywords
            keyword_check = search_by_keywords(query, max_results=1)

            if keyword_check.get("found"):
                # Keywords matched → use semantic for better ranking
                if self.use_semantic:
                    results, sources = self._semantic_search(query, max_results)
                if not results:
                    results, sources = self._database_search(query, intent, max_results)
            else:
                # No keyword match → product likely NOT in catalog → web search
                logger.info("  No keyword match in DB → skipping to web search")

        # 2. Web fallback
        web_results = None
        if not results and self.use_web_fallback:
            logger.info("  Trying web search...")
            web_result = web_search(query, max_results=3)
            if web_result.get("found"):
                web_results = web_result["results"]
                sources.append("web")
                logger.info("  Web: %d results", len(web_results))

        return {
            "found": bool(results) or web_results is not None,
            "intent": intent,
            "products": results[:max_results],
            "web_results": web_results,
            "sources": sources,
        }

    def _database_search(self, query: str, intent: Dict, max_results: int):
        """Run intent-based database search."""
        db_result = search_with_intent(query, intent, max_results)
        if db_result.get("found"):
            for p in db_result["products"]:
                p["source"] = "database"
                p.setdefault("similarity", 0.8)
            logger.info("  Database: %d results", db_result["count"])
            return db_result["products"], ["database"]
        return [], []

    def _semantic_search(self, query: str, max_results: int):
        """Run semantic search with threshold filtering."""
        try:
            result = semantic_search(query, n_results=max_results)
            if result.get("found"):
                good = [p for p in result["products"]
                        if p.get("similarity", 0) >= SIMILARITY_THRESHOLD]
                if good:
                    logger.info("  Semantic: %d/%d above threshold (%.1f)",
                                len(good), len(result["products"]),
                                SIMILARITY_THRESHOLD)
                    return good, ["vector_db"]
                else:
                    logger.info("  Semantic: all %d results below threshold",
                                len(result["products"]))
        except Exception as exc:
            logger.warning("  Semantic search failed: %s", exc)
        return [], []

    # ------------------------------------------------------------------
    # Response generation
    # ------------------------------------------------------------------

    def generate_response(self, query: str, search_result: Dict) -> str:
        """Format search results into a user-friendly response."""
        intent = search_result.get("intent", {})
        products = search_result.get("products", [])
        web_results = search_result.get("web_results")
        sources = search_result.get("sources", [])

        if products:
            return self._format_product_response(intent, products, sources)
        if web_results:
            return self._format_web_response(web_results)
        return self._format_no_results()

    def process(self, query: str) -> str:
        """Full RAG pipeline: search → generate response."""
        return self.generate_response(query, self.search(query))

    # ------------------------------------------------------------------
    # Private formatters
    # ------------------------------------------------------------------

    @staticmethod
    def _format_product_response(intent: Dict, products: List[Dict],
                                 sources: List[str]) -> str:
        intent_type = intent.get("intent", "search")
        category = intent.get("category", "")
        src_label = ", ".join(sources)

        if intent_type == "highest_price":
            p = products[0]
            return (
                f"💎 **Sản phẩm {category} giá cao nhất:**\n\n"
                f"📦 **{p['ten']}**\n"
                f"- Model: {p.get('model', 'N/A')}\n"
                f"- Giá: **{p['gia']:,} VND**\n"
                f"- Độ phù hợp: {p.get('similarity', 0.9)*100:.0f}%\n\n"
                f"📍 Nguồn: {src_label}"
            )

        if intent_type == "lowest_price":
            p = products[0]
            return (
                f"💰 **Sản phẩm {category} giá rẻ nhất:**\n\n"
                f"📦 **{p['ten']}**\n"
                f"- Model: {p.get('model', 'N/A')}\n"
                f"- Giá: **{p['gia']:,} VND**\n"
                f"- Độ phù hợp: {p.get('similarity', 0.9)*100:.0f}%\n\n"
                f"📍 Nguồn: {src_label}"
            )

        if intent_type == "compare":
            lines = [f"📊 **So sánh {category or 'sản phẩm'}:**\n"]
            for i, p in enumerate(products[:5], 1):
                lines.append(f"{i}. **{p['ten']}** ({p.get('model', 'N/A')})")
                lines.append(f"   - Giá: **{p['gia']:,} VND**")
                if p.get("similarity"):
                    lines.append(f"   - Độ phù hợp: {p['similarity']*100:.0f}%")
            lines.append(f"\n📍 Nguồn: {src_label}")
            return "\n".join(lines)

        # Default search
        lines = ["📦 **Sản phẩm tìm được:**\n"]
        for p in products[:5]:
            sim = p.get("similarity", 0)
            icon = "🟢" if sim > 0.7 else "🟡" if sim > 0.5 else "🔴"
            lines.append(f"{icon} **{p['ten']}** ({p.get('model', 'N/A')})")
            lines.append(f"   - Giá: **{p['gia']:,} VND**")
        lines.append(f"\n📍 Nguồn: {src_label}")
        return "\n".join(lines)

    @staticmethod
    def _format_web_response(web_results: List[Dict]) -> str:
        lines = ["🌐 **Không tìm thấy trong kho VIVOHOME. Kết quả từ web:**\n"]
        for r in web_results:
            if r["type"] == "answer":
                lines.append(f"💡 **Tóm tắt:** {r['content']}\n")
            else:
                lines.append(f"🔗 **{r['title']}**")
                lines.append(f"   {r['content'][:150]}...")
                if r.get("url"):
                    lines.append(f"   [Xem thêm]({r['url']})")
                lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _format_no_results() -> str:
        return (
            "❌ **Không tìm thấy sản phẩm**\n\n"
            "Xin lỗi, tôi không tìm thấy sản phẩm phù hợp.\n"
            "Bạn có thể thử:\n"
            '- Mô tả sản phẩm khác đi\n'
            '- Kiểm tra lại tên sản phẩm\n'
            '- Hỏi cụ thể hơn (ví dụ: "TV Samsung 55 inch")'
        )


# ---------------------------------------------------------------------------
# Global instance
# ---------------------------------------------------------------------------

rag_engine = RAGEngine(use_web_fallback=True, use_semantic=True)


def rag_search(query: str) -> str:
    """Convenience function for quick RAG search."""
    return rag_engine.process(query)


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from vector_store import init_vector_store
    init_vector_store()

    print("=" * 60)
    print("VIVOHOME AI - RAG Engine Test")
    print("=" * 60)

    for q in ["TV giá cao nhất", "máy giặt tiết kiệm điện",
              "iPhone 15 Pro Max", "Tủ lạnh rẻ nhất"]:
        print(f"\n{'='*40}\nQuery: '{q}'\n{'='*40}")
        print(rag_search(q))
