"""
VIVOHOME AI - Query Parser
Rule-based intent detection from user queries (Vietnamese + English).
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class QueryIntent:
    """Structured result from query parsing."""
    intent: str = "search"           # highest_price | lowest_price | compare | search
    category: Optional[str] = None   # TV, Tủ lạnh, Máy giặt, ...
    brands: Optional[List[str]] = None
    original_query: str = ""

    def to_dict(self) -> Dict:
        return {
            "intent": self.intent,
            "category": self.category,
            "brands": self.brands,
            "original_query": self.original_query,
        }


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

INTENT_PATTERNS: Dict[str, List[str]] = {
    "highest_price": [
        r"giá cao nhất", r"đắt nhất", r"cao nhất",
        r"mắc nhất", r"premium", r"cao cấp nhất",
        r"price.*high", r"most expensive",
    ],
    "lowest_price": [
        r"giá rẻ nhất", r"rẻ nhất", r"thấp nhất",
        r"tiết kiệm nhất", r"bình dân",
        r"price.*low", r"cheapest",
    ],
    "compare": [
        r"so sánh", r"khác gì", r"nên mua",
        r"compare", r"versus", r"\bvs\b",
    ],
}

CATEGORY_PATTERNS: Dict[str, List[str]] = {
    "TV":              [r"\btv\b", r"tivi", r"ti vi", r"television", r"tele"],
    "Tủ lạnh":         [r"tủ lạnh", r"tu lanh", r"tủ mát", r"fridge", r"refrigerator"],
    "Tủ đông":         [r"tủ đông", r"tu dong", r"freezer"],
    "Máy lọc nước":    [r"máy lọc nước", r"may loc nuoc", r"lọc nước", r"water filter"],
    "Bàn là":          [r"bàn là", r"ban la", r"bàn ủi", r"iron"],
    "Bình tắm":        [r"bình tắm", r"binh tam", r"nước nóng", r"water heater"],
    "Bếp":             [r"\bbếp\b", r"\bbep\b", r"stove", r"cooker", r"bếp từ", r"bếp gas"],
    "Nồi":             [r"\bnồi\b", r"\bnoi\b", r"nồi cơm", r"pot"],
    "Máy giặt":        [r"máy giặt", r"may giat", r"washing machine"],
    "Máy hút ẩm":      [r"máy hút ẩm", r"may hut am", r"dehumidifier"],
    "Điều hòa":        [r"điều hòa", r"dieu hoa", r"máy lạnh", r"air con"],
    "Quạt":            [r"\bquạt\b", r"\bquat\b", r"fan"],
}

BRAND_PATTERNS: Dict[str, List[str]] = {
    "Samsung":   [r"samsung", r"sam sung"],
    "LG":        [r"\blg\b"],
    "Panasonic": [r"panasonic"],
    "Toshiba":   [r"toshiba"],
    "Rossi":     [r"rossi"],
    "Sunhouse":  [r"sunhouse", r"sun house"],
    "Hòa Phát":  [r"hòa phát", r"hoa phat", r"hoà phát"],
    "Korichi":   [r"korichi"],
    "Karofi":    [r"karofi"],
    "Kangaroo":  [r"kangaroo"],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_query(query: str) -> Dict:
    """
    Parse a user query to extract intent, category, and brands.

    Returns a dict (not QueryIntent) for backward compatibility with
    existing callers.
    """
    q = query.lower()
    result = QueryIntent(original_query=query)

    # Detect intent
    for intent_type, patterns in INTENT_PATTERNS.items():
        if any(re.search(p, q) for p in patterns):
            result.intent = intent_type
            break

    # Detect category
    for category, patterns in CATEGORY_PATTERNS.items():
        if any(re.search(p, q) for p in patterns):
            result.category = category
            break

    # Detect brands
    detected = [
        brand for brand, patterns in BRAND_PATTERNS.items()
        if any(re.search(p, q) for p in patterns)
    ]
    if detected:
        result.brands = detected

    return result.to_dict()


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_queries = [
        "TV giá cao nhất",
        "Tủ lạnh rẻ nhất",
        "Máy lọc nước Hòa Phát",
        "So sánh TV Samsung và LG",
        "có những loại tv nào",
        "bàn là giá bao nhiêu",
        "điều hòa Panasonic",
        "quạt Sunhouse",
    ]

    print("=" * 60)
    print("QUERY PARSER TEST")
    print("=" * 60)

    for q in test_queries:
        r = parse_query(q)
        print(f"\n  Query:    '{q}'")
        print(f"  Intent:   {r['intent']}")
        print(f"  Category: {r['category']}")
        print(f"  Brands:   {r['brands']}")
