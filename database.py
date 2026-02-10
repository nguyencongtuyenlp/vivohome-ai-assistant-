"""
VIVOHOME AI - Database Module
SQLite database for product storage and search.
Uses named column access (sqlite3.Row) instead of magic indices.
"""

import sqlite3
import os
from typing import Dict, List, Optional

import pandas as pd

from config import DB_PATH, CSV_PATH
from logger import db_logger


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """Get a database connection with Row factory for named access."""
    if not os.path.exists(DB_PATH):
        db_logger.warning("Database not found. Creating from CSV...")
        init_database()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


# ---------------------------------------------------------------------------
# Database initialisation
# ---------------------------------------------------------------------------

def init_database() -> None:
    """Create the SQLite database and import data from product.csv."""
    db_logger.info("Initializing database from %s ...", CSV_PATH)

    # Read CSV — try semicolon first (Vietnamese Excel), fall back to comma
    try:
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", sep=";",
                         on_bad_lines="skip", engine="python")
    except Exception:
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig",
                         on_bad_lines="skip", engine="python")

    df.columns = df.columns.str.strip()
    db_logger.info("CSV loaded: %d rows, columns=%s", len(df), list(df.columns))

    conn = sqlite3.connect(DB_PATH)

    # Rebuild table
    conn.execute("DROP TABLE IF EXISTS products")
    conn.execute("""
        CREATE TABLE products (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            stt             INTEGER,
            nhom_hang       TEXT,
            nhom_hang_loai  TEXT,
            ten_san_pham    TEXT,
            model           TEXT,
            thong_so_chinh  TEXT,
            gia             INTEGER DEFAULT 0,
            mo_ta           TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    success, errors = 0, 0
    for idx, row in df.iterrows():
        try:
            ten = row.get("Tên sản phẩm")
            if pd.isna(ten) or not str(ten).strip():
                continue

            gia = _parse_price(row.get("Giá (VND)") or row.get("Giá") or 0)

            conn.execute("""
                INSERT INTO products
                    (stt, nhom_hang, nhom_hang_loai, ten_san_pham, model,
                     thong_so_chinh, gia, mo_ta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get("STT"),
                row.get("Nhóm hàng"),
                row.get("Nhóm hàng/Loại"),
                str(ten).strip(),
                row.get("Model"),
                row.get("Thông số chính"),
                gia,
                row.get("Mô tả"),
            ))
            success += 1
        except Exception as exc:
            errors += 1
            if errors <= 5:
                db_logger.warning("Row %d import error: %s", idx, exc)

    conn.commit()

    # Indexes for fast lookup
    conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON products(model)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ten ON products(ten_san_pham)")
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    db_logger.info("Database ready — %d products (success=%d, errors=%d)",
                   count, success, errors)
    conn.close()


def _parse_price(raw) -> int:
    """Robustly parse a price string/number into an integer."""
    if pd.isna(raw):
        return 0
    try:
        # Convert to float first (handles '250000.0'), then to int
        # Only strip commas (thousands separator), NOT dots (decimal point)
        cleaned = str(raw).replace(",", "")
        return int(float(cleaned))
    except (ValueError, TypeError):
        return 0


# ---------------------------------------------------------------------------
# Search functions
# ---------------------------------------------------------------------------

