#!/usr/bin/env python3
"""
FileOrganizerPro v2.6.3
By Bart Labs

AI-powered file organization with Photo Mode, LrForge integration,
and maximalist 2026 UI design.

Changes in v2.6.3:
- FIXED: Preferences dialog layout - URL input now full width, visible
- FIXED: Test connection now uses socket-level test first
- FIXED: Shows what host:port is being tested for debugging
- Better error messages with specific host info

Changes in v2.6.2:
- Folder tree click filters files to that folder/subfolder
- Fixed welcome page empty space (content at top now)
- Thin color borders (5px) on setup sections
- Removed AI Connection from Setup (in Preferences only)
- Added clear filter button when folder is selected

Changes in v2.6:
- Welcome: Bigger cards, settings gear, no dead whitespace
- Setup: Wider labels, flat scroll
- Results: Compact header, pastel stat colors
- Execute: Explicit Move/Copy, LrC checkbox
- Export: CSV, TXT, Shell, .fopplan options
"""

import sys
import os
import json
import hashlib
import subprocess
import threading
import queue
import time
import re
import shutil
import socket
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QProgressBar,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QTreeWidget, QTreeWidgetItem, QSplitter, QFrame, QScrollArea,
    QCheckBox, QSpinBox, QComboBox, QStackedWidget, QDialog,
    QRadioButton, QButtonGroup, QGroupBox, QMessageBox, QToolTip,
    QSizePolicy, QSpacerItem, QGridLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QPainter, QPixmap

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

VERSION = "2.6.4"

class Colors:
    # Primary
    ORANGE = "#FF6B35"
    ORANGE_DARK = "#E85A2A"
    TEAL = "#00D4AA"
    TEAL_DARK = "#00B894"
    
    # Secondary
    PURPLE = "#6C5CE7"
    PURPLE_DARK = "#5B4CC7"
    GOLD = "#FDCB6E"
    MAGENTA = "#E84393"
    
    # Neutrals
    NAVY = "#2D3436"
    CHARCOAL = "#4a5568"
    SLATE = "#64748b"
    CREAM = "#FDF8F3"
    WARM = "#FFFAF5"
    
    # Pastel versions for stat cards
    PURPLE_PASTEL = "#A29BDB"
    TEAL_PASTEL = "#6EE7C8"
    ORANGE_PASTEL = "#FFB088"
    GOLD_PASTEL = "#FDE5A0"
    
    # Semantic
    SUCCESS = "#10B981"
    WARNING = "#F59E0B"
    ERROR = "#EF4444"


# Prompt Presets
PROMPT_PRESETS = {
    1: {
        "name": "General Cleanup",
        "icon": "🗂️",
        "preview": "Sort by type & date",
        "prompt": """Organize files by type and date:

📁 Documents (PDF, DOCX, TXT) → Documents/YYYY/
📁 Images (JPG, PNG, GIF) → Images/YYYY/
📁 Videos (MP4, MOV, AVI) → Videos/YYYY/
📁 Audio (MP3, WAV, FLAC) → Audio/YYYY/
📁 Archives (ZIP, RAR, 7Z) → Archives/
📁 Code → Code/[language]/

Group recent files (30 days) in "Active" folder.
Flag duplicates for review."""
    },
    2: {
        "name": "📸 Photographer",
        "icon": "📸",
        "preview": "Wildlife, weddings, sports...",
        "prompt": """I'm a photographer. Organize by content:

🦅 Wildlife (birds, bears, deer) → Photos/Wildlife/[Species]/YYYY
💒 Weddings → Photos/Weddings/YYYY-MM
🏎️ Sports/Racing → Photos/Sports/[Type]/YYYY
👤 Portraits → Photos/Portraits/YYYY
🏔️ Landscapes → Photos/Landscapes/YYYY
🐕 Pets → Photos/Pets/YYYY
📱 Screenshots → Photos/Screenshots/YYYY

Use existing keywords when available.
Use Vision AI to analyze image content.
Flag duplicates for review."""
    },
    3: {
        "name": "Developer",
        "icon": "💻",
        "preview": "Code by language",
        "prompt": """Developer workflow organization:

📁 Python (.py) → Code/Python/
📁 JavaScript (.js, .ts) → Code/JavaScript/
📁 Web (.html, .css) → Code/Web/
📁 Config (.env, .yaml, .json) → Config/
📁 Documentation (.md, .rst) → Docs/
📁 Data (.csv, .json, .sql) → Data/

Keep project folders intact (detect package.json, requirements.txt).
Group by project when possible."""
    },
    4: {
        "name": "Work/Personal",
        "icon": "💼",
        "preview": "Split by context",
        "prompt": """Split files by context:

💼 Work files → Work/[Category]/YYYY/
   - Contracts, invoices, reports
   - Company logos, brand assets
   - Meeting notes, presentations

🏠 Personal files → Personal/[Category]/YYYY/
   - Photos, videos, music
   - Personal documents
   - Receipts, statements

⚠️ Flag sensitive files for manual review.
Organize by type within each category."""
    },
    5: {
        "name": "Custom",
        "icon": "✏️",
        "preview": "Start blank",
        "prompt": ""
    }
}


class TrustLevel(Enum):
    TRUST = "trust"
    VERIFY = "verify"
    IGNORE = "ignore"


class ClassificationSource(Enum):
    KEYWORDS = "keywords"
    CLIP = "clip"
    VISION = "vision"
    RULE = "rule"
    HASH = "hash"


class Confidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FileInfo:
    path: Path
    name: str
    size: int
    extension: str
    modified: datetime
    destination: str = ""
    confidence: Confidence = Confidence.MEDIUM
    source: ClassificationSource = ClassificationSource.RULE
    reasoning: str = ""
    keywords: List[str] = field(default_factory=list)
    description: str = ""
    gps: Optional[Tuple[float, float]] = None
    file_hash: str = ""
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    is_photo: bool = False
    thumbnail_path: Optional[Path] = None


@dataclass
class OrganizationPlan:
    fopplan_version: str = "1.0"
    created_by: str = "FileOrganizerPro"
    created_at: str = ""
    fop_version: str = VERSION
    source_root: str = ""
    target_root: str = ""
    action: str = "copy"
    statistics: Dict[str, Any] = field(default_factory=dict)
    folders: List[str] = field(default_factory=list)
    moves: List[Dict[str, Any]] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)
    
    def save(self, filepath: Path):
        with open(filepath, 'w') as f:
            f.write(self.to_json())
    
    def to_csv(self) -> str:
        lines = ["Source,Destination,Filename,Size,Confidence,Classification,Reason,IsDuplicate"]
        for m in self.moves:
            lines.append(f'"{m["source"]}","{m["destination"]}","{m["filename"]}",{m["size_bytes"]},{m["confidence"]},{m["classification_source"]},"{m["reasoning"]}",{m["is_duplicate"]}')
        return '\n'.join(lines)
    
    def to_summary(self) -> str:
        lines = [
            "FileOrganizerPro - Organization Plan",
            f"Generated: {self.created_at}",
            "=" * 50,
            "",
            f"Source: {self.source_root}",
            f"Target: {self.target_root}",
            f"Action: {self.action.upper()}",
            "",
            "STATISTICS",
            f"  Files: {self.statistics.get('total_files', 0):,}",
            f"  Size: {self._format_size(self.statistics.get('total_size_bytes', 0))}",
            f"  Folders to create: {self.statistics.get('folders_to_create', 0)}",
            f"  Duplicates found: {self.statistics.get('duplicates_flagged', 0)}",
            "",
            "FOLDER STRUCTURE",
        ]
        
        # Group by top-level folder
        folder_counts = {}
        for m in self.moves:
            top = m['destination'].split('/')[0] if '/' in m['destination'] else m['destination']
            folder_counts[top] = folder_counts.get(top, 0) + 1
        
        for folder, count in sorted(folder_counts.items()):
            lines.append(f"  📁 {folder}/ ({count} files)")
        
        lines.extend(["", "FILE MOVES (first 50)", ""])
        for m in self.moves[:50]:
            lines.append(f"  {m['filename']} → {m['destination']}")
        
        if len(self.moves) > 50:
            lines.append(f"  ... and {len(self.moves) - 50} more files")
        
        return '\n'.join(lines)
    
    def to_shell_script(self) -> str:
        lines = [
            "#!/bin/bash",
            f"# FileOrganizerPro Organization Script",
            f"# Generated: {self.created_at}",
            f"# Source: {self.source_root}",
            f"# Target: {self.target_root}",
            f"# Action: {self.action}",
            "",
            "set -e  # Exit on error",
            "",
            "# Create folders",
        ]
        
        for folder in sorted(set(self.folders)):
            lines.append(f'mkdir -p "{self.target_root}/{folder}"')
        
        lines.extend(["", "# Move/Copy files"])
        
        cmd = "mv" if self.action == "move" else "cp"
        for m in self.moves:
            dest_path = f"{self.target_root}/{m['destination']}"
            lines.append(f'{cmd} "{m["source"]}" "{dest_path}"')
        
        lines.extend(["", f'echo "Done! Processed {len(self.moves)} files."'])
        
        return '\n'.join(lines)
    
    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"


