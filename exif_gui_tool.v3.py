import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import piexif
from pathlib import Path
import shutil

class ExifManualMatcher:
    def __init__(self, root):
        self.root = root
        self.root.title("EXIF 人工配對修正工具 - 多選版本")
        self.root.geometry("1500x900")
        
        # 資料儲存
        self.target_folder = ""
        self.reference_folder = ""
        self.target_photos = []
        self.reference_photos = []
        self.selected_targets = []  # 改為列表支援多選
        self.selected_references = []  # 改為列表支援多選
        self.mappings = {}  # {target_path: reference_path}
        
        self._setup_ui()
        
    def _setup_ui(self):
        """建立使用者介面"""
        # 頂部控制區
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        # 資料夾選擇
        ttk.Label(control_frame, text="目標資料夾 (LINE照片):").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.target_label = ttk.Label(control_frame, text="未選擇", foreground="gray")
        self.target_label.grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Button(control_frame, text="選擇", command=self._select_target_folder).grid(row=0, column=2, padx=5)
        
        ttk.Label(control_frame, text="參考資料夾 (原始照片):").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.ref_label = ttk.Label(control_frame, text="未選擇", foreground="gray")
        self.ref_label.grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Button(control_frame, text="選擇", command=self._select_reference_folder).grid(row=1, column=2, padx=5)
        
        # 載入按鈕
        ttk.Button(control_frame, text="載入照片", command=self._load_photos, 
                  style="Accent.TButton").grid(row=0, column=3, rowspan=2, padx=20, pady=5)
        
        # 搜尋框
        ttk.Label(control_frame, text="搜尋:").grid(row=0, column=4, sticky=tk.W, padx=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(control_frame, textvariable=self.search_var, width=20)
        search_entry.grid(row=0, column=5, padx=5)
        ttk.Button(control_frame, text="🔍", command=self._on_search).grid(row=0, column=6, padx=2)
        
        # 狀態列
        self.status_label = ttk.Label(control_frame, text="請選擇資料夾並載入照片", foreground="blue")
        self.status_label.grid(row=1, column=4, columnspan=3, sticky=tk.W, padx=5)
        
        # 主要內容區域
        content_frame = ttk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左側：目標照片 (LINE)
        target_frame = ttk.LabelFrame(content_frame, text="🎯 目標照片 (無EXIF) - 支援多選", padding="10")
        target_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 目標照片工具列
        target_tools = ttk.Frame(target_frame)
        target_tools.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(target_tools, text="清除選擇", command=lambda: self._clear_selection('target')).pack(side=tk.LEFT, padx=2)
        ttk.Button(target_tools, text="顯示 EXIF", command=self._show_target_exif).pack(side=tk.LEFT, padx=2)
        ttk.Button(target_tools, text="僅顯示無 EXIF", command=lambda: self._filter_target(True)).pack(side=tk.LEFT, padx=2)
        ttk.Button(target_tools, text="顯示全部", command=lambda: self._filter_target(False)).pack(side=tk.LEFT, padx=2)
        
        self.target_count_label = ttk.Label(target_tools, text="已選: 0", foreground="blue", font=("Arial", 9, "bold"))
        self.target_count_label.pack(side=tk.RIGHT, padx=5)
        
        target_scroll_frame = ttk.Frame(target_frame)
        target_scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        target_canvas = tk.Canvas(target_scroll_frame, bg="white")
        target_scrollbar = ttk.Scrollbar(target_scroll_frame, orient="vertical", command=target_canvas.yview)
        self.target_content = ttk.Frame(target_canvas)
        
        target_canvas.configure(yscrollcommand=target_scrollbar.set)
        target_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        target_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        target_canvas.create_window((0, 0), window=self.target_content, anchor="nw")
        
        self.target_canvas = target_canvas
        self.target_content.bind("<Configure>", lambda e: target_canvas.configure(scrollregion=target_canvas.bbox("all")))
        
        # 中間：操作按鈕
        middle_frame = ttk.Frame(content_frame, width=180)
        middle_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        middle_frame.pack_propagate(False)
        
        ttk.Label(middle_frame, text="批次配對", font=("Arial", 12, "bold")).pack(pady=10)
        
        # 配對模式選擇
        self.match_mode = tk.StringVar(value="one_to_one")
        ttk.Radiobutton(middle_frame, text="一對一配對", variable=self.match_mode, 
                       value="one_to_one").pack(anchor=tk.W, padx=10)
        ttk.Radiobutton(middle_frame, text="多對一配對", variable=self.match_mode, 
                       value="many_to_one").pack(anchor=tk.W, padx=10)
        
        ttk.Label(middle_frame, text="(左側多張 → 右側一張)", font=("Arial", 8), 
                 foreground="gray").pack(padx=10)
        
        ttk.Separator(middle_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        self.match_btn = ttk.Button(middle_frame, text="⬇\n執行配對\n⬇", 
                                     command=self._create_mapping, state=tk.DISABLED)
        self.match_btn.pack(pady=10, fill=tk.X)
        
        self.match_info_label = ttk.Label(middle_frame, text="", foreground="blue", 
                                          font=("Arial", 8), wraplength=150)
        self.match_info_label.pack(pady=5)
        
        ttk.Separator(middle_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        ttk.Button(middle_frame, text="取消選中配對", command=self._remove_selected_mapping).pack(pady=5, fill=tk.X)
        ttk.Button(middle_frame, text="清除所有配對", command=self._clear_all_mappings).pack(pady=5, fill=tk.X)
        
        ttk.Separator(middle_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        ttk.Label(middle_frame, text="配對統計", font=("Arial", 10, "bold")).pack(pady=5)
        self.mapping_count_label = ttk.Label(middle_frame, text="0 組", foreground="green", 
                                             font=("Arial", 16, "bold"))
        self.mapping_count_label.pack(pady=5)
        
        ttk.Separator(middle_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        ttk.Button(middle_frame, text="💾 執行修正", command=self._apply_mappings,
                  style="Accent.TButton").pack(pady=10, fill=tk.X)
        ttk.Button(middle_frame, text="📋 匯出配對表", command=self._export_mappings).pack(pady=5, fill=tk.X)
        ttk.Button(middle_frame, text="📥 匯入配對表", command=self._import_mappings).pack(pady=5, fill=tk.X)
        
        # 右側：參考照片 (原始)
        reference_frame = ttk.LabelFrame(content_frame, text="📚 參考照片 (有EXIF) - 支援多選", padding="10")
        reference_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 參考照片工具列
        ref_tools = ttk.Frame(reference_frame)
        ref_tools.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(ref_tools, text="清除選擇", command=lambda: self._clear_selection('reference')).pack(side=tk.LEFT, padx=2)
        ttk.Button(ref_tools, text="顯示 EXIF", command=self._show_reference_exif).pack(side=tk.LEFT, padx=2)
        ttk.Button(ref_tools, text="排序: 名稱", command=lambda: self._sort_reference("name")).pack(side=tk.LEFT, padx=2)
        ttk.Button(ref_tools, text="排序: 日期", command=lambda: self._sort_reference("date")).pack(side=tk.LEFT, padx=2)
        
        self.ref_count_label = ttk.Label(ref_tools, text="已選: 0", foreground="blue", font=("Arial", 9, "bold"))
        self.ref_count_label.pack(side=tk.RIGHT, padx=5)
        
        reference_scroll_frame = ttk.Frame(reference_frame)
        reference_scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        reference_canvas = tk.Canvas(reference_scroll_frame, bg="white")
        reference_scrollbar = ttk.Scrollbar(reference_scroll_frame, orient="vertical", command=reference_canvas.yview)
        self.reference_content = ttk.Frame(reference_canvas)
        
        reference_canvas.configure(yscrollcommand=reference_scrollbar.set)
        reference_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        reference_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        reference_canvas.create_window((0, 0), window=self.reference_content, anchor="nw")
        
        self.reference_canvas = reference_canvas
        self.reference_content.bind("<Configure>", lambda e: reference_canvas.configure(scrollregion=reference_canvas.bbox("all")))
        
        # 底部進度條
        self.progress_frame = ttk.Frame(self.root)
        self.progress_frame.pack(fill=tk.X, padx=10, pady=5)
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='determinate')
        self.progress_label = ttk.Label(self.progress_frame, text="")
        
    def _select_target_folder(self):
        """選擇目標資料夾"""
        folder = filedialog.askdirectory(title="選擇目標資料夾 (LINE下載的照片)")
        if folder:
            self.target_folder = folder
            self.target_label.config(text=Path(folder).name, foreground="black")
            
    def _select_reference_folder(self):
        """選擇參考資料夾"""
        folder = filedialog.askdirectory(title="選擇參考資料夾 (原始照片)")
        if folder:
            self.reference_folder = folder
            self.ref_label.config(text=Path(folder).name, foreground="black")
    
    def _load_photos(self):
        """載入照片"""
        if not self.target_folder or not self.reference_folder:
            messagebox.showwarning("警告", "請先選擇目標和參考資料夾！")
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
                        'has_exif': self._has_exif(path),
                        'selected': False
                    })
        
        # 載入參考照片
        self.reference_photos = []
        for root, _, files in os.walk(self.reference_folder):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.heic')):
                    path = os.path.join(root, file)
                    exif_date = self._get_exif_datetime(path)
                    self.reference_photos.append({
                        'path': path,
                        'filename': file,
                        'exif_date': exif_date,
                        'selected': False
                    })
        
        # 排序
        self.reference_photos.sort(key=lambda x: x['filename'])
        
        # 顯示照片
        self._display_target_photos()
        self._display_reference_photos()
        
        self.status_label.config(
            text=f"載入完成：目標 {len(self.target_photos)} 張，參考 {len(self.reference_photos)} 張",
            foreground="green"
        )
    
    def _has_exif(self, image_path):
        """檢查是否有 EXIF"""
        try:
            exif_dict = piexif.load(image_path)
            return bool(exif_dict.get('Exif', {}).get(piexif.ExifIFD.DateTimeOriginal))
        except:
            return False
    
    def _get_exif_datetime(self, image_path):
        """取得 EXIF 日期"""
        try:
            exif_dict = piexif.load(image_path)
            if piexif.ExifIFD.DateTimeOriginal in exif_dict.get('Exif', {}):
                return exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
            elif piexif.ImageIFD.DateTime in exif_dict.get('0th', {}):
                return exif_dict['0th'][piexif.ImageIFD.DateTime].decode('utf-8')
        except:
            pass
        return None
    
    def _display_target_photos(self, filter_no_exif=False):
        """顯示目標照片"""
        # 清空現有內容
        for widget in self.target_content.winfo_children():
            widget.destroy()
        
        photos_to_show = self.target_photos
        if filter_no_exif:
            photos_to_show = [p for p in self.target_photos if not p['has_exif']]
        
        row, col = 0, 0
        max_cols = 3
        
        for photo in photos_to_show:
            self._create_photo_card(self.target_content, photo, row, col, is_target=True)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def _display_reference_photos(self):
        """顯示參考照片"""
        # 清空現有內容
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
        # 判斷是否被選中
        is_selected = photo.get('selected', False)
        
        card = ttk.Frame(parent, relief=tk.RAISED, borderwidth=2)
        card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        
        # 如果被選中，改變邊框
        if is_selected:
            card.config(relief=tk.SOLID, borderwidth=3)
        
        # 載入縮圖
        try:
            img = Image.open(photo['path'])
            img.thumbnail((150, 150))
            photo_img = ImageTk.PhotoImage(img)
            
            img_label = tk.Label(card, image=photo_img, cursor="hand2")
            img_label.image = photo_img  # 保持引用
            img_label.pack()
            
            # 綁定點擊事件 - 支援多選
            if is_target:
                img_label.bind("<Button-1>", lambda e, p=photo: self._toggle_target_selection(p))
            else:
                img_label.bind("<Button-1>", lambda e, p=photo: self._toggle_reference_selection(p))
        except Exception as e:
            error_label = tk.Label(card, text="無法載入", fg="red")
            error_label.pack()
        
        # 檔名
        filename_label = tk.Label(card, text=photo['filename'][:20], font=("Arial", 8))
        filename_label.pack()
        
        # 狀態標籤
        if is_target:
            if photo['path'] in self.mappings:
                ref_name = Path(self.mappings[photo['path']]).name[:15]
                status = tk.Label(card, text=f"✓ → {ref_name}", fg="green", font=("Arial", 7, "bold"))
            elif photo['has_exif']:
                status = tk.Label(card, text="已有EXIF", fg="blue", font=("Arial", 8))
            else:
                status = tk.Label(card, text="待配對", fg="orange", font=("Arial", 8))
            status.pack()
        else:
            if photo.get('exif_date'):
                date_label = tk.Label(card, text=photo['exif_date'][:10], fg="gray", font=("Arial", 7))
                date_label.pack()
        
        # 選中標記
        if is_selected:
            select_mark = tk.Label(card, text="✓ 已選", fg="blue", font=("Arial", 9, "bold"), 
                                  bg="yellow")
            select_mark.pack()
        
        # 儲存卡片引用
        photo['card'] = card
    
    def _toggle_target_selection(self, photo):
        """切換目標照片選擇狀態"""
        photo['selected'] = not photo.get('selected', False)
        
        # 更新 selected_targets 列表
        if photo['selected']:
            if photo not in self.selected_targets:
                self.selected_targets.append(photo)
        else:
            if photo in self.selected_targets:
                self.selected_targets.remove(photo)
        
        # 重新顯示
        self._display_target_photos()
        self.target_count_label.config(text=f"已選: {len(self.selected_targets)}")
        
        # 更新按鈕狀態
        self._update_match_button()
    
    def _toggle_reference_selection(self, photo):
        """切換參考照片選擇狀態"""
        photo['selected'] = not photo.get('selected', False)
        
        # 更新 selected_references 列表
        if photo['selected']:
            if photo not in self.selected_references:
                self.selected_references.append(photo)
        else:
            if photo in self.selected_references:
                self.selected_references.remove(photo)
        
        # 重新顯示
        self._display_reference_photos()
        self.ref_count_label.config(text=f"已選: {len(self.selected_references)}")
        
        # 更新按鈕狀態
        self._update_match_button()
    
    def _clear_selection(self, side):
        """清除選擇"""
        if side == 'target':
            for photo in self.selected_targets:
                photo['selected'] = False
            self.selected_targets.clear()
            self._display_target_photos()
            self.target_count_label.config(text="已選: 0")
        else:
            for photo in self.selected_references:
                photo['selected'] = False
            self.selected_references.clear()
            self._display_reference_photos()
            self.ref_count_label.config(text="已選: 0")
        
        self._update_match_button()
    
    def _update_match_button(self):
        """更新配對按鈕狀態"""
        target_count = len(self.selected_targets)
        ref_count = len(self.selected_references)
        
        mode = self.match_mode.get()
        
        if mode == "one_to_one":
            if target_count > 0 and ref_count > 0 and target_count == ref_count:
                self.match_btn.config(state=tk.NORMAL)
                self.match_info_label.config(
                    text=f"將建立 {target_count} 組一對一配對",
                    foreground="green"
                )
            else:
                self.match_btn.config(state=tk.DISABLED)
                self.match_info_label.config(
                    text=f"請選擇相同數量\n目標: {target_count}\n參考: {ref_count}",
                    foreground="orange"
                )
        elif mode == "many_to_one":
            if target_count > 0 and ref_count == 1:
                self.match_btn.config(state=tk.NORMAL)
                self.match_info_label.config(
                    text=f"將 {target_count} 張目標\n配對到 1 張參考",
                    foreground="green"
                )
            else:
                self.match_btn.config(state=tk.DISABLED)
                self.match_info_label.config(
                    text=f"請選擇多張目標\n和 1 張參考\n(目標: {target_count}, 參考: {ref_count})",
                    foreground="orange"
                )
    
    def _create_mapping(self):
        """創建配對"""
        mode = self.match_mode.get()
        
        if mode == "one_to_one":
            # 一對一配對
            if len(self.selected_targets) != len(self.selected_references):
                messagebox.showwarning("警告", "目標和參考照片數量必須相同！")
                return
            
            for target, reference in zip(self.selected_targets, self.selected_references):
                self.mappings[target['path']] = reference['path']
            
            success_count = len(self.selected_targets)
            
        elif mode == "many_to_one":
            # 多對一配對
            if len(self.selected_references) != 1:
                messagebox.showwarning("警告", "請只選擇一張參考照片！")
                return
            
            reference = self.selected_references[0]
            for target in self.selected_targets:
                self.mappings[target['path']] = reference['path']
            
            success_count = len(self.selected_targets)
        
        # 清除選擇
        self._clear_selection('target')
        self._clear_selection('reference')
        
        # 更新顯示
        self._display_target_photos()
        self._display_reference_photos()
        
        # 更新計數
        self.mapping_count_label.config(text=f"{len(self.mappings)} 組")
        self.status_label.config(text=f"成功建立 {success_count} 組配對！", foreground="green")
    
    def _remove_selected_mapping(self):
        """取消選中照片的配對"""
        removed = 0
        for target in self.selected_targets:
            if target['path'] in self.mappings:
                del self.mappings[target['path']]
                removed += 1
        
        if removed > 0:
            self._display_target_photos()
            self.mapping_count_label.config(text=f"{len(self.mappings)} 組")
            self.status_label.config(text=f"已取消 {removed} 組配對", foreground="orange")
        else:
            self.status_label.config(text="選中的照片沒有配對", foreground="gray")
    
    def _clear_all_mappings(self):
        """清除所有配對"""
        if messagebox.askyesno("確認", "確定要清除所有配對嗎？"):
            self.mappings.clear()
            self._display_target_photos()
            self.mapping_count_label.config(text="0 組")
            self.status_label.config(text="所有配對已清除", foreground="orange")
    
    def _apply_mappings(self):
        """執行 EXIF 修正"""
        if not self.mappings:
            messagebox.showwarning("警告", "沒有任何配對需要處理！")
            return
        
        if not messagebox.askyesno("確認", f"確定要修正 {len(self.mappings)} 張照片的 EXIF 嗎？\n原始檔案將會被備份。"):
            return
        
        # 顯示進度條
        self.progress_bar.pack(fill=tk.X)
        self.progress_label.pack()
        
        total = len(self.mappings)
        success = 0
        
        for i, (target_path, ref_path) in enumerate(self.mappings.items()):
            # 更新進度
            progress = (i + 1) / total * 100
            self.progress_bar['value'] = progress
            self.progress_label.config(text=f"處理中: {i+1}/{total} - {Path(target_path).name}")
            self.root.update()
            
            # 備份
            backup_dir = os.path.join(os.path.dirname(target_path), '.backup')
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, os.path.basename(target_path))
            shutil.copy2(target_path, backup_path)
            
            # 複製 EXIF
            try:
                source_exif = piexif.load(ref_path)
                if "thumbnail" in source_exif:
                    del source_exif["thumbnail"]
                exif_bytes = piexif.dump(source_exif)
                piexif.insert(exif_bytes, target_path)
                success += 1
            except Exception as e:
                print(f"錯誤: {target_path} - {e}")
        
        # 隱藏進度條
        self.progress_bar.pack_forget()
        self.progress_label.pack_forget()
        
        messagebox.showinfo("完成", f"成功修正 {success}/{total} 張照片！\n原始檔案已備份至 .backup 資料夾")
        
        # 重新載入
        self.mappings.clear()
        self._load_photos()
    
    def _export_mappings(self):
        """匯出配對表"""
        if not self.mappings:
            messagebox.showwarning("警告", "沒有配對可以匯出！")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                for target, ref in self.mappings.items():
                    f.write(f"{target}\t{ref}\n")
            messagebox.showinfo("成功", f"配對表已匯出至 {filename}")
    
    def _import_mappings(self):
        """匯入配對表"""
        filename = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    for line in f:
                        target, ref = line.strip().split('\t')
                        self.mappings[target] = ref
                self._display_target_photos()
                self.mapping_count_label.config(text=f"{len(self.mappings)} 組")
                messagebox.showinfo("成功", f"已匯入 {len(self.mappings)} 組配對")
            except Exception as e:
                messagebox.showerror("錯誤", f"匯入失敗：{e}")
    
    def _show_target_exif(self):
        """顯示目標照片 EXIF"""
        if not self.selected_targets:
            messagebox.showwarning("提示", "請先選擇照片")
            return
        
        info = ""
        for i, photo in enumerate(self.selected_targets[:5], 1):  # 最多顯示5張
            exif_info = self._get_exif_info(photo['path'])
            info += f"【{i}】{exif_info}\n{'-'*40}\n"
        
        if len(self.selected_targets) > 5:
            info += f"\n... 還有 {len(self.selected_targets) - 5} 張照片"
        
        messagebox.showinfo("EXIF 資訊", info)
    
    def _show_reference_exif(self):
        """顯示參考照片 EXIF"""
        if not self.selected_references:
            messagebox.showwarning("提示", "請先選擇照片")
            return
        
        info = ""
        for i, photo in enumerate(self.selected_references[:5], 1):
            exif_info = self._get_exif_info(photo['path'])
            info += f"【{i}】{exif_info}\n{'-'*40}\n"
        
        if len(self.selected_references) > 5:
            info += f"\n... 還有 {len(self.selected_references) - 5} 張照片"
        
        messagebox.showinfo("EXIF 資訊", info)
    
    def _get_exif_info(self, image_path):
        """取得 EXIF 資訊"""
        try:
            exif_dict = piexif.load(image_path)
            info = f"檔案: {Path(image_path).name}\n"
            
            if piexif.ExifIFD.DateTimeOriginal in exif_dict.get('Exif', {}):
                date = exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
                info += f"拍攝日期: {date}\n"
            
            if piexif.ImageIFD.Make in exif_dict.get('0th', {}):
                make = exif_dict['0th'][piexif.ImageIFD.Make].decode('utf-8')
                info += f"製造商: {make}\n"
            
            if piexif.ImageIFD.Model in exif_dict.get('0th', {}):
                model = exif_dict['0th'][piexif.ImageIFD.Model].decode('utf-8')
                info += f"型號: {model}\n"
            
            if not info.strip():
                info = "無 EXIF 資訊\n"
            
            return info
        except:
            return f"檔案: {Path(image_path).name}\n無法讀取 EXIF\n"
    
    def _filter_target(self, no_exif_only):
        """過濾目標照片"""
        self._display_target_photos(filter_no_exif=no_exif_only)
    
    def _sort_reference(self, sort_by):
        """排序參考照片"""
        if sort_by == "name":
            self.reference_photos.sort(key=lambda x: x['filename'])
        elif sort_by == "date":
            self.reference_photos.sort(key=lambda x: x.get('exif_date', ''))
        self._display_reference_photos()
    
    def _on_search(self):
        """搜尋功能"""
        search_text = self.search_var.get().lower()
        if not search_text:
            self._display_target_photos()
            self._display_reference_photos()
            self.status_label.config(text="顯示所有照片", foreground="blue")
            return
        
        # 過濾目標照片
        filtered_target = [p for p in self.target_photos if search_text in p['filename'].lower()]
        
        # 清空並顯示
        for widget in self.target_content.winfo_children():
            widget.destroy()
        
        row, col = 0, 0
        max_cols = 3
        for photo in filtered_target:
            self._create_photo_card(self.target_content, photo, row, col, is_target=True)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # 過濾參考照片
        filtered_ref = [p for p in self.reference_photos if search_text in p['filename'].lower()]
        
        for widget in self.reference_content.winfo_children():
            widget.destroy()
        
        row, col = 0, 0
        for photo in filtered_ref:
            self._create_photo_card(self.reference_content, photo, row, col, is_target=False)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        self.status_label.config(
            text=f"搜尋結果: 目標 {len(filtered_target)} 張，參考 {len(filtered_ref)} 張",
            foreground="blue"
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = ExifManualMatcher(root)
    root.mainloop()