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
| 📍 **GPS 支援** | 讀取、顯示和寫入 GPS 座標資訊，保留或複製地點資訊 |
| 🧹 **資料清理階段** | 自動偵測系統檔案、縮圖、截圖並分離處理 |
| 🔍 **重複偵測與合併** | iOS 風格合併選項（保留最佳品質、時間軸、智慧合併等） |
| 🖥️ **雙模式支援** | CLI 命令列模式 + GUI 圖形界面 |
| 🎯 **三種處理模式** | Folder Date（資料夾日期）、Visual Match（視覺匹配）、Hybrid（混合） |
| ⏰ **智能時間推測** | 最相似、加權平均、智能插值三種演算法 |
| 💾 **自動備份** | 處理前自動備份到 `.backup` 資料夾 |
| 📊 **詳細報告** | 完整的處理統計和信心度評估 |
| 🎨 **直觀介面** | EXIF/GPS 狀態一目了然，支援篩選和排序 |

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

### 完整工作流程（推薦）

**CLI 模式現在包含三個階段：**
1. **資料清理階段** - 自動偵測並移除系統檔案、縮圖、截圖
2. **重複偵測與合併階段** - 找出重複照片並提供 iOS 風格合併選項
3. **EXIF 修復階段** - 寫入日期資料到照片

```bash
# 完整工作流程（包含所有階段）
python scripts/smart_exif_restorer.py --cli --folder "C:/Photos"

# 跳過資料清理
python scripts/smart_exif_restorer.py --cli --folder "C:/Photos" --skip-cleanup

# 跳過重複偵測
python scripts/smart_exif_restorer.py --cli --folder "C:/Photos" --skip-duplicates

# 自動合併重複照片（無需手動確認）
python scripts/smart_exif_restorer.py --cli --folder "C:/Photos" --auto-merge

# 最小化模式（僅 EXIF 修復，無清理、無重複偵測、無備份）
python scripts/smart_exif_restorer.py --cli --folder "C:/Photos" --skip-cleanup --skip-duplicates --no-backup

# 自動確認所有提示（小心使用）
python scripts/smart_exif_restorer.py --cli --folder "C:/Photos" --auto-yes
```

### 階段一：資料清理

**自動偵測並處理：**
- 系統檔案：`._`、`.DS_Store`、`Thumbs.db`、`.picasa.ini`
- 截圖檔案：`screenshot`、`截圖`、`IMG_1234 (1)` 模式

**處理選項：**
- 刪除系統檔案（移至 `.backup/cleanup`）
- 分離截圖（移至 `.backup/screenshots`）

### 階段二：重複偵測與合併

**偵測方法：**
- MD5 雜湊 - 完全相同的檔案
- 感知雜湊 (pHash) - 視覺相似的檔案

**iOS 風格合併選項：**
| 選項 | 說明 |
|------|------|
| [K] Keep All | 保留所有版本，不進行合併 |
| [B] Best Quality | 保留最高解析度版本 |
| [T] Timeline | 保留最早拍攝時間的版本 |
| [M] Smart Merge | 智慧合併（推薦）- 最佳品質 + EXIF 協調 |
| [D] Delete | 安全刪除重複（保留原始） |
| [R] Review | 手動審閱每張照片 |

### 階段三：EXIF 修復

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
python scripts/smart_exif_restorer.py
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
2. 選擇參考資料夾（有正確 EXIF 的照片庫，Folder Date 模式不需要）
3. 點擊「Load Photos」載入照片
4. 使用篩選按鈕快速識別照片狀態：
   - 📅 Has EXIF - 顯示有日期資訊的照片
   - ⚠ No EXIF - 顯示無日期資訊的照片
   - 📍 Has GPS - 顯示有地點資訊的照片
5. 選擇要處理的照片（可單選或全選）
6. 調整相似度門檻（預設 0.70）
7. 點擊「Analyze」執行分析
8. 查看結果後點擊「Apply EXIF」寫入（包含 GPS 資訊）

**GUI 界面說明：**
- **左邊 - Reference (Source)**: 參考照片庫，有完整 EXIF/GPS 的源照片
- **中間 - AI Controls**: 分析選項、時間推測模式、操作按鈕
- **右邊 - Target (Destination)**: 目標照片，需要修復 EXIF 的照片
- **照片卡片顯示**:
  - 📅 2024-01-15 (綠色) - 有 EXIF 日期
  - ⚠ No EXIF (紅色) - 無 EXIF 日期
  - 📍 25.1234, 121.5678 (藍色) - 有 GPS 座標

---

## 🎯 使用範例

### 範例 1：完整工作流程（推薦）

**情境：** 從手機匯出大量照片，包含系統檔案、重複照片、截圖，需要清理並修復 EXIF

```bash
# 執行完整工作流程（清理 + 重複偵測 + EXIF 修復）
python scripts/smart_exif_restorer.py --cli --folder "C:/Photos/Mixed"
```