def search_by_model(model_code: str) -> Dict:
    """Find a product by exact model code (LIKE match)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE model LIKE ? LIMIT 1",
            (f"%{model_code}%",),
        ).fetchone()

    if row:
        return {
            "found": True,
            "id": row["id"],
            "ten_san_pham": row["ten_san_pham"],
            "model": row["model"],
            "gia": row["gia"],
            "nhom_hang": row["nhom_hang_loai"],
            "thong_so": row["thong_so_chinh"],
        }
    return {"found": False}


def search_by_keywords(query: str, max_results: int = 3) -> Dict:
    """Score-based keyword search across product name, model, and specs."""
    if not query or not query.strip():
        return {"found": False}

    keywords = query.lower().split()
    if not keywords:
        return {"found": False}

    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM products").fetchall()

    scored: List = []
    for row in rows:
        ten = (row["ten_san_pham"] or "").lower()
        model = (row["model"] or "").lower()
        specs = (row["thong_so_chinh"] or "").lower()

        score = sum(
            (3 if kw in ten else 0) +
            (2 if kw in model else 0) +
            (1 if kw in specs else 0)
            for kw in keywords
        )
        if score > 0:
            scored.append((score, row))

    scored.sort(reverse=True, key=lambda x: x[0])

    if scored:
        products = [
            {"ten": r["ten_san_pham"], "model": r["model"] or "N/A", "gia": r["gia"]}
            for _, r in scored[:max_results]
        ]
        return {"found": True, "count": len(products), "products": products}
    return {"found": False}


def search_with_intent(query: str, intent: Dict, max_results: int = 3) -> Dict:
    """
    Smart search using parsed intent (category, brands, price ordering).

    Args:
        query: Original user query.
        intent: Output of query_parser.parse_query().
        max_results: Maximum products to return.
    """
    with get_connection() as conn:
        rows = list(conn.execute("SELECT * FROM products").fetchall())

    # Step 1 — filter by category
    if intent.get("category"):
        rows = _filter_by_category(rows, intent["category"])

    # Step 2 — filter / group by brand
    if intent.get("brands") and intent["intent"] == "compare":
        rows = _collect_comparison_brands(rows, intent["brands"])
    elif intent.get("brands"):
        rows = _filter_by_brands(rows, intent["brands"])

    # Step 3 — deduplicate by model
    rows = _deduplicate(rows)

    # Step 4 — sort by intent
    if intent["intent"] == "highest_price" and rows:
        rows = sorted(rows, key=lambda r: r["gia"] or 0, reverse=True)[:1]
    elif intent["intent"] == "lowest_price" and rows:
        rows = sorted(rows, key=lambda r: r["gia"] or 0)[:1]
    elif intent["intent"] == "compare" and rows:
        rows = sorted(rows, key=lambda r: r["gia"] or 0, reverse=True)
        max_results = min(6, len(rows))

    # Step 5 — format output
    if rows:
        products = [
            {
                "ten": r["ten_san_pham"],
                "model": r["model"] or "N/A",
                "gia": r["gia"],
                "nsx": r["thong_so_chinh"] or "N/A",
            }
            for r in rows[:max_results]
        ]
        return {"found": True, "count": len(products), "products": products}
    return {"found": False}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_TV_KEYWORDS = ("tv", "tivi", "ti vi", "tele", "television")


def _filter_by_category(rows: List, category: str) -> List:
    cat = category.lower()
    filtered = []
    for r in rows:
        ten = (r["ten_san_pham"] or "").lower()
        if cat == "tv":
            if any(kw in ten for kw in _TV_KEYWORDS):
                filtered.append(r)
        elif cat in ten:
            filtered.append(r)
    return filtered


def _filter_by_brands(rows: List, brands: List[str]) -> List:
    result = []
    for r in rows:
        text = " ".join([
            (r["ten_san_pham"] or ""),
            (r["model"] or ""),
            (r["thong_so_chinh"] or ""),
        ]).lower()
        if any(b.lower() in text for b in brands):
            result.append(r)
    return result


def _collect_comparison_brands(rows: List, brands: List[str]) -> List:
    """For comparison queries: pick top products from each brand."""
    seen_models: set = set()
    result = []
    for brand in brands:
        brand_lower = brand.lower()
        brand_rows = [
            r for r in rows
            if brand_lower in " ".join([
                (r["ten_san_pham"] or ""),
                (r["model"] or ""),
                (r["thong_so_chinh"] or ""),
            ]).lower()
        ]
        brand_rows.sort(key=lambda r: r["gia"] or 0, reverse=True)
        for r in brand_rows[:2]:
            model = r["model"] or ""
            if model not in seen_models:
                result.append(r)
                seen_models.add(model)
    return result


def _deduplicate(rows: List) -> List:
    seen: set = set()
    unique = []
    for r in rows:
        model = r["model"] or ""
        if model and model not in seen:
            unique.append(r)
            seen.add(model)
        elif not model:
            unique.append(r)
    return unique


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 50)
    print("VIVOHOME Database Setup")
    print("=" * 50)

    init_database()

    print("\nTEST: search_by_model('RT20HAR8DBU')")
    print(search_by_model("RT20HAR8DBU"))

    print("\nTEST: search_by_keywords('Rossi 15')")
    print(search_by_keywords("Rossi 15"))
