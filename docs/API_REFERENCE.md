# API 參考

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
