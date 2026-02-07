"""
VIVOHOME AI - Vector Store with ChromaDB
Semantic search for products using embeddings
"""

import chromadb
from chromadb.utils import embedding_functions
import sqlite3
import os
from logger import app_logger

# Initialize ChromaDB
CHROMA_PATH = "chroma_db"

def get_embedding_function():
    """Get sentence-transformer embedding function for Vietnamese"""
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

def init_vector_store():
    """Initialize ChromaDB and embed all products"""
    app_logger.info("🧠 Initializing Vector Store...")
    
    # Create ChromaDB client
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # Get or create collection
    embedding_fn = get_embedding_function()
    collection = client.get_or_create_collection(
        name="products",
        embedding_function=embedding_fn,
        metadata={"description": "VIVOHOME product embeddings"}
    )
    
    # Check if already populated
    if collection.count() > 0:
        app_logger.info(f"✅ Vector store already has {collection.count()} products")
        return collection
    
    # Load products from SQLite
    conn = sqlite3.connect("vivohome.db")
    cursor = conn.execute("SELECT * FROM products")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        app_logger.warning("⚠️ No products in database")
        return collection
    
    # Prepare data for embedding
    documents = []
    metadatas = []
    ids = []
    
    for row in rows:
        # Create rich text for embedding
        product_text = f"""
        Tên sản phẩm: {row[4]}
        Model: {row[5] or 'N/A'}
        Nhà sản xuất: {row[6] or 'N/A'}
        Giá: {row[7]:,} VND
        Thông số: {row[3] or 'N/A'}
        """
        
        documents.append(product_text)
        metadatas.append({
            "ten": row[4],
            "model": row[5] or "N/A",
            "gia": str(row[7]),
            "nsx": row[6] or "N/A",
            "nhom_hang": row[2] or "N/A"
        })
        ids.append(f"product_{row[0]}")
    
    # Add to collection
    app_logger.info(f"📦 Embedding {len(documents)} products...")
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    app_logger.info(f"✅ Vector store initialized with {collection.count()} products")
    return collection

def semantic_search(query: str, n_results: int = 5):
    """
    Search products using semantic similarity
    
    Args:
        query: User's natural language query
        n_results: Number of results to return
        
    Returns:
        List of matching products with scores
    """
    try:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        embedding_fn = get_embedding_function()
        collection = client.get_collection(
            name="products",
            embedding_function=embedding_fn
        )
        
        # Query with embeddings
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["metadatas", "documents", "distances"]
        )
        
        # Format results
        products = []
        if results and results['metadatas']:
            for i, metadata in enumerate(results['metadatas'][0]):
                distance = results['distances'][0][i] if results['distances'] else 0
                similarity = 1 - distance  # Convert distance to similarity
                
                products.append({
                    "ten": metadata.get("ten", "N/A"),
                    "model": metadata.get("model", "N/A"),
                    "gia": int(metadata.get("gia", 0)),
                    "nsx": metadata.get("nsx", "N/A"),
                    "nhom_hang": metadata.get("nhom_hang", "N/A"),
                    "similarity": round(similarity, 3),
                    "source": "vector_db"
                })
        
        app_logger.info(f"🔍 Semantic search found {len(products)} products")
        return {"found": len(products) > 0, "count": len(products), "products": products}
        
    except Exception as e:
        app_logger.error(f"❌ Semantic search error: {e}")
        return {"found": False, "error": str(e)}

def hybrid_search(query: str, keyword_results: list = None, n_results: int = 5):
    """
    Combine semantic search with keyword results
    
    Args:
        query: User query
        keyword_results: Results from keyword search (database.py)
        n_results: Max results
        
    Returns:
        Combined and ranked results
    """
    # Get semantic results
    semantic_result = semantic_search(query, n_results)
    semantic_products = semantic_result.get("products", [])
    
    # Combine with keyword results if provided
    if keyword_results:
        # Add source tag to keyword results
        for p in keyword_results:
            p["source"] = "keyword"
            p["similarity"] = 0.8  # Default score for keyword matches
        
        # Merge and deduplicate
        all_products = []
        seen_models = set()
        
        # Prioritize semantic results
        for p in semantic_products:
            model = p.get("model", "")
            if model not in seen_models:
                all_products.append(p)
                seen_models.add(model)
        
        # Add keyword results not in semantic
        for p in keyword_results:
            model = p.get("model", "")
            if model not in seen_models:
                all_products.append(p)
                seen_models.add(model)
        
        # Sort by similarity
        all_products.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        
        return {
            "found": len(all_products) > 0,
            "count": len(all_products[:n_results]),
            "products": all_products[:n_results]
        }
    
    return semantic_result

# Initialize on import
if __name__ == "__main__":
    print("=" * 50)
    print("🧠 VIVOHOME AI - Vector Store Setup")
    print("=" * 50)
    
    # Initialize
    collection = init_vector_store()
    
    # Test semantic search
    print("\n📝 Testing semantic search...")
    test_queries = [
        "máy giặt tiết kiệm điện",
        "tivi màn hình lớn",
        "tủ lạnh gia đình"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        result = semantic_search(query, n_results=3)
        if result.get("found"):
            for p in result["products"]:
                print(f"  - {p['ten']} ({p['model']}): {p['gia']:,} VND | Similarity: {p['similarity']}")
        else:
            print("  No results")
