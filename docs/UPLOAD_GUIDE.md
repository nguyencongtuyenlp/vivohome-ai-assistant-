# 📹 Video & Screenshots Setup Guide

## 1. Video Upload Options

### Option A: GitHub (if video < 10MB)

1. **Compress video** (if needed):
   ```bash
   # Using FFmpeg
   ffmpeg -i demo-raw.mp4 -vcodec h264 -acodec aac -b:v 1M demo-compressed.mp4
   ```

2. **Upload to GitHub**:
   - Drag `demo.mp4` into `docs/` folder
   - Commit: `git add docs/demo.mp4 && git commit -m "docs: add demo video"`
   - Push: `git push origin main`

3. **Get video URL**:
   - Go to GitHub repo → `docs/demo.mp4`
   - Click "Download" → Copy URL
   - Replace in README.md line 20:
     ```markdown
     https://github.com/user-attachments/assets/YOUR-VIDEO-ID-HERE
     ```

### Option B: YouTube (recommended if video > 10MB)

1. **Upload to YouTube**:
   - Set visibility: **Unlisted** (không public nhưng ai có link đều xem được)
   - Title: "VIVOHOME AI Assistant - Demo"
   - Description: Link to GitHub repo

2. **Get embed code**:
   - Click "Share" → "Embed"
   - Copy iframe code

3. **Update README.md** (line 20):
   ```markdown
   [![Demo Video](https://img.youtube.com/vi/YOUR-VIDEO-ID/maxresdefault.jpg)](https://www.youtube.com/watch?v=YOUR-VIDEO-ID)
   ```

---

## 2. Screenshots Checklist

Chụp **5 ảnh** này và save vào `docs/screenshots/`:

### ✅ Screenshot 1: `hero.png`
- **Nội dung**: Toàn bộ giao diện app (full browser window)
- **Kích thước**: 1920x1080 hoặc 1280x720
- **Format**: PNG
- **Cách chụp**: 
  - Mở app ở tab mới
  - Zoom browser = 100%
  - F11 (fullscreen) hoặc Ctrl+Shift+S (screenshot tool)
  - Crop để loại bỏ browser toolbar (chỉ giữ nội dung app)

### ✅ Screenshot 2: `intent-detection.png`
- **Query**: "So sánh TV Samsung và LG"
- **Highlight**: Response có cả 2 hãng
- **Cách chụp**:
  - Gửi query
  - Chờ response hiển thị đầy đủ
  - Chụp phần chat (bao gồm query + response)

### ✅ Screenshot 3: `vision-ai.png`
- **Nội dung**: Upload ảnh tem nhãn + response
- **Cách chụp**:
  - Upload ảnh sản phẩm
  - Chờ response với model + giá
  - Chụp cả ảnh upload và response

### ✅ Screenshot 4: `web-search.png`
- **Query**: "iPhone 15 Pro Max giá bao nhiêu"
- **Highlight**: Web search results với links
- **Cách chụp**:
  - Gửi query
  - Chờ web results hiển thị
  - Chụp response với 3 links

### ✅ Screenshot 5: `ui-features.png`
- **Nội dung**: Accordion "Ví dụ câu hỏi" mở ra
- **Cách chụp**:
  - Click vào "💡 Ví dụ câu hỏi" để mở accordion
  - Chụp phần examples

---

## 3. Image Optimization

Sau khi chụp, optimize để giảm dung lượng:

```bash
# Using ImageMagick (nếu có)
convert hero.png -quality 85 -resize 1280x720 hero-optimized.png

# Hoặc dùng online tools:
# - TinyPNG.com
# - Squoosh.app
```

**Target size**: < 500KB mỗi ảnh

---

## 4. Upload to GitHub

```bash
# 1. Add screenshots
git add docs/screenshots/*.png

# 2. Add video (if < 10MB)
git add docs/demo.mp4

# 3. Commit
git commit -m "docs: add demo video and screenshots"

# 4. Push
git push origin main
```

---

## 5. Verify README

Sau khi push, check GitHub repo:
- [ ] Video hiển thị đúng
- [ ] 5 screenshots load được
- [ ] Layout đẹp, không bị lỗi markdown
- [ ] Links hoạt động

---

## 📝 Quick Commands

```bash
# Create folders
mkdir -p docs/screenshots

# Move screenshots (example)
mv ~/Downloads/screenshot1.png docs/screenshots/hero.png
mv ~/Downloads/screenshot2.png docs/screenshots/intent-detection.png
mv ~/Downloads/screenshot3.png docs/screenshots/vision-ai.png
mv ~/Downloads/screenshot4.png docs/screenshots/web-search.png
mv ~/Downloads/screenshot5.png docs/screenshots/ui-features.png

# Add & commit
git add docs/
git commit -m "docs: add demo assets"
git push origin main
```

---

## 🎨 Pro Tips

1. **Consistent sizing**: Tất cả screenshots nên cùng width (1280px recommended)
2. **Clean UI**: Xóa chat history trước khi chụp
3. **High contrast**: Đảm bảo text dễ đọc
4. **No personal info**: Không để lộ email, API keys trong screenshots
5. **Compress**: Luôn optimize images trước khi commit

---

## ✅ Final Checklist

- [ ] Video uploaded (GitHub hoặc YouTube)
- [ ] 5 screenshots in `docs/screenshots/`
- [ ] README.md updated with correct URLs
- [ ] All images < 500KB
- [ ] Pushed to GitHub
- [ ] Verified on GitHub web interface
