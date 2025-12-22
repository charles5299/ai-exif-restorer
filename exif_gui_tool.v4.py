import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import piexif
from pathlib import Path
import shutil
import numpy as np
from datetime import datetime, timedelta
import imagehash
from collections import defaultdict
import cv2

class AIExifEstimator:
    def __init__(self, root):
        self.root = root
        self.root.title("AI 智能 EXIF 推測系統")
        self.root.geometry("1600x900")
        
        # 資料儲存
        self.target_folder = ""
        self.reference_folder = ""
        self.target_photos = []
        self.reference_photos = []
        self.selected_targets = []
        self.analysis_results = []  # AI 分析結果
        
        self._setup_ui()
        
    def _setup_ui(self):
        """建立使用者介面"""
        # 頂部控制區
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        # 資料夾選擇
        ttk.Label(control_frame, text="目標資料夾:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.target_label = ttk.Label(control_frame, text="未選擇", foreground="gray")
        self.target_label.grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Button(control_frame, text="選擇", command=self._select_target_folder).grid(row=0, column=2, padx=5)
        
        ttk.Label(control_frame, text="參考資料夾:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.ref_label = ttk.Label(control_frame, text="未選擇", foreground="gray")
        self.ref_label.grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Button(control_frame, text="選擇", command=self._select_reference_folder).grid(row=1, column=2, padx=5)
        
        ttk.Button(control_frame, text="載入照片", command=self._load_photos, 
                  style="Accent.TButton").grid(row=0, column=3, rowspan=2, padx=20)
        
        # AI 分析參數
        ttk.Label(control_frame, text="相似度門檻:").grid(row=0, column=4, sticky=tk.W, padx=5)
        self.similarity_threshold = tk.DoubleVar(value=0.7)
        ttk.Scale(control_frame, from_=0.5, to=0.95, variable=self.similarity_threshold, 
                 orient=tk.HORIZONTAL, length=150).grid(row=0, column=5, padx=5)
        self.threshold_label = ttk.Label(control_frame, text="0.70")
        self.threshold_label.grid(row=0, column=6, padx=5)
        self.similarity_threshold.trace('w', self._update_threshold_label)
        
        # 狀態列
        self.status_label = ttk.Label(control_frame, text="請選擇資料夾並載入照片", foreground="blue")
        self.status_label.grid(row=1, column=4, columnspan=3, sticky=tk.W, padx=5)
        
        # 主要內容區域
        content_frame = ttk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左側：目標照片
        target_frame = ttk.LabelFrame(content_frame, text="🎯 目標照片 (待分析)", padding="10")
        target_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        target_tools = ttk.Frame(target_frame)
        target_tools.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(target_tools, text="清除選擇", command=self._clear_target_selection).pack(side=tk.LEFT, padx=2)
        ttk.Button(target_tools, text="全選", command=self._select_all_targets).pack(side=tk.LEFT, padx=2)
        self.target_count_label = ttk.Label(target_tools, text="已選: 0", foreground="blue", font=("Arial", 9, "bold"))
        self.target_count_label.pack(side=tk.RIGHT, padx=5)
        
        target_scroll = self._create_scroll_frame(target_frame)
        self.target_canvas, self.target_content = target_scroll
        
        # 中間：AI 分析控制
        middle_frame = ttk.Frame(content_frame, width=200)
        middle_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        middle_frame.pack_propagate(False)
        
        ttk.Label(middle_frame, text="AI 智能分析", font=("Arial", 12, "bold")).pack(pady=10)
        
        # 分析選項
        analysis_opts = ttk.LabelFrame(middle_frame, text="分析選項", padding="10")
        analysis_opts.pack(fill=tk.X, pady=10)
        
        self.use_visual = tk.BooleanVar(value=True)
        ttk.Checkbutton(analysis_opts, text="視覺相似度", variable=self.use_visual).pack(anchor=tk.W)
        
        self.use_color = tk.BooleanVar(value=True)
        ttk.Checkbutton(analysis_opts, text="色彩直方圖", variable=self.use_color).pack(anchor=tk.W)
        
        self.use_edge = tk.BooleanVar(value=True)
        ttk.Checkbutton(analysis_opts, text="邊緣特徵", variable=self.use_edge).pack(anchor=tk.W)
        
        self.use_texture = tk.BooleanVar(value=False)
        ttk.Checkbutton(analysis_opts, text="紋理分析", variable=self.use_texture).pack(anchor=tk.W)
        
        ttk.Separator(middle_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # 時間推測模式
        time_mode_frame = ttk.LabelFrame(middle_frame, text="時間推測", padding="10")
        time_mode_frame.pack(fill=tk.X, pady=10)
        
        self.time_mode = tk.StringVar(value="interpolate")
        ttk.Radiobutton(time_mode_frame, text="智能插值", variable=self.time_mode, 
                       value="interpolate").pack(anchor=tk.W)
        ttk.Radiobutton(time_mode_frame, text="最相似", variable=self.time_mode, 
                       value="most_similar").pack(anchor=tk.W)
        ttk.Radiobutton(time_mode_frame, text="加權平均", variable=self.time_mode, 
                       value="weighted_avg").pack(anchor=tk.W)
        
        ttk.Separator(middle_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # 執行按鈕
        self.analyze_btn = ttk.Button(middle_frame, text="🤖 執行 AI 分析", 
                                      command=self._run_ai_analysis, state=tk.DISABLED)
        self.analyze_btn.pack(pady=10, fill=tk.X)
        
        ttk.Button(middle_frame, text="📊 查看結果", command=self._show_results, 
                  state=tk.DISABLED).pack(pady=5, fill=tk.X)
        self.result_btn = ttk.Button(middle_frame, text="📊 查看結果", command=self._show_results, state=tk.DISABLED)
        self.result_btn.pack(pady=5, fill=tk.X)
        
        ttk.Button(middle_frame, text="💾 應用 EXIF", command=self._apply_estimated_exif, 
                  state=tk.DISABLED).pack(pady=5, fill=tk.X)
        self.apply_btn = ttk.Button(middle_frame, text="💾 應用 EXIF", command=self._apply_estimated_exif, state=tk.DISABLED)
        self.apply_btn.pack(pady=5, fill=tk.X)
        
        # 右側：參考照片
        reference_frame = ttk.LabelFrame(content_frame, text="📚 參考照片資料庫", padding="10")
        reference_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        ref_tools = ttk.Frame(reference_frame)
        ref_tools.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(ref_tools, text="排序: 名稱", command=lambda: self._sort_reference("name")).pack(side=tk.LEFT, padx=2)
        ttk.Button(ref_tools, text="排序: 日期", command=lambda: self._sort_reference("date")).pack(side=tk.LEFT, padx=2)
        self.ref_count_label = ttk.Label(ref_tools, text=f"共: 0 張", foreground="green", font=("Arial", 9, "bold"))
        self.ref_count_label.pack(side=tk.RIGHT, padx=5)
        
        ref_scroll = self._create_scroll_frame(reference_frame)
        self.reference_canvas, self.reference_content = ref_scroll
        
        # 底部：分析結果預覽
        result_frame = ttk.LabelFrame(self.root, text="📋 分析結果預覽", padding="10")
        result_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.result_text = tk.Text(result_frame, height=8, wrap=tk.WORD, font=("Consolas", 9))
        result_scroll = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=result_scroll.set)
        result_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 進度條
        self.progress_frame = ttk.Frame(self.root)
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='determinate')
        self.progress_label = ttk.Label(self.progress_frame, text="")
    
    def _create_scroll_frame(self, parent):
        """創建可滾動框架"""
        scroll_frame = ttk.Frame(parent)
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(scroll_frame, bg="white")
        scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
        content = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_window((0, 0), window=content, anchor="nw")
        
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        return canvas, content
    
    def _update_threshold_label(self, *args):
        """更新門檻標籤"""
        self.threshold_label.config(text=f"{self.similarity_threshold.get():.2f}")
    
    def _select_target_folder(self):
        folder = filedialog.askdirectory(title="選擇目標資料夾")
        if folder:
            self.target_folder = folder
            self.target_label.config(text=Path(folder).name, foreground="black")
    
    def _select_reference_folder(self):
        folder = filedialog.askdirectory(title="選擇參考資料夾")
        if folder:
            self.reference_folder = folder
            self.ref_label.config(text=Path(folder).name, foreground="black")
    
    def _load_photos(self):
        """載入照片"""
        if not self.target_folder or not self.reference_folder:
            messagebox.showwarning("警告", "請先選擇資料夾！")
            return
        
        self.status_label.config(text="正在載入照片...", foreground="orange")
        self.root.update()
        
        # 載入目標照片
        self.target_photos = []
        for root, _, files in os.walk(self.target_folder):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg')):
                    path = os.path.join(root, file)
                    self.target_photos.append({
                        'path': path,
                        'filename': file,
                        'selected': False
                    })
        
        # 載入參考照片並提取特徵
        self.reference_photos = []
        for root, _, files in os.walk(self.reference_folder):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.heic')):
                    path = os.path.join(root, file)
                    
                    # 提取 EXIF 和特徵
                    exif_date = self._get_exif_datetime(path)
                    features = self._extract_features(path)
                    
                    self.reference_photos.append({
                        'path': path,
                        'filename': file,
                        'exif_date': exif_date,
                        'features': features
                    })
        
        self.reference_photos.sort(key=lambda x: x.get('exif_date', ''))
        
        self._display_target_photos()
        self._display_reference_photos()
        
        self.ref_count_label.config(text=f"共: {len(self.reference_photos)} 張")
        self.status_label.config(
            text=f"載入完成：目標 {len(self.target_photos)} 張，參考 {len(self.reference_photos)} 張",
            foreground="green"
        )
    
    def _extract_features(self, image_path):
        """提取影像特徵"""
        try:
            img = Image.open(image_path)
            
            # 1. 感知哈希 (視覺相似度)
            p_hash = imagehash.phash(img, hash_size=16)
            d_hash = imagehash.dhash(img, hash_size=16)
            a_hash = imagehash.average_hash(img, hash_size=16)
            
            # 2. 色彩直方圖
            img_array = np.array(img.resize((256, 256)))
            if len(img_array.shape) == 3:
                color_hist = [np.histogram(img_array[:,:,i], bins=32)[0] for i in range(3)]
                color_hist = np.concatenate(color_hist)
            else:
                color_hist = np.histogram(img_array, bins=32)[0]
            
            # 3. 邊緣特徵 (使用 OpenCV)
            img_cv = cv2.cvtColor(np.array(img.resize((256, 256))), cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(img_cv, 100, 200)
            edge_density = np.sum(edges > 0) / edges.size
            
            return {
                'p_hash': p_hash,
                'd_hash': d_hash,
                'a_hash': a_hash,
                'color_hist': color_hist,
                'edge_density': edge_density
            }
        except Exception as e:
            print(f"特徵提取失敗 {image_path}: {e}")
            return None
    
    def _calculate_similarity(self, target_features, ref_features):
        """計算綜合相似度"""
        if not target_features or not ref_features:
            return 0.0
        
        scores = []
        weights = []
        
        # 視覺哈希相似度
        if self.use_visual.get():
            hash_sim = 1 - (target_features['p_hash'] - ref_features['p_hash']) / 256.0
            scores.append(hash_sim)
            weights.append(0.4)
        
        # 色彩相似度
        if self.use_color.get():
            color_sim = 1 - np.sum(np.abs(target_features['color_hist'] - ref_features['color_hist'])) / (2 * np.sum(target_features['color_hist']))
            scores.append(max(0, color_sim))
            weights.append(0.3)
        
        # 邊緣相似度
        if self.use_edge.get():
            edge_diff = abs(target_features['edge_density'] - ref_features['edge_density'])
            edge_sim = 1 - min(edge_diff, 1.0)
            scores.append(edge_sim)
            weights.append(0.3)
        
        if not scores:
            return 0.0
        
        # 加權平均
        total_weight = sum(weights)
        weighted_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
        
        return weighted_score
    
    def _get_exif_datetime(self, image_path):
        """取得 EXIF 日期時間"""
        try:
            exif_dict = piexif.load(image_path)
            if piexif.ExifIFD.DateTimeOriginal in exif_dict.get('Exif', {}):
                return exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
            elif piexif.ImageIFD.DateTime in exif_dict.get('0th', {}):
                return exif_dict['0th'][piexif.ImageIFD.DateTime].decode('utf-8')
        except:
            pass
        return None
    
    def _display_target_photos(self):
        """顯示目標照片"""
        for widget in self.target_content.winfo_children():
            widget.destroy()
        
        row, col = 0, 0
        max_cols = 3
        
        for photo in self.target_photos:
            self._create_photo_card(self.target_content, photo, row, col, is_target=True)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def _display_reference_photos(self):
        """顯示參考照片"""
        for widget in self.reference_content.winfo_children():
            widget.destroy()
        
        row, col = 0, 0
        max_cols = 3
        
        for photo in self.reference_photos:
            self._create_photo_card(self.reference_content, photo, row, col, is_target=False)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def _create_photo_card(self, parent, photo, row, col, is_target=True):
        """創建照片卡片"""
        is_selected = photo.get('selected', False)
        
        card = ttk.Frame(parent, relief=tk.RAISED, borderwidth=2)
        card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        
        if is_selected:
            card.config(relief=tk.SOLID, borderwidth=3)
        
        # 縮圖
        try:
            img = Image.open(photo['path'])
            img.thumbnail((150, 150))
            photo_img = ImageTk.PhotoImage(img)
            
            img_label = tk.Label(card, image=photo_img, cursor="hand2")
            img_label.image = photo_img
            img_label.pack()
            
            if is_target:
                img_label.bind("<Button-1>", lambda e, p=photo: self._toggle_target_selection(p))
        except:
            error_label = tk.Label(card, text="無法載入", fg="red")
            error_label.pack()
        
        # 檔名
        filename_label = tk.Label(card, text=photo['filename'][:20], font=("Arial", 8))
        filename_label.pack()
        
        # 狀態
        if is_target and is_selected:
            select_mark = tk.Label(card, text="✓ 已選", fg="blue", font=("Arial", 9, "bold"), bg="yellow")
            select_mark.pack()
        elif not is_target and photo.get('exif_date'):
            date_label = tk.Label(card, text=photo['exif_date'][:10], fg="gray", font=("Arial", 7))
            date_label.pack()
        
        photo['card'] = card
    
    def _toggle_target_selection(self, photo):
        """切換選擇狀態"""
        photo['selected'] = not photo.get('selected', False)
        
        if photo['selected']:
            if photo not in self.selected_targets:
                self.selected_targets.append(photo)
        else:
            if photo in self.selected_targets:
                self.selected_targets.remove(photo)
        
        self._display_target_photos()
        self.target_count_label.config(text=f"已選: {len(self.selected_targets)}")
        
        # 更新按鈕狀態
        if len(self.selected_targets) > 0:
            self.analyze_btn.config(state=tk.NORMAL)
        else:
            self.analyze_btn.config(state=tk.DISABLED)
    
    def _clear_target_selection(self):
        """清除選擇"""
        for photo in self.selected_targets:
            photo['selected'] = False
        self.selected_targets.clear()
        self._display_target_photos()
        self.target_count_label.config(text="已選: 0")
        self.analyze_btn.config(state=tk.DISABLED)
    
    def _select_all_targets(self):
        """全選"""
        for photo in self.target_photos:
            photo['selected'] = True
            if photo not in self.selected_targets:
                self.selected_targets.append(photo)
        self._display_target_photos()
        self.target_count_label.config(text=f"已選: {len(self.selected_targets)}")
        self.analyze_btn.config(state=tk.NORMAL)
    
    def _sort_reference(self, sort_by):
        """排序參考照片"""
        if sort_by == "name":
            self.reference_photos.sort(key=lambda x: x['filename'])
        elif sort_by == "date":
            self.reference_photos.sort(key=lambda x: x.get('exif_date', ''))
        self._display_reference_photos()
    
    def _run_ai_analysis(self):
        """執行 AI 分析"""
        if not self.selected_targets:
            messagebox.showwarning("警告", "請先選擇目標照片！")
            return
        
        # 顯示進度
        self.progress_frame.pack(fill=tk.X, padx=10, pady=5)
        self.progress_bar.pack(fill=tk.X)
        self.progress_label.pack()
        
        self.analysis_results = []
        total = len(self.selected_targets)
        
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "=== AI 分析開始 ===\n\n")
        
        for i, target_photo in enumerate(self.selected_targets):
            # 更新進度
            progress = (i + 1) / total * 100
            self.progress_bar['value'] = progress
            self.progress_label.config(text=f"分析中: {i+1}/{total} - {target_photo['filename']}")
            self.root.update()
            
            # 提取目標照片特徵
            target_features = self._extract_features(target_photo['path'])
            
            if not target_features:
                continue
            
            # 計算與所有參考照片的相似度
            similarities = []
            for ref_photo in self.reference_photos:
                if ref_photo['features']:
                    sim_score = self._calculate_similarity(target_features, ref_photo['features'])
                    if sim_score >= self.similarity_threshold.get():
                        similarities.append({
                            'ref_photo': ref_photo,
                            'similarity': sim_score
                        })
            
            # 排序並選取最相似的
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            top_matches = similarities[:5]  # 取前5個
            
            # 推測 EXIF
            estimated_exif = self._estimate_exif(target_photo, top_matches)
            
            self.analysis_results.append({
                'target': target_photo,
                'matches': top_matches,
                'estimated_exif': estimated_exif
            })
            
            # 顯示結果
            self.result_text.insert(tk.END, f"📷 {target_photo['filename']}\n")
            self.result_text.insert(tk.END, f"   找到 {len(top_matches)} 個相似照片\n")
            if estimated_exif:
                self.result_text.insert(tk.END, f"   推測時間: {estimated_exif['datetime']}\n")
                self.result_text.insert(tk.END, f"   信心度: {estimated_exif['confidence']:.2%}\n")
            self.result_text.insert(tk.END, "\n")
        
        # 隱藏進度
        self.progress_bar.pack_forget()
        self.progress_label.pack_forget()
        self.progress_frame.pack_forget()
        
        self.result_text.insert(tk.END, f"\n=== 分析完成：共 {len(self.analysis_results)} 張照片 ===\n")
        
        # 啟用按鈕
        self.result_btn.config(state=tk.NORMAL)
        self.apply_btn.config(state=tk.NORMAL)
        
        messagebox.showinfo("完成", f"AI 分析完成！\n成功分析 {len(self.analysis_results)} 張照片")
    
    def _estimate_exif(self, target_photo, matches):
        """推測 EXIF 資訊"""
        if not matches:
            return None
        
        mode = self.time_mode.get()
        
        if mode == "most_similar":
            # 使用最相似的照片
            best_match = matches[0]
            ref_exif = self._load_full_exif(best_match['ref_photo']['path'])
            return {
                'datetime': best_match['ref_photo']['exif_date'],
                'confidence': best_match['similarity'],
                'source': 'most_similar',
                'full_exif': ref_exif
            }
        
        elif mode == "weighted_avg":
            # 加權平均時間
            datetimes = []
            weights = []
            
            for match in matches:
                if match['ref_photo']['exif_date']:
                    try:
                        dt = datetime.strptime(match['ref_photo']['exif_date'], "%Y:%m:%d %H:%M:%S")
                        datetimes.append(dt)
                        weights.append(match['similarity'])
                    except:
                        pass
            
            if datetimes:
                total_weight = sum(weights)
                weighted_timestamps = sum(dt.timestamp() * w for dt, w in zip(datetimes, weights))
                avg_timestamp = weighted_timestamps / total_weight
                avg_datetime = datetime.fromtimestamp(avg_timestamp)
                
                # 使用最相似照片的完整 EXIF，但修改時間
                best_match = matches[0]
                ref_exif = self._load_full_exif(best_match['ref_photo']['path'])
                
                return {
                    'datetime': avg_datetime.strftime("%Y:%m:%d %H:%M:%S"),
                    'confidence': sum(weights) / len(weights),
                    'source': 'weighted_average',
                    'full_exif': ref_exif
                }
        
        elif mode == "interpolate":
            # 智能插值：如果有多個相似照片，推測在它們之間
            if len(matches) >= 2:
                times = []
                for match in matches[:3]:
                    if match['ref_photo']['exif_date']:
                        try:
                            dt = datetime.strptime(match['ref_photo']['exif_date'], "%Y:%m:%d %H:%M:%S")
                            times.append((dt, match['similarity']))
                        except:
                            pass
                
                if len(times) >= 2:
                    times.sort(key=lambda x: x[0])
                    # 使用最早和最晚時間的中點
                    start_time = times[0][0]
                    end_time = times[-1][0]
                    mid_time = start_time + (end_time - start_time) / 2
                    
                    best_match = matches[0]
                    ref_exif = self._load_full_exif(best_match['ref_photo']['path'])
                    
                    return {
                        'datetime': mid_time.strftime("%Y:%m:%d %H:%M:%S"),
                        'confidence': sum(t[1] for t in times) / len(times),
                        'source': 'interpolated',
                        'full_exif': ref_exif
                    }
        
        return None
    
    def _load_full_exif(self, image_path):
        """載入完整 EXIF"""
        try:
            return piexif.load(image_path)
        except:
            return None
    
    def _show_results(self):
        """顯示詳細結果"""
        if not self.analysis_results:
            messagebox.showwarning("提示", "尚未進行分析")
            return
        
        # 創建結果視窗
        result_window = tk.Toplevel(self.root)
        result_window.title("詳細分析結果")
        result_window.geometry("800x600")
        
        # 樹狀視圖
        tree_frame = ttk.Frame(result_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("目標照片", "相似照片數", "推測時間", "信心度", "方法")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 填充資料
        for result in self.analysis_results:
            target_name = result['target']['filename']
            match_count = len(result['matches'])
            
            if result['estimated_exif']:
                est_time = result['estimated_exif']['datetime']
                confidence = f"{result['estimated_exif']['confidence']:.1%}"
                method = result['estimated_exif']['source']
            else:
                est_time = "無法推測"
                confidence = "0%"
                method = "-"
            
            tree.insert("", tk.END, values=(target_name, match_count, est_time, confidence, method))
        
        # 底部按鈕
        btn_frame = ttk.Frame(result_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(btn_frame, text="匯出報告", command=lambda: self._export_report()).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="關閉", command=result_window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _export_report(self):
        """匯出分析報告"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("AI 智能 EXIF 推測系統 - 分析報告\n")
                f.write("=" * 80 + "\n\n")
                
                for i, result in enumerate(self.analysis_results, 1):
                    f.write(f"\n【{i}】目標照片: {result['target']['filename']}\n")
                    f.write(f"    路徑: {result['target']['path']}\n")
                    f.write(f"    相似照片數: {len(result['matches'])}\n\n")
                    
                    if result['estimated_exif']:
                        f.write(f"    推測 EXIF:\n")
                        f.write(f"      時間: {result['estimated_exif']['datetime']}\n")
                        f.write(f"      信心度: {result['estimated_exif']['confidence']:.2%}\n")
                        f.write(f"      方法: {result['estimated_exif']['source']}\n\n")
                    
                    f.write(f"    前 5 個最相似照片:\n")
                    for j, match in enumerate(result['matches'][:5], 1):
                        f.write(f"      {j}. {match['ref_photo']['filename']}\n")
                        f.write(f"         相似度: {match['similarity']:.2%}\n")
                        f.write(f"         時間: {match['ref_photo']['exif_date']}\n")
                    
                    f.write("\n" + "-" * 80 + "\n")
            
            messagebox.showinfo("成功", f"報告已匯出至 {filename}")
    
    def _apply_estimated_exif(self):
        """應用推測的 EXIF"""
        if not self.analysis_results:
            messagebox.showwarning("警告", "尚未進行分析！")
            return
        
        count = len([r for r in self.analysis_results if r['estimated_exif']])
        
        if not messagebox.askyesno("確認", 
            f"將為 {count} 張照片寫入推測的 EXIF 資訊\n原始檔案將被備份\n\n是否繼續？"):
            return
        
        # 顯示進度
        self.progress_frame.pack(fill=tk.X, padx=10, pady=5)
        self.progress_bar.pack(fill=tk.X)
        self.progress_label.pack()
        
        success = 0
        total = len(self.analysis_results)
        
        for i, result in enumerate(self.analysis_results):
            # 更新進度
            progress = (i + 1) / total * 100
            self.progress_bar['value'] = progress
            self.progress_label.config(text=f"寫入中: {i+1}/{total}")
            self.root.update()
            
            if not result['estimated_exif']:
                continue
            
            target_path = result['target']['path']
            
            # 備份
            backup_dir = os.path.join(os.path.dirname(target_path), '.backup')
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, os.path.basename(target_path))
            shutil.copy2(target_path, backup_path)
            
            # 寫入 EXIF
            try:
                estimated_datetime = result['estimated_exif']['datetime']
                source_exif = result['estimated_exif']['full_exif']
                
                if source_exif:
                    # 使用參考照片的 EXIF，但修改時間
                    if "thumbnail" in source_exif:
                        del source_exif["thumbnail"]
                    
                    # 更新時間欄位
                    source_exif['0th'][piexif.ImageIFD.DateTime] = estimated_datetime
                    source_exif['Exif'][piexif.ExifIFD.DateTimeOriginal] = estimated_datetime
                    source_exif['Exif'][piexif.ExifIFD.DateTimeDigitized] = estimated_datetime
                else:
                    # 創建新的 EXIF
                    source_exif = {"0th":{}, "Exif":{}, "GPS":{}, "1st":{}}
                    source_exif['0th'][piexif.ImageIFD.DateTime] = estimated_datetime
                    source_exif['Exif'][piexif.ExifIFD.DateTimeOriginal] = estimated_datetime
                    source_exif['Exif'][piexif.ExifIFD.DateTimeDigitized] = estimated_datetime
                
                exif_bytes = piexif.dump(source_exif)
                piexif.insert(exif_bytes, target_path)
                success += 1
                
            except Exception as e:
                print(f"寫入失敗 {target_path}: {e}")
        
        # 隱藏進度
        self.progress_bar.pack_forget()
        self.progress_label.pack_forget()
        self.progress_frame.pack_forget()
        
        messagebox.showinfo("完成", 
            f"成功寫入 {success}/{total} 張照片的 EXIF！\n原始檔案已備份至 .backup 資料夾")
        
        # 重新載入
        self.analysis_results.clear()
        self._load_photos()


if __name__ == "__main__":
    root = tk.Tk()
    app = AIExifEstimator(root)
    root.mainloop()