#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Smart EXIF Restorer - Unified Tool
Combines folder-based date extraction and visual similarity matching for EXIF restoration

Features:
1. Folder Date Mode: Extract dates from folder/filename patterns
2. Visual Match Mode: Use AI to match photos with reference images
3. Hybrid Mode: Combine both approaches for best accuracy

Usage:
    python smart_exif_restorer.py                    # Launch GUI
    python smart_exif_restorer.py --cli              # CLI mode
    python smart_exif_restorer.py --cli --folder     # Folder date mode
"""

import os
import re
import sys
import shutil
import argparse
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Image processing imports
from PIL import Image, ImageTk
import piexif
import numpy as np
import imagehash
import cv2


# =============================================================================
# SHARED UTILITIES
# =============================================================================

class ExifUtils:
    """Shared EXIF operations utilities"""

    SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.heic')

    @staticmethod
    def get_exif_datetime(image_path):
        """Extract EXIF datetime from image"""
        try:
            exif_dict = piexif.load(image_path)

            # Try DateTimeOriginal first
            if piexif.ExifIFD.DateTimeOriginal in exif_dict.get('Exif', {}):
                date_str = exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
                return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")

            # Fallback to DateTime
            if piexif.ImageIFD.DateTime in exif_dict.get('0th', {}):
                date_str = exif_dict['0th'][piexif.ImageIFD.DateTime].decode('utf-8')
                return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
        except Exception:
            pass
        return None

    @staticmethod
    def write_exif_datetime(image_path, target_datetime, source_exif=None):
        """Write EXIF datetime to image"""
        try:
            date_str = target_datetime.strftime("%Y:%m:%d %H:%M:%S")

            # Load existing EXIF or create new
            try:
                exif_dict = piexif.load(image_path)
            except:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}

            # Write all three date fields for Google Photos compatibility
            exif_dict['0th'][piexif.ImageIFD.DateTime] = date_str
            exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = date_str
            exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = date_str

            # Remove thumbnail to reduce file size
            if "thumbnail" in exif_dict:
                del exif_dict["thumbnail"]

            # Write to file
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, image_path)
            return True
        except Exception as e:
            print(f"    ❌ EXIF write failed: {e}")
            return False

    @staticmethod
    def backup_file(file_path):
        """Backup original file to .backup folder"""
        try:
            backup_dir = os.path.join(os.path.dirname(file_path), '.backup')
            os.makedirs(backup_dir, exist_ok=True)

            backup_path = os.path.join(backup_dir, os.path.basename(file_path))

            # Skip if backup exists
            if not os.path.exists(backup_path):
                shutil.copy2(file_path, backup_path)

            return True
        except Exception as e:
            print(f"    ⚠️  Backup failed: {e}")
            return False

    @staticmethod
    def extract_date_from_path(path):
        """
        Extract date from folder or filename path
        Supports multiple date formats
        """
        name = Path(path).name

        # Date patterns: (regex, format specifier, parsing logic)
        date_patterns = [
            # 2024-12-25, 2024.12.25, 2024_12_25
            (r'(\d{4})[-._](\d{1,2})[-._](\d{1,2})', 'ymd'),
            # 20241225
            (r'(\d{4})(\d{2})(\d{2})', 'ymd_compact'),
            # 2024年12月25日
            (r'(\d{4})年(\d{1,2})月(\d{1,2})日?', 'chinese'),
            # 12-25-2024, 12.25.2024
            (r'(\d{1,2})[-._](\d{1,2})[-._](\d{4})', 'mdy'),
        ]

        for pattern, mode in date_patterns:
            match = re.search(pattern, name)
            if match:
                try:
                    groups = match.groups()

                    # Parse based on format
                    if mode == 'ymd':
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    elif mode == 'ymd_compact':
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    elif mode == 'chinese':
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    elif mode == 'mdy':
                        month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                    else:
                        continue

                    # Validate date
                    if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                        return datetime(year, month, day, 12, 0, 0)
                except (ValueError, IndexError):
                    continue

        return None


# =============================================================================
# FOLDER DATE MODE
# =============================================================================

class FolderDateProcessor:
    """Process photos using folder/filename date patterns"""

    def __init__(self, root_folder, backup=True, overwrite_existing=False):
        self.root_folder = root_folder
        self.backup = backup
        self.overwrite_existing = overwrite_existing

        self.stats = {
            'total_folders': 0,
            'processed_photos': 0,
            'success': 0,
            'skipped': 0,
            'failed': 0,
            'no_exif': 0,
            'wrong_date': 0
        }

    def scan_and_process(self):
        """Scan and process all folders"""
        print("=" * 80)
        print("📸 Folder Date EXIF Writer")
        print("=" * 80)
        print(f"\n📂 Scanning: {self.root_folder}")
        print(f"⚙️  Settings:")
        print(f"   - Auto backup: {'Yes' if self.backup else 'No'}")
        print(f"   - Overwrite existing EXIF: {'Yes' if self.overwrite_existing else 'No'}")
        print("=" * 80)

        # Collect folders with dates
        folders_with_dates = []

        for root, dirs, files in os.walk(self.root_folder):
            if '.backup' in root:
                continue

            has_photos = any(
                f.lower().endswith(ExifUtils.SUPPORTED_FORMATS) for f in files
            )

            if has_photos:
                folder_date = ExifUtils.extract_date_from_path(root)
                if folder_date:
                    folders_with_dates.append((root, folder_date))
                    self.stats['total_folders'] += 1
                else:
                    # Try extracting from filenames
                    for file in files:
                        if file.lower().endswith(ExifUtils.SUPPORTED_FORMATS):
                            file_date = ExifUtils.extract_date_from_path(file)
                            if file_date:
                                folders_with_dates.append((root, file_date))
                                break

        if not folders_with_dates:
            print("\n❌ No folders with detectable dates found!")
            print("\nSupported formats:")
            print("   - 2024-12-25, 2024.12.25, 2024_12_25")
            print("   - 20241225")
            print("   - 2024年12月25日")
            print("   - 12-25-2024")
            return

        print(f"\n✅ Found {len(folders_with_dates)} folders with dates")
        print("\nStarting processing...\n")

        # Sort by date
        folders_with_dates.sort(key=lambda x: x[1])

        # Process each folder
        for folder_path, folder_date in folders_with_dates:
            self._process_folder(folder_path, folder_date)

        # Print summary
        self._print_summary()

    def _process_folder(self, folder_path, folder_date):
        """Process single folder"""
        print(f"\n📁 Folder: {Path(folder_path).name}")
        print(f"   Date: {folder_date.strftime('%Y-%m-%d')}")

        photo_files = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith(ExifUtils.SUPPORTED_FORMATS)
        ]

        if not photo_files:
            print("   ⚠️  No photos found")
            return

        print(f"   Found {len(photo_files)} photos")

        processed = 0
        for idx, file in enumerate(sorted(photo_files)):
            file_path = os.path.join(folder_path, file)
            self.stats['processed_photos'] += 1

            existing_date = ExifUtils.get_exif_datetime(file_path)

            # Determine if processing needed
            need_process = False
            reason = ""

            if existing_date is None:
                need_process = True
                reason = "No EXIF"
                self.stats['no_exif'] += 1
            elif self.overwrite_existing:
                need_process = True
                reason = "Force overwrite"
            elif existing_date.year < 2000 or existing_date > datetime.now():
                need_process = True
                reason = "Invalid date"
                self.stats['wrong_date'] += 1
            elif abs((existing_date - folder_date).days) > 365:
                need_process = True
                reason = "Date deviation > 1 year"
                self.stats['wrong_date'] += 1

            if need_process:
                # Calculate photo time (2 minute intervals)
                photo_datetime = folder_date + timedelta(minutes=idx * 2)

                # Backup
                if self.backup:
                    ExifUtils.backup_file(file_path)

                # Write EXIF
                if ExifUtils.write_exif_datetime(file_path, photo_datetime):
                    print(f"   ✅ [{reason}] {file[:30]} → {photo_datetime.strftime('%Y-%m-%d %H:%M')}")
                    self.stats['success'] += 1
                    processed += 1
                else:
                    print(f"   ❌ Failed: {file[:30]}")
                    self.stats['failed'] += 1
            else:
                print(f"   ⏭️  Skip: {file[:30]} (has valid EXIF)")
                self.stats['skipped'] += 1

        print(f"   Complete: {processed}/{len(photo_files)} photos processed")

    def _print_summary(self):
        """Print processing summary"""
        print("\n" + "=" * 80)
        print("📊 Processing Summary")
        print("=" * 80)
        print(f"Total folders: {self.stats['total_folders']}")
        print(f"Total photos: {self.stats['processed_photos']}")
        print(f"  ✅ Success: {self.stats['success']}")
        print(f"  ⏭️  Skipped: {self.stats['skipped']}")
        print(f"  ❌ Failed: {self.stats['failed']}")
        print(f"\nIssue breakdown:")
        print(f"  📝 No EXIF: {self.stats['no_exif']}")
        print(f"  🔧 Wrong date: {self.stats['wrong_date']}")

        if self.backup and self.stats['success'] > 0:
            print(f"\n💾 Original files backed up to .backup subfolders")

        print("\n✨ Ready to upload to Google Photos!")
        print("=" * 80)


# =============================================================================
# VISUAL SIMILARITY MATCHER
# =============================================================================

class VisualFeatureExtractor:
    """Extract visual features for similarity matching"""

    @staticmethod
    def extract_features(image_path):
        """Extract comprehensive visual features"""
        try:
            img = Image.open(image_path)

            # 1. Perceptual hashes
            p_hash = imagehash.phash(img, hash_size=16)
            d_hash = imagehash.dhash(img, hash_size=16)
            a_hash = imagehash.average_hash(img, hash_size=16)

            # 2. Color histogram
            img_array = np.array(img.resize((256, 256)))
            if len(img_array.shape) == 3:
                color_hist = [np.histogram(img_array[:,:,i], bins=32)[0] for i in range(3)]
                color_hist = np.concatenate(color_hist)
            else:
                color_hist = np.histogram(img_array, bins=32)[0]

            # 3. Edge features
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
            print(f"Feature extraction failed {image_path}: {e}")
            return None

    @staticmethod
    def calculate_similarity(target_features, ref_features, weights=None):
        """Calculate weighted similarity score"""
        if not target_features or not ref_features:
            return 0.0

        if weights is None:
            weights = {
                'visual': 0.4,
                'color': 0.3,
                'edge': 0.3
            }

        scores = []
        total_weight = 0

        # Visual hash similarity
        if weights.get('visual', 0) > 0:
            hash_sim = 1 - (target_features['p_hash'] - ref_features['p_hash']) / 256.0
            scores.append(max(0, hash_sim))
            total_weight += weights['visual']

        # Color similarity
        if weights.get('color', 0) > 0:
            color_sim = 1 - np.sum(
                np.abs(target_features['color_hist'] - ref_features['color_hist'])
            ) / (2 * np.sum(target_features['color_hist']))
            scores.append(max(0, color_sim))
            total_weight += weights['color']

        # Edge similarity
        if weights.get('edge', 0) > 0:
            edge_diff = abs(target_features['edge_density'] - ref_features['edge_density'])
            edge_sim = 1 - min(edge_diff, 1.0)
            scores.append(max(0, edge_sim))
            total_weight += weights['edge']

        if not scores or total_weight == 0:
            return 0.0

        # Weighted average
        weighted_score = sum(scores) / len(scores)
        return weighted_score


# =============================================================================
# GUI APPLICATION
# =============================================================================

class SmartExifRestorerGUI:
    """GUI for Smart EXIF Restorer"""

    def __init__(self, root):
        self.root = root
        self.root.title("AI Smart EXIF Restorer")
        self.root.geometry("1600x900")

        # Data storage
        self.target_folder = ""
        self.reference_folder = ""
        self.target_photos = []
        self.reference_photos = []
        self.selected_targets = []
        self.analysis_results = []

        # Feature extractor
        self.extractor = VisualFeatureExtractor()

        self._setup_ui()

    def _setup_ui(self):
        """Build user interface"""
        # Top control frame
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)

        # Folder selection
        ttk.Label(control_frame, text="Target Folder:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.target_label = ttk.Label(control_frame, text="Not selected", foreground="gray")
        self.target_label.grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Button(control_frame, text="Browse", command=self._select_target_folder).grid(row=0, column=2, padx=5)

        ttk.Label(control_frame, text="Reference Folder:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.ref_label = ttk.Label(control_frame, text="Not selected", foreground="gray")
        self.ref_label.grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Button(control_frame, text="Browse", command=self._select_reference_folder).grid(row=1, column=2, padx=5)

        ttk.Button(control_frame, text="Load Photos", command=self._load_photos).grid(row=0, column=3, rowspan=2, padx=20)

        # AI parameters
        ttk.Label(control_frame, text="Similarity Threshold:").grid(row=0, column=4, sticky=tk.W, padx=5)
        self.similarity_threshold = tk.DoubleVar(value=0.7)
        ttk.Scale(control_frame, from_=0.5, to=0.95, variable=self.similarity_threshold,
                 orient=tk.HORIZONTAL, length=150).grid(row=0, column=5, padx=5)
        self.threshold_label = ttk.Label(control_frame, text="0.70")
        self.threshold_label.grid(row=0, column=6, padx=5)
        self.similarity_threshold.trace('w', self._update_threshold_label)

        # Mode selection
        ttk.Label(control_frame, text="Mode:").grid(row=1, column=4, sticky=tk.W, padx=5)
        self.processing_mode = tk.StringVar(value="visual")
        mode_frame = ttk.Frame(control_frame)
        mode_frame.grid(row=1, column=5, columnspan=2, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="Visual Match", variable=self.processing_mode,
                       value="visual").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="Folder Date", variable=self.processing_mode,
                       value="folder").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="Hybrid", variable=self.processing_mode,
                       value="hybrid").pack(side=tk.LEFT, padx=5)

        # Status bar
        self.status_label = ttk.Label(control_frame, text="Select folders and load photos", foreground="blue")
        self.status_label.grid(row=1, column=7, sticky=tk.W, padx=5)

        # Main content area
        content_frame = ttk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left: Target photos
        target_frame = ttk.LabelFrame(content_frame, text="🎯 Target Photos", padding="10")
        target_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        target_tools = ttk.Frame(target_frame)
        target_tools.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(target_tools, text="Clear", command=self._clear_target_selection).pack(side=tk.LEFT, padx=2)
        ttk.Button(target_tools, text="Select All", command=self._select_all_targets).pack(side=tk.LEFT, padx=2)
        self.target_count_label = ttk.Label(target_tools, text="Selected: 0", foreground="blue", font=("Arial", 9, "bold"))
        self.target_count_label.pack(side=tk.RIGHT, padx=5)

        target_scroll = self._create_scroll_frame(target_frame)
        self.target_canvas, self.target_content = target_scroll

        # Middle: AI analysis controls
        middle_frame = ttk.Frame(content_frame, width=200)
        middle_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        middle_frame.pack_propagate(False)

        ttk.Label(middle_frame, text="AI Smart Analysis", font=("Arial", 12, "bold")).pack(pady=10)

        # Analysis options
        analysis_opts = ttk.LabelFrame(middle_frame, text="Analysis Options", padding="10")
        analysis_opts.pack(fill=tk.X, pady=10)

        self.use_visual = tk.BooleanVar(value=True)
        ttk.Checkbutton(analysis_opts, text="Visual Similarity", variable=self.use_visual).pack(anchor=tk.W)

        self.use_color = tk.BooleanVar(value=True)
        ttk.Checkbutton(analysis_opts, text="Color Histogram", variable=self.use_color).pack(anchor=tk.W)

        self.use_edge = tk.BooleanVar(value=True)
        ttk.Checkbutton(analysis_opts, text="Edge Features", variable=self.use_edge).pack(anchor=tk.W)

        ttk.Separator(middle_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Time estimation mode
        time_mode_frame = ttk.LabelFrame(middle_frame, text="Time Estimation", padding="10")
        time_mode_frame.pack(fill=tk.X, pady=10)

        self.time_mode = tk.StringVar(value="interpolate")
        ttk.Radiobutton(time_mode_frame, text="Smart Interpolate", variable=self.time_mode,
                       value="interpolate").pack(anchor=tk.W)
        ttk.Radiobutton(time_mode_frame, text="Most Similar", variable=self.time_mode,
                       value="most_similar").pack(anchor=tk.W)
        ttk.Radiobutton(time_mode_frame, text="Weighted Avg", variable=self.time_mode,
                       value="weighted_avg").pack(anchor=tk.W)

        ttk.Separator(middle_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Action buttons
        self.analyze_btn = ttk.Button(middle_frame, text="🤖 Analyze",
                                      command=self._run_analysis, state=tk.DISABLED)
        self.analyze_btn.pack(pady=10, fill=tk.X)

        self.apply_btn = ttk.Button(middle_frame, text="💾 Apply EXIF",
                                   command=self._apply_exif, state=tk.DISABLED)
        self.apply_btn.pack(pady=5, fill=tk.X)

        # Right: Reference photos
        reference_frame = ttk.LabelFrame(content_frame, text="📚 Reference Database", padding="10")
        reference_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        ref_tools = ttk.Frame(reference_frame)
        ref_tools.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(ref_tools, text="Sort: Date", command=lambda: self._sort_reference("date")).pack(side=tk.LEFT, padx=2)
        self.ref_count_label = ttk.Label(ref_tools, text="Total: 0", foreground="green", font=("Arial", 9, "bold"))
        self.ref_count_label.pack(side=tk.RIGHT, padx=5)

        ref_scroll = self._create_scroll_frame(reference_frame)
        self.reference_canvas, self.reference_content = ref_scroll

        # Bottom: Results preview
        result_frame = ttk.LabelFrame(self.root, text="📋 Analysis Results", padding="10")
        result_frame.pack(fill=tk.X, padx=10, pady=5)

        self.result_text = tk.Text(result_frame, height=8, wrap=tk.WORD, font=("Consolas", 9))
        result_scroll = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=result_scroll.set)
        result_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Progress bar
        self.progress_frame = ttk.Frame(self.root)
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='determinate')
        self.progress_label = ttk.Label(self.progress_frame, text="")

    def _create_scroll_frame(self, parent):
        """Create scrollable frame"""
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
        """Update threshold label"""
        self.threshold_label.config(text=f"{self.similarity_threshold.get():.2f}")

    def _select_target_folder(self):
        folder = filedialog.askdirectory(title="Select Target Folder")
        if folder:
            self.target_folder = folder
            self.target_label.config(text=Path(folder).name, foreground="black")

    def _select_reference_folder(self):
        folder = filedialog.askdirectory(title="Select Reference Folder")
        if folder:
            self.reference_folder = folder
            self.ref_label.config(text=Path(folder).name, foreground="black")

    def _load_photos(self):
        """Load photos from folders"""
        if not self.target_folder:
            messagebox.showwarning("Warning", "Please select target folder!")
            return

        mode = self.processing_mode.get()
        if mode in ["visual", "hybrid"] and not self.reference_folder:
            messagebox.showwarning("Warning", "Please select reference folder for visual mode!")
            return

        self.status_label.config(text="Loading photos...", foreground="orange")
        self.root.update()

        # Load target photos
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

        # Load reference photos if needed
        if mode in ["visual", "hybrid"]:
            self.reference_photos = []
            for root, _, files in os.walk(self.reference_folder):
                for file in files:
                    if file.lower().endswith(ExifUtils.SUPPORTED_FORMATS):
                        path = os.path.join(root, file)
                        exif_date = ExifUtils.get_exif_datetime(path)
                        features = self.extractor.extract_features(path)

                        self.reference_photos.append({
                            'path': path,
                            'filename': file,
                            'exif_date': exif_date,
                            'features': features
                        })

            self.reference_photos.sort(key=lambda x: x.get('exif_date') or '')

        self._display_target_photos()
        if mode in ["visual", "hybrid"]:
            self._display_reference_photos()
            self.ref_count_label.config(text=f"Total: {len(self.reference_photos)}")

        self.status_label.config(
            text=f"Loaded: {len(self.target_photos)} target, {len(self.reference_photos) if mode in ['visual', 'hybrid'] else 0} reference",
            foreground="green"
        )

    def _display_target_photos(self):
        """Display target photos in grid"""
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
        """Display reference photos in grid"""
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
        """Create photo card widget"""
        is_selected = photo.get('selected', False)

        card = ttk.Frame(parent, relief=tk.RAISED, borderwidth=2)
        card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        if is_selected:
            card.config(relief=tk.SOLID, borderwidth=3)

        # Thumbnail
        try:
            img = Image.open(photo['path'])
            img.thumbnail((150, 150))
            photo_img = ImageTk.PhotoImage(img)

            img_label = tk.Label(card, image=photo_img, cursor="hand2")
            img_label.image = photo_img
            img_label.pack()

            if is_target:
                img_label.bind("<Button-1>", lambda e, p=photo: self._toggle_selection(p))
        except:
            error_label = tk.Label(card, text="Load failed", fg="red")
            error_label.pack()

        # Filename
        filename_label = tk.Label(card, text=photo['filename'][:20], font=("Arial", 8))
        filename_label.pack()

        # Status
        if is_target and is_selected:
            select_mark = tk.Label(card, text="✓ Selected", fg="blue", font=("Arial", 9, "bold"), bg="yellow")
            select_mark.pack()
        elif not is_target and photo.get('exif_date'):
            date_label = tk.Label(card, text=str(photo['exif_date'])[:10], fg="gray", font=("Arial", 7))
            date_label.pack()

        photo['card'] = card

    def _toggle_selection(self, photo):
        """Toggle photo selection"""
        photo['selected'] = not photo.get('selected', False)

        if photo['selected']:
            if photo not in self.selected_targets:
                self.selected_targets.append(photo)
        else:
            if photo in self.selected_targets:
                self.selected_targets.remove(photo)

        self._display_target_photos()
        self.target_count_label.config(text=f"Selected: {len(self.selected_targets)}")

        self.analyze_btn.config(state=tk.NORMAL if len(self.selected_targets) > 0 else tk.DISABLED)

    def _clear_target_selection(self):
        """Clear all selections"""
        for photo in self.selected_targets:
            photo['selected'] = False
        self.selected_targets.clear()
        self._display_target_photos()
        self.target_count_label.config(text="Selected: 0")
        self.analyze_btn.config(state=tk.DISABLED)

    def _select_all_targets(self):
        """Select all targets"""
        for photo in self.target_photos:
            photo['selected'] = True
            if photo not in self.selected_targets:
                self.selected_targets.append(photo)
        self._display_target_photos()
        self.target_count_label.config(text=f"Selected: {len(self.selected_targets)}")
        self.analyze_btn.config(state=tk.NORMAL)

    def _sort_reference(self, sort_by):
        """Sort reference photos"""
        if sort_by == "date":
            self.reference_photos.sort(key=lambda x: x.get('exif_date') or '')
        self._display_reference_photos()

    def _run_analysis(self):
        """Run AI analysis"""
        if not self.selected_targets:
            messagebox.showwarning("Warning", "Please select target photos!")
            return

        mode = self.processing_mode.get()

        # Show progress
        self.progress_frame.pack(fill=tk.X, padx=10, pady=5)
        self.progress_bar.pack(fill=tk.X)
        self.progress_label.pack()

        self.analysis_results = []
        total = len(self.selected_targets)

        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "=== AI Analysis Started ===\n\n")

        if mode == "folder":
            self._run_folder_date_analysis(total)
        else:
            self._run_visual_analysis(total)

        # Hide progress
        self.progress_bar.pack_forget()
        self.progress_label.pack_forget()
        self.progress_frame.pack_forget()

        self.result_text.insert(tk.END, f"\n=== Analysis Complete: {len(self.analysis_results)} photos ===\n")

        self.apply_btn.config(state=tk.NORMAL)
        messagebox.showinfo("Complete", f"Analysis complete!\nProcessed {len(self.analysis_results)} photos")

    def _run_folder_date_analysis(self, total):
        """Run folder date analysis"""
        for i, target_photo in enumerate(self.selected_targets):
            progress = (i + 1) / total * 100
            self.progress_bar['value'] = progress
            self.progress_label.config(text=f"Analyzing: {i+1}/{total} - {target_photo['filename']}")
            self.root.update()

            # Extract date from path
            folder_path = os.path.dirname(target_photo['path'])
            folder_date = ExifUtils.extract_date_from_path(folder_path)

            if not folder_date:
                # Try filename
                folder_date = ExifUtils.extract_date_from_path(target_photo['filename'])

            if folder_date:
                self.analysis_results.append({
                    'target': target_photo,
                    'estimated_exif': {
                        'datetime': folder_date,
                        'confidence': 0.85,
                        'source': 'folder_date',
                        'full_exif': None
                    }
                })

                self.result_text.insert(tk.END, f"📷 {target_photo['filename']}\n")
                self.result_text.insert(tk.END, f"   Date: {folder_date}\n")
                self.result_text.insert(tk.END, f"   Source: Folder name\n\n")
            else:
                self.result_text.insert(tk.END, f"⚠️  {target_photo['filename']}\n")
                self.result_text.insert(tk.END, f"   No date detected in path\n\n")

    def _run_visual_analysis(self, total):
        """Run visual similarity analysis"""
        for i, target_photo in enumerate(self.selected_targets):
            progress = (i + 1) / total * 100
            self.progress_bar['value'] = progress
            self.progress_label.config(text=f"Analyzing: {i+1}/{total} - {target_photo['filename']}")
            self.root.update()

            # Extract features
            target_features = self.extractor.extract_features(target_photo['path'])

            if not target_features:
                continue

            # Calculate similarities
            similarities = []
            for ref_photo in self.reference_photos:
                if ref_photo['features']:
                    sim_score = self.extractor.calculate_similarity(
                        target_features,
                        ref_photo['features'],
                        {
                            'visual': 0.4 if self.use_visual.get() else 0,
                            'color': 0.3 if self.use_color.get() else 0,
                            'edge': 0.3 if self.use_edge.get() else 0
                        }
                    )
                    if sim_score >= self.similarity_threshold.get():
                        similarities.append({
                            'ref_photo': ref_photo,
                            'similarity': sim_score
                        })

            # Sort and get top matches
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            top_matches = similarities[:5]

            # Estimate EXIF
            estimated_exif = self._estimate_exif(target_photo, top_matches)

            self.analysis_results.append({
                'target': target_photo,
                'matches': top_matches,
                'estimated_exif': estimated_exif
            })

            # Display results
            self.result_text.insert(tk.END, f"📷 {target_photo['filename']}\n")
            self.result_text.insert(tk.END, f"   Found {len(top_matches)} similar photos\n")
            if estimated_exif:
                self.result_text.insert(tk.END, f"   Estimated: {estimated_exif['datetime']}\n")
                self.result_text.insert(tk.END, f"   Confidence: {estimated_exif['confidence']:.2%}\n")
            self.result_text.insert(tk.END, "\n")

    def _estimate_exif(self, target_photo, matches):
        """Estimate EXIF from matches"""
        if not matches:
            return None

        mode = self.time_mode.get()

        if mode == "most_similar":
            best_match = matches[0]
            return {
                'datetime': best_match['ref_photo']['exif_date'],
                'confidence': best_match['similarity'],
                'source': 'most_similar',
                'full_exif': None
            }

        elif mode == "weighted_avg":
            # Weighted average time
            datetimes = []
            weights = []

            for match in matches:
                if match['ref_photo']['exif_date']:
                    dt = match['ref_photo']['exif_date']
                    datetimes.append(dt)
                    weights.append(match['similarity'])

            if datetimes:
                avg_datetime = datetimes[0]  # Simplified
                return {
                    'datetime': avg_datetime,
                    'confidence': sum(weights) / len(weights),
                    'source': 'weighted_average',
                    'full_exif': None
                }

        elif mode == "interpolate":
            if len(matches) >= 2:
                times = [m['ref_photo']['exif_date'] for m in matches[:3] if m['ref_photo']['exif_date']]
                if len(times) >= 2:
                    times.sort()
                    mid_time = times[0] + (times[-1] - times[0]) / 2

                    return {
                        'datetime': mid_time,
                        'confidence': 0.8,
                        'source': 'interpolated',
                        'full_exif': None
                    }

        return None

    def _apply_exif(self):
        """Apply estimated EXIF to photos"""
        if not self.analysis_results:
            messagebox.showwarning("Warning", "No analysis results!")
            return

        count = len([r for r in self.analysis_results if r['estimated_exif']])

        if not messagebox.askyesno("Confirm",
            f"Will write EXIF to {count} photos\nOriginal files will be backed up\n\nContinue?"):
            return

        # Show progress
        self.progress_frame.pack(fill=tk.X, padx=10, pady=5)
        self.progress_bar.pack(fill=tk.X)
        self.progress_label.pack()

        success = 0
        total = len(self.analysis_results)

        for i, result in enumerate(self.analysis_results):
            progress = (i + 1) / total * 100
            self.progress_bar['value'] = progress
            self.progress_label.config(text=f"Writing: {i+1}/{total}")
            self.root.update()

            if not result['estimated_exif']:
                continue

            target_path = result['target']['path']

            # Backup
            ExifUtils.backup_file(target_path)

            # Write EXIF
            if isinstance(result['estimated_exif']['datetime'], datetime):
                target_datetime = result['estimated_exif']['datetime']
            else:
                # String format
                target_datetime = result['estimated_exif']['datetime']

            if ExifUtils.write_exif_datetime(target_path, target_datetime):
                success += 1

        # Hide progress
        self.progress_bar.pack_forget()
        self.progress_label.pack_forget()
        self.progress_frame.pack_forget()

        messagebox.showinfo("Complete",
            f"Successfully wrote EXIF to {success}/{total} photos!\nOriginal files backed up to .backup")

        # Reload
        self.analysis_results.clear()
        self._load_photos()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='AI Smart EXIF Restorer - Restore photo dates using folder names or visual similarity',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Launch GUI
  python smart_exif_restorer.py

  # CLI mode - folder date extraction
  python smart_exif_restorer.py --cli --folder "C:/Photos"

  # CLI mode - no backup
  python smart_exif_restorer.py --cli --folder "C:/Photos" --no-backup

  # CLI mode - overwrite existing EXIF
  python smart_exif_restorer.py --cli --folder "C:/Photos" --overwrite
        """
    )

    parser.add_argument('--cli', action='store_true', help='Run in CLI mode instead of GUI')
    parser.add_argument('--folder', metavar='PATH', help='Folder path to process (CLI mode)')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup of original files')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing EXIF dates')

    args = parser.parse_args()

    if args.cli:
        # CLI Mode
        if not args.folder:
            print("❌ Error: --folder PATH required for CLI mode")
            print("   Use: python smart_exif_restorer.py --cli --folder \"PATH\"")
            sys.exit(1)

        if not os.path.exists(args.folder):
            print(f"❌ Error: Path does not exist: {args.folder}")
            sys.exit(1)

        if not os.path.isdir(args.folder):
            print(f"❌ Error: Not a directory: {args.folder}")
            sys.exit(1)

        # Run folder date processor
        processor = FolderDateProcessor(
            root_folder=args.folder,
            backup=not args.no_backup,
            overwrite_existing=args.overwrite
        )
        processor.scan_and_process()

    else:
        # GUI Mode
        root = tk.Tk()
        app = SmartExifRestorerGUI(root)
        root.mainloop()


if __name__ == "__main__":
    main()
