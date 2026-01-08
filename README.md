# AI Smart EXIF Restorer

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**智能照片 EXIF 修復工具 - 使用 AI 視覺分析與日期模式匹配修復照片元數據**

[功能特色](#-核心特色) • [快速開始](#-快速開始) • [使用指南](#-使用指南) • [常見問題](#-常見問題)

</div>

---

## 📋 專案簡介

這是一個專為解決照片 EXIF 遺失問題設計的智能修復工具。特別適用於：

- 📱 **LINE/WeChat 下載照片** - 遺失原始拍攝時間
- 🔄 **Google Photos 上傳錯誤** - 日期顯示不正確
- 📁 **資料夾整理的照片** - 從檔案名稱推測拍攝日期
- 🎯 **視覺相似度匹配** - 通過 AI 分析推測正確時間

### ✨ 核心特色

| 功能 | 說明 |
|------|------|
| 🧠 **AI 視覺分析** | 使用感知哈希、色彩直方圖、邊緣特徵等多維度分析 |
| 📅 **智能日期提取** | 支援多種日期格式（2024-12-25、2024年12月25日、20241225） |
| 🖥️ **雙模式支援** | CLI 命令列模式 + GUI 圖形界面 |
| 🎯 **三種處理模式** | Folder Date（資料夾日期）、Visual Match（視覺匹配）、Hybrid（混合） |
| ⏰ **智能時間推測** | 最相似、加權平均、智能插值三種演算法 |
| 💾 **自動備份** | 處理前自動備份到 `.backup` 資料夾 |
| 📊 **詳細報告** | 完整的處理統計和信心度評估 |

---

## 🚀 快速開始

### 系統需求

- Python 3.8 或以上
- Windows / macOS / Linux
- 建議 4GB+ RAM（處理大量照片時）

### 安裝

```bash
# 克隆專案
git clone https://github.com/charles5299/ai-exif-restorer.git
cd ai-exif-restorer

# 安裝依賴
pip install -r requirements.txt
```

### 依賴套件

```
Pillow>=10.0.0        # 影像處理
piexif>=1.1.3         # EXIF 讀寫
imagehash>=4.3.1      # 視覺哈希（AI 模式）
opencv-python>=4.8.0  # 電腦視覺（AI 模式）
numpy>=1.24.0         # 數值運算（AI 模式）
```

---

## 📖 使用指南

### 模式一：CLI 命令列模式（資料夾日期）

**最簡單快速的方式，從資料夾名稱提取日期**

```bash
# 基本使用 - 自動備份
python smart_exif_restorer.py --cli --folder "C:/Photos"

# 不備份原始檔案
python smart_exif_restorer.py --cli --folder "C:/Photos" --no-backup

# 強制覆蓋已有 EXIF
python smart_exif_restorer.py --cli --folder "C:/Photos" --overwrite
```

**支援的資料夾命名格式：**
- `2024-12-25`、`2024.12.25`、`2024_12_25`
- `20241225`
- `2024年12月25日`
- `12-25-2024`

**處理邏輯：**
```
✅ 有 EXIF 且日期正確 → 跳過
⚠️  無 EXIF → 寫入資料夾日期
⚠️  日期異常（<2000 或 >今天）→ 寫入資料夾日期
⚠️  與資料夾日期相差 >1 年 → 寫入資料夾日期
```

### 模式二：GUI 圖形界面模式

**啟動 GUI：**
```bash
python smart_exif_restorer.py
```

**GUI 三種處理模式：**

#### 1. Folder Date Mode（資料夾日期）
- 從資料夾/檔案名稱提取日期
- 最快速，無需參考照片
- 適合有規律命名的照片

#### 2. Visual Match Mode（視覺匹配）
- 使用 AI 視覺相似度分析
- 需要提供參考照片庫（有正確 EXIF）
- 適合 LINE/通訊軟體下載的照片

#### 3. Hybrid Mode（混合模式）
- 結合資料夾日期和視覺匹配
- 最高準確度
- 適合複雜場景

**GUI 使用步驟：**
1. 選擇目標資料夾（待修復的照片）
2. 選擇參考資料夾（有正確 EXIF 的照片庫）
3. 點擊「Load Photos」載入照片
4. 選擇要處理的照片（可單選或全選）
5. 調整相似度門檻（預設 0.70）
6. 點擊「Analyze」執行分析
7. 查看結果後點擊「Apply EXIF」寫入

---

## 🎯 使用範例

### 範例 1：處理 LINE 聊天室照片

**情境：** 從 LINE 下載了 100 張照片，上傳 Google Photos 後日期全部錯誤

**解決方案：**
```bash
# 準備資料夾結構
photos/
├── line_photos/        # LINE 下載的照片（無 EXIF）
└── phone_camera/       # 手機相簿原始照片（有正確 EXIF）

# 方法 1：使用 GUI（推薦）
python smart_exif_restorer.py
# - 目標資料夾：line_photos
# - 參考資料夾：phone_camera
# - 模式：Visual Match
# - 相似度門檻：0.70

# 方法 2：如果資料夾有日期命名
python smart_exif_restorer.py --cli --folder "photos/line_photos"
```

**結果：**
- ✅ 成功為 95/100 張照片推測正確日期
- 📊 平均信心度：87%
- 💾 原始檔案備份至 `.backup` 資料夾

### 範例 2：修復資料夾歸檔照片

**情境：** 照片按日期整理在資料夾中，但 EXIF 遺失

```bash
# 資料夾結構
archive/
├── 2024-12-25 Christmas/
├── 2024-01-01 New Year/
└── 2023-06-15 Summer Trip/

# 一鍵修復
python smart_exif_restorer.py --cli --folder "archive"
```

**輸出：**
```
================================================================================
📸 Folder Date EXIF Writer
================================================================================

📂 Scanning: archive
⚙️  Settings:
   - Auto backup: Yes
   - Overwrite existing EXIF: No
================================================================================

✅ Found 3 folders with dates

📁 Folder: Christmas
   Date: 2024-12-25
   Found 15 photos
   ✅ [No EXIF] IMG_001.jpg → 2024-12-25 12:00
   ✅ [No EXIF] IMG_002.jpg → 2024-12-25 12:02
   ...

================================================================================
📊 Processing Summary
================================================================================
Total folders: 3
Total photos: 156
  ✅ Success: 142
  ⏭️  Skipped: 14
  ❌ Failed: 0
```

### 範例 3：批次處理多個來源

```bash
# 處理多個資料夾
for folder in path/to/photos/*; do
    python smart_exif_restorer.py --cli --folder "$folder"
done
```

---

## 📁 專案結構

```
ai-exif-restorer/
├── smart_exif_restorer.py    # 主程式（CLI + GUI）
├── requirements.txt           # Python 依賴
├── README.md                  # 專案說明
├── .gitignore                 # Git 忽略規則
└── .backup/                   # 自動備份資料夾（運行時生成）
```

---

## 🔧 技術細節

### AI 視覺分析演算法

**特徵提取：**
1. **感知哈希 (Perceptual Hash)**
   - pHash: 基於 DCT 變換
   - dHash: 漸變哈希
   - aHash: 平均哈希

2. **色彩直方圖**
   - RGB 三通道分別分析
   - 32 bins 精細度

3. **邊緣特徵**
   - Canny 邊緣檢測
   - 邊緣密度計算

**相似度計算：**
```python
score = 0.4 × visual_similarity +
        0.3 × color_similarity +
        0.3 × edge_similarity
```

### 時間推測模式

| 模式 | 說明 | 適用場景 |
|------|------|----------|
| **Most Similar** | 使用最相似照片的時間 | 參考照片品質高 |
| **Weighted Avg** | 加權平均相似照片的時間 | 有多張相似照片 |
| **Interpolate** | 在相似照片時間範圍內插值 | 連續拍攝的照片 |

### EXIF 寫入策略

為確保 Google Photos 正確識別，寫入三個日期欄位：
- `DateTime` - 修改時間
- `DateTimeOriginal` - 原始拍攝時間
- `DateTimeDigitized` - 數位化時間

---

## ❓ 常見問題

<details>
<summary><b>Q: 為什麼需要備份？</b></summary>

A: 寫入 EXIF 會修改原始檔案。雖然程式經過測試，但為了安全起見，建議保留備份。備份檔案儲存在同資料夾的 `.backup` 子目錄中。
</details>

<details>
<summary><b>Q: 支援哪些圖片格式？</b></summary>

A: 目前支援 `.jpg`、`.jpeg`、`.png`、`.heic`。HEIC 格式需要額外安裝 `pillow-heif` 套件。
</details>

<details>
<summary><b>Q: 視覺匹配的準確度如何？</b></summary>

A: 取決於參考照片的品質和數量。一般情況下：
- 高品質參照庫：85-95% 準確度
- 中等品質：70-85% 準確度
- 低品質/無參照：< 70% 建議使用資料夾日期模式
</details>

<details>
<summary><b>Q: 處理速度如何？</b></summary>

A:
- CLI 資料夾模式：~100 張/秒
- GUI 視覺匹配：~2-5 張/秒（取決於 CPU）
- 建議批次處理大量照片
</details>

<details>
<summary><b>Q: 可以恢復備份的檔案嗎？</b></summary>

A: 可以。備份檔案位於 `.backup` 資料夾，手動複製回原位置即可覆蓋修改後的檔案。
</details>

<details>
<summary><b>Q: 處理後上傳 Google Photos 日期還是錯？</b></summary>

A: 請確認：
1. 已寫入三個日期欄位（DateTime, DateTimeOriginal, DateTimeDigitized）
2. 日期格式正確（YYYY:MM:DD HH:MM:SS）
3. 重新上傳檔案（Google Photos 會快取 EXIF）
</details>

---

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

**貢獻方向：**
- 支援更多圖片格式（WebP, AVIF）
- 改進 AI 演算法準確度
- 新增多語言介面
- 效能優化

---

## 📄 授權

本專案採用 [MIT License](LICENSE)

```
MIT License

Copyright (c) 2025 Charles

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

## 🙏 致謝

本專案使用以下開源庫：

- [Pillow](https://python-pillow.org/) - 影像處理
- [piexif](https://pypi.org/project/piexif/) - EXIF 操作
- [ImageHash](https://github.com/JohannesBuchner/imagehash) - 視覺哈希
- [OpenCV](https://opencv.org/) - 電腦視覺
- [NumPy](https://numpy.org/) - 數值運算

---

## 📮 聯絡方式

- **GitHub Issues:** [回報問題](https://github.com/charles5299/ai-exif-restorer/issues)
- **Email:** charles5299@users.noreply.github.com

---

<div align="center">

**如果這個專案對你有幫助，請給一個 ⭐ Star！**

Made with ❤️ by Charles

</div>
