"""
Quick test for intent-based search
"""

from query_parser import parse_query
from database import search_with_intent

# Test cases
test_cases = [
    "TV giá cao nhất",
    "Tủ lạnh rẻ nhất",
    "So sánh TV Samsung và LG",
    "Máy lọc nước Hòa Phát"
]

print("=" * 60)
print("INTENT-BASED SEARCH TEST")
print("=" * 60)

for query in test_cases:
    print(f"\n📝 Query: '{query}'")
    
    # Parse intent
    intent = parse_query(query)
    print(f"   Intent: {intent['intent']}")
    print(f"   Category: {intent['category']}")
    print(f"   Brands: {intent['brands']}")
    
    # Search
    result = search_with_intent(query, intent, max_results=3)
    
    if result.get("found"):
        print(f"   ✅ Found {result['count']} products:")
        for p in result['products']:
            print(f"      - {p['ten']} ({p['model']}): {p['gia']:,} VND")
    else:
        print("   ❌ No results")

print("\n" + "=" * 60)
