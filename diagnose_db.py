"""
VIVOHOME - Database Diagnostic
Kiểm tra nội dung database
"""

import sqlite3
import os

DB_PATH = "vivohome.db"

def diagnose_database():
    """Chẩn đoán database"""
    
    print("=" * 60)
    print("VIVOHOME DATABASE DIAGNOSTIC")
    print("=" * 60)
    
    # Check if DB exists
    if not os.path.exists(DB_PATH):
        print("❌ Database file NOT FOUND!")
        print(f"   Expected: {os.path.abspath(DB_PATH)}")
        return
    
    print(f"✅ Database file exists: {os.path.abspath(DB_PATH)}")
    print(f"   Size: {os.path.getsize(DB_PATH):,} bytes\n")
    
    # Connect
    conn = sqlite3.connect(DB_PATH)
    
    # Count products
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    print(f"📊 Total products: {count}\n")
    
    # Show first 5 products
    print("=" * 60)
    print("FIRST 5 PRODUCTS:")
    print("=" * 60)
    cursor = conn.execute("SELECT ten_san_pham, model, gia FROM products LIMIT 5")
    for i, row in enumerate(cursor, 1):
        print(f"{i}. {row[0]}")
        print(f"   Model: {row[1] or 'N/A'}")
        print(f"   Giá: {row[2]:,} VND\n")
    
    # Test search
    print("=" * 60)
    print("TEST SEARCHES:")
    print("=" * 60)
    
    # Test 1: Search by keyword
    test_queries = [
        ("tủ lạnh", "LOWER(ten_san_pham) LIKE '%tủ lạnh%'"),
        ("Samsung", "LOWER(ten_san_pham) LIKE '%samsung%' OR LOWER(model) LIKE '%samsung%'"),
        ("bàn là", "LOWER(ten_san_pham) LIKE '%bàn là%'"),
        ("KORICHI", "LOWER(ten_san_pham) LIKE '%korichi%' OR LOWER(model) LIKE '%korichi%'"),
    ]
    
    for query_name, where_clause in test_queries:
        cursor = conn.execute(f"SELECT COUNT(*) FROM products WHERE {where_clause}")
        count = cursor.fetchone()[0]
        status = "✅" if count > 0 else "❌"
        print(f"{status} '{query_name}': {count} results")
    
    # Show all unique brands
    print("\n" + "=" * 60)
    print("UNIQUE BRANDS/KEYWORDS:")
    print("=" * 60)
    cursor = conn.execute("SELECT DISTINCT ten_san_pham FROM products LIMIT 20")
    for row in cursor:
        # Extract brand from product name
        name = row[0]
        words = name.split()
        if len(words) > 2:
            print(f"- {' '.join(words[:3])}...")
        else:
            print(f"- {name}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    diagnose_database()
