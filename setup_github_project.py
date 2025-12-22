#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動生成 GitHub 專案結構和文件
執行此腳本會在當前目錄建立完整的專案結構
"""

import os
from pathlib import Path

def create_file(filename, content):
    """創建文件並寫入內容"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✓ 創建: {filename}")

def create_directory(dirname):
    """創建目錄"""
    os.makedirs(dirname, exist_ok=True)
    print(f"✓ 創建目錄: {dirname}")

def main():
    print("=" * 70)
    print("🚀 AI Smart EXIF Restorer - GitHub 專案結構生成器")
    print("=" * 70)
    print()
    
    # 獲取當前目錄
    current_dir = Path.cwd()
    print(f"當前目錄: {current_dir}")
    print()
    
    # 檢查現有檔案
    print("📋 檢查現有檔案...")
    existing_files = []
    for file in ['app.v5.py', 'exif_gui_tool.v2.py', 'app.v3.py']:
        if os.path.exists(file):
            existing_files.append(file)
            print(f"  ✓ 找到: {file}")
    
    if not existing_files:
        print("  ⚠️  警告: 找不到現有的 Python 檔案")
    print()
    
    # === 創建 README.md ===
    readme_content = """# AI Smart EXIF Restorer

🤖 使用 AI 視覺分析智能推測照片 EXIF 資訊的工具

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 📋 專案簡介

這是一個專為 **LINE 下載照片** 設計的 EXIF 補全工具。LINE 下載的照片會遺失 EXIF 資訊（拍攝時間、地點、相機型號等），本工具透過 AI 視覺分析，智能推測最合理的 EXIF 資訊。

### ✨ 核心特色

- 🧠 **AI 視覺分析**：不是簡單複製貼上，而是通過影像相似度推測最合理的時間
- 🎯 **多維度特徵匹配**：視覺哈希、色彩直方圖、邊緣特徵等多重分析
- ⏰ **智能時間推測**：三種模式（最相似、加權平均、智能插值）
- 🖼️ **圖形化介面**：直觀的照片瀏覽和批次操作
- 📊 **詳細報告**：生成完整的分析報告和信心度評估
- 💾 **安全備份**：自動備份原始檔案

## 🚀 快速開始

### 安裝依賴

```bash
pip install -r requirements.txt
```

### 使用方法

#### 方案 1：AI 智能推測系統（推薦）

```bash
python ai_exif_estimator.py
```

**適合場景：**
- 大量照片需要自動處理
- 有充足的參考照片庫
- 需要 AI 智能推測時間

#### 方案 2：人工配對工具

```bash
python exif_manual_matcher.py
```

**適合場景：**
- 自動匹配不準確時
- 需要手動確認配對關係
- 小批量照片處理

#### 方案 3：命令列自動化工具

```bash
python smart_exif_restorer.py
```

**適合場景：**
- 基於檔名的自動匹配
- 不需要圖形界面
- 腳本自動化

## 📖 詳細文檔

- [用戶指南](docs/USER_GUIDE.md) - 完整使用說明
- [API 參考](docs/API_REFERENCE.md) - 開發者文檔
- [常見問題](docs/FAQ.md) - 疑難排解

## 🎯 使用範例

### 範例 1：處理 LINE 聊天室照片

```
情境：從 LINE 下載了 50 張照片，需要補全 EXIF

步驟：
1. 準備資料夾：
   - target/     # LINE 下載的 50 張照片
   - reference/  # 手機相簿的 500 張原始照片

2. 執行 AI 分析：
   - 載入照片
   - 全選 50 張目標照片
   - 設定相似度門檻 0.70
   - 執行分析

3. 結果：
   - 成功為 48 張照片推測 EXIF
   - 信心度平均 87%
```

## 📁 專案結構

```
ai-exif-restorer/
├── ai_exif_estimator.py      # AI 智能推測系統
├── exif_manual_matcher.py    # 人工配對工具
├── smart_exif_restorer.py    # 命令列工具
├── requirements.txt           # 依賴套件
├── README.md                  # 專案說明
├── LICENSE                    # MIT 授權
├── .gitignore                 # Git 忽略規則
├── docs/                      # 文檔資料夾
│   ├── USER_GUIDE.md
│   ├── API_REFERENCE.md
│   └── FAQ.md
└── examples/                  # 範例腳本
    └── batch_process.py
```

## 🔧 系統需求

- Python 3.8 或以上
- Windows / macOS / Linux
- 至少 2GB RAM（處理大量照片時建議 4GB+）

## 📦 依賴套件

```
Pillow>=10.0.0        # 影像處理
piexif>=1.1.3         # EXIF 操作
imagehash>=4.3.1      # 視覺哈希
opencv-python>=4.8.0  # 電腦視覺
numpy>=1.24.0         # 數值運算
```

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權

本專案採用 [MIT License](LICENSE)

## 🙏 致謝

- [Pillow](https://python-pillow.org/)
- [piexif](https://pypi.org/project/piexif/)
- [ImageHash](https://github.com/JohannesBuchner/imagehash)
- [OpenCV](https://opencv.org/)

## 📮 聯絡

- GitHub Issues: [回報問題](https://github.com/charles5299/ai-exif-restorer/issues)

---

⭐ 如果這個專案對你有幫助，請給一個 Star！
"""
    
    create_file("README.md", readme_content)
    
    # === 創建 requirements.txt ===
    requirements_content = """# 影像處理核心
Pillow>=10.0.0
piexif>=1.1.3

# AI 視覺分析
imagehash>=4.3.1
opencv-python>=4.8.0
numpy>=1.24.0
"""
    
    create_file("requirements.txt", requirements_content)
    
    # === 創建 .gitignore ===
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# 虛擬環境
venv/
ENV/
env/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# 測試資料和照片（重要！避免上傳大量照片）
target_dir/
reference_dir/
target/
reference/
test_photos/
test_data/
*.jpg
*.jpeg
*.png
*.heic
*.JPG
*.JPEG
*.PNG
*.HEIC

