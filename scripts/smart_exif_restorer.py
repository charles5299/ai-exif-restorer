#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Smart EXIF Restorer - Unified Tool
Combines folder-based date extraction and visual similarity matching for EXIF restoration

Features:
1. Folder Date Mode: Extract dates from folder/filename patterns
2. Visual Match Mode: Use AI to match photos with reference images
3. Hybrid Mode: Combine both approaches for best accuracy
4. Data Cleaning Phase: Detect and remove system files, thumbnails, screenshots
5. Duplicate Detection & Merge: Find duplicates with iOS-style merge options

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
import hashlib
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Optional, Tuple, Set

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

            # EXIF exists but no datetime found
            print(f"    ℹ️  EXIF found but no datetime in: {os.path.basename(image_path)}")
        except piexif.InvalidImageDataError:
            print(f"    ⚠️  No EXIF data in: {os.path.basename(image_path)}")
        except Exception as e:
            print(f"    ⚠️  EXIF read error for {os.path.basename(image_path)}: {e}")
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
    def get_gps_coords(image_path):
        """Extract GPS coordinates from image EXIF"""
        try:
            exif_dict = piexif.load(image_path)
            gps_ifd = exif_dict.get('GPS', {})

            if piexif.GPSIFD.GPSLatitude in gps_ifd and piexif.GPSIFD.GPSLongitude in gps_ifd:
                # Convert to decimal degrees
                def to_decimal(coords, ref):
                    degrees = coords[0][0] / coords[0][1]
                    minutes = coords[1][0] / coords[1][1]
                    seconds = coords[2][0] / coords[2][1]
                    decimal = degrees + minutes / 60 + seconds / 3600
                    if ref in ['S', 'W']:
                        decimal = -decimal
                    return decimal

                lat = to_decimal(gps_ifd[piexif.GPSIFD.GPSLatitude],
                                 gps_ifd.get(piexif.GPSIFD.GPSLatitudeRef, 'N'))
                lon = to_decimal(gps_ifd[piexif.GPSIFD.GPSLongitude],
                                 gps_ifd.get(piexif.GPSIFD.GPSLongitudeRef, 'E'))

                return {'lat': lat, 'lon': lon}
        except Exception as e:
            print(f"    ⚠️  GPS read error for {os.path.basename(image_path)}: {e}")
        return None

    @staticmethod
    def write_gps_coords(image_path, gps_coords):
        """Write GPS coordinates to image EXIF"""
        try:
            try:
                exif_dict = piexif.load(image_path)
            except:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}

            def to_dms(decimal, ref):
                """Convert decimal degrees to DMS format"""
                decimal = abs(decimal)
                degrees = int(decimal)
                minutes = int((decimal - degrees) * 60)
                seconds = int(((decimal - degrees) * 60 - minutes) * 3600 * 100) / 100.0
                return [
                    (degrees, 1),
                    (minutes, 1),
                    (int(seconds * 100), 100)
                ]

            lat = gps_coords['lat']
            lon = gps_coords['lon']

            exif_dict['GPS'][piexif.GPSIFD.GPSLatitude] = to_dms(lat, 'N')
            exif_dict['GPS'][piexif.GPSIFD.GPSLatitudeRef] = 'S' if lat < 0 else 'N'
            exif_dict['GPS'][piexif.GPSIFD.GPSLongitude] = to_dms(lon, 'E')
            exif_dict['GPS'][piexif.GPSIFD.GPSLongitudeRef] = 'W' if lon < 0 else 'E'

            # Remove thumbnail to reduce file size
            if "thumbnail" in exif_dict:
                del exif_dict["thumbnail"]

            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, image_path)
            return True
        except Exception as e:
            print(f"    ❌ GPS write failed: {e}")
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
# DATA CLEANING MODULE
# =============================================================================

