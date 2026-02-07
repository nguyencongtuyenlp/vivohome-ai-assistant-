import os
import subprocess
import sys

# 1. Hàm tự động cài đặt thư viện nếu thiếu
def install_and_import(package, import_name=None):
    if import_name is None: import_name = package
    try:
        __import__(import_name)
    except ImportError:
        print(f"--- Đang cài đặt {package}... ---")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Tự động sửa lỗi môi trường cho Tuyền
packages = {
    "langchain": "langchain",
    "langchain-community": "langchain_community",
    "langchain-huggingface": "langchain_huggingface",
    "faiss-cpu": "faiss",
    "sentence-transformers": "sentence_transformers",
    "pandas": "pandas"
}

for pkg, imp in packages.items():
    install_and_import(pkg, imp)

import pandas as pd
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
import glob

print("--- Môi trường: OK ---")

# 2. Đọc dữ liệu từ file của VIVOHOME
csv_files = glob.glob("*.csv")
if not csv_files:
    print("❌ Lỗi: Không tìm thấy file CSV. Tuyền hãy chắc chắn đã upload file vào cùng thư mục!")
    sys.exit()

df = pd.read_csv(csv_files[0], encoding='utf-8-sig')
df.columns = df.columns.str.strip() # Xóa khoảng trắng tên cột
df = df.astype(str)

# 3. Chuyển đổi dữ liệu
docs = []
for _, row in df.iterrows():
    text = f"Sản phẩm: {row['Tên sản phẩm']}. Model: {row['Model']}. Giá: {row['Giá (VND)']} VND. Thông số: {row['Thông số chính']}"
    docs.append(Document(page_content=text))

# 4. Tạo bộ não vector (Dùng CPU để không tranh chấp với vLLM)
print("--- Đang tạo bộ não AI (Embedding)... ---")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vector_db = FAISS.from_documents(docs, embeddings)

# 5. Lưu lại
vector_db.save_local("vivohome_vector_db")
print(f"✅ THÀNH CÔNG: Đã nạp {len(docs)} sản phẩm vào 'vivohome_vector_db'!")