# 備份資料夾
.backup/
backup/

# 日誌和臨時文件
*.log
*.tmp
*.cache

# 分析結果
analysis_results/
reports/
output/

# 配對表（可能包含隱私路徑）
*.txt
!requirements.txt

# 系統文件
Thumbs.db
desktop.ini
.DS_Store
"""
    
    create_file(".gitignore", gitignore_content)
    
    # === 創建 LICENSE ===
    license_content = """MIT License

Copyright (c) 2024 [charles5299]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
    
    create_file("LICENSE", license_content)
    
    # === 創建 docs 目錄和文檔 ===
    create_directory("docs")
    
    user_guide_content = """# 用戶指南

## 目錄
- [安裝](#安裝)
- [快速開始](#快速開始)
- [功能詳解](#功能詳解)
- [常見問題](#常見問題)

## 安裝

### 1. 安裝 Python
確保已安裝 Python 3.8 或以上版本。

### 2. 安裝依賴套件
```bash
pip install -r requirements.txt
```

## 快速開始

### AI 智能推測系統

1. 準備資料夾
2. 執行程式：`python ai_exif_estimator.py`
3. 選擇目標和參考資料夾
4. 選擇照片並執行分析

詳細步驟請參考 README.md

## 功能詳解

### 視覺相似度分析
使用感知哈希演算法比對照片相似度...

### 時間推測模式
- 最相似模式
- 加權平均模式
- 智能插值模式

## 常見問題

請參考 [FAQ.md](FAQ.md)
"""
    
    create_file("docs/USER_GUIDE.md", user_guide_content)
    
    api_reference_content = """# API 參考

## 核心類別

### AIExifEstimator

AI 智能 EXIF 推測系統的主類別。

#### 方法

##### `__init__(root)`
初始化 GUI 應用程式

##### `_extract_features(image_path)`
提取影像特徵

參數：
- `image_path` (str): 圖片路徑

返回：
- `dict`: 包含各種特徵的字典

##### `_calculate_similarity(target_features, ref_features)`
計算兩張照片的相似度

參數：
- `target_features` (dict): 目標照片特徵
- `ref_features` (dict): 參考照片特徵

返回：
- `float`: 相似度分數 (0.0-1.0)

## 使用範例

```python
from ai_exif_estimator import AIExifEstimator
import tkinter as tk

root = tk.Tk()
app = AIExifEstimator(root)
root.mainloop()
```
"""
    
    create_file("docs/API_REFERENCE.md", api_reference_content)
    
    faq_content = """# 常見問題 (FAQ)

## 安裝相關

### Q: 安裝套件時出現錯誤？
A: 嘗試升級 pip：`pip install --upgrade pip`

### Q: OpenCV 安裝失敗？
A: 在 Windows 上可能需要安裝 Visual C++ 運行庫

## 使用相關

### Q: 找不到相似照片？
A: 
- 降低相似度門檻
- 確認參考照片充足
- 檢查照片是否為同一時期拍攝

### Q: 推測時間不準確？
A:
- 嘗試不同的時間推測模式
- 增加相似度門檻
- 使用人工配對工具手動確認

### Q: 程式執行很慢？
A:
- 減少參考照片數量
- 關閉紋理分析選項
- 使用較小的哈希大小

## 錯誤處理

### Q: 出現 "無法載入圖片" 錯誤？
A: 檢查圖片是否損壞或格式不支援

### Q: EXIF 寫入失敗？
A: 確認檔案有寫入權限，且不是唯讀

## 其他問題

如果以上無法解決你的問題，請在 GitHub Issues 提出。
"""
    
    create_file("docs/FAQ.md", faq_content)
    
    # === 創建 examples 目錄 ===
    create_directory("examples")
    
    batch_example_content = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"\"\"
