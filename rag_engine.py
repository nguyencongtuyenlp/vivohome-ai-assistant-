"""
VIVOHOME AI - RAG Engine
Orchestrates Vector Search + Web Search + LLM Response Generation
"""

from query_parser import parse_query
from database import search_with_intent, search_by_keywords
from vector_store import semantic_search, hybrid_search
from web_search import web_search
from logger import app_logger

class RAGEngine:
    """
    Full RAG Pipeline for VIVOHOME AI
    
    Pipeline:
    1. Parse query intent
    2. Vector search (semantic)
    3. Keyword search (fallback)
    4. Web search (if no results)
    5. Generate response
    """
    
    def __init__(self, use_web_fallback: bool = True, use_semantic: bool = True):
        self.use_web_fallback = use_web_fallback
        self.use_semantic = use_semantic
        app_logger.info("🧠 RAG Engine initialized")
    
    def search(self, query: str, max_results: int = 5):
        """
        Full RAG search pipeline
        
        Args:
            query: User's natural language query
            max_results: Maximum results to return
            
        Returns:
            Search results with source attribution
        """
        app_logger.info(f"🔍 RAG Search: {query}")
        
        # Similarity threshold - below this, results are not relevant
        SIMILARITY_THRESHOLD = 0.5
        
        # Step 1: Parse intent
        intent = parse_query(query)
        app_logger.info(f"   Intent: {intent['intent']}, Category: {intent['category']}")
        
        # Step 2: Semantic search (if enabled)
        results = []
        sources_used = []
        
        if self.use_semantic:
            try:
                semantic_result = semantic_search(query, n_results=max_results)
                if semantic_result.get("found"):
                    # Filter by similarity threshold
                    good_results = [
                        p for p in semantic_result["products"]
                        if p.get("similarity", 0) >= SIMILARITY_THRESHOLD
                    ]
                    if good_results:
                        results.extend(good_results)
                        sources_used.append("vector_db")
                        app_logger.info(f"   ✅ Semantic: {len(good_results)} results (threshold={SIMILARITY_THRESHOLD})")
                    else:
                        app_logger.info(f"   ⚠️ Semantic: {len(semantic_result['products'])} results but all below threshold")
            except Exception as e:
                app_logger.warning(f"   ⚠️ Semantic search failed: {e}")
        
        # Step 3: Intent-based search (only if category detected)
        if intent.get('category') and not results:
            intent_result = search_with_intent(query, intent, max_results)
            if intent_result.get("found"):
                for p in intent_result["products"]:
                    p["source"] = "database"
                    p["similarity"] = 0.8  # Assume good match for intent-based
                    results.append(p)
                sources_used.append("database")
                app_logger.info(f"   ✅ Database: {intent_result['count']} results")
        
        # Step 4: Web search fallback (if no good results)
        web_results = None
        if not results and self.use_web_fallback:
            app_logger.info("   🌐 No local results, trying web search...")
            web_result = web_search(query, max_results=3)
            if web_result.get("found"):
                web_results = web_result["results"]
                sources_used.append("web")
                app_logger.info(f"   ✅ Web: {len(web_results)} results")
        
        # Step 5: Prepare response
        return {
            "found": len(results) > 0 or web_results is not None,
            "intent": intent,
            "products": results[:max_results],
            "web_results": web_results,
            "sources": sources_used
        }
    
    def generate_response(self, query: str, search_result: dict) -> str:
        """
        Generate natural language response from search results
        
        Args:
            query: Original query
            search_result: Result from search()
            
        Returns:
            Formatted response string
        """
        intent = search_result.get("intent", {})
        products = search_result.get("products", [])
        web_results = search_result.get("web_results")
        sources = search_result.get("sources", [])
        
        # Build response based on intent
        if products:
            if intent.get("intent") == "highest_price":
                p = products[0]
                response = f"""💎 **Sản phẩm {intent.get('category', '')} giá cao nhất:**

📦 **{p['ten']}**
- Model: {p.get('model', 'N/A')}
- Giá: **{p['gia']:,} VND**
- Độ phù hợp: {p.get('similarity', 0.9)*100:.0f}%

📍 Nguồn: {', '.join(sources)}"""
            
            elif intent.get("intent") == "lowest_price":
                p = products[0]
                response = f"""💰 **Sản phẩm {intent.get('category', '')} giá rẻ nhất:**

📦 **{p['ten']}**
- Model: {p.get('model', 'N/A')}
- Giá: **{p['gia']:,} VND**
- Độ phù hợp: {p.get('similarity', 0.9)*100:.0f}%

📍 Nguồn: {', '.join(sources)}"""
            
            elif intent.get("intent") == "compare":
                lines = [f"📊 **So sánh {intent.get('category', 'sản phẩm')}:**\n"]
                for i, p in enumerate(products[:5], 1):
                    lines.append(f"{i}. **{p['ten']}** ({p.get('model', 'N/A')})")
                    lines.append(f"   - Giá: **{p['gia']:,} VND**")
                    if p.get('similarity'):
                        lines.append(f"   - Độ phù hợp: {p['similarity']*100:.0f}%")
                lines.append(f"\n📍 Nguồn: {', '.join(sources)}")
                response = "\n".join(lines)
            
            else:  # Normal search
                lines = ["📦 **Sản phẩm tìm được:**\n"]
                for p in products[:5]:
                    similarity = p.get('similarity', 0)
                    sim_icon = "🟢" if similarity > 0.7 else "🟡" if similarity > 0.5 else "🔴"
                    lines.append(f"{sim_icon} **{p['ten']}** ({p.get('model', 'N/A')})")
                    lines.append(f"   - Giá: **{p['gia']:,} VND**")
                lines.append(f"\n📍 Nguồn: {', '.join(sources)}")
                response = "\n".join(lines)
        
        # Web fallback response
        elif web_results:
            lines = ["🌐 **Không tìm thấy trong kho VIVOHOME. Kết quả từ web:**\n"]
            for r in web_results:
                if r["type"] == "answer":
                    lines.append(f"💡 **Tóm tắt:** {r['content']}\n")
                else:
                    lines.append(f"🔗 **{r['title']}**")
                    lines.append(f"   {r['content'][:150]}...")
                    if r.get('url'):
                        lines.append(f"   [Xem thêm]({r['url']})")
                    lines.append("")
            response = "\n".join(lines)
        
        else:
            response = """❌ **Không tìm thấy sản phẩm**

Xin lỗi, tôi không tìm thấy sản phẩm phù hợp trong hệ thống.
Bạn có thể thử:
- Mô tả sản phẩm khác đi
- Kiểm tra lại tên sản phẩm
- Hỏi cụ thể hơn (ví dụ: "TV Samsung 55 inch")"""
        
        return response
    
    def process(self, query: str) -> str:
        """
        Full RAG pipeline: Search + Generate Response
        
        Args:
            query: User query
            
        Returns:
            Natural language response
        """
        search_result = self.search(query)
        return self.generate_response(query, search_result)

# Global RAG engine instance
rag_engine = RAGEngine(use_web_fallback=True, use_semantic=True)

def rag_search(query: str) -> str:
    """
    Quick function for RAG search
    
    Args:
        query: User query
        
    Returns:
        Formatted response
    """
    return rag_engine.process(query)

# Test
if __name__ == "__main__":
    print("=" * 60)
    print("🧠 VIVOHOME AI - RAG Engine Test")
    print("=" * 60)
    
    # Initialize vector store first
    from vector_store import init_vector_store
    init_vector_store()
    
    # Test queries
    test_queries = [
        "TV giá cao nhất",
        "máy giặt tiết kiệm điện",  # Semantic search test
        "iPhone 15 Pro Max",  # Web fallback test
        "Tủ lạnh rẻ nhất"
    ]
    
    for query in test_queries:
        print(f"\n{'='*40}")
        print(f"📝 Query: '{query}'")
        print("="*40)
        
        response = rag_search(query)
        print(response)
