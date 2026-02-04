"""
Multi-Catalog Search Dialog UI for FileOrganizerPro
Visual grid-based search across multiple Lightroom catalogs
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QScrollArea, QWidget, QFileDialog, QFrame,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings, QThread
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen

from catalog_search import MultiCatalogSearch, FileResult


class Colors:
    """Bart Labs color palette"""
    ORANGE = "#FF6B35"
    CHARCOAL = "#4a5568"
    NAVY = "#2D3436"
    SLATE = "#64748b"
    CREAM = "#FDF8F3"
    WARM = "#FFFAF5"
    WHITE = "#FFFFFF"
    LIGHT_GRAY = "#F0F0F0"
    HOVER_BG = "#F8F8F8"


class ThumbnailCard(QFrame):
    """
    Widget displaying a single search result with thumbnail placeholder.
    170x170 thumbnail + filename + metadata
    """
    
    clicked = pyqtSignal(object)  # Emits FileResult when clicked
    
    def __init__(self, result: FileResult, parent=None):
        super().__init__(parent)
        self.result = result
        self.is_selected = False
        
        self.setFixedSize(180, 220)
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(0)
        self.setStyleSheet(f"""
            ThumbnailCard {{
                background-color: {Colors.WHITE};
                border: 2px solid transparent;
                border-radius: 8px;
            }}
            ThumbnailCard:hover {{
                background-color: {Colors.HOVER_BG};
                border: 2px solid {Colors.ORANGE};
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)
        
        # Thumbnail placeholder (170x170)
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(170, 170)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setStyleSheet(f"""
            QLabel {{
                background-color: {Colors.LIGHT_GRAY};
                border-radius: 6px;
                color: {Colors.SLATE};
                font-size: 48px;
            }}
        """)
        self.thumbnail_label.setText("📷")
        layout.addWidget(self.thumbnail_label)
        
        # Filename (truncate if too long)
        filename = result.filename
        if len(filename) > 20:
            filename = filename[:17] + "..."
        
        filename_label = QLabel(filename)
        filename_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.NAVY};
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(filename_label)
        
        # Catalog name
        catalog_label = QLabel(f"📁 {result.catalog_name}")
        catalog_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.SLATE};
                font-size: 10px;
            }}
        """)
        catalog_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(catalog_label)
        
        # Date
        date_label = QLabel(result.get_display_date())
        date_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.SLATE};
                font-size: 10px;
            }}
        """)
        date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(date_label)
        
        self.setLayout(layout)
    
    def mousePressEvent(self, event):
        """Emit clicked signal when card is clicked"""
        self.clicked.emit(self.result)
        super().mousePressEvent(event)
    
    def set_selected(self, selected: bool):
        """Update visual state when selected"""
        self.is_selected = selected
        if selected:
            self.setStyleSheet(f"""
                ThumbnailCard {{
                    background-color: {Colors.HOVER_BG};
                    border: 2px solid {Colors.ORANGE};
                    border-radius: 8px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                ThumbnailCard {{
                    background-color: {Colors.WHITE};
                    border: 2px solid transparent;
                    border-radius: 8px;
                }}
                ThumbnailCard:hover {{
                    background-color: {Colors.HOVER_BG};
                    border: 2px solid {Colors.ORANGE};
                }}
            """)


class SearchWorker(QThread):
    """Background thread for catalog search"""
    results_ready = pyqtSignal(list)
    search_error = pyqtSignal(str)
    
    def __init__(self, searcher: MultiCatalogSearch, query: str, search_type: str):
        super().__init__()
        self.searcher = searcher
        self.query = query
        self.search_type = search_type
    
    def run(self):
        try:
            results = self.searcher.search(self.query, self.search_type)
            self.results_ready.emit(results)
        except Exception as e:
            self.search_error.emit(str(e))