class DataCleaningDetector:
    """Detect and handle system files, thumbnails, and screenshots"""

    # System file patterns
    SYSTEM_FILE_PATTERNS = [
        r'^\._',           # macOS resource forks
        r'^\.DS_Store',    # macOS system files
        r'^Thumbs\.db',    # Windows thumbnails
        r'^\.picasa\.ini', # Picasa metadata
        r'^\.Spotlight-V100',
        r'^\.Trashes',
        r'^\.fseventsd',
        r'^\.TemporaryItems',
    ]

    # Screenshot patterns
    SCREENSHOT_PATTERNS = [
        r'screenshot',
        r'screen shot',
        r'screencap',
        r'capture',
        r'snapchat',
        r'截圖',
        r'截图',
        r'截屏',
        r'屏幕截图',
        r'屏幕快照',
        r'IMG_\d{4}\s*\(\d+\)',  # IMG_1234 (1), IMG_1234 (2), etc.
        r'Screenshot_\d{4}-\d{2}-\d{2}',
        r'Screen\s+Shot\s+\d{4}-\d{2}-\d{2}',
    ]

    def __init__(self, root_folder: str, backup_base: str = None):
        self.root_folder = root_folder
        self.backup_base = backup_base or os.path.join(root_folder, '.backup')

        self.system_files: List[str] = []
        self.screenshot_files: List[str] = []

        self.stats = {
            'total_scanned': 0,
            'system_files': 0,
            'screenshot_files': 0,
            'clean_photos': 0
        }

    def scan_directory(self) -> Dict:
        """Scan directory for system files and screenshots"""
        print("\n" + "=" * 80)
        print("🧹 Data Cleaning Phase")
        print("=" * 80)
        print(f"\n🔍 Scanning: {self.root_folder}")

        self.system_files.clear()
        self.screenshot_files.clear()
        self.stats['total_scanned'] = 0

        for root, dirs, files in os.walk(self.root_folder):
            if '.backup' in root:
                continue

            for file in files:
                self.stats['total_scanned'] += 1
                file_path = os.path.join(root, file)

                if self._is_system_file(file):
                    self.system_files.append(file_path)
                    self.stats['system_files'] += 1

                elif self._is_screenshot(file):
                    self.screenshot_files.append(file_path)
                    self.stats['screenshot_files'] += 1

        self.stats['clean_photos'] = (
            self.stats['total_scanned']
            - self.stats['system_files']
            - self.stats['screenshot_files']
        )

        return self._get_scan_report()

    def _is_system_file(self, filename: str) -> bool:
        """Check if file matches system file patterns"""
        for pattern in self.SYSTEM_FILE_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                return True
        return False

    def _is_screenshot(self, filename: str) -> bool:
        """Check if file matches screenshot patterns"""
        for pattern in self.SCREENSHOT_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                return True
        return False

    def _get_scan_report(self) -> Dict:
        """Generate scan report"""
        return {
            'total': self.stats['total_scanned'],
            'system': self.stats['system_files'],
            'screenshots': self.stats['screenshot_files'],
            'clean': self.stats['clean_photos']
        }

    def clean_system_files(self, confirm: bool = True) -> bool:
        """Clean system files by moving to backup"""
        if not self.system_files:
            return True

        if confirm:
            print(f"\n⚠️  Found {len(self.system_files)} system/thumbnail files:")
            for file in self.system_files[:10]:
                print(f"    ├── {os.path.basename(file)}")
            if len(self.system_files) > 10:
                print(f"    └── ... and {len(self.system_files) - 10} more")

            response = input("\n❓ Delete these files? (y/n/review): ").strip().lower()
            if response == 'n':
                return False
            elif response == 'r':
                # Review mode
                for file in self.system_files:
                    print(f"\n📄 {os.path.basename(file)}")
                    print(f"   Path: {file}")
                    resp = input("   Delete? (y/n): ").strip().lower()
                    if resp != 'y':
                        self.system_files.remove(file)

        # Move to backup
        cleanup_dir = os.path.join(self.backup_base, 'cleanup')
        os.makedirs(cleanup_dir, exist_ok=True)

        for file in self.system_files:
            try:
                rel_path = os.path.relpath(file, self.root_folder)
                backup_path = os.path.join(cleanup_dir, os.path.basename(file))
                shutil.move(file, backup_path)
            except Exception as e:
                print(f"    ⚠️  Failed to move {file}: {e}")

        print(f"✅ System files moved: {cleanup_dir}")
        return True

    def clean_screenshot_files(self, mode: str = 'move') -> bool:
        """
        Handle screenshot files

        Args:
            mode: 'skip', 'move', 'delete'
        """
        if not self.screenshot_files:
            return True

        print(f"\n⚠️  Found {len(self.screenshot_files)} screenshot files:")
        for file in self.screenshot_files[:10]:
            print(f"    ├── {os.path.basename(file)}")
        if len(self.screenshot_files) > 10:
            print(f"    └── ... and {len(self.screenshot_files) - 10} more")

        mode_options = {
            's': 'skip',
            'm': 'move',
            'd': 'delete'
        }

        response = input(f"\n❓ How to handle screenshots? (s=Skip, m=Move to folder, d=Delete): ").strip().lower()
        mode = mode_options.get(response, 'skip')

        if mode == 'skip':
            print("⏭️  Screenshots skipped")
            return True

        elif mode == 'move':
            screenshot_dir = os.path.join(self.backup_base, 'screenshots')
            os.makedirs(screenshot_dir, exist_ok=True)

            for file in self.screenshot_files:
                try:
                    filename = os.path.basename(file)
                    # Handle naming conflicts
                    dest = os.path.join(screenshot_dir, filename)
                    if os.path.exists(dest):
                        base, ext = os.path.splitext(filename)
                        counter = 1
                        while os.path.exists(os.path.join(screenshot_dir, f"{base}_{counter}{ext}")):
                            counter += 1
                        dest = os.path.join(screenshot_dir, f"{base}_{counter}{ext}")

                    shutil.move(file, dest)
                except Exception as e:
                    print(f"    ⚠️  Failed to move {file}: {e}")

            print(f"✅ Screenshots moved: {screenshot_dir}")

        elif mode == 'delete':
            cleanup_dir = os.path.join(self.backup_base, 'cleanup')
            os.makedirs(cleanup_dir, exist_ok=True)

            for file in self.screenshot_files:
                try:
                    shutil.move(file, os.path.join(cleanup_dir, os.path.basename(file)))
                except Exception as e:
                    print(f"    ⚠️  Failed to delete {file}: {e}")

            print(f"✅ Screenshots moved to backup (not deleted for safety)")

        return True

    def print_summary(self):
        """Print cleaning summary"""
        print("\n" + "=" * 80)
        print("📊 Data Cleaning Summary")
        print("=" * 80)
        print(f"Total files scanned: {self.stats['total_scanned']}")
        print(f"├── Regular photos: {self.stats['clean_photos']}")
        print(f"├── System/Thumbnail files: {self.stats['system_files']} ✅ Cleaned" if self.stats['system_files'] == 0 else f"├── System/Thumbnail files: {self.stats['system_files']} ⚠️  Found")
        print(f"└── Screenshot files: {self.stats['screenshot_files']}")
        print(f"\nBackup location: {self.backup_base}")
        print("=" * 80)


