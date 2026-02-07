"""
VIVOHOME - Query Parser
Phân tích intent từ user query (rule-based, no LLM)
"""

import re
from typing import Dict, List, Optional

# === INTENT PATTERNS ===
INTENT_PATTERNS = {
    'highest_price': [
        r'giá cao nhất',
        r'đắt nhất',
        r'cao nhất',
        r'mắc nhất',
        r'price.*high',
        r'most expensive'
    ],
    'lowest_price': [
        r'giá rẻ nhất',
        r'rẻ nhất',
        r'thấp nhất',
        r'price.*low',
        r'cheapest'
    ],
    'compare': [
        r'so sánh',
        r'khác gì',
        r'compare',
        r'versus',
        r'vs'
    ]
}

# === CATEGORY PATTERNS ===
CATEGORY_PATTERNS = {
    'TV': [r'\btv\b', r'tivi', r'ti vi', r'television', r'tele'],
    'Tủ lạnh': [r'tủ lạnh', r'tu lanh', r'fridge', r'refrigerator'],
    'Máy lọc nước': [r'máy lọc nước', r'may loc nuoc', r'water filter'],
    'Bàn là': [r'bàn là', r'ban la', r'iron'],
    'Bình tắm': [r'bình tắm', r'binh tam', r'water heater', r'nước nóng'],
    'Bếp': [r'\bbếp\b', r'\bbep\b', r'stove', r'cooker'],
    'Nồi': [r'\bnồi\b', r'\bnoi\b', r'pot', r'cooker'],
    'Máy giặt': [r'máy giặt', r'may giat', r'washing machine'],
    'Máy hút ẩm': [r'máy hút ẩm', r'may hut am', r'dehumidifier']
}

# === BRAND PATTERNS ===
BRAND_PATTERNS = {
    'Samsung': [r'samsung', r'sam sung'],
    'LG': [r'\blg\b'],
    'Rossi': [r'rossi'],
    'Sunhouse': [r'sunhouse', r'sun house'],
    'Hòa Phát': [r'hòa phát', r'hoa phat'],
    'Korichi': [r'korichi'],
    'Karofi': [r'karofi']
}

def parse_query(query: str) -> Dict:
    """
    Phân tích query để trích xuất intent, category, brands
    
    Returns:
        {
            'intent': 'highest_price' | 'lowest_price' | 'compare' | 'search',
            'category': str | None,
            'brands': List[str] | None,
            'original_query': str
        }
    """
    query_lower = query.lower()
    
    result = {
        'intent': 'search',  # Default
        'category': None,
        'brands': None,
        'original_query': query
    }
    
    # Detect intent
    for intent_type, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                result['intent'] = intent_type
                break
        if result['intent'] != 'search':
            break
    
    # Detect category
    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                result['category'] = category
                break
        if result['category']:
            break
    
    # Detect brands (for comparison)
    detected_brands = []
    for brand, patterns in BRAND_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                detected_brands.append(brand)
                break
    
    if detected_brands:
        result['brands'] = detected_brands
    
    return result

# === TEST ===
if __name__ == "__main__":
    test_queries = [
        "TV giá cao nhất",
        "Tủ lạnh rẻ nhất",
        "Máy lọc nước Hòa Phát",
        "So sánh TV Samsung và LG",
        "có những loại tv nào",
        "bàn là giá bao nhiêu"
    ]
    
    print("=" * 60)
    print("QUERY PARSER TEST")
    print("=" * 60)
    
    for query in test_queries:
        result = parse_query(query)
        print(f"\nQuery: '{query}'")
        print(f"  Intent: {result['intent']}")
        print(f"  Category: {result['category']}")
        print(f"  Brands: {result['brands']}")