# =============================================================================
# METADATA READER (READ-ONLY)
# =============================================================================

class MetadataReader:
    PHOTO_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
        '.raw', '.cr2', '.cr3', '.nef', '.arw', '.dng', '.orf',
        '.rw2', '.pef', '.srw', '.heic', '.heif'
    }
    
    RAW_EXTENSIONS = {
        '.raw', '.cr2', '.cr3', '.nef', '.arw', '.dng', '.orf',
        '.rw2', '.pef', '.srw'
    }
    
    def __init__(self):
        self.exiftool_available = self._check_exiftool()
    
    def _check_exiftool(self) -> bool:
        try:
            result = subprocess.run(['exiftool', '-ver'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def is_photo(self, filepath: Path) -> bool:
        return filepath.suffix.lower() in self.PHOTO_EXTENSIONS
    
    def is_raw(self, filepath: Path) -> bool:
        return filepath.suffix.lower() in self.RAW_EXTENSIONS
    
    def read_metadata(self, filepath: Path) -> Dict[str, Any]:
        metadata = {'keywords': [], 'description': '', 'gps_lat': None, 'gps_lon': None}
        
        if not self.exiftool_available:
            return metadata
        
        try:
            result = subprocess.run([
                'exiftool', '-json', '-Keywords', '-Subject',
                '-Description', '-Caption-Abstract',
                '-GPSLatitude', '-GPSLongitude', str(filepath)
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data:
                    item = data[0]
                    keywords = []
                    if 'Keywords' in item:
                        kw = item['Keywords']
                        keywords.extend(kw if isinstance(kw, list) else [kw])
                    if 'Subject' in item:
                        subj = item['Subject']
                        keywords.extend(subj if isinstance(subj, list) else [subj])
                    metadata['keywords'] = list(set(keywords))
                    metadata['description'] = item.get('Description') or item.get('Caption-Abstract', '')
        except:
            pass
        
        return metadata


# =============================================================================
# FILE SCANNER
# =============================================================================

class FileScanner(QThread):
    progress = pyqtSignal(int, int, str)
    file_found = pyqtSignal(object)
    scan_complete = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, source_path: Path, options: Dict[str, Any]):
        super().__init__()
        self.source_path = source_path
        self.options = options
        self.files: List[FileInfo] = []
        self.metadata_reader = MetadataReader()
        self._stop_requested = False
    
    def stop(self):
        self._stop_requested = True
    
    def run(self):
        try:
            self._scan_directory(self.source_path)
            self.scan_complete.emit(self.files)
        except Exception as e:
            self.error.emit(str(e))
    
    def _scan_directory(self, path: Path, depth: int = 0):
        if self._stop_requested:
            return
        
        max_files = self.options.get('max_files', 10000)
        include_subfolders = self.options.get('include_subfolders', True)
        
        try:
            items = list(path.iterdir())
        except PermissionError:
            return
        
        for item in items:
            if self._stop_requested or len(self.files) >= max_files:
                return
            
            if item.is_file() and not item.name.startswith('.'):
                file_info = self._process_file(item)
                if file_info:
                    self.files.append(file_info)
                    self.file_found.emit(file_info)
                    self.progress.emit(len(self.files), max_files, item.name)
            
            elif item.is_dir() and include_subfolders and not item.name.startswith('.'):
                self._scan_directory(item, depth + 1)
    
    def _process_file(self, filepath: Path) -> Optional[FileInfo]:
        try:
            stat = filepath.stat()
            file_info = FileInfo(
                path=filepath,
                name=filepath.name,
                size=stat.st_size,
                extension=filepath.suffix.lower(),
                modified=datetime.fromtimestamp(stat.st_mtime),
                is_photo=self.metadata_reader.is_photo(filepath)
            )
            
            if self.options.get('read_keywords', True):
                metadata = self.metadata_reader.read_metadata(filepath)
                file_info.keywords = metadata.get('keywords', [])
                file_info.description = metadata.get('description', '')
            
            if self.options.get('detect_duplicates', True):
                file_info.file_hash = self._calculate_hash(filepath)
            
            return file_info
        except:
            return None
    
    def _calculate_hash(self, filepath: Path, chunk_size: int = 8192) -> str:
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                f.seek(0)
                hasher.update(f.read(chunk_size))
                file_size = filepath.stat().st_size
                if file_size > chunk_size * 2:
                    f.seek(-chunk_size, 2)
                    hasher.update(f.read(chunk_size))
                hasher.update(str(file_size).encode())
            return hasher.hexdigest()
        except:
            return ""


# =============================================================================
# CLASSIFIER
# =============================================================================

class FileClassifier(QThread):
    progress = pyqtSignal(int, int, str)
    file_classified = pyqtSignal(object)
    classification_complete = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, files: List[FileInfo], options: Dict[str, Any]):
        super().__init__()
        self.files = files
        self.options = options
        self._stop_requested = False
        self.rules = self._build_rules()
    
    def stop(self):
        self._stop_requested = True
    
    def _build_rules(self) -> List[Dict]:
        return [
            {'pattern': r'\.(dmg|iso|img)$', 'dest': 'Archives/Disk Images/{year}', 'name': 'Disk Images'},
            {'pattern': r'\.(zip|rar|7z|tar|gz)$', 'dest': 'Archives/Compressed/{year}', 'name': 'Compressed'},
            {'pattern': r'\.(pdf)$', 'dest': 'Documents/PDF/{year}', 'name': 'PDF'},
            {'pattern': r'\.(docx?|rtf)$', 'dest': 'Documents/Word/{year}', 'name': 'Word Docs'},
            {'pattern': r'\.(xlsx?|csv)$', 'dest': 'Documents/Spreadsheets/{year}', 'name': 'Spreadsheets'},
            {'pattern': r'\.(pptx?|key)$', 'dest': 'Documents/Presentations/{year}', 'name': 'Presentations'},
            {'pattern': r'\.(txt|md|rst)$', 'dest': 'Documents/Text/{year}', 'name': 'Text Files'},
            {'pattern': r'\.(py|pyw)$', 'dest': 'Code/Python', 'name': 'Python'},
            {'pattern': r'\.(js|ts|jsx|tsx)$', 'dest': 'Code/JavaScript', 'name': 'JavaScript'},
            {'pattern': r'\.(html|htm|css|scss)$', 'dest': 'Code/Web', 'name': 'Web'},
            {'pattern': r'\.(java|kt)$', 'dest': 'Code/Java', 'name': 'Java'},
            {'pattern': r'\.(c|cpp|h|hpp)$', 'dest': 'Code/C++', 'name': 'C/C++'},
            {'pattern': r'\.(swift|m)$', 'dest': 'Code/Swift', 'name': 'Swift'},
            {'pattern': r'\.(go)$', 'dest': 'Code/Go', 'name': 'Go'},
            {'pattern': r'\.(rs)$', 'dest': 'Code/Rust', 'name': 'Rust'},
            {'pattern': r'\.(sh|bash|zsh)$', 'dest': 'Code/Shell', 'name': 'Shell'},
            {'pattern': r'\.(json|yaml|yml|toml|ini|cfg)$', 'dest': 'Config', 'name': 'Config'},
            {'pattern': r'\.(mp4|mov|avi|mkv|wmv|flv|webm)$', 'dest': 'Videos/{year}', 'name': 'Videos'},
            {'pattern': r'\.(mp3|wav|flac|aac|ogg|m4a)$', 'dest': 'Audio/{year}', 'name': 'Audio'},
            {'pattern': r'\.(svg|ai|eps|psd)$', 'dest': 'Graphics/Design/{year}', 'name': 'Design'},
            {'pattern': r'screenshot', 'dest': 'Images/Screenshots/{year}', 'name': 'Screenshots', 'check_name': True},
            {'pattern': r'\.(app|exe|msi|pkg)$', 'dest': 'Applications/{year}', 'name': 'Applications'},
            {'pattern': r'\.(ttf|otf|woff|woff2)$', 'dest': 'Fonts', 'name': 'Fonts'},
        ]
    
    def run(self):
        try:
            trust_level = TrustLevel(self.options.get('trust_level', 'trust'))
            self._detect_duplicates()
            
            total = len(self.files)
            for i, file_info in enumerate(self.files):
                if self._stop_requested:
                    break
                
                self.progress.emit(i + 1, total, file_info.name)
                
                if file_info.is_duplicate:
                    file_info.destination = "_Duplicates"
                    file_info.confidence = Confidence.HIGH
                    file_info.source = ClassificationSource.HASH
                    file_info.reasoning = f"Duplicate of {Path(file_info.duplicate_of).name if file_info.duplicate_of else 'unknown'}"
                elif file_info.keywords and trust_level == TrustLevel.TRUST:
                    self._classify_from_keywords(file_info)
                elif self._classify_by_rules(file_info):
                    pass
                elif file_info.is_photo and self.options.get('photo_mode', False):
                    self._classify_photo(file_info)
                else:
                    year = file_info.modified.strftime('%Y')
                    file_info.destination = f"Unsorted/{year}"
                    file_info.confidence = Confidence.LOW
                    file_info.source = ClassificationSource.RULE
                    file_info.reasoning = "No matching rule found"
                
                self.file_classified.emit(file_info)
            
            self.classification_complete.emit(self.files)
        except Exception as e:
            self.error.emit(str(e))
    
    def _detect_duplicates(self):
        hash_map: Dict[str, FileInfo] = {}
        for file_info in self.files:
            if not file_info.file_hash:
                continue
            if file_info.file_hash in hash_map:
                file_info.is_duplicate = True
                file_info.duplicate_of = str(hash_map[file_info.file_hash].path)
            else:
                hash_map[file_info.file_hash] = file_info
    
    def _classify_from_keywords(self, file_info: FileInfo):
        keywords = [k.lower() for k in file_info.keywords]
        keywords_str = ', '.join(file_info.keywords)
        
        photo_categories = {
            'Wildlife': ['wildlife', 'bird', 'eagle', 'hawk', 'owl', 'bear', 'deer', 'fox', 'animal'],
            'Weddings': ['wedding', 'bride', 'groom', 'ceremony', 'reception'],
            'Sports': ['sports', 'racing', 'football', 'soccer', 'basketball', 'tennis'],
            'Portraits': ['portrait', 'headshot', 'people', 'person', 'face', 'model'],
            'Landscapes': ['landscape', 'scenery', 'mountain', 'beach', 'sunset', 'sunrise'],
            'Pets': ['pet', 'dog', 'cat', 'puppy', 'kitten'],
        }
        
        year = file_info.modified.strftime('%Y')
        
        for category, category_keywords in photo_categories.items():
            if any(kw in keywords for kw in category_keywords):
                file_info.destination = f"Photos/{category}/{year}"
                file_info.confidence = Confidence.HIGH
                file_info.source = ClassificationSource.KEYWORDS
                file_info.reasoning = f"From keywords: {keywords_str}"
                return
        
        file_info.destination = f"Photos/General/{year}"
        file_info.confidence = Confidence.MEDIUM
        file_info.source = ClassificationSource.KEYWORDS
        file_info.reasoning = f"Has keywords: {keywords_str}"
    
    def _classify_by_rules(self, file_info: FileInfo) -> bool:
        year = file_info.modified.strftime('%Y')
        
        for rule in self.rules:
            pattern = rule['pattern']
            check_name = rule.get('check_name', False)
            text_to_check = file_info.name.lower() if check_name else file_info.extension
            
            if re.search(pattern, text_to_check, re.IGNORECASE):
                dest = rule['dest'].replace('{year}', year)
                file_info.destination = dest
                file_info.confidence = Confidence.HIGH
                file_info.source = ClassificationSource.RULE
                file_info.reasoning = f"Matched rule '{rule['name']}'"
                return True
        return False
    
    def _classify_photo(self, file_info: FileInfo):
        year = file_info.modified.strftime('%Y')
        name_lower = file_info.name.lower()
        
        if any(x in name_lower for x in ['screenshot', 'screen shot', 'screen_shot']):
            file_info.destination = f"Photos/Screenshots/{year}"
            file_info.confidence = Confidence.HIGH
            file_info.source = ClassificationSource.RULE
            file_info.reasoning = "Filename indicates screenshot"
        else:
            file_info.destination = f"Photos/Uncategorized/{year}"
            file_info.confidence = Confidence.LOW
            file_info.source = ClassificationSource.VISION
            file_info.reasoning = "Photo file - Vision AI would classify content"


# =============================================================================
# SETTINGS DIALOG
# =============================================================================

class PreferencesDialog(QDialog):
    def __init__(self, parent, settings: Dict[str, Any]):
        super().__init__(parent)
        self.settings = settings.copy()
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("Preferences")
        self.setFixedSize(600, 580)
        self.setStyleSheet(f"background: {Colors.CREAM};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)
        
        title = QLabel("⚙️ Preferences")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {Colors.NAVY};")
        layout.addWidget(title)
        
        # AI Connection
        ai_group = QGroupBox("AI Connection")
        ai_group.setStyleSheet(self._group_style())
        ai_layout = QVBoxLayout(ai_group)
        ai_layout.setSpacing(12)
        ai_layout.setContentsMargins(16, 20, 16, 16)
        
        url_label = QLabel("LLM Server URL:")
        url_label.setStyleSheet("font-weight: bold;")
        ai_layout.addWidget(url_label)
        
        # URL input - full width
        self.llm_url = QLineEdit(self.settings.get('llm_url', 'http://localhost:1234'))
        self.llm_url.setPlaceholderText("http://localhost:1234")
        self.llm_url.setStyleSheet(f"""
            QLineEdit {{
                background: white;
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 14px;
            }}
            QLineEdit:focus {{ border-color: {Colors.ORANGE}; }}
        """)
        ai_layout.addWidget(self.llm_url)
        
        url_hint = QLabel("Base URL only (e.g., http://localhost:1234 or http://192.168.1.93:1234)")
        url_hint.setStyleSheet(f"font-size: 11px; color: {Colors.SLATE};")
        ai_layout.addWidget(url_hint)
        
        # Test button - on its own row, left aligned
        self.test_btn = QPushButton("🔌 Test Connection")
        self.test_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.NAVY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {Colors.PURPLE}; }}
        """)
        self.test_btn.setFixedWidth(160)
        self.test_btn.clicked.connect(self._test_connection)
        ai_layout.addWidget(self.test_btn)
        
        # Connection status
        self.connection_status = QLabel("")
        self.connection_status.setStyleSheet("font-size: 12px;")
        self.connection_status.setWordWrap(True)
        ai_layout.addWidget(self.connection_status)
        
        layout.addWidget(ai_group)
        
        # Performance
        perf_group = QGroupBox("Performance")
        perf_group.setStyleSheet(self._group_style())
        perf_layout = QGridLayout(perf_group)
        perf_layout.setContentsMargins(16, 20, 16, 16)
        perf_layout.setSpacing(12)
        perf_layout.setColumnMinimumWidth(0, 140)
        perf_layout.setColumnStretch(1, 1)
        
        perf_layout.addWidget(QLabel("Max files:"), 0, 0)
        self.max_files = QSpinBox()
        self.max_files.setRange(100, 100000)
        self.max_files.setValue(self.settings.get('max_files', 10000))
        perf_layout.addWidget(self.max_files, 0, 1)
        
        perf_layout.addWidget(QLabel("Threads:"), 1, 0)
        self.threads = QSpinBox()
        self.threads.setRange(1, 16)
        self.threads.setValue(self.settings.get('threads', 8))
        perf_layout.addWidget(self.threads, 1, 1)
        
        perf_layout.addWidget(QLabel("Thumbnail size:"), 2, 0)
        self.thumb_size = QSpinBox()
        self.thumb_size.setRange(256, 1024)
        self.thumb_size.setValue(self.settings.get('thumb_size', 512))
        perf_layout.addWidget(self.thumb_size, 2, 1)
        
        layout.addWidget(perf_group)
        
        # Logging
        log_group = QGroupBox("Logging")
        log_group.setStyleSheet(self._group_style())
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(16, 20, 16, 16)
        log_layout.setSpacing(12)
        
        self.enable_logging = QCheckBox("Enable logging to file")
        self.enable_logging.setChecked(self.settings.get('enable_logging', True))
        log_layout.addWidget(self.enable_logging)
        
        log_path_row = QHBoxLayout()
        log_path_label = QLabel("Log path:")
        log_path_label.setFixedWidth(80)
        log_path_row.addWidget(log_path_label)
        self.log_path = QLineEdit(self.settings.get('log_path', '~/fop_logs/'))
        self.log_path.setStyleSheet(f"""
            QLineEdit {{
                background: white;
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        log_path_row.addWidget(self.log_path)
        log_layout.addLayout(log_path_row)
        
        layout.addWidget(log_group)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(self._btn_secondary_style())
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(self._btn_primary_style())
        save_btn.clicked.connect(self._save_and_close)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _group_style(self) -> str:
        return f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 12px;
                color: {Colors.NAVY};
                border: 2px solid {Colors.NAVY};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }}
        """
    
    def _input_style(self) -> str:
        return f"""
            QLineEdit {{
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                padding: 6px 10px;
            }}
        """
    
    def _btn_secondary_style(self) -> str:
        return f"""
            QPushButton {{
                background: white;
                border: 2px solid {Colors.NAVY};
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #f1f5f9; }}
        """
    
    def _btn_primary_style(self) -> str:
        return f"""
            QPushButton {{
                background: {Colors.TEAL};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {Colors.TEAL_DARK}; }}
        """
    
    def _test_connection(self):
        self.connection_status.setText("Testing...")
        self.connection_status.setStyleSheet(f"color: {Colors.SLATE}; font-size: 11px;")
        QApplication.processEvents()
        
        url = self.llm_url.text().strip()
        if not url:
            self.connection_status.setText("❌ Please enter a URL")
            self.connection_status.setStyleSheet(f"color: {Colors.ERROR}; font-size: 11px;")
            return
        
        # Clean up URL - get base URL
        url = url.rstrip('/')
        # Remove common endpoint suffixes to get base
        for suffix in ['/v1/chat/completions', '/chat/completions', '/v1/completions', '/completions', '/v1', '/api']:
            if url.endswith(suffix):
                url = url[:-len(suffix)]
                break
        
        # Parse host and port for socket test
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or 80
        
        # First try socket-level connection to verify host is reachable
        self.connection_status.setText(f"Testing {host}:{port}...")
        QApplication.processEvents()
        
        try:
            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
        except socket.timeout:
            self.connection_status.setText(f"❌ Timeout connecting to {host}:{port}")
            self.connection_status.setStyleSheet(f"color: {Colors.ERROR}; font-size: 11px;")
            return
        except socket.error as e:
            error_msg = str(e)
            if 'Errno 65' in error_msg or 'No route' in error_msg:
                self.connection_status.setText(f"❌ Cannot reach {host} - check network/IP")
            elif 'Errno 61' in error_msg or 'Connection refused' in error_msg:
                self.connection_status.setText(f"❌ {host}:{port} refused - is LM Studio server enabled?")
            elif 'Errno 8' in error_msg or 'nodename' in error_msg:
                self.connection_status.setText(f"❌ Invalid hostname: {host}")
            else:
                self.connection_status.setText(f"❌ Network error: {error_msg[:50]}")
            self.connection_status.setStyleSheet(f"color: {Colors.ERROR}; font-size: 11px;")
            return
        
        # Socket connected! Now try HTTP endpoints
        self.connection_status.setText(f"Checking API at {url}...")
        QApplication.processEvents()
        
        # Try multiple endpoints - different LLM servers use different paths
        endpoints_to_try = [
            f"{url}/v1/models",
            f"{url}/models",
            f"{url}/api/models", 
            url,  # Just the base URL
        ]
        
        import urllib.request
        import urllib.error
        
        for test_url in endpoints_to_try:
            try:
                req = urllib.request.Request(test_url, method='GET')
                req.add_header('Content-Type', 'application/json')
                req.add_header('Accept', 'application/json')
                with urllib.request.urlopen(req, timeout=8) as response:
                    # Success! Server responded
                    self.connection_status.setText(f"✅ Connected to {url}")
                    self.connection_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px;")
                    return
            except urllib.error.HTTPError as e:
                # HTTP error means server IS reachable
                if e.code in [404, 405, 400, 401, 403]:
                    continue  # Try next endpoint
                # Any other response means connected
                self.connection_status.setText(f"✅ Connected to {url}")
                self.connection_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px;")
                return
            except:
                continue
        
        # If socket worked but HTTP didn't, server is up but API path unknown
        self.connection_status.setText(f"✅ Server at {url} is reachable")
        self.connection_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px;")
    
    def _save_and_close(self):
        self.settings['llm_url'] = self.llm_url.text()
        self.settings['max_files'] = self.max_files.value()
        self.settings['threads'] = self.threads.value()
        self.settings['thumb_size'] = self.thumb_size.value()
        self.settings['enable_logging'] = self.enable_logging.isChecked()
        self.settings['log_path'] = self.log_path.text()
        self.accept()
    
    def get_settings(self) -> Dict[str, Any]:
        return self.settings


# =============================================================================
# EXECUTE DIALOG
# =============================================================================

class ExecuteDialog(QDialog):
    def __init__(self, parent, file_count: int, total_size: int, source_path: str, target_path: str):
        super().__init__(parent)
        self.file_count = file_count
        self.total_size = total_size
        self.source_path = source_path
        self.target_path = target_path
        self.same_root = self._is_same_root()
        self._setup_ui()
    
    def _is_same_root(self) -> bool:
        if not self.target_path:
            return True
        return Path(self.source_path).resolve() == Path(self.target_path).resolve()
    
    def _setup_ui(self):
        self.setWindowTitle("Execute Organization")
        self.setFixedSize(550, 480)
        self.setStyleSheet(f"background: white;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)
        
        # Header
        title = QLabel("Execute Organization")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {Colors.NAVY};")
        layout.addWidget(title)
        
        stats = QLabel(f"{self.file_count:,} files → {self._format_size(self.total_size)}")
        stats.setStyleSheet(f"font-size: 13px; color: {Colors.SLATE};")
        layout.addWidget(stats)
        
        # Action section
        action_frame = QFrame()
        action_frame.setStyleSheet(f"""
            QFrame {{
                background: {Colors.WARM};
                border: 2px solid {Colors.NAVY};
                border-radius: 10px;
                padding: 16px;
            }}
        """)
        action_layout = QVBoxLayout(action_frame)
        
        action_title = QLabel("ACTION")
        action_title.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {Colors.PURPLE};")
        action_layout.addWidget(action_title)
        
        self.action_group = QButtonGroup()
        
        # Copy option
        self.copy_radio = QRadioButton()
        copy_widget = self._create_option_widget(
            self.copy_radio,
            "Copy files (originals unchanged)",
            f"Creates organized copies. Uses {self._format_size(self.total_size)} additional space."
        )
        self.action_group.addButton(self.copy_radio)
        action_layout.addWidget(copy_widget)
        
        # Move option
        self.move_radio = QRadioButton()
        move_widget = self._create_option_widget(
            self.move_radio,
            "Move files (relocates originals)",
            "Reorganizes in place. No extra space needed.\n⚠️ Cannot be undone without backup."
        )
        self.action_group.addButton(self.move_radio)
        action_layout.addWidget(move_widget)
        
        # Smart default
        if self.same_root:
            self.move_radio.setChecked(True)
        else:
            self.copy_radio.setChecked(True)
        
        layout.addWidget(action_frame)
        
        # Lightroom option
        lr_frame = QFrame()
        lr_frame.setStyleSheet(f"""
            QFrame {{
                background: {Colors.WARM};
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                padding: 16px;
            }}
        """)
        lr_layout = QVBoxLayout(lr_frame)
        
        lr_title = QLabel("LIGHTROOM USERS (optional)")
        lr_title.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {Colors.PURPLE};")
        lr_layout.addWidget(lr_title)
        
        self.lr_checkbox = QCheckBox("Update Lightroom Classic catalog")
        self.lr_checkbox.setStyleSheet("font-weight: bold;")
        lr_layout.addWidget(self.lr_checkbox)
        
        lr_desc = QLabel("Keeps all edits, keywords & collections linked.\nRequires LrForge plugin.")
        lr_desc.setStyleSheet(f"font-size: 11px; color: {Colors.SLATE}; margin-left: 24px;")
        lr_layout.addWidget(lr_desc)
        
        lr_link = QLabel("<a href='#' style='color: #6C5CE7;'>Get LrForge</a>")
        lr_link.setStyleSheet("margin-left: 24px; font-size: 11px;")
        lr_layout.addWidget(lr_link)
        
        layout.addWidget(lr_frame)
        
        # Export only option
        self.export_only = QCheckBox("Export plan only (no files moved)")
        self.export_only.setStyleSheet(f"color: {Colors.SLATE};")
        self.export_only.toggled.connect(self._toggle_export_only)
        layout.addWidget(self.export_only)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                border: 2px solid {Colors.NAVY};
                border-radius: 8px;
                padding: 10px 24px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #f1f5f9; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.execute_btn = QPushButton("Execute →")
        self.execute_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.TEAL};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {Colors.TEAL_DARK}; }}
        """)
        self.execute_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.execute_btn)
        
        layout.addLayout(btn_layout)
    
    def _create_option_widget(self, radio: QRadioButton, title: str, desc: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 8)
        
        layout.addWidget(radio)
        
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(8, 0, 0, 0)
        text_layout.setSpacing(2)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-weight: bold; color: {Colors.NAVY};")
        text_layout.addWidget(title_lbl)
        
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"font-size: 11px; color: {Colors.SLATE};")
        text_layout.addWidget(desc_lbl)
        
        layout.addWidget(text_widget)
        layout.addStretch()
        
        return widget
    
    def _toggle_export_only(self, checked: bool):
        self.copy_radio.setEnabled(not checked)
        self.move_radio.setEnabled(not checked)
        self.lr_checkbox.setEnabled(not checked)
        self.execute_btn.setText("Export →" if checked else "Execute →")
    
    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    
    def get_action(self) -> str:
        if self.export_only.isChecked():
            return "export"
        return "move" if self.move_radio.isChecked() else "copy"
    
    def get_update_lightroom(self) -> bool:
        return self.lr_checkbox.isChecked() and not self.export_only.isChecked()


