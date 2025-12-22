# GitHub 上傳完整指南

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