批次處理範例
示範如何使用腳本批次處理大量照片
\"\"\"

import os
from pathlib import Path

def batch_process_photos(target_folder, reference_folder):
    \"\"\"
    批次處理照片的範例函數
    
    Args:
        target_folder: 目標照片資料夾
        reference_folder: 參考照片資料夾
    \"\"\"
    print(f"正在處理：")
    print(f"  目標資料夾: {target_folder}")
    print(f"  參考資料夾: {reference_folder}")
    
    # 在這裡添加你的處理邏輯
    # 可以導入主程式的功能模組
    
    pass

if __name__ == "__main__":
    target_dir = "./target"
    reference_dir = "./reference"
    
    batch_process_photos(target_dir, reference_dir)
"""
    
    create_file("examples/batch_process.py", batch_example_content)
    
    # === 重命名現有檔案（如果存在）===
    print()
    print("📝 處理現有檔案...")
    
    rename_map = {
        'app.v5.py': 'smart_exif_restorer.py',
        'exif_gui_tool.v2.py': 'exif_manual_matcher.py',
        'app.v3.py': 'ai_exif_estimator.py'
    }
    
    for old_name, new_name in rename_map.items():
        if os.path.exists(old_name):
            if os.path.exists(new_name):
                print(f"  ⚠️  {new_name} 已存在，跳過 {old_name}")
            else:
                os.rename(old_name, new_name)
                print(f"  ✓ 重命名: {old_name} → {new_name}")
    
    # === 創建上傳腳本 ===
    print()
    print("📝 創建上傳腳本...")
    
    upload_script_content = """@echo off
REM GitHub 快速上傳腳本 (Windows)

echo ========================================
echo GitHub 快速上傳工具
echo ========================================
echo.

REM 檢查 Git 是否已初始化
if not exist .git (
    echo 初始化 Git 儲存庫...
    git init
    echo.
)

REM 顯示當前狀態
echo 當前狀態:
git status
echo.

REM 添加所有檔案
echo 添加檔案...
git add .
echo.

REM 提交
set /p commit_msg="請輸入 commit 訊息: "
git commit -m "%commit_msg%"
echo.

REM 檢查是否已設定 remote
git remote -v | findstr origin >nul
if errorlevel 1 (
    echo.
    echo 尚未設定遠端儲存庫！
    echo.
    set /p repo_url="請輸入 GitHub 儲存庫 URL: "
    git remote add origin %repo_url%
    git branch -M main
    echo.
)

REM 推送
echo 推送到 GitHub...
git push -u origin main

echo.
echo ========================================
echo 上傳完成！
echo ========================================
pause
"""
    
    create_file("upload.bat", upload_script_content)
    
    # === 創建設定指南 ===
    setup_guide_content = """# GitHub 上傳完整指南

## 🎯 目前檔案結構

您的專案現在包含：

```
ai-exif-restorer/
├── smart_exif_restorer.py      # 命令列工具（原 app.v5.py）
├── exif_manual_matcher.py      # 人工配對工具（原 exif_gui_tool.v2.py）
├── ai_exif_estimator.py        # AI 智能系統（原 app.v3.py）
├── requirements.txt            # 依賴套件清單
├── README.md                   # 專案說明文件
├── LICENSE                     # MIT 授權條款
├── .gitignore                  # Git 忽略規則
├── setup_github_project.py     # 本腳本
├── upload.bat                  # Windows 快速上傳腳本
├── UPLOAD_GUIDE.md             # 本文件
├── docs/                       # 文檔目錄
│   ├── USER_GUIDE.md
│   ├── API_REFERENCE.md
│   └── FAQ.md
└── examples/                   # 範例目錄
    └── batch_process.py
```

## 🚀 上傳步驟

### 步驟 1：在 GitHub 建立儲存庫

1. 前往 https://github.com
2. 點擊右上角 `+` → `New repository`
3. 填寫資訊：
   - Repository name: `ai-exif-restorer`
   - Description: `AI 智能 EXIF 推測系統`
   - 選擇 Public 或 Private
   - **不要** 勾選 "Initialize this repository with..."