class CatalogSearchDialog(QDialog):
    """
    Main dialog for multi-catalog search.
    Grid view with thumbnail cards, catalog management, and actions.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.searcher = MultiCatalogSearch()
        self.current_results: List[FileResult] = []
        self.selected_result: Optional[FileResult] = None
        self.thumbnail_cards: List[ThumbnailCard] = []
        self.search_worker: Optional[SearchWorker] = None
        
        self.setWindowTitle("🔍 Search Multiple Catalogs")
        self.setMinimumSize(900, 700)
        self.resize(1100, 800)
        
        self.setup_ui()
        self.load_catalogs()
    
    def setup_ui(self):
        """Build the UI layout"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(16)
        
        # === HEADER ===
        header_layout = QHBoxLayout()
        
        title_label = QLabel("🔍 Search Multiple Catalogs")
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 18px;
                font-weight: bold;
                color: {Colors.NAVY};
            }}
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # === CATALOGS SECTION ===
        catalogs_frame = QFrame()
        catalogs_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.WARM};
                border: 1px solid {Colors.LIGHT_GRAY};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        catalogs_layout = QVBoxLayout()
        
        catalogs_header = QLabel("📚 CATALOGS")
        catalogs_header.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                font-weight: bold;
                color: {Colors.SLATE};
            }}
        """)
        catalogs_layout.addWidget(catalogs_header)
        
        # Catalog list area
        self.catalog_list_widget = QWidget()
        self.catalog_list_layout = QVBoxLayout()
        self.catalog_list_layout.setSpacing(4)
        self.catalog_list_widget.setLayout(self.catalog_list_layout)
        
        catalogs_scroll = QScrollArea()
        catalogs_scroll.setWidget(self.catalog_list_widget)
        catalogs_scroll.setWidgetResizable(True)
        catalogs_scroll.setMaximumHeight(120)
        catalogs_scroll.setStyleSheet("QScrollArea { border: none; }")
        catalogs_layout.addWidget(catalogs_scroll)
        
        # Add catalog button
        add_catalog_btn = QPushButton("+ Add Catalog...")
        add_catalog_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ORANGE};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #E85A2A;
            }}
        """)
        add_catalog_btn.clicked.connect(self.add_catalog)
        catalogs_layout.addWidget(add_catalog_btn)
        
        catalogs_frame.setLayout(catalogs_layout)
        main_layout.addWidget(catalogs_frame)
        
        # === SEARCH BAR ===
        search_layout = QHBoxLayout()
        
        search_label = QLabel("Search:")
        search_label.setStyleSheet(f"color: {Colors.CHARCOAL}; font-weight: bold;")
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter filename or pattern...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px;
                border: 2px solid {Colors.LIGHT_GRAY};
                border-radius: 6px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 2px solid {Colors.ORANGE};
            }}
        """)
        self.search_input.returnPressed.connect(self.perform_search)
        search_layout.addWidget(self.search_input, stretch=1)
        
        search_btn = QPushButton("🔍 Search")
        search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ORANGE};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #E85A2A;
            }}
        """)
        search_btn.clicked.connect(self.perform_search)
        search_layout.addWidget(search_btn)
        
        search_layout.addWidget(QLabel("Type:"))
        
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(["Contains", "Exact", "Wildcard"])
        self.search_type_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 6px;
                border: 2px solid {Colors.LIGHT_GRAY};
                border-radius: 6px;
            }}
        """)
        search_layout.addWidget(self.search_type_combo)
        
        main_layout.addLayout(search_layout)
        
        # === RESULTS SECTION ===
        results_frame = QFrame()
        results_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.WHITE};
                border: 1px solid {Colors.LIGHT_GRAY};
                border-radius: 8px;
            }}
        """)
        results_layout = QVBoxLayout()
        results_layout.setContentsMargins(12, 12, 12, 12)
        
        self.results_header = QLabel("RESULTS (0 found)")
        self.results_header.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                font-weight: bold;
                color: {Colors.SLATE};
            }}
        """)
        results_layout.addWidget(self.results_header)
        
        # Scrollable grid area
        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.results_container = QWidget()
        self.results_grid = QGridLayout()
        self.results_grid.setSpacing(10)
        self.results_container.setLayout(self.results_grid)
        self.results_scroll.setWidget(self.results_container)
        
        results_layout.addWidget(self.results_scroll)
        results_frame.setLayout(results_layout)
        main_layout.addWidget(results_frame, stretch=1)
        
        # === SELECTED FILE INFO ===
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.WARM};
                border: 1px solid {Colors.LIGHT_GRAY};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        info_layout = QVBoxLayout()
        
        info_header = QLabel("SELECTED FILE")
        info_header.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                font-weight: bold;
                color: {Colors.SLATE};
                margin-bottom: 4px;
            }}
        """)
        info_layout.addWidget(info_header)
        
        self.info_filename = QLabel("Filename: (none selected)")
        self.info_catalog = QLabel("Catalog: —")
        self.info_path = QLabel("Path: —")
        self.info_date = QLabel("Date: —")
        
        for label in [self.info_filename, self.info_catalog, self.info_path, self.info_date]:
            label.setStyleSheet(f"color: {Colors.CHARCOAL}; font-size: 12px;")
            label.setWordWrap(True)
            info_layout.addWidget(label)
        
        info_frame.setLayout(info_layout)
        main_layout.addWidget(info_frame)
        
        # === ACTION BUTTONS ===
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        self.finder_btn = QPushButton("📂 Show in Finder")
        self.finder_btn.setEnabled(False)
        self.finder_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.CHARCOAL};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover:enabled {{
                background-color: {Colors.NAVY};
            }}
            QPushButton:disabled {{
                background-color: {Colors.LIGHT_GRAY};
                color: {Colors.SLATE};
            }}
        """)
        self.finder_btn.clicked.connect(self.show_in_finder)
        actions_layout.addWidget(self.finder_btn)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.LIGHT_GRAY};
                color: {Colors.CHARCOAL};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #E0E0E0;
            }}
        """)
        close_btn.clicked.connect(self.accept)
        actions_layout.addWidget(close_btn)
        
        main_layout.addLayout(actions_layout)
        
        self.setLayout(main_layout)
    
    def add_catalog(self):
        """Open file picker to add a .lrcat file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Lightroom Catalog",
            str(Path.home()),
            "Lightroom Catalogs (*.lrcat)"
        )
        
        if file_path:
            catalog_path = Path(file_path)
            if self.searcher.add_catalog(catalog_path):
                self.add_catalog_to_ui(catalog_path)
                self.save_catalogs()
            else:
                QMessageBox.warning(
                    self,
                    "Invalid Catalog",
                    f"Could not add catalog:\n{self.searcher.last_error}"
                )
    
    def add_catalog_to_ui(self, catalog_path: Path):
        """Add catalog entry to UI list"""
        catalog_widget = QWidget()
        catalog_layout = QHBoxLayout()
        catalog_layout.setContentsMargins(4, 4, 4, 4)
        
        # Checkbox (always checked for now)
        label = QLabel(f"✓ {catalog_path.name}")
        label.setStyleSheet(f"color: {Colors.CHARCOAL}; font-size: 12px;")
        catalog_layout.addWidget(label, stretch=1)
        
        # Remove button
        remove_btn = QPushButton("Remove")
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.ORANGE};
                border: 1px solid {Colors.ORANGE};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {Colors.ORANGE};
                color: white;
            }}
        """)
        remove_btn.clicked.connect(lambda: self.remove_catalog(catalog_path, catalog_widget))
        catalog_layout.addWidget(remove_btn)
        
        catalog_widget.setLayout(catalog_layout)
        self.catalog_list_layout.addWidget(catalog_widget)
    
    def remove_catalog(self, catalog_path: Path, widget: QWidget):
        """Remove catalog from search list and UI"""
        self.searcher.remove_catalog(catalog_path)
        self.catalog_list_layout.removeWidget(widget)
        widget.deleteLater()
        self.save_catalogs()
    
    def perform_search(self):
        """Execute search across all catalogs"""
        query = self.search_input.text().strip()
        
        if not query:
            QMessageBox.information(self, "Empty Query", "Please enter a search term.")
            return
        
        if not self.searcher.catalogs:
            QMessageBox.information(self, "No Catalogs", "Please add at least one catalog to search.")
            return
        
        # Clear previous results
        self.clear_results()
        
        # Map combo box to search type
        search_type_map = {
            "Contains": "contains",
            "Exact": "exact",
            "Wildcard": "wildcard"
        }
        search_type = search_type_map[self.search_type_combo.currentText()]
        
        # Perform search in background thread
        self.search_worker = SearchWorker(self.searcher, query, search_type)
        self.search_worker.results_ready.connect(self.display_results)
        self.search_worker.search_error.connect(self.show_search_error)
        self.search_worker.start()
        
        # Show searching message
        self.results_header.setText(f"RESULTS (Searching...)")
    
    def display_results(self, results: List[FileResult]):
        """Display search results in grid"""
        self.current_results = results
        self.results_header.setText(f"RESULTS ({len(results)} found)")
        
        if not results:
            no_results_label = QLabel("No files found matching your search.")
            no_results_label.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.SLATE};
                    font-size: 14px;
                    padding: 40px;
                }}
            """)
            no_results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_grid.addWidget(no_results_label, 0, 0)
            return
        
        # Add thumbnail cards to grid (4 per row)
        row = 0
        col = 0
        for result in results:
            card = ThumbnailCard(result)
            card.clicked.connect(self.select_result)
            self.thumbnail_cards.append(card)
            
            self.results_grid.addWidget(card, row, col)
            
            col += 1
            if col >= 4:
                col = 0
                row += 1
    
    def clear_results(self):
        """Clear all result cards from grid"""
        for card in self.thumbnail_cards:
            self.results_grid.removeWidget(card)
            card.deleteLater()
        
        self.thumbnail_cards.clear()
        self.selected_result = None
        self.update_info_panel()
    
    def select_result(self, result: FileResult):
        """Handle result card selection"""
        # Deselect all cards
        for card in self.thumbnail_cards:
            card.set_selected(False)
        
        # Select clicked card
        for card in self.thumbnail_cards:
            if card.result == result:
                card.set_selected(True)
                break
        
        self.selected_result = result
        self.update_info_panel()
    
    def update_info_panel(self):
        """Update the selected file info panel"""
        if not self.selected_result:
            self.info_filename.setText("Filename: (none selected)")
            self.info_catalog.setText("Catalog: —")
            self.info_path.setText("Path: —")
            self.info_date.setText("Date: —")
            self.finder_btn.setEnabled(False)
        else:
            r = self.selected_result
            self.info_filename.setText(f"Filename: {r.filename}")
            self.info_catalog.setText(f"Catalog: {r.catalog_name}")
            self.info_path.setText(f"Path: {r.folder_path}")
            self.info_date.setText(f"Date: {r.get_display_date()}")
            self.finder_btn.setEnabled(True)
    
    def show_in_finder(self):
        """Open Finder/Explorer to the selected file's location"""
        if not self.selected_result:
            return
        
        file_path = Path(self.selected_result.file_path)
        
        if not file_path.exists():
            QMessageBox.warning(
                self,
                "File Not Found",
                f"The file no longer exists at:\n{file_path}"
            )
            return
        
        # Platform-specific file reveal
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", "-R", str(file_path)])
            elif sys.platform == "win32":  # Windows
                subprocess.run(["explorer", "/select,", str(file_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(file_path.parent)])
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Could not open file location:\n{e}"
            )
    
    def show_search_error(self, error_msg: str):
        """Display search error message"""
        QMessageBox.critical(self, "Search Error", f"Search failed:\n{error_msg}")
        self.results_header.setText("RESULTS (Error)")
    
    def save_catalogs(self):
        """Save catalog list to user preferences"""
        settings = QSettings("BartLabs", "FileOrganizerPro")
        catalog_paths = [str(p) for p in self.searcher.catalogs]
        settings.setValue("catalog_search/catalogs", catalog_paths)
    
    def load_catalogs(self):
        """Load saved catalogs from preferences"""
        settings = QSettings("BartLabs", "FileOrganizerPro")
        catalog_paths = settings.value("catalog_search/catalogs", [])
        
        if isinstance(catalog_paths, str):
            catalog_paths = [catalog_paths]
        
        for path_str in catalog_paths:
            catalog_path = Path(path_str)
            if catalog_path.exists():
                if self.searcher.add_catalog(catalog_path):
                    self.add_catalog_to_ui(catalog_path)