**輸出流程：**
```
================================================================================
📸 AI Smart EXIF Restorer - Full Workflow
================================================================================

📂 Target: C:/Photos/Mixed
================================================================================

================================================================================
🧹 Data Cleaning Phase
================================================================================
🔍 Scanning: C:/Photos/Mixed

📊 Scan Results:
   Total files: 245
   Regular photos: 189
   System files: 12
   Screenshots: 8

⚠️  Found 12 system/thumbnail files:
    ├── ._IMG_001.jpg
    ├── Thumbs.db
    └── ... (10 more)

❓ Delete these files? (y/n/review): y
✅ System files moved: .backup/cleanup

⚠️  Found 8 screenshot files:
    ├── 截圖 2024-01-15.png
    └── ... (7 more)

❓ How to handle screenshots? (s=Skip, m=Move to folder, d=Delete): m
✅ Screenshots moved: .backup/screenshots

================================================================================
🔍 Duplicate Detection Phase
================================================================================
🔍 Scanning: C:/Photos/Mixed
⏳ Extracting features...
✅ Analyzed 189 photos

🔍 Finding duplicates...
✅ Found 3 duplicate groups
   Total duplicates: 7 photos

================================================================================
📊 Duplicate Merge Summary
================================================================================
Groups processed: 3
Photos kept: 3
Photos backed up: 7
Space saved: 45.8 MB

================================================================================
✨ EXIF Restoration Phase
================================================================================
... (EXIF processing)

================================================================================
🎉 Complete Workflow Finished
================================================================================
```

### 範例 2：處理 LINE 聊天室照片

**情境：** 從 LINE 下載了 100 張照片，上傳 Google Photos 後日期全部錯誤

```bash
# 使用 GUI（推薦用於視覺匹配）
python scripts/smart_exif_restorer.py
# - 目標資料夾：line_photos
# - 參考資料夾：phone_camera
# - 模式：Visual Match
# - 相似度門檻：0.70
```

### 範例 3：iPhone 匯出照片修復（含 GPS）

**情境：** 從 iPhone 匯出的照片，部分有 GPS 地點資訊，需要根據資料夾名稱恢復日期並保留 GPS

**GUI 操作步驟：**
```bash
# 啟動 GUI
python scripts/smart_exif_restorer.py

# 1. 選擇模式：Folder Date
# 2. 選擇目標資料夾：iPhone 匯出的照片目錄
#    例如：2024-01-15 台北之旅/
#          2024-02-20 公司聚餐/
# 3. 點擊 Load Photos
# 4. 查看照片狀態：
#    - 📅 2024-01-15 - 已有日期
#    - ⚠ No EXIF - 需要修復
#    - 📍 25.0340, 121.5644 - 有 GPS（會保留）
# 5. 全選照片 → Analyze → Apply EXIF
```

**處理結果：**
- 從資料夾名稱提取日期並寫入 EXIF
- 保留原始 GPS 座標（如果有）
- 結果顯示：`GPS: 25.0340, 121.5644 (preserved)`

### 範例 4：快速修復資料夾歸檔照片（跳過清理和重複偵測）

**情境：** 照片已經整理好，只需要快速修復 EXIF

```bash
# 資料夾結構
archive/
├── 2024-12-25 Christmas/
├── 2024-01-01 New Year/
└── 2023-06-15 Summer Trip/

# 快速修復（跳過清理和重複偵測）
python scripts/smart_exif_restorer.py --cli --folder "archive" --skip-cleanup --skip-duplicates
```

### 範例 5：批次處理多個來源

```bash
# 處理多個資料夾
for folder in path/to/photos/*; do
    python scripts/smart_exif_restorer.py --cli --folder "$folder" --skip-cleanup
done
```

---

## 📁 專案結構

```
ai-exif-restorer/
├── scripts/
│   └── smart_exif_restorer.py    # 主程式（CLI + GUI，~1800 行）
├── requirements.txt              # Python 依賴
├── README.md                     # 專案說明
├── SKILL.md                      # 功能規格文件
├── LICENSE                       # MIT 授權
├── .gitignore                    # Git 忽略規則
└── .backup/                      # 自動備份資料夾（運行時生成）
    ├── cleanup/                  # 清理的系統檔案
    ├── screenshots/              # 分離的截圖
    ├── duplicates/               # 合併的重複照片
    └── originals/                # EXIF 修改前的原始檔案
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

### GPS 處理策略

**Folder Date 模式：**
- 保留目標照片原有的 GPS 座標
- 如果照片已有 GPS，寫入日期時一併保留

**Visual Match/Hybrid 模式：**
- 從最相似的參考照片複製 GPS 座標
- 自動轉換座標格式（DMS ↔ Decimal）
- 與日期資訊一併寫入目標照片

**GPS 格式支援：**
- 讀取：標準 EXIF GPS 格式（經緯度 + 方向參考）
- 顯示：十進位格式（精確到小數點後 4 位）
- 寫入：EXIF 標準 DMS（度分秒）格式

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

<details>
<summary><b>Q: GPS 資訊會保留嗎？</b></summary>

A: 會的！
- Folder Date 模式：會保留目標照片原有的 GPS
- Visual Match/Hybrid 模式：會從參考照片複製 GPS 到目標照片
- 可以使用 📍 Has GPS 按鈕篩選查看有 GPS 的照片
</details>

<details>
<summary><b>Q: 為什麼有些照片沒有顯示 GPS？</b></summary>

A: 可能的原因：
- 原始照片沒有 GPS 資訊（例如：室內拍攝、關閉定位）
- 照片格式不支援 GPS（例如：某些 PNG 格式）
- GPS 資訊在編輯過程中丟失
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
