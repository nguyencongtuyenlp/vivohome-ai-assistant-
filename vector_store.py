"""
VIVOHOME AI - Vector Store (ChromaDB)
Semantic search for products using multilingual sentence embeddings.
"""

from typing import Dict, List, Optional

from app_config import CHROMA_PATH, DB_PATH, EMBEDDING_MODEL
from logger import get_logger

logger = get_logger("vector_store")

# Lazy imports — chromadb may not be installed in all environments
_client = None
_collection = None


def _get_collection():
    """Lazy-init ChromaDB collection (singleton)."""
    global _client, _collection
    if _collection is not None:
        return _collection

    import chromadb
    from chromadb.utils import embedding_functions

    _client = chromadb.PersistentClient(path=CHROMA_PATH)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    _collection = _client.get_or_create_collection(
        name="products",
        embedding_function=embedding_fn,
        metadata={"description": "VIVOHOME product embeddings"},
    )
    return _collection


def init_vector_store():
    """Embed all products from SQLite into ChromaDB (idempotent)."""
    import sqlite3

    collection = _get_collection()

    if collection.count() > 0:
        logger.info("Vector store already has %d products", collection.count())
        return collection

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM products").fetchall()
    conn.close()

    if not rows:
        logger.warning("No products in database — nothing to embed")
        return collection

    documents, metadatas, ids = [], [], []

    for row in rows:
        text = (
            f"Tên sản phẩm: {row['ten_san_pham']}  "
            f"Model: {row['model'] or 'N/A'}  "
            f"Thông số: {row['thong_so_chinh'] or 'N/A'}  "
            f"Giá: {row['gia']:,} VND  "
            f"Nhóm hàng: {row['nhom_hang_loai'] or 'N/A'}"
        )
        documents.append(text)
        metadatas.append({
            "ten": row["ten_san_pham"],
            "model": row["model"] or "N/A",
            "gia": str(row["gia"]),
            "nsx": row["thong_so_chinh"] or "N/A",
            "nhom_hang": row["nhom_hang"] or "N/A",
        })
        ids.append(f"product_{row['id']}")

    logger.info("Embedding %d products into vector store...", len(documents))
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    logger.info("Vector store ready — %d products", collection.count())
    return collection


def semantic_search(query: str, n_results: int = 5) -> Dict:
    """
    Search products by semantic similarity.

    Returns:
        {"found": bool, "count": int, "products": [...]}
    """
    try:
        collection = _get_collection()
        if collection.count() == 0:
            init_vector_store()

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
            include=["metadatas", "documents", "distances"],
        )

        products = []
        if results and results["metadatas"]:
            for i, meta in enumerate(results["metadatas"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                similarity = round(1 - distance, 3)

                products.append({
                    "ten": meta.get("ten", "N/A"),
                    "model": meta.get("model", "N/A"),
                    "gia": int(meta.get("gia", 0)),
                    "nsx": meta.get("nsx", "N/A"),
                    "nhom_hang": meta.get("nhom_hang", "N/A"),
                    "similarity": similarity,
                    "source": "vector_db",
                })

        logger.info("Semantic search: %d results for '%s'", len(products), query[:50])
        return {"found": len(products) > 0, "count": len(products), "products": products}

    except Exception as exc:
        logger.error("Semantic search error: %s", exc)
        return {"found": False, "error": str(exc)}


def hybrid_search(query: str, keyword_results: Optional[List] = None,
                  n_results: int = 5) -> Dict:
    """Combine semantic search with keyword results, deduplicating by model."""
    semantic_result = semantic_search(query, n_results)
    semantic_products = semantic_result.get("products", [])

    if not keyword_results:
        return semantic_result

    # Tag keyword results
    for p in keyword_results:
        p.setdefault("source", "keyword")
        p.setdefault("similarity", 0.8)

    # Merge and deduplicate
    seen_models: set = set()
    merged = []
    for p in semantic_products + keyword_results:
        model = p.get("model", "")
        if model not in seen_models:
            merged.append(p)
            seen_models.add(model)

    merged.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    top = merged[:n_results]
    return {"found": len(top) > 0, "count": len(top), "products": top}


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 50)
    print("VIVOHOME AI - Vector Store Setup")
    print("=" * 50)

    init_vector_store()

    for q in ["máy giặt tiết kiệm điện", "tivi màn hình lớn", "tủ lạnh gia đình"]:
        print(f"\nQuery: '{q}'")
        result = semantic_search(q, n_results=3)
        if result.get("found"):
            for p in result["products"]:
                print(f"  - {p['ten']} | {p['gia']:,} VND | sim={p['similarity']}")
        else:
            print("  No results")
