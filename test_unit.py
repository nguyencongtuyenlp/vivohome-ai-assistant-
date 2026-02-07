"""
VIVOHOME AI - Comprehensive Unit Tests
Test coverage for query parser, database, and integration
"""

import pytest
import os
from query_parser import parse_query
from database import search_by_keywords, search_with_intent, search_by_model, init_database

# Setup: Ensure database exists
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Initialize database before tests"""
    if not os.path.exists("vivohome.db"):
        print("\n🗄️  Creating test database...")
        init_database()
    yield
    # Cleanup not needed - keep DB for future tests

# ============================================================
# TEST 1: Query Parser - Intent Detection
# ============================================================

class TestQueryParser:
    """Test intent detection and category extraction"""
    
    def test_highest_price_intent(self):
        """Test: 'TV giá cao nhất' should detect highest_price intent"""
        result = parse_query("TV giá cao nhất")
        assert result['intent'] == 'highest_price', "Should detect highest_price intent"
        assert result['category'] == 'TV', "Should extract TV category"
        assert result['brands'] is None, "Should not detect brands"
    
    def test_lowest_price_intent(self):
        """Test: 'Tủ lạnh rẻ nhất' should detect lowest_price intent"""
        result = parse_query("Tủ lạnh rẻ nhất")
        assert result['intent'] == 'lowest_price', "Should detect lowest_price intent"
        assert result['category'] == 'Tủ lạnh', "Should extract Tủ lạnh category"
    
    def test_compare_intent(self):
        """Test: 'So sánh TV Samsung và LG' should detect compare intent"""
        result = parse_query("So sánh TV Samsung và LG")
        assert result['intent'] == 'compare', "Should detect compare intent"
        assert result['category'] == 'TV', "Should extract TV category"
        assert 'Samsung' in result['brands'], "Should detect Samsung brand"
        assert 'LG' in result['brands'], "Should detect LG brand"
    
    def test_normal_search_intent(self):
        """Test: Normal search without special intent"""
        result = parse_query("Máy lọc nước Hòa Phát")
        assert result['intent'] == 'search', "Should default to search intent"
        assert result['category'] == 'Máy lọc nước', "Should extract category"
        assert 'Hòa Phát' in result['brands'], "Should detect Hòa Phát brand"
    
    def test_category_detection_variations(self):
        """Test: Category detection with different spellings"""
        # TV variations
        assert parse_query("tivi giá bao nhiêu")['category'] == 'TV'
        assert parse_query("ti vi Samsung")['category'] == 'TV'
        
        # Bàn là
        assert parse_query("bàn là Sunhouse")['category'] == 'Bàn là'

# ============================================================
# TEST 2: Database - Search Functions
# ============================================================

class TestDatabase:
    """Test database search functions"""
    
    def test_search_by_keywords_found(self):
        """Test: Search by keywords should find products"""
        result = search_by_keywords("Rossi")
        assert result['found'] == True, "Should find Rossi products"
        assert result['count'] > 0, "Should return at least 1 product"
        assert 'products' in result, "Should contain products list"
    
    def test_search_by_keywords_not_found(self):
        """Test: Search for non-existent product"""
        result = search_by_keywords("iPhone 15 Pro Max")
        assert result['found'] == False, "Should not find iPhone"
    
    def test_search_by_model_found(self):
        """Test: Search by exact model code"""
        result = search_by_model("RPG 15SQ")
        assert result['found'] == True, "Should find model RPG 15SQ"
        assert 'Rossi' in result['ten_san_pham'].upper(), "Should be Rossi product"
    
    def test_search_by_model_not_found(self):
        """Test: Search for non-existent model"""
        result = search_by_model("NOTEXIST123")
        assert result['found'] == False, "Should not find non-existent model"
    
    def test_vietnamese_text_search(self):
        """Test: Vietnamese text matching"""
        result = search_by_keywords("bàn là")
        assert result['found'] == True, "Should find 'bàn là' products"
        
        result2 = search_by_keywords("tủ lạnh")
        assert result2['found'] == True, "Should find 'tủ lạnh' products"

# ============================================================
# TEST 3: Intent-Based Search
# ============================================================

class TestIntentSearch:
    """Test intent-based search logic"""
    
    def test_highest_price_search(self):
        """Test: Highest price query should return most expensive product"""
        intent = parse_query("TV giá cao nhất")
        result = search_with_intent("TV giá cao nhất", intent, max_results=1)
        
        assert result['found'] == True, "Should find TV products"
        assert result['count'] == 1, "Should return exactly 1 product"
        
        # Verify it's the most expensive TV (Samsung 75" = 19.5M)
        product = result['products'][0]
        assert product['gia'] >= 19000000, "Should be the most expensive TV"
    
    def test_lowest_price_search(self):
        """Test: Lowest price query should return cheapest product"""
        intent = parse_query("Tủ lạnh rẻ nhất")
        result = search_with_intent("Tủ lạnh rẻ nhất", intent, max_results=1)
        
        assert result['found'] == True, "Should find fridge products"
        assert result['count'] == 1, "Should return exactly 1 product"
        
        # Verify it's a fridge
        product = result['products'][0]
        assert 'lạnh' in product['ten'].lower(), "Should be a fridge"
    
    def test_compare_search(self):
        """Test: Compare query should return multiple products"""
        intent = parse_query("So sánh TV Samsung và LG")
        result = search_with_intent("So sánh TV Samsung và LG", intent, max_results=5)
        
        assert result['found'] == True, "Should find products"
        # Should find at least LG (Samsung might not be in DB)
        assert result['count'] >= 1, "Should return at least 1 product"
    
    def test_category_filtering(self):
        """Test: Category filter should only return matching category"""
        intent = {'intent': 'search', 'category': 'TV', 'brands': None}
        result = search_with_intent("TV", intent, max_results=10)
        
        if result['found']:
            # All products should contain TV-related keywords
            for product in result['products']:
                name_lower = product['ten'].lower()
                assert any(kw in name_lower for kw in ['tv', 'tivi', 'ti vi']), \
                    f"Product {product['ten']} should be a TV"

# ============================================================
# TEST 4: Integration Tests
# ============================================================

class TestIntegration:
    """Test end-to-end workflows"""
    
    def test_full_search_workflow(self):
        """Test: Complete search workflow from query to result"""
        # Step 1: User query
        query = "TV giá cao nhất"
        
        # Step 2: Parse intent
        intent = parse_query(query)
        assert intent['intent'] == 'highest_price'
        assert intent['category'] == 'TV'
        
        # Step 3: Search with intent
        result = search_with_intent(query, intent, max_results=1)
        
        # Step 4: Verify result
        assert result['found'] == True
        assert len(result['products']) == 1
        assert result['products'][0]['gia'] > 0
    
    def test_multiple_queries(self):
        """Test: Multiple different queries in sequence"""
        queries = [
            "TV giá cao nhất",
            "Tủ lạnh rẻ nhất",
            "Máy lọc nước Hòa Phát",
            "Bình tắm Rossi"
        ]
        
        for query in queries:
            intent = parse_query(query)
            result = search_with_intent(query, intent)
            # All queries should return results (we have these products)
            assert result['found'] == True, f"Query '{query}' should find results"
    
    def test_edge_cases(self):
        """Test: Edge cases and error handling"""
        # Empty query
        result = search_by_keywords("")
        assert result['found'] == False, "Empty query should return no results"
        
        # Very long query
        long_query = "TV " * 100
        result = search_by_keywords(long_query)
        # Should not crash, may or may not find results
        assert 'found' in result, "Should handle long queries"

# ============================================================
# TEST 5: Performance Tests
# ============================================================

class TestPerformance:
    """Test performance and response times"""
    
    def test_search_speed(self):
        """Test: Search should complete within reasonable time"""
        import time
        
        start = time.time()
        result = search_by_keywords("TV")
        elapsed = time.time() - start
        
        assert elapsed < 1.0, f"Search took {elapsed:.2f}s, should be < 1s"
    
    def test_intent_parsing_speed(self):
        """Test: Intent parsing should be fast (< 10ms)"""
        import time
        
        start = time.time()
        for _ in range(100):
            parse_query("TV giá cao nhất")
        elapsed = time.time() - start
        
        avg_time = elapsed / 100
        assert avg_time < 0.01, f"Intent parsing took {avg_time*1000:.2f}ms, should be < 10ms"

# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 VIVOHOME AI - Unit Tests")
    print("=" * 60)
    pytest.main([__file__, "-v", "--tb=short"])