# =============================================================================
# EXPORT DIALOG
# =============================================================================

class ExportDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("Export Organization Plan")
        self.setFixedSize(450, 350)
        self.setStyleSheet(f"background: white;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        title = QLabel("📤 Export Organization Plan")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {Colors.NAVY};")
        layout.addWidget(title)
        
        self.format_group = QButtonGroup()
        
        formats = [
            ("csv", "Spreadsheet (.csv)", "Open in Excel/Sheets. Review, sort, filter."),
            ("txt", "Summary Report (.txt)", "Human-readable overview with folder tree."),
            ("sh", "Shell Script (.sh)", "Executable commands. Review before running."),
            ("fopplan", "LrForge Plan (.fopplan)", "For Lightroom catalog linking via LrForge."),
        ]
        
        for value, title_text, desc in formats:
            radio = QRadioButton()
            radio.setProperty('format', value)
            
            widget = QWidget()
            widget_layout = QHBoxLayout(widget)
            widget_layout.setContentsMargins(0, 8, 0, 8)
            
            widget_layout.addWidget(radio)
            
            text_widget = QWidget()
            text_layout = QVBoxLayout(text_widget)
            text_layout.setContentsMargins(8, 0, 0, 0)
            text_layout.setSpacing(2)
            
            title_lbl = QLabel(title_text)
            title_lbl.setStyleSheet(f"font-weight: bold; color: {Colors.NAVY};")
            text_layout.addWidget(title_lbl)
            
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"font-size: 11px; color: {Colors.SLATE};")
            text_layout.addWidget(desc_lbl)
            
            widget_layout.addWidget(text_widget)
            widget_layout.addStretch()
            
            self.format_group.addButton(radio)
            layout.addWidget(widget)
            
            if value == "csv":
                radio.setChecked(True)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                border: 2px solid {Colors.NAVY};
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        export_btn = QPushButton("Export")
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.TEAL};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }}
        """)
        export_btn.clicked.connect(self.accept)
        btn_layout.addWidget(export_btn)
        
        layout.addLayout(btn_layout)
    
    def get_format(self) -> str:
        for btn in self.format_group.buttons():
            if btn.isChecked():
                return btn.property('format')
        return "csv"


# =============================================================================
# MAIN WINDOW
# =============================================================================

class FileOrganizerPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.files: List[FileInfo] = []
        self.scanner: Optional[FileScanner] = None
        self.classifier: Optional[FileClassifier] = None
        self.scan_start_time: float = 0
        self.settings = {
            'llm_url': 'http://localhost:1234',
            'max_files': 10000,
            'threads': 8,
            'thumb_size': 512,
            'enable_logging': True,
            'log_path': '~/fop_logs/'
        }
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        self.setWindowTitle(f"FileOrganizerPro v{VERSION} — Bart Labs")
        self.setMinimumSize(1200, 800)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)
        
        self._create_welcome_page()
        self._create_setup_page()
        self._create_results_page()
        
        self.stack.setCurrentIndex(0)
    
    def _create_welcome_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        # Top bar with settings gear
        top_bar = QHBoxLayout()
        
        badge = QLabel("● BART LABS")
        badge.setStyleSheet(f"""
            QLabel {{
                background: {Colors.NAVY};
                color: white;
                padding: 6px 14px;
                border-radius: 15px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        top_bar.addWidget(badge)
        top_bar.addStretch()
        
        # Settings gear button
        settings_btn = QPushButton("⚙️")
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 2px solid {Colors.NAVY};
                border-radius: 18px;
                font-size: 18px;
                min-width: 36px;
                max-width: 36px;
                min-height: 36px;
                max-height: 36px;
            }}
            QPushButton:hover {{
                background: {Colors.GOLD};
            }}
        """)
        settings_btn.clicked.connect(self._open_settings)
        top_bar.addWidget(settings_btn)
        
        version_label = QLabel(f"v{VERSION}")
        version_label.setStyleSheet(f"color: {Colors.SLATE}; font-size: 11px; margin-left: 12px;")
        top_bar.addWidget(version_label)
        
        layout.addLayout(top_bar)
        
        # Hero section
        hero_layout = QHBoxLayout()
        hero_layout.setSpacing(60)
        
        # Left side
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 40, 0, 0)
        
        # Logo
        logo_layout = QHBoxLayout()
        logo_icon = QLabel("📷")
        logo_icon.setStyleSheet("font-size: 60px;")
        logo_layout.addWidget(logo_icon)
        
        logo_text_widget = QWidget()
        logo_text_layout = QVBoxLayout(logo_text_widget)
        logo_text_layout.setSpacing(2)
        logo_text_layout.setContentsMargins(10, 0, 0, 0)
        
        title_label = QLabel()
        title_label.setText(f'<span style="color: {Colors.ORANGE}; font-size: 36px; font-weight: bold;">File</span>'
                           f'<span style="color: {Colors.NAVY}; font-size: 36px; font-weight: bold;">OrganizerPro</span>')
        logo_text_layout.addWidget(title_label)
        
        tagline = QLabel("✨ AI-powered magic for your files")
        tagline.setStyleSheet(f"color: {Colors.SLATE}; font-size: 18px; font-style: italic;")
        logo_text_layout.addWidget(tagline)
        
        logo_layout.addWidget(logo_text_widget)
        logo_layout.addStretch()
        left_layout.addLayout(logo_layout)
        
        # Description
        desc = QLabel()
        desc.setText("Say goodbye to digital chaos! FOP uses <b>local AI</b> to understand your files "
                    "and organize them your way. Perfect for <b>photographers</b> with thousands of images. "
                    "100% private — nothing leaves your computer.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {Colors.NAVY}; font-size: 16px; line-height: 1.6; margin-top: 20px;")
        desc.setMaximumWidth(500)
        left_layout.addWidget(desc)
        
        left_layout.addSpacing(20)
        
        # CTA
        cta_btn = QPushButton("Let's Get Organized  →")
        cta_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 {Colors.ORANGE}, stop:1 {Colors.ORANGE_DARK});
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 16px 32px;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 {Colors.ORANGE_DARK}, stop:1 {Colors.ORANGE});
            }}
        """)
        cta_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cta_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        cta_btn.setFixedWidth(280)
        left_layout.addWidget(cta_btn)
        
        # Small spacer, not unlimited stretch
        left_layout.addSpacing(40)
        hero_layout.addWidget(left_widget, 1)
        
        # Right side - feature cards (BIGGER)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(16)
        
        features = [
            ("🤖", "AI Powered", "Local LLM + CLIP", Colors.TEAL),
            ("📸", "Photo Mode", "RAW + Vision AI", Colors.MAGENTA),
            ("🔗", "LrForge Ready", "LrC integration", Colors.PURPLE),
            ("🔒", "100% Private", "Nothing uploaded", Colors.GOLD),
        ]
        
        for emoji, title, subtitle, color in features:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: white;
                    border: 2px solid {Colors.NAVY};
                    border-radius: 12px;
                }}
            """)
            card.setMinimumHeight(80)
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            
            icon = QLabel(emoji)
            icon.setStyleSheet("font-size: 40px;")  # BIGGER
            icon.setFixedWidth(60)
            card_layout.addWidget(icon)
            
            text_widget = QWidget()
            text_layout = QVBoxLayout(text_widget)
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(4)
            
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {Colors.NAVY};")  # BIGGER
            text_layout.addWidget(title_lbl)
            
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet(f"font-size: 13px; color: {Colors.SLATE};")  # BIGGER
            text_layout.addWidget(sub_lbl)
            
            card_layout.addWidget(text_widget)
            # NO addStretch() - removes dead whitespace
            
            right_layout.addWidget(card)
        
        # Small spacer after cards
        right_layout.addSpacing(20)
        hero_layout.addWidget(right_widget, 1)
        
        layout.addLayout(hero_layout)
        
        # Push footer to bottom
        layout.addStretch()
        
        # Footer
        footer = QLabel(f"FileOrganizerPro v{VERSION} — Built with ♥ by Bart Labs")
        footer.setStyleSheet(f"color: {Colors.SLATE}; font-size: 11px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)
        
        self.stack.addWidget(page)
    
    def _create_setup_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)
        
        # Header
        header = QHBoxLayout()
        
        back_btn = QPushButton("←")
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                border: 2px solid {Colors.NAVY};
                border-radius: 22px;
                font-size: 20px;
                min-width: 44px; max-width: 44px;
                min-height: 44px; max-height: 44px;
            }}
            QPushButton:hover {{ background: {Colors.GOLD}; }}
        """)
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        header.addWidget(back_btn)
        
        title = QLabel()
        title.setText(f'<span style="font-size: 28px; font-weight: bold; color: {Colors.NAVY};">Setup</span> '
                     f'<span style="font-size: 28px; color: {Colors.ORANGE}; font-style: italic;">your way</span>')
        header.addWidget(title)
        header.addStretch()
        
        badge = QLabel("● BART LABS")
        badge.setStyleSheet(f"""
            QLabel {{
                background: {Colors.NAVY};
                color: white;
                padding: 6px 14px;
                border-radius: 15px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        header.addWidget(badge)
        
        layout.addLayout(header)
        
        # Single scroll area (FLAT - no nested scrolling)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(16)
        scroll_layout.setContentsMargins(0, 0, 16, 0)
        
        # Folders section
        folders_frame = self._create_section_frame("FOLDERS", Colors.ORANGE)
        folders_layout = QVBoxLayout()
        folders_layout.setSpacing(12)
        
        # Source row
        source_row = QHBoxLayout()
        source_label = QLabel("Source")
        source_label.setFixedWidth(100)  # WIDER
        source_label.setStyleSheet(f"font-weight: 500; color: {Colors.NAVY};")
        source_row.addWidget(source_label)
        
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("~/Downloads or drag folder here...")
        self.source_input.setStyleSheet(self._input_style())
        source_row.addWidget(self.source_input)
        
        source_btn = QPushButton("Browse")
        source_btn.setStyleSheet(self._button_style())
        source_btn.clicked.connect(self._browse_source)
        source_row.addWidget(source_btn)
        folders_layout.addLayout(source_row)
        
        # Target row
        target_row = QHBoxLayout()
        target_label = QLabel("Target")
        target_label.setFixedWidth(100)  # WIDER
        target_label.setStyleSheet(f"font-weight: 500; color: {Colors.NAVY};")
        target_row.addWidget(target_label)
        
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Where organized files will go...")
        self.target_input.setStyleSheet(self._input_style())
        target_row.addWidget(self.target_input)
        
        target_btn = QPushButton("Browse")
        target_btn.setStyleSheet(self._button_style())
        target_btn.clicked.connect(self._browse_target)
        target_row.addWidget(target_btn)
        folders_layout.addLayout(target_row)
        
        folders_frame.layout().addLayout(folders_layout)
        scroll_layout.addWidget(folders_frame)
        
        # Guidance section
        guidance_frame = self._create_section_frame("ORGANIZATION GUIDANCE", Colors.PURPLE)
        guidance_layout = QVBoxLayout()
        guidance_layout.setSpacing(12)
        
        # Presets header
        preset_header = QHBoxLayout()
        preset_label = QLabel("🎯 Quick Start Presets")
        preset_label.setStyleSheet(f"font-weight: bold; color: {Colors.NAVY};")
        preset_header.addWidget(preset_label)
        preset_header.addStretch()
        guidance_layout.addLayout(preset_header)
        
        # Preset buttons
        presets_row = QHBoxLayout()
        presets_row.setSpacing(8)
        
        self.preset_buttons = []
        for num, preset in PROMPT_PRESETS.items():
            btn = QPushButton(f"{num}\n{preset['name']}")
            btn.setProperty('preset_num', num)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Colors.WARM};
                    border: 2px solid #e2e8f0;
                    border-radius: 10px;
                    padding: 10px;
                    font-size: 11px;
                    min-width: 110px;
                }}
                QPushButton:hover {{ border-color: {Colors.ORANGE}; }}
                QPushButton:checked {{
                    border-color: {Colors.ORANGE};
                    background: white;
                }}
            """)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, n=num: self._select_preset(n))
            self.preset_buttons.append(btn)
            presets_row.addWidget(btn)
        
        guidance_layout.addLayout(presets_row)
        
        # Prompt textarea
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Describe how you want your files organized...")
        self.prompt_input.setStyleSheet(f"""
            QTextEdit {{
                background: {Colors.WARM};
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 12px;
                font-size: 12px;
            }}
            QTextEdit:focus {{ border-color: {Colors.ORANGE}; }}
        """)
        self.prompt_input.setMinimumHeight(100)
        self.prompt_input.setMaximumHeight(140)
        guidance_layout.addWidget(self.prompt_input)
        
        # Trust levels
        trust_frame = QFrame()
        trust_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #F0FFF8, stop:1 white);
                border: 2px solid {Colors.TEAL};
                border-radius: 10px;
                padding: 12px;
            }}
        """)
        trust_layout = QVBoxLayout(trust_frame)
        trust_layout.setSpacing(8)
        
        trust_title = QLabel("🏷️ Existing Keywords")
        trust_title.setStyleSheet(f"font-weight: bold; color: {Colors.NAVY};")
        trust_layout.addWidget(trust_title)
        
        self.trust_group = QButtonGroup()
        trust_options = [
            ("trust", "Trust existing keywords — ⚡ FASTEST"),
            ("verify", "Verify with AI — ⚡ FAST"),
            ("ignore", "Ignore (AI only) — Standard"),
        ]
        
        for value, label in trust_options:
            radio = QRadioButton(label)
            radio.setProperty('trust_value', value)
            self.trust_group.addButton(radio)
            trust_layout.addWidget(radio)
            if value == "trust":
                radio.setChecked(True)
        
        # Read-only notice
        readonly_label = QLabel("🛡️ READ-ONLY: FOP never writes metadata or creates XMP files.")
        readonly_label.setStyleSheet(f"""
            background: #FFF9E6;
            border: 2px solid {Colors.GOLD};
            border-radius: 6px;
            padding: 8px;
            font-size: 11px;
        """)
        trust_layout.addWidget(readonly_label)
        
        guidance_layout.addWidget(trust_frame)
        guidance_frame.layout().addLayout(guidance_layout)
        scroll_layout.addWidget(guidance_frame)
        
        # Options section
        options_frame = self._create_section_frame("OPTIONS", Colors.TEAL)
        options_layout = QHBoxLayout()
        
        # Left column
        left_col = QVBoxLayout()
        self.include_subfolders = QCheckBox("Include subfolders")
        self.include_subfolders.setChecked(True)
        left_col.addWidget(self.include_subfolders)
        
        self.detect_duplicates = QCheckBox("Detect duplicates")
        self.detect_duplicates.setChecked(True)
        left_col.addWidget(self.detect_duplicates)
        
        self.photo_mode = QCheckBox("Photo Mode (RAW thumbnails)")
        self.photo_mode.setChecked(True)
        left_col.addWidget(self.photo_mode)
        
        self.use_vision = QCheckBox("Vision AI (detailed analysis)")
        left_col.addWidget(self.use_vision)
        
        options_layout.addLayout(left_col)
        options_layout.addStretch()
        options_frame.layout().addLayout(options_layout)
        scroll_layout.addWidget(options_frame)
        
        # Analyze button
        self.analyze_btn = QPushButton("📸 Analyze Files  →")
        self.analyze_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 {Colors.TEAL}, stop:1 {Colors.TEAL_DARK});
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 16px;
                border: none;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 {Colors.TEAL_DARK}, stop:1 {Colors.TEAL});
            }}
            QPushButton:disabled {{ background: #cccccc; }}
        """)
        self.analyze_btn.clicked.connect(self._start_analysis)
        scroll_layout.addWidget(self.analyze_btn)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        self._select_preset(2)
        self.stack.addWidget(page)
    
    def _create_section_frame(self, title: str, accent_color: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: 2px solid {Colors.NAVY};
                border-left: 5px solid {accent_color};
                border-radius: 12px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {Colors.PURPLE};")
        layout.addWidget(title_label)
        
        return frame
    
    def _create_results_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 12, 30, 16)  # REDUCED top padding
        layout.setSpacing(12)
        
        # Header (compact)
        header = QHBoxLayout()
        
        back_btn = QPushButton("←")
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                border: 2px solid {Colors.NAVY};
                border-radius: 18px;
                font-size: 18px;
                min-width: 36px; max-width: 36px;
                min-height: 36px; max-height: 36px;
            }}
            QPushButton:hover {{ background: {Colors.GOLD}; }}
        """)
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        header.addWidget(back_btn)
        
        title = QLabel()
        title.setText(f'<span style="font-size: 22px; font-weight: bold; color: {Colors.NAVY};">Organization</span> '
                     f'<span style="font-size: 22px; color: {Colors.ORANGE}; font-style: italic;">Preview</span>')
        header.addWidget(title)
        header.addStretch()
        
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet(f"color: {Colors.SLATE}; font-size: 11px;")
        header.addWidget(self.stats_label)
        
        layout.addLayout(header)
        
        # Metrics (PASTEL colors)
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(10)
        
        self.metric_cards = {}
        metrics = [
            ("total_files", "Files", Colors.PURPLE_PASTEL),
            ("total_size", "Size", Colors.TEAL_PASTEL),
            ("folders", "Folders", "#B8A9D9"),  # Lighter purple
            ("duplicates", "Duplicates", Colors.ORANGE_PASTEL),
            ("time", "Time", Colors.GOLD_PASTEL),
        ]
        
        for key, label, color in metrics:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {color};
                    border-radius: 10px;
                    min-width: 100px;
                }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            value_label = QLabel("0")
            value_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(value_label)
            
            name_label = QLabel(label)
            name_label.setStyleSheet("color: rgba(255,255,255,0.9); font-size: 9px; font-weight: bold;")
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(name_label)
            
            self.metric_cards[key] = value_label
            metrics_layout.addWidget(card)
        
        layout.addLayout(metrics_layout)
        
        # Main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Folder tree
        folder_frame = QFrame()
        folder_frame.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: 2px solid {Colors.NAVY};
                border-radius: 10px;
            }}
        """)
        folder_layout = QVBoxLayout(folder_frame)
        folder_layout.setContentsMargins(12, 12, 12, 12)
        
        folder_title = QLabel("FOLDER STRUCTURE")
        folder_title.setStyleSheet(f"font-size: 9px; font-weight: bold; color: {Colors.PURPLE};")
        folder_layout.addWidget(folder_title)
        
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setStyleSheet("border: none; font-size: 11px;")
        self.folder_tree.itemClicked.connect(self._on_folder_clicked)
        self.selected_folder = None  # Track selected folder for filtering
        folder_layout.addWidget(self.folder_tree)
        
        splitter.addWidget(folder_frame)
        
        # Files table
        files_frame = QFrame()
        files_frame.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: 2px solid {Colors.NAVY};
                border-radius: 10px;
            }}
        """)
        files_layout = QVBoxLayout(files_frame)
        files_layout.setContentsMargins(12, 12, 12, 12)
        
        files_header = QHBoxLayout()
        self.files_title = QLabel("FILE SUGGESTIONS")
        self.files_title.setStyleSheet(f"font-size: 9px; font-weight: bold; color: {Colors.PURPLE};")
        files_header.addWidget(self.files_title)
        
        # Folder filter indicator (hidden by default)
        self.folder_filter_label = QLabel("")
        self.folder_filter_label.setStyleSheet(f"font-size: 10px; color: {Colors.ORANGE}; margin-left: 8px;")
        self.folder_filter_label.hide()
        files_header.addWidget(self.folder_filter_label)
        
        # Clear filter button
        self.clear_filter_btn = QPushButton("✕ Clear")
        self.clear_filter_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {Colors.ORANGE};
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 10px;
                color: {Colors.ORANGE};
            }}
            QPushButton:hover {{ background: {Colors.WARM}; }}
        """)
        self.clear_filter_btn.clicked.connect(self._clear_folder_filter)
        self.clear_filter_btn.hide()
        files_header.addWidget(self.clear_filter_btn)
        
        files_header.addStretch()
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Files", "High Confidence", "From Keywords", "From AI", "Duplicates"])
        self.filter_combo.setStyleSheet(f"padding: 4px 8px; font-size: 11px;")
        self.filter_combo.currentTextChanged.connect(self._filter_files)
        files_header.addWidget(self.filter_combo)
        files_layout.addLayout(files_header)
        
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(4)
        self.files_table.setHorizontalHeaderLabels(["File", "Confidence", "Source", "Size"])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files_table.setStyleSheet("border: none; font-size: 11px;")
        files_layout.addWidget(self.files_table)
        
        splitter.addWidget(files_frame)
        splitter.setSizes([250, 650])
        
        layout.addWidget(splitter, 1)
        
        # Action bar
        action_layout = QHBoxLayout()
        
        export_btn = QPushButton("📤 Export Plan")
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                border: 2px solid {Colors.NAVY};
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {Colors.GOLD}; }}
        """)
        export_btn.clicked.connect(self._show_export_dialog)
        action_layout.addWidget(export_btn)
        
        action_layout.addStretch()
        
        execute_btn = QPushButton("Execute Organization  →")
        execute_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.TEAL};
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{ background: {Colors.TEAL_DARK}; }}
        """)
        execute_btn.clicked.connect(self._show_execute_dialog)
        action_layout.addWidget(execute_btn)
        
        layout.addLayout(action_layout)
        
        self.stack.addWidget(page)
    
    def _input_style(self) -> str:
        return f"""
            QLineEdit {{
                background: {Colors.WARM};
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {Colors.ORANGE}; }}
        """
    
    def _button_style(self) -> str:
        return f"""
            QPushButton {{
                background: {Colors.NAVY};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {Colors.PURPLE}; }}
        """
    
    def _apply_styles(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background: {Colors.CREAM}; }}
            QWidget {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
            QCheckBox {{ font-size: 12px; }}
        """)
    
    # Actions
    def _open_settings(self):
        dialog = PreferencesDialog(self, self.settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.settings = dialog.get_settings()
    
    def _browse_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if folder:
            self.source_input.setText(folder)
    
    def _browse_target(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Target Folder")
        if folder:
            self.target_input.setText(folder)
    
    def _select_preset(self, num: int):
        for btn in self.preset_buttons:
            btn.setChecked(btn.property('preset_num') == num)
        preset = PROMPT_PRESETS.get(num, {})
        self.prompt_input.setText(preset.get('prompt', ''))
    
    def _get_trust_level(self) -> str:
        for btn in self.trust_group.buttons():
            if btn.isChecked():
                return btn.property('trust_value')
        return 'trust'
    
    def _start_analysis(self):
        source = self.source_input.text().strip()
        if not source:
            QMessageBox.warning(self, "Missing Source", "Please select a source folder.")
            return
        
        source_path = Path(source).expanduser()
        if not source_path.exists():
            QMessageBox.warning(self, "Invalid Source", f"Folder not found:\n{source_path}")
            return
        
        options = {
            'include_subfolders': self.include_subfolders.isChecked(),
            'detect_duplicates': self.detect_duplicates.isChecked(),
            'photo_mode': self.photo_mode.isChecked(),
            'use_vision': self.use_vision.isChecked(),
            'max_files': self.settings['max_files'],
            'threads': self.settings['threads'],
            'read_keywords': True,
            'trust_level': self._get_trust_level(),
            'prompt': self.prompt_input.toPlainText(),
            'use_llm': True,
            'llm_url': self.settings['llm_url'],
        }
        
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Scanning...")
        self.scan_start_time = time.time()
        
        self.scanner = FileScanner(source_path, options)
        self.scanner.progress.connect(self._on_scan_progress)
        self.scanner.scan_complete.connect(lambda files: self._on_scan_complete(files, options))
        self.scanner.error.connect(self._on_error)
        self.scanner.start()
    
    def _on_scan_progress(self, current: int, total: int, filename: str):
        self.analyze_btn.setText(f"Scanning... {current} files")
    
    def _on_scan_complete(self, files: List[FileInfo], options: Dict):
        self.files = files
        self.analyze_btn.setText(f"Classifying {len(files)} files...")
        
        self.classifier = FileClassifier(files, options)
        self.classifier.progress.connect(self._on_classify_progress)
        self.classifier.classification_complete.connect(self._on_classification_complete)
        self.classifier.error.connect(self._on_error)
        self.classifier.start()
    
    def _on_classify_progress(self, current: int, total: int, filename: str):
        self.analyze_btn.setText(f"Classifying... {current}/{total}")
    
    def _on_classification_complete(self, files: List[FileInfo]):
        self.files = files
        elapsed = time.time() - self.scan_start_time
        
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("📸 Analyze Files  →")
        
        self._update_results(elapsed)
        self.stack.setCurrentIndex(2)
    
    def _on_error(self, error: str):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("📸 Analyze Files  →")
        QMessageBox.critical(self, "Error", f"An error occurred:\n{error}")
    
    def _update_results(self, elapsed: float):
        total_size = sum(f.size for f in self.files)
        duplicates = sum(1 for f in self.files if f.is_duplicate)
        folders = len(set(f.destination.split('/')[0] for f in self.files if f.destination))
        
        self.metric_cards['total_files'].setText(str(len(self.files)))
        self.metric_cards['total_size'].setText(self._format_size(total_size))
        self.metric_cards['folders'].setText(str(folders))
        self.metric_cards['duplicates'].setText(str(duplicates))
        self.metric_cards['time'].setText(f"{elapsed:.1f}s")
        
        keywords_count = sum(1 for f in self.files if f.keywords)
        keywords_pct = (keywords_count / len(self.files) * 100) if self.files else 0
        self.stats_label.setText(f"{len(self.files)} files • {self._format_size(total_size)} • {keywords_pct:.0f}% had keywords")
        
        self._build_folder_tree()
        self._populate_files_table()
    
    def _build_folder_tree(self):
        self.folder_tree.clear()
        
        folder_counts: Dict[str, int] = {}
        for f in self.files:
            if f.destination:
                parts = f.destination.split('/')
                for i in range(len(parts)):
                    path = '/'.join(parts[:i+1])
                    folder_counts[path] = folder_counts.get(path, 0) + 1
        
        root = QTreeWidgetItem(["📁 Organized Files"])
        self.folder_tree.addTopLevelItem(root)
        
        items: Dict[str, QTreeWidgetItem] = {'': root}
        
        for path in sorted(folder_counts.keys()):
            parts = path.split('/')
            parent_path = '/'.join(parts[:-1])
            name = parts[-1]
            count = folder_counts[path]
            
            parent = items.get(parent_path, root)
            item = QTreeWidgetItem([f"📁 {name} ({count})"])
            parent.addChild(item)
            items[path] = item
        
        root.setExpanded(True)
    
    def _populate_files_table(self, filter_text: str = "All Files"):
        self.files_table.setRowCount(0)
        
        for f in self.files:
            # Filter by dropdown selection
            if filter_text == "High Confidence" and f.confidence != Confidence.HIGH:
                continue
            elif filter_text == "From Keywords" and f.source != ClassificationSource.KEYWORDS:
                continue
            elif filter_text == "From AI" and f.source not in [ClassificationSource.CLIP, ClassificationSource.VISION]:
                continue
            elif filter_text == "Duplicates" and not f.is_duplicate:
                continue
            
            # Filter by selected folder (from tree click)
            if self.selected_folder:
                if not f.destination.startswith(self.selected_folder):
                    continue
            
            row = self.files_table.rowCount()
            self.files_table.insertRow(row)
            
            # File info
            file_widget = QWidget()
            file_layout = QVBoxLayout(file_widget)
            file_layout.setContentsMargins(4, 4, 4, 4)
            file_layout.setSpacing(2)
            
            icon = "📷" if f.is_photo else "📄"
            name_label = QLabel(f"{icon} {f.name}")
            name_label.setStyleSheet(f"font-weight: bold; color: {Colors.NAVY}; font-size: 11px;")
            file_layout.addWidget(name_label)
            
            dest_label = QLabel(f"→ {f.destination}")
            dest_label.setStyleSheet(f"font-size: 10px; color: {Colors.ORANGE};")
            file_layout.addWidget(dest_label)
            
            reason_label = QLabel(f.reasoning[:50] + "..." if len(f.reasoning) > 50 else f.reasoning)
            reason_label.setStyleSheet(f"font-size: 9px; color: {Colors.SLATE};")
            file_layout.addWidget(reason_label)
            
            self.files_table.setCellWidget(row, 0, file_widget)
            
            # Confidence
            conf_colors = {
                Confidence.HIGH: ("#d4edda", "#155724"),
                Confidence.MEDIUM: ("#fff3cd", "#856404"),
                Confidence.LOW: ("#f8d7da", "#721c24"),
            }
            bg, fg = conf_colors.get(f.confidence, ("#f1f5f9", Colors.NAVY))
            conf_label = QLabel(f.confidence.value.upper())
            conf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            conf_label.setStyleSheet(f"background: {bg}; color: {fg}; border-radius: 8px; padding: 4px 6px; font-size: 9px; font-weight: bold;")
            self.files_table.setCellWidget(row, 1, conf_label)
            
            # Source
            source_label = QLabel(f.source.value.upper())
            source_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            source_label.setStyleSheet(f"background: {Colors.WARM}; border-radius: 8px; padding: 4px 6px; font-size: 9px;")
            self.files_table.setCellWidget(row, 2, source_label)
            
            # Size
            size_item = QTableWidgetItem(self._format_size(f.size))
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.files_table.setItem(row, 3, size_item)
            
            self.files_table.setRowHeight(row, 60)
    
    def _filter_files(self, filter_text: str):
        self._populate_files_table(filter_text)
    
    def _on_folder_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle folder tree click - filter files to show only that folder"""
        # Extract folder path from item text (remove emoji and count)
        text = item.text(0)
        if text.startswith("📁 "):
            text = text[2:].strip()
        
        # Remove count in parentheses
        if " (" in text:
            text = text[:text.rfind(" (")]
        
        # Check if clicking on root "Organized Files"
        if text == "Organized Files":
            self._clear_folder_filter()
            return
        
        # Build full path by walking up the tree
        path_parts = [text]
        parent = item.parent()
        while parent:
            parent_text = parent.text(0)
            if parent_text.startswith("📁 "):
                parent_text = parent_text[2:].strip()
            if " (" in parent_text:
                parent_text = parent_text[:parent_text.rfind(" (")]
            if parent_text != "Organized Files":
                path_parts.insert(0, parent_text)
            parent = parent.parent()
        
        self.selected_folder = "/".join(path_parts) if path_parts else None
        
        # Update filter indicator
        if self.selected_folder:
            self.folder_filter_label.setText(f"📁 {self.selected_folder}")
            self.folder_filter_label.show()
            self.clear_filter_btn.show()
        
        # Re-filter with current combo selection
        self._populate_files_table(self.filter_combo.currentText())
    
    def _clear_folder_filter(self):
        """Clear the folder filter and show all files"""
        self.selected_folder = None
        self.folder_filter_label.hide()
        self.clear_filter_btn.hide()
        self.folder_tree.clearSelection()
        self._populate_files_table(self.filter_combo.currentText())
    
    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    
    def _create_plan(self, action: str = "copy") -> OrganizationPlan:
        plan = OrganizationPlan()
        plan.created_at = datetime.now().isoformat()
        plan.source_root = self.source_input.text()
        plan.target_root = self.target_input.text() or self.source_input.text() + "_Organized"
        plan.action = action
        
        plan.statistics = {
            'total_files': len(self.files),
            'total_size_bytes': sum(f.size for f in self.files),
            'folders_to_create': len(set(f.destination for f in self.files if f.destination)),
            'duplicates_flagged': sum(1 for f in self.files if f.is_duplicate),
        }
        
        plan.folders = list(set(f.destination for f in self.files if f.destination))
        
        for f in self.files:
            plan.moves.append({
                'source': str(f.path),
                'destination': f.destination + '/' + f.name if f.destination else f.name,
                'filename': f.name,
                'size_bytes': f.size,
                'confidence': f.confidence.value,
                'classification_source': f.source.value,
                'reasoning': f.reasoning,
                'is_duplicate': f.is_duplicate,
                'duplicate_of': f.duplicate_of,
            })
        
        plan.options = {
            'handle_duplicates': 'move_to_duplicates_folder',
            'create_folders': True,
            'on_conflict': 'rename',
        }
        
        return plan
    
    def _show_export_dialog(self):
        if not self.files:
            return
        
        dialog = ExportDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            fmt = dialog.get_format()
            plan = self._create_plan()
            
            extensions = {'csv': 'csv', 'txt': 'txt', 'sh': 'sh', 'fopplan': 'fopplan'}
            filters = {
                'csv': 'CSV Files (*.csv)',
                'txt': 'Text Files (*.txt)',
                'sh': 'Shell Scripts (*.sh)',
                'fopplan': 'FOP Plans (*.fopplan)',
            }
            
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Export Plan",
                f"organization_plan.{extensions[fmt]}",
                filters[fmt]
            )
            
            if filepath:
                if fmt == 'csv':
                    with open(filepath, 'w') as f:
                        f.write(plan.to_csv())
                elif fmt == 'txt':
                    with open(filepath, 'w') as f:
                        f.write(plan.to_summary())
                elif fmt == 'sh':
                    with open(filepath, 'w') as f:
                        f.write(plan.to_shell_script())
                else:
                    plan.save(Path(filepath))
                
                QMessageBox.information(self, "Export Complete", f"Plan saved to:\n{filepath}")
    
    def _show_execute_dialog(self):
        if not self.files:
            return
        
        total_size = sum(f.size for f in self.files)
        dialog = ExecuteDialog(
            self,
            len(self.files),
            total_size,
            self.source_input.text(),
            self.target_input.text()
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            action = dialog.get_action()
            update_lr = dialog.get_update_lightroom()
            
            if action == "export":
                self._show_export_dialog()
            else:
                plan = self._create_plan(action)
                
                if update_lr:
                    # Export .fopplan for LrForge
                    filepath, _ = QFileDialog.getSaveFileName(
                        self, "Save Plan for LrForge",
                        f"fop_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.fopplan",
                        "FOP Plans (*.fopplan)"
                    )
                    if filepath:
                        plan.save(Path(filepath))
                        QMessageBox.information(
                            self, "Plan Saved",
                            f"Plan saved to:\n{filepath}\n\n"
                            "Next steps:\n"
                            "1. Open Lightroom Classic\n"
                            "2. Go to File → Plug-in Extras → LrForge\n"
                            "3. Load this .fopplan file\n"
                            "4. Click Execute to organize with catalog linking"
                        )
                else:
                    # Direct execution
                    QMessageBox.information(
                        self, "Execute",
                        f"Would {action} {len(self.files)} files.\n\n"
                        "(Direct execution coming in next update)"
                    )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FileOrganizerPro")
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("Bart Labs")
    
    window = FileOrganizerPro()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