# =============================================================================
# DUPLICATE DETECTION MODULE
# =============================================================================

class DuplicateDetector:
    """Detect duplicate photos using hash and visual similarity"""

    def __init__(self, root_folder: str, similarity_threshold: float = 0.92):
        self.root_folder = root_folder
        self.similarity_threshold = similarity_threshold
        self.photo_list: List[Dict] = []
        self.duplicate_groups: List[List[Dict]] = []

        self.stats = {
            'total_photos': 0,
            'unique_photos': 0,
            'duplicates_found': 0,
            'groups_found': 0
        }

    def scan_photos(self, skip_patterns: Set[str] = None) -> None:
        """Scan directory for photos"""
        print("\n" + "=" * 80)
        print("🔍 Duplicate Detection Phase")
        print("=" * 80)
        print(f"\n🔍 Scanning: {self.root_folder}")
        print("⏳ Extracting features...")

        self.photo_list = []

        for root, dirs, files in os.walk(self.root_folder):
            if '.backup' in root:
                continue

            for file in files:
                if not file.lower().endswith(ExifUtils.SUPPORTED_FORMATS):
                    continue

                file_path = os.path.join(root, file)

                # Skip if matches pattern
                if skip_patterns:
                    if any(p in file.lower() for p in skip_patterns):
                        continue

                photo_info = self._analyze_photo(file_path)
                if photo_info:
                    self.photo_list.append(photo_info)

        self.stats['total_photos'] = len(self.photo_list)
        print(f"✅ Analyzed {len(self.photo_list)} photos")

    def _analyze_photo(self, file_path: str) -> Optional[Dict]:
        """Analyze single photo for duplicate detection"""
        try:
            img = Image.open(file_path)

            # Get file info
            file_size = os.path.getsize(file_path)
            width, height = img.size

            # Calculate hashes
            md5_hash = self._calculate_md5(file_path)
            p_hash = imagehash.phash(img, hash_size=16)
            d_hash = imagehash.dhash(img, hash_size=16)

            # Get EXIF
            exif_date = ExifUtils.get_exif_datetime(file_path)

            # Check if screenshot by size
            is_screenshot = self._is_likely_screenshot(file_path, width, height)

            return {
                'path': file_path,
                'filename': os.path.basename(file_path),
                'size': file_size,
                'width': width,
                'height': height,
                'megapixels': width * height / 1_000_000,
                'md5': md5_hash,
                'p_hash': p_hash,
                'd_hash': d_hash,
                'exif_date': exif_date,
                'is_screenshot': is_screenshot
            }
        except Exception as e:
            print(f"    ⚠️  Failed to analyze {file_path}: {e}")
            return None

    def _calculate_md5(self, file_path: str) -> str:
        """Calculate MD5 hash of file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _is_likely_screenshot(self, file_path: str, width: int, height: int) -> bool:
        """Detect if image is likely a screenshot by dimensions"""
        # Common screenshot resolutions
        screenshot_resolutions = [
            (1920, 1080), (2560, 1440), (3840, 2160),  # Desktop
            (1080, 1920), (1440, 2560), (2160, 3840),  # Portrait
            (2048, 2732), (2732, 2048),  # iPad
            (1170, 2532), (1179, 2556),  # iPhone
        ]

        # Check for exact match or close match
        for w, h in screenshot_resolutions:
            if (width, height) in [(w, h), (h, w)]:
                return True
            # Allow small variations
            if abs(width - w) <= 10 and abs(height - h) <= 10:
                return True

        return False

    def find_duplicates(self) -> None:
        """Find duplicate groups using hash and visual similarity"""
        print("\n🔍 Finding duplicates...")

        # Group by MD5 (exact duplicates)
        md5_groups = defaultdict(list)
        for photo in self.photo_list:
            md5_groups[photo['md5']].append(photo)

        # Group by perceptual hash (visual duplicates)
        p_hash_groups = defaultdict(list)
        for photo in self.photo_list:
            # Convert p_hash to string for grouping
            p_hash_str = str(photo['p_hash'])
            p_hash_groups[p_hash_str].append(photo)

        # Find similar groups using hash distance
        self.duplicate_groups = []

        processed = set()

        # First, add exact MD5 duplicates
        for md5, photos in md5_groups.items():
            if len(photos) > 1:
                self.duplicate_groups.append({
                    'type': 'exact',
                    'photos': photos,
                    'hash': md5[:8]
                })
                for p in photos:
                    processed.add(id(p))

        # Then find visual duplicates
        for i, photo1 in enumerate(self.photo_list):
            if id(photo1) in processed:
                continue

            similar_photos = [photo1]

            for j, photo2 in enumerate(self.photo_list):
                if i == j or id(photo2) in processed:
                    continue

                # Calculate hash distance
                hash_distance = photo1['p_hash'] - photo2['p_hash']

                # If distance is small (≤ 5), consider similar
                if hash_distance <= 5:
                    similar_photos.append(photo2)

            if len(similar_photos) > 1:
                self.duplicate_groups.append({
                    'type': 'similar',
                    'photos': similar_photos,
                    'hash': str(photo1['p_hash'])[:8]
                })
                for p in similar_photos:
                    processed.add(id(p))

        self.stats['groups_found'] = len(self.duplicate_groups)
        self.stats['duplicates_found'] = sum(len(g['photos']) for g in self.duplicate_groups) - len(self.duplicate_groups)
        self.stats['unique_photos'] = self.stats['total_photos'] - self.stats['duplicates_found']

        print(f"✅ Found {len(self.duplicate_groups)} duplicate groups")
        print(f"   Total duplicates: {self.stats['duplicates_found']} photos")

    def print_duplicate_groups(self):
        """Print duplicate group details"""
        if not self.duplicate_groups:
            print("\n✅ No duplicates found!")
            return

        print("\n" + "=" * 80)
        print("📋 Duplicate Groups Found")
        print("=" * 80)

        for idx, group in enumerate(self.duplicate_groups, 1):
            group_type = "EXACT DUPLICATES" if group['type'] == 'exact' else "SIMILAR PHOTOS"
            print(f"\nGROUP {idx}: {group_type} ({len(group['photos'])} photos, Hash: {group['hash']})")

            for photo in group['photos']:
                exif_str = photo['exif_date'].strftime('%Y-%m-%d %H:%M') if photo['exif_date'] else "No EXIF"
                screenshot_tag = " - SCREENSHOT" if photo['is_screenshot'] else ""

                print(f"  ├── {photo['filename']}")
                print(f"  │    └── {photo['width']}x{photo['height']}, {photo['size']/1024/1024:.1f}MB, {exif_str}{screenshot_tag}")

    def get_merge_recommendation(self, group: Dict) -> str:
        """Get recommended merge action for a group"""
        photos = group['photos']

        # If all are screenshots, recommend delete
        if all(p['is_screenshot'] for p in photos):
            return 'delete'

        # If one has much better quality, recommend best quality
        sizes = [(p['size'], p) for p in photos]
        sizes.sort(reverse=True)
        if sizes[0][0] > sizes[1][0] * 1.5:
            return 'best_quality'

        # Default to smart merge
        return 'smart_merge'


class DuplicateMergeManager:
    """Manage duplicate merging with iOS-style options"""

    MERGE_OPTIONS = {
        'K': 'keep_all',
        'B': 'best_quality',
        'T': 'timeline',
        'M': 'smart_merge',
        'D': 'delete',
        'R': 'review'
    }

    def __init__(self, root_folder: str, backup_base: str = None):
        self.root_folder = root_folder
        self.backup_base = backup_base or os.path.join(root_folder, '.backup')
        self.duplicate_dir = os.path.join(self.backup_base, 'duplicates')

        self.merge_results = {
            'groups_processed': 0,
            'photos_merged': 0,
            'photos_kept': 0,
            'photos_backed_up': 0
        }

    def present_merge_options(self, group: Dict) -> str:
        """Present iOS-style merge options for a duplicate group"""
        photos = group['photos']

        print("\n" + "-" * 80)
        print("❓ How would you like to handle this group?")
        print("-" * 80)
        print("[K] Keep All Versions")
        print("    → No merge, process each photo independently")
        print("")
        print("[B] Keep Best Quality Version")
        print("    → Keep highest resolution, backup others")
        print("")
        print("[T] Keep Timeline Version")
        print("    → Keep photo with earliest shooting time")
        print("")
        print("[M] Smart Merge (Recommended)")
        print("    → Keep best version + reconcile EXIF metadata")
        print("")
        print("[D] Delete Duplicates Safely")
        print("    → Keep original, backup duplicates")
        print("")
        print("[R] Manual Review Mode")
        print("    → View each photo and decide individually")
        print("-" * 80)

        response = input("Your choice: ").strip().upper()
        return self.MERGE_OPTIONS.get(response, 'keep_all')

    def execute_merge(self, group: Dict, action: str) -> Dict:
        """Execute merge action on duplicate group"""
        photos = group['photos']
        result = {
            'action': action,
            'kept': [],
            'backed_up': [],
            'success': False
        }

        if action == 'keep_all':
            result['kept'] = photos
            result['success'] = True

        elif action == 'best_quality':
            # Sort by file size (quality proxy)
            sorted_photos = sorted(photos, key=lambda p: p['size'], reverse=True)
            master = sorted_photos[0]
            duplicates = sorted_photos[1:]

            result['kept'] = [master]
            result['backed_up'] = duplicates
            result['success'] = self._backup_duplicates(duplicates, group['hash'])

        elif action == 'timeline':
            # Sort by EXIF date, keep earliest
            photos_with_dates = [p for p in photos if p['exif_date']]
            if photos_with_dates:
                sorted_photos = sorted(photos_with_dates, key=lambda p: p['exif_date'])
                master = sorted_photos[0]
                # Find remaining in original list
                duplicates = [p for p in photos if p != master]

                result['kept'] = [master]
                result['backed_up'] = duplicates
                result['success'] = self._backup_duplicates(duplicates, group['hash'])
            else:
                print("    ⚠️  No EXIF dates found, falling back to best quality")
                return self.execute_merge(group, 'best_quality')

        elif action == 'smart_merge':
            # Combine best quality with EXIF reconciliation
            sorted_photos = sorted(photos, key=lambda p: p['size'], reverse=True)
            master = sorted_photos[0]
            duplicates = sorted_photos[1:]

            # Reconcile EXIF
            exif_dates = [p['exif_date'] for p in photos if p['exif_date']]
            if exif_dates:
                # Use consensus date
                exif_dates.sort()
                consensus_date = exif_dates[len(exif_dates) // 2]

                # Write to master if different
                if master['exif_date'] and abs((master['exif_date'] - consensus_date).total_seconds()) > 60:
                    print(f"    📝 Reconciling EXIF for {master['filename']}")
                    ExifUtils.backup_file(master['path'])
                    ExifUtils.write_exif_datetime(master['path'], consensus_date)

            result['kept'] = [master]
            result['backed_up'] = duplicates
            result['success'] = self._backup_duplicates(duplicates, group['hash'])

        elif action == 'delete':
            sorted_photos = sorted(photos, key=lambda p: p['size'], reverse=True)
            master = sorted_photos[0]
            duplicates = sorted_photos[1:]

            result['kept'] = [master]
            result['backed_up'] = duplicates
            result['success'] = self._backup_duplicates(duplicates, group['hash'])

        elif action == 'review':
            # Manual review - implement basic version
            print("\n📸 Manual Review Mode:")
            for i, photo in enumerate(photos):
                print(f"\n[{i}] {photo['filename']}")
                print(f"    Size: {photo['width']}x{photo['height']}, {photo['size']/1024/1024:.1f}MB")
                print(f"    EXIF: {photo['exif_date'] or 'No EXIF'}")

            keep_input = input(f"\nEnter indices to keep (0-{len(photos)-1}, comma-separated, or 'all'): ").strip()
            if keep_input.lower() == 'all':
                result['kept'] = photos
            else:
                indices = [int(x.strip()) for x in keep_input.split(',')]
                kept = [photos[i] for i in indices if 0 <= i < len(photos)]
                duplicates = [p for p in photos if p not in kept]

                result['kept'] = kept
                result['backed_up'] = duplicates
                result['success'] = self._backup_duplicates(duplicates, group['hash'])

        self.merge_results['groups_processed'] += 1
        self.merge_results['photos_kept'] += len(result['kept'])
        self.merge_results['photos_backed_up'] += len(result['backed_up'])

        return result

    def _backup_duplicates(self, duplicates: List[Dict], group_hash: str) -> bool:
        """Backup duplicate files"""
        if not duplicates:
            return True

        # Create group-specific backup folder
        group_backup = os.path.join(self.duplicate_dir, f"group_{group_hash}")
        os.makedirs(group_backup, exist_ok=True)

        for photo in duplicates:
            try:
                dest = os.path.join(group_backup, photo['filename'])
                shutil.move(photo['path'], dest)
            except Exception as e:
                print(f"    ⚠️  Failed to backup {photo['filename']}: {e}")
                return False

        return True

    def print_summary(self):
        """Print merge summary"""
        print("\n" + "=" * 80)
        print("📊 Duplicate Merge Summary")
        print("=" * 80)
        print(f"Groups processed: {self.merge_results['groups_processed']}")
        print(f"Photos kept: {self.merge_results['photos_kept']}")
        print(f"Photos backed up: {self.merge_results['photos_backed_up']}")
        print(f"Space saved: N/A (calculate if needed)")
        print(f"\nBackup location: {self.duplicate_dir}")
        print("=" * 80)


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

        # Left: Reference photos (Source)
        reference_frame = ttk.LabelFrame(content_frame, text="📚 Reference (Source)", padding="10")
        reference_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        ref_tools = ttk.Frame(reference_frame)
        ref_tools.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(ref_tools, text="Sort: Date", command=lambda: self._sort_reference("date")).pack(side=tk.LEFT, padx=2)
        self.ref_count_label = ttk.Label(ref_tools, text="Total: 0", foreground="green", font=("Arial", 9, "bold"))
        self.ref_count_label.pack(side=tk.RIGHT, padx=5)

        ref_scroll = self._create_scroll_frame(reference_frame)
        self.reference_canvas, self.reference_content = ref_scroll

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

        # Right: Target photos (Destination)
        target_frame = ttk.LabelFrame(content_frame, text="🎯 Target (Destination)", padding="10")
        target_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        target_tools = ttk.Frame(target_frame)
        target_tools.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(target_tools, text="Clear", command=self._clear_target_selection).pack(side=tk.LEFT, padx=2)
        ttk.Button(target_tools, text="Select All", command=self._select_all_targets).pack(side=tk.LEFT, padx=2)
        ttk.Separator(target_tools, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        ttk.Button(target_tools, text="📅 Has EXIF", command=self._filter_has_exif).pack(side=tk.LEFT, padx=2)
        ttk.Button(target_tools, text="⚠ No EXIF", command=self._filter_no_exif).pack(side=tk.LEFT, padx=2)
        ttk.Button(target_tools, text="📍 Has GPS", command=self._filter_has_gps).pack(side=tk.LEFT, padx=2)
        ttk.Button(target_tools, text="🔄 Show All", command=self._filter_show_all).pack(side=tk.LEFT, padx=2)
        self.target_count_label = ttk.Label(target_tools, text="Selected: 0", foreground="blue", font=("Arial", 9, "bold"))
        self.target_count_label.pack(side=tk.RIGHT, padx=5)

        target_scroll = self._create_scroll_frame(target_frame)
        self.target_canvas, self.target_content = target_scroll

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
                    exif_date = ExifUtils.get_exif_datetime(path)
                    gps_coords = ExifUtils.get_gps_coords(path)
                    self.target_photos.append({
                        'path': path,
                        'filename': file,
                        'selected': False,
                        'exif_date': exif_date,
                        'gps_coords': gps_coords
                    })

        # Load reference photos if needed
        if mode in ["visual", "hybrid"]:
            self.reference_photos = []
            for root, _, files in os.walk(self.reference_folder):
                for file in files:
                    if file.lower().endswith(ExifUtils.SUPPORTED_FORMATS):
                        path = os.path.join(root, file)
                        exif_date = ExifUtils.get_exif_datetime(path)
                        gps_coords = ExifUtils.get_gps_coords(path)
                        features = self.extractor.extract_features(path)

                        self.reference_photos.append({
                            'path': path,
                            'filename': file,
                            'exif_date': exif_date,
                            'gps_coords': gps_coords,
                            'features': features
                        })

            self.reference_photos.sort(key=lambda x: x.get('exif_date') or datetime.min)

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

        # EXIF Status indicator
        if photo.get('exif_date'):
            exif_label = tk.Label(
                card,
                text=f"📅 {photo['exif_date'].strftime('%Y-%m-%d')}",
                fg="green",
                font=("Arial", 8)
            )
            exif_label.pack()
        else:
            exif_label = tk.Label(
                card,
                text="⚠ No EXIF",
                fg="red",
                font=("Arial", 8, "bold")
            )
            exif_label.pack()

        # GPS Status indicator
        if photo.get('gps_coords'):
            gps = photo['gps_coords']
            gps_label = tk.Label(
                card,
                text=f"📍 {gps['lat']:.4f}, {gps['lon']:.4f}",
                fg="blue",
                font=("Arial", 7)
            )
            gps_label.pack()

        # Status
        if is_target and is_selected:
            select_mark = tk.Label(card, text="✓ Selected", fg="blue", font=("Arial", 9, "bold"), bg="yellow")
            select_mark.pack()

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

    def _filter_has_exif(self):
        """Filter to show only photos with EXIF data"""
        for widget in self.target_content.winfo_children():
            widget.destroy()

        row, col = 0, 0
        max_cols = 3
        count = 0

        for photo in self.target_photos:
            if photo.get('exif_date'):
                self._create_photo_card(self.target_content, photo, row, col, is_target=True)
                col += 1
                count += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        self.target_count_label.config(text=f"Showing: {count} with EXIF")

    def _filter_no_exif(self):
        """Filter to show only photos without EXIF data"""
        for widget in self.target_content.winfo_children():
            widget.destroy()

        row, col = 0, 0
        max_cols = 3
        count = 0

        for photo in self.target_photos:
            if not photo.get('exif_date'):
                self._create_photo_card(self.target_content, photo, row, col, is_target=True)
                col += 1
                count += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        self.target_count_label.config(text=f"Showing: {count} without EXIF")

    def _filter_has_gps(self):
        """Filter to show only photos with GPS data"""
        for widget in self.target_content.winfo_children():
            widget.destroy()

        row, col = 0, 0
        max_cols = 3
        count = 0

        for photo in self.target_photos:
            if photo.get('gps_coords'):
                self._create_photo_card(self.target_content, photo, row, col, is_target=True)
                col += 1
                count += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        self.target_count_label.config(text=f"Showing: {count} with GPS")

    def _filter_show_all(self):
        """Show all photos"""
        self._display_target_photos()
        self.target_count_label.config(text=f"Selected: {len(self.selected_targets)}")

    def _sort_reference(self, sort_by):
        """Sort reference photos"""
        if sort_by == "date":
            self.reference_photos.sort(key=lambda x: x.get('exif_date') or datetime.min)
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
                # Preserve existing GPS if available
                gps_coords = target_photo.get('gps_coords')

                self.analysis_results.append({
                    'target': target_photo,
                    'estimated_exif': {
                        'datetime': folder_date,
                        'confidence': 0.85,
                        'source': 'folder_date',
                        'full_exif': None,
                        'gps_coords': gps_coords
                    }
                })

                self.result_text.insert(tk.END, f"📷 {target_photo['filename']}\n")
                self.result_text.insert(tk.END, f"   Date: {folder_date}\n")
                self.result_text.insert(tk.END, f"   Source: Folder name\n")
                if gps_coords:
                    self.result_text.insert(tk.END, f"   GPS: {gps_coords['lat']:.4f}, {gps_coords['lon']:.4f} (preserved)\n")
                self.result_text.insert(tk.END, "\n")
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
        # Get GPS from best match if available
        gps_coords = matches[0]['ref_photo'].get('gps_coords')

        if mode == "most_similar":
            best_match = matches[0]
            return {
                'datetime': best_match['ref_photo']['exif_date'],
                'confidence': best_match['similarity'],
                'source': 'most_similar',
                'full_exif': None,
                'gps_coords': gps_coords
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
                    'full_exif': None,
                    'gps_coords': gps_coords
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
                        'full_exif': None,
                        'gps_coords': gps_coords
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

            # Write EXIF datetime
            if isinstance(result['estimated_exif']['datetime'], datetime):
                target_datetime = result['estimated_exif']['datetime']
            else:
                # String format
                target_datetime = result['estimated_exif']['datetime']

            if ExifUtils.write_exif_datetime(target_path, target_datetime):
                # Write GPS if available
                gps_coords = result['estimated_exif'].get('gps_coords')
                if gps_coords:
                    ExifUtils.write_gps_coords(target_path, gps_coords)
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

def run_cli_workflow(args):
    """Run complete CLI workflow with data cleaning, duplicate detection, and EXIF restoration"""
    folder = args.folder
    backup_base = os.path.join(folder, '.backup')

    print("\n" + "=" * 80)
    print("📸 AI Smart EXIF Restorer - Full Workflow")
    print("=" * 80)
    print(f"\n📂 Target: {folder}")
    print("=" * 80)

    # Phase 1: Data Cleaning
    if not args.skip_cleanup:
        cleaner = DataCleaningDetector(root_folder=folder, backup_base=backup_base)
        report = cleaner.scan_directory()

        print(f"\n📊 Scan Results:")
        print(f"   Total files: {report['total']}")
        print(f"   Regular photos: {report['clean']}")
        print(f"   System files: {report['system']}")
        print(f"   Screenshots: {report['screenshots']}")

        # Handle system files
        if report['system'] > 0:
            cleaner.clean_system_files(confirm=not args.auto_yes)

        # Handle screenshots
        if report['screenshots'] > 0:
            cleaner.clean_screenshot_files()

        cleaner.print_summary()
    else:
        print("\n⏭️  Skipping data cleaning phase")

    # Phase 2: Duplicate Detection
    if not args.skip_duplicates:
        detector = DuplicateDetector(root_folder=folder, similarity_threshold=0.92)
        detector.scan_photos()
        detector.find_duplicates()

        if detector.duplicate_groups:
            detector.print_duplicate_groups()

            if not args.auto_merge:
                print("\n❓ Process duplicates? (y/n): ", end='')
                response = input().strip().lower()
                if response != 'y':
                    print("⏭️  Skipping duplicate merge")
                    detector.duplicate_groups = []
                else:
                    # Process each group
                    merge_manager = DuplicateMergeManager(root_folder=folder, backup_base=backup_base)

                    for group in detector.duplicate_groups:
                        action = merge_manager.present_merge_options(group)
                        result = merge_manager.execute_merge(group, action)

                        print(f"\n✅ Group processed: {action}")
                        print(f"   Kept: {len(result['kept'])} photos")
                        print(f"   Backed up: {len(result['backed_up'])} photos")

                    merge_manager.print_summary()
            else:
                # Auto-merge with smart merge
                print("\n🤖 Auto-merging duplicates...")
                merge_manager = DuplicateMergeManager(root_folder=folder, backup_base=backup_base)

                for group in detector.duplicate_groups:
                    action = detector.get_merge_recommendation(group)
                    result = merge_manager.execute_merge(group, action)

                    print(f"✅ Auto-merged: {action} - {len(result['kept'])} kept, {len(result['backed_up'])} backed up")

                merge_manager.print_summary()
        else:
            print("\n✅ No duplicates found!")
    else:
        print("\n⏭️  Skipping duplicate detection phase")

    # Phase 3: EXIF Restoration
    print("\n" + "=" * 80)
    print("✨ EXIF Restoration Phase")
    print("=" * 80)

    processor = FolderDateProcessor(
        root_folder=folder,
        backup=not args.no_backup,
        overwrite_existing=args.overwrite
    )
    processor.scan_and_process()

    # Final Summary
    print("\n" + "=" * 80)
    print("🎉 Complete Workflow Finished")
    print("=" * 80)
    print(f"✅ All phases completed!")
    print(f"💾 Backups stored in: {backup_base}")
    print("=" * 80)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='AI Smart EXIF Restorer - Restore photo dates using folder names or visual similarity',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Launch GUI
  python smart_exif_restorer.py

  # CLI mode - Full workflow with all features
  python smart_exif_restorer.py --cli --folder "C:/Photos"

  # CLI mode - Skip data cleaning
  python smart_exif_restorer.py --cli --folder "C:/Photos" --skip-cleanup

  # CLI mode - Skip duplicate detection
  python smart_exif_restorer.py --cli --folder "C:/Photos" --skip-duplicates

  # CLI mode - Auto-merge all duplicates
  python smart_exif_restorer.py --cli --folder "C:/Photos" --auto-merge

  # CLI mode - No backup (use with caution)
  python smart_exif_restorer.py --cli --folder "C:/Photos" --no-backup

  # CLI mode - Overwrite existing EXIF
  python smart_exif_restorer.py --cli --folder "C:/Photos" --overwrite

  # CLI mode - Minimal (skip cleaning and duplicates, no backup)
  python smart_exif_restorer.py --cli --folder "C:/Photos" --skip-cleanup --skip-duplicates --no-backup
        """
    )

    parser.add_argument('--cli', action='store_true', help='Run in CLI mode instead of GUI')
    parser.add_argument('--folder', metavar='PATH', help='Folder path to process (CLI mode)')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup of original files')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing EXIF dates')
    parser.add_argument('--skip-cleanup', action='store_true', help='Skip data cleaning phase')
    parser.add_argument('--skip-duplicates', action='store_true', help='Skip duplicate detection phase')
    parser.add_argument('--auto-merge', action='store_true', help='Automatically merge duplicates using smart recommendations')
    parser.add_argument('--auto-yes', action='store_true', help='Auto-confirm all prompts (use with caution)')

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

        # Run full CLI workflow
        run_cli_workflow(args)

    else:
        # GUI Mode
        root = tk.Tk()
        app = SmartExifRestorerGUI(root)
        root.mainloop()


if __name__ == "__main__":
    main()
