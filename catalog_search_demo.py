#!/usr/bin/env python3
"""
Standalone demo of Multi-Catalog Search feature for FileOrganizerPro
Run this to test the catalog search without the full FOP app

Usage:
    python catalog_search_demo.py
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from catalog_search_dialog import CatalogSearchDialog, Colors


class DemoWindow(QMainWindow):
    """Simple window to launch the catalog search dialog"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Catalog Search Demo - FileOrganizerPro v2.6.5")
        self.setMinimumSize(500, 300)
        
        # Center widget
        central = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("🔍 Multi-Catalog Search")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {Colors.NAVY};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Search across multiple Lightroom catalogs")
        subtitle.setFont(QFont("Arial", 14))
        subtitle.setStyleSheet(f"color: {Colors.SLATE};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Launch button
        launch_btn = QPushButton("🚀 Launch Search")
        launch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ORANGE};
                color: white;
                border: none;
                border-radius: 12px;
                padding: 16px 32px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #E85A2A;
            }}
        """)
        launch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        launch_btn.clicked.connect(self.open_search)
        layout.addWidget(launch_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Instructions
        instructions = QLabel(
            "Click the button to open the catalog search dialog.\n"
            "Add .lrcat files and search for photos across all catalogs!"
        )
        instructions.setFont(QFont("Arial", 11))
        instructions.setStyleSheet(f"color: {Colors.CHARCOAL}; padding: 20px;")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        central.setLayout(layout)
        self.setCentralWidget(central)
        
        # Styling
        self.setStyleSheet(f"background-color: {Colors.CREAM};")
    
    def open_search(self):
        """Open the catalog search dialog"""
        dialog = CatalogSearchDialog(self)
        dialog.exec()


def main():
    """Run the demo application"""
    app = QApplication(sys.argv)
    app.setApplicationName("FileOrganizerPro - Catalog Search Demo")
    app.setOrganizationName("BartLabs")
    
    window = DemoWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    print("=" * 60)
    print("FileOrganizerPro - Multi-Catalog Search Demo")
    print("=" * 60)
    print("\nThis demo lets you test the catalog search feature.")
    print("\nTo use:")
    print("1. Click 'Launch Search'")
    print("2. Add one or more .lrcat files")
    print("3. Enter a search term (e.g., 'sunset', '*.jpg')")
    print("4. Select search type (Contains, Exact, or Wildcard)")
    print("5. Click Search")
    print("6. Click thumbnails to select files")
    print("7. Use 'Show in Finder' to open file location")
    print("\n" + "=" * 60 + "\n")
    
    main()