4. 點擊 `Create repository`
5. 記下顯示的 URL（例如：`https://github.com/charles5299/ai-exif-restorer.git`）

### 步驟 2：修改個人資訊

在上傳前，請修改以下文件中的個人資訊：

**README.md:**
- 第 90 行左右：`https://github.com/charles5299/` → 改成你的 GitHub 使用者名稱

**LICENSE:**
- 第 3 行：`[Your Name]` → 改成你的名字

### 步驟 3：初始化並上傳

#### 方法 A：使用快速上傳腳本（Windows）

```bash
# 直接雙擊執行
upload.bat

# 或在命令提示字元中執行
upload.bat
```

按照提示輸入 commit 訊息和 GitHub URL 即可。

#### 方法 B：手動執行指令

在專案資料夾中打開終端機，執行：

```bash
# 1. 初始化 Git
git init

# 2. 添加所有檔案
git add .

# 3. 第一次提交
git commit -m "Initial commit: AI Smart EXIF Restorer v1.0"

# 4. 連接到 GitHub（替換成你的 URL）
git remote add origin https://github.com/YOUR_USERNAME/ai-exif-restorer.git

# 5. 設定主分支
git branch -M main

# 6. 推送到 GitHub
git push -u origin main
```

### 步驟 4：驗證上傳

1. 打開瀏覽器
2. 前往你的 GitHub 儲存庫
3. 確認所有檔案都已上傳
4. 檢查 README.md 是否正確顯示

## 🔄 後續更新

當你修改程式碼後，使用以下指令更新：

```bash
# 快速更新（一行指令）
git add . && git commit -m "Update: 描述你的修改" && git push

# 或分步驟執行
git add .
git commit -m "Update: 改進 AI 演算法"
git push
```

## ✅ 上傳檢查清單

上傳前確認：

- [ ] 已在 GitHub 建立儲存庫
- [ ] 已修改 README.md 中的使用者名稱
- [ ] 已修改 LICENSE 中的姓名
- [ ] .gitignore 已設定（確保不會上傳測試照片）
- [ ] 程式碼可正常執行
- [ ] commit 訊息清楚明瞭

## 🎯 上傳後優化

上傳成功後，可以在 GitHub 做以下設定：

1. **添加 Topics 標籤**
   - exif, photo, image-processing, ai, python, tkinter

2. **編輯 About 描述**
   - 簡短描述專案功能

3. **設定 GitHub Pages**（可選）
   - 如果要建立專案網站

4. **啟用 Issues**
   - 方便用戶回報問題

## 🆘 常見問題

### Q: push 被拒絕（rejected）

```bash
# 解決方法：先拉取遠端變更
git pull origin main --rebase
git push origin main
```

### Q: 忘記添加 remote

```bash
# 添加遠端儲存庫
git remote add origin https://github.com/charles5299/ai-exif-restorer.git
```

### Q: 需要修改上一次 commit

```bash
# 修改訊息
git commit --amend -m "新的訊息"

# 重新推送（小心使用）
git push --force
```

## 📮 需要幫助？

如果遇到問題：

1. 檢查 Git 是否正確安裝：`git --version`
2. 檢查網路連線
3. 確認 GitHub 帳號已登入
4. 查看錯誤訊息並搜尋解決方案

---

**專案上傳完成後的 URL：**
`https://github.com/YOUR_USERNAME/ai-exif-restorer`

記得替換 `YOUR_USERNAME` 為你的 GitHub 使用者名稱！
"""
    
    create_file("UPLOAD_GUIDE.md", setup_guide_content)
    
    # === 完成訊息 ===
    print()
    print("=" * 70)
    print("✅ 專案結構創建完成！")
    print("=" * 70)
    print()
    print("📁 已創建的檔案和目錄：")
    print("   ✓ README.md")
    print("   ✓ requirements.txt")
    print("   ✓ .gitignore")
    print("   ✓ LICENSE")
    print("   ✓ UPLOAD_GUIDE.md")
    print("   ✓ upload.bat")
    print("   ✓ docs/USER_GUIDE.md")
    print("   ✓ docs/API_REFERENCE.md")
    print("   ✓ docs/FAQ.md")
    print("   ✓ examples/batch_process.py")
    print()
    print("📝 下一步：")
    print("   1. 閱讀 UPLOAD_GUIDE.md 了解上傳步驟")
    print("   2. 修改 README.md 和 LICENSE 中的個人資訊")
    print("   3. 在 GitHub 建立新儲存庫")
    print("   4. 執行 upload.bat 或按照指南手動上傳")
    print()
    print("🚀 快速上傳（Windows）：")
    print("   直接雙擊 upload.bat")
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()