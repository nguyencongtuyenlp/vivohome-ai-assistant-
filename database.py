"""
VIVOHOME - Database Setup
Chuyển từ CSV sang SQLite
"""

import sqlite3
import pandas as pd
import os

DB_PATH = "vivohome.db"

def init_database():
    """Tạo database và import dữ liệu từ CSV"""
    
    # Đọc CSV (use semicolon separator for European/Vietnamese Excel format)
    print("📂 Đọc product.csv...")
    try:
        df = pd.read_csv("product.csv", encoding='utf-8-sig', sep=';', 
                         on_bad_lines='skip', engine='python')
    except Exception as e:
        print(f"⚠️ Trying comma separator: {e}")
        df = pd.read_csv("product.csv", encoding='utf-8-sig', 
                         on_bad_lines='skip', engine='python')
    
    df.columns = df.columns.str.strip()
    print(f"📊 Found columns: {list(df.columns)}")
    print(f"📊 Total rows in CSV: {len(df)}")
    
    # Tạo connection
    print("🗄️  Tạo SQLite database...")
    conn = sqlite3.connect(DB_PATH)
    
    # Drop existing table to rebuild
    conn.execute("DROP TABLE IF EXISTS products")
    
    # Tạo bảng products (allow NULL for ten_san_pham to avoid errors)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stt INTEGER,
        nhom_hang TEXT,
        nhom_hang_loai TEXT,
        ten_san_pham TEXT,
        model TEXT,
        thong_so_chinh TEXT,
        gia INTEGER,
        mo_ta TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Import data with error handling
    print(f"📥 Importing products...")
    success_count = 0
    error_count = 0
    
    for idx, row in df.iterrows():
        try:
            ten = row.get('Tên sản phẩm') or row.get('Tên sản phẩm'.strip())
            
            # Skip rows without product name
            if pd.isna(ten) or not str(ten).strip():
                continue
            
            # Parse price (handle various formats)
            gia_raw = row.get('Giá (VND)') or row.get('Giá') or 0
            try:
                if pd.isna(gia_raw):
                    gia = 0
                else:
                    gia = int(float(str(gia_raw).replace(',', '').replace('.', '')))
            except:
                gia = 0
            
            conn.execute("""
            INSERT INTO products 
            (stt, nhom_hang, nhom_hang_loai, ten_san_pham, model, thong_so_chinh, gia, mo_ta)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get('STT'),
                row.get('Nhóm hàng') or row.get('Nhóm hàng '.strip()),
                row.get('Nhóm hàng/Loại'),
                str(ten).strip(),
                row.get('Model'),
                row.get('Thông số chính'),
                gia,
                row.get('Mô tả')
            ))
            success_count += 1
        except Exception as e:
            error_count += 1
            if error_count <= 5:  # Only show first 5 errors
                print(f"⚠️ Row {idx} error: {e}")
    
    conn.commit()
    
    # Tạo indexes để tăng tốc search
    print("🔍 Tạo indexes...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON products(model)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ten ON products(ten_san_pham)")
    conn.commit()
    
    # Verify
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    print(f"✅ Hoàn thành! Database có {count} sản phẩm (success: {success_count}, errors: {error_count})")
    
    conn.close()

def get_db_connection():
    """Lấy connection tới database"""
    if not os.path.exists(DB_PATH):
        print("⚠️  Database chưa tồn tại. Đang tạo...")
        init_database()
    return sqlite3.connect(DB_PATH)

def search_by_model(model_code: str):
    """Tìm sản phẩm theo Model"""
    conn = get_db_connection()
    cursor = conn.execute(
        "SELECT * FROM products WHERE model LIKE ? LIMIT 1",
        (f"%{model_code}%",)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "found": True,
            "id": row[0],
            "ten_san_pham": row[4],
            "model": row[5],
            "gia": row[7],
            "nhom_hang": row[3],
            "thong_so": row[6]
        }
    return {"found": False}

def search_by_keywords(query: str, max_results: int = 3):
    """Tìm sản phẩm theo từ khóa - Vietnamese-aware"""
    conn = get_db_connection()
    
    # Validate query
    if not query or not query.strip():
        conn.close()
        return {"found": False}
    
    # Normalize query (lowercase for comparison)
    query_lower = query.lower()
    keywords = query_lower.split()
    
    if not keywords:
        conn.close()
        return {"found": False}
    
    # Fetch all products (small dataset, this is OK)
    cursor = conn.execute("SELECT * FROM products")
    all_products = cursor.fetchall()
    conn.close()
    
    # Score each product
    scored_products = []
    for row in all_products:
        ten = (row[4] or "").lower()
        model = (row[5] or "").lower()
        thong_so = (row[6] or "").lower()
        
        # Calculate score
        score = 0
        for kw in keywords:
            if kw in ten:
                score += 3  # Name match = highest priority
            if kw in model:
                score += 2  # Model match = medium priority
            if kw in thong_so:
                score += 1  # Spec match = low priority
        
        if score > 0:
            scored_products.append((score, row))
    
    # Sort by score and take top results
    scored_products.sort(reverse=True, key=lambda x: x[0])
    top_results = scored_products[:max_results]
    
    if top_results:
        products = []
        for score, row in top_results:
            products.append({
                "ten": row[4],
                "model": row[5] or "N/A",
                "gia": row[7]
            })
        return {"found": True, "count": len(products), "products": products}
    
    return {"found": False}

def search_with_intent(query: str, intent: dict, max_results: int = 3):
    """
    Smart search với intent detection
    
    Args:
        query: Original query string
        intent: Dict from query_parser.parse_query()
        max_results: Max number of results
    
    Returns:
        Dict with found, count, products
    """
    conn = get_db_connection()
    
    # Fetch all products
    cursor = conn.execute("SELECT * FROM products")
    all_products = cursor.fetchall()
    conn.close()
    
    # Step 1: Filter by category if specified
    if intent.get('category'):
        category_lower = intent['category'].lower()
        filtered = []
        for row in all_products:
            ten = (row[4] or "").lower()
            # Flexible matching: "TV" matches "TIVI", "Ti vi", etc.
            if category_lower == 'tv':
                if any(keyword in ten for keyword in ['tv', 'tivi', 'ti vi', 'tele', 'sam sung', 'samsung', 'lg']):
                    filtered.append(row)
            elif category_lower in ten:
                filtered.append(row)
        all_products = filtered
    
    # Step 2: Filter by brands if specified (for comparison)
    if intent.get('brands') and intent['intent'] == 'compare':
        # For comparison: collect products for EACH brand separately
        brand_products = {}
        for brand in intent['brands']:
            brand_lower = brand.lower()
            brand_products[brand] = []
            for row in all_products:
                ten = (row[4] or "").lower()
                model = (row[5] or "").lower()
                nsx = (row[6] or "").lower()  # Manufacturer column
                if brand_lower in ten or brand_lower in model or brand_lower in nsx:
                    brand_products[brand].append(row)
        
        # Take best from each brand (avoid duplicates)
        all_products = []
        seen_models = set()
        for brand, products in brand_products.items():
            # Sort by price DESC to get featured product per brand
            sorted_prods = sorted(products, key=lambda x: x[7] or 0, reverse=True)
            for p in sorted_prods[:2]:  # Take top 2 per brand
                model = p[5] or ""
                if model not in seen_models:
                    all_products.append(p)
                    seen_models.add(model)
    
    elif intent.get('brands'):
        # Normal brand filter
        brand_filtered = []
        for row in all_products:
            ten = (row[4] or "").lower()
            model = (row[5] or "").lower()
            nsx = (row[6] or "").lower()
            for brand in intent['brands']:
                if brand.lower() in ten or brand.lower() in model or brand.lower() in nsx:
                    brand_filtered.append(row)
                    break
        all_products = brand_filtered
    
    # Step 3: Deduplicate by model
    seen_models = set()
    unique_products = []
    for row in all_products:
        model = row[5] or ""
        if model and model not in seen_models:
            unique_products.append(row)
            seen_models.add(model)
        elif not model:  # Keep products without model
            unique_products.append(row)
    all_products = unique_products
    
    # Step 4: Apply intent-specific logic
    if intent['intent'] == 'highest_price' and all_products:
        # Sort by price DESC, take top 1
        sorted_products = sorted(all_products, key=lambda x: x[7] or 0, reverse=True)
        all_products = sorted_products[:1]
    
    elif intent['intent'] == 'lowest_price' and all_products:
        # Sort by price ASC, take top 1
        sorted_products = sorted(all_products, key=lambda x: x[7] or 0)
        all_products = sorted_products[:1]
    
    elif intent['intent'] == 'compare' and all_products:
        # Sort by price for comparison, take more
        sorted_products = sorted(all_products, key=lambda x: x[7] or 0, reverse=True)
        all_products = sorted_products
        max_results = min(6, len(all_products))
    
    # Step 5: Format results
    if all_products:
        products = []
        for row in all_products[:max_results]:
            products.append({
                "ten": row[4],
                "model": row[5] or "N/A",
                "gia": row[7],
                "nsx": row[6] or "N/A"
            })
        return {"found": True, "count": len(products), "products": products}
    
    return {"found": False}

# === TEST ===
if __name__ == "__main__":
    print("=" * 50)
    print("VIVOHOME Database Setup")
    print("=" * 50)
    
    # Khởi tạo database
    init_database()
    
    # Test search
    print("\n" + "=" * 50)
    print("TEST: Tìm theo Model")
    result = search_by_model("RT20HAR8DBU")
    print(result)
    
    print("\n" + "=" * 50)
    print("TEST: Tìm theo keywords")
    result = search_by_keywords("Rossi 15")
    print(result)
