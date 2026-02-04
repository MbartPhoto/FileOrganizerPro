"""
INTEGRATION GUIDE: Adding Multi-Catalog Search to FileOrganizerPro

This file shows exactly what changes to make to your existing FileOrganizerPro.py
to integrate the new catalog search feature.

=== STEP 1: ADD IMPORTS ===

At the top of FileOrganizerPro.py, add these imports after the existing PyQt6 imports:

    from catalog_search_dialog import CatalogSearchDialog

=== STEP 2: ADD BUTTON TO WELCOME PAGE ===

In the FileOrganizerPro class, find the create_welcome_page() method.
After the "Let's Get Organized" button, add the new "Search Catalogs" button:

    def create_welcome_page(self):
        # ... existing code for welcome page ...
        
        # EXISTING: "Let's Get Organized" button
        organize_btn = QPushButton("Let's Get Organized  →")
        # ... button styling ...
        organize_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        main_content.addWidget(organize_btn)
        
        # === ADD THIS NEW BUTTON ===
        main_content.addSpacing(12)  # Small gap between buttons
        
        search_btn = QPushButton("🔍 Search Catalogs  →")
        search_btn.setStyleSheet(f'''
            QPushButton {{
                background: linear-gradient(135deg, {Colors.CHARCOAL} 0%, {Colors.NAVY} 100%);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 20px 40px;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: linear-gradient(135deg, {Colors.NAVY} 0%, {Colors.CHARCOAL} 100%);
                padding: 22px 42px;
            }}
        ''')
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.clicked.connect(self.open_catalog_search)
        main_content.addWidget(search_btn)
        
        # Add subtitle under button
        search_subtitle = QLabel("Find files across multiple Lightroom catalogs")
        search_subtitle.setStyleSheet(f'''
            QLabel {{
                color: {Colors.SLATE};
                font-size: 13px;
                font-style: italic;
            }}
        ''')
        search_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_content.addWidget(search_subtitle)
        
        # ... rest of welcome page code ...

=== STEP 3: ADD OPEN CATALOG SEARCH METHOD ===

In the FileOrganizerPro class, add this new method:

    def open_catalog_search(self):
        """Open the multi-catalog search dialog"""
        try:
            dialog = CatalogSearchDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Could not open catalog search:\n{e}"
            )

=== STEP 4: UPDATE VERSION NUMBER ===

Find the VERSION constant at the top of FileOrganizerPro.py and update it:

    VERSION = "2.6.5"  # Was 2.6.4

=== THAT'S IT! ===

The integration is minimal:
- 1 import line
- 1 button + subtitle (15 lines)
- 1 method (8 lines)
- 1 version number change

Total changes: ~25 lines of code

=== FILE PLACEMENT ===

Make sure these files are in the same directory as FileOrganizerPro.py:
- catalog_search.py
- catalog_search_dialog.py

=== TESTING ===

1. Run FileOrganizerPro.py
2. Click "Search Catalogs" button on welcome page
3. Add a .lrcat file using "+ Add Catalog..."
4. Enter a search term (e.g., "sunset")
5. Click "Search"
6. Results appear in grid
7. Click a thumbnail card
8. Click "Show in Finder" to open file location

=== DEPENDENCIES ===

No new dependencies needed! Everything uses existing PyQt6 and Python stdlib.

=== PLATFORM COMPATIBILITY ===

- macOS: "Show in Finder" works via `open -R`
- Windows: Works via `explorer /select,`
- Linux: Opens parent folder via `xdg-open`

=== WHAT'S NEXT (PHASE 2) ===

For v2.6.6, add real thumbnails:
- Parse .lrdata/previews.db
- Extract JPEG from .lrprev files
- Display in ThumbnailCard instead of placeholder

For v2.7.0, add Lightroom integration:
- "Open in Lightroom" button
- Use AppleScript (macOS) or COM (Windows)
- Opens catalog and selects photo
"""

print("Integration guide created!")
print("\nTo integrate into FileOrganizerPro:")
print("1. Copy catalog_search.py and catalog_search_dialog.py to FOP directory")
print("2. Follow the 4 steps in fop_catalog_search_integration.py")
print("3. Test by running FileOrganizerPro.py")
