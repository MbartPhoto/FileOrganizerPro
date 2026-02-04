"""
Multi-catalog search functionality for FileOrganizerPro
Searches multiple Lightroom .lrcat files (SQLite databases) simultaneously
READ-ONLY access - never writes to catalogs
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Literal
from dataclasses import dataclass
from datetime import datetime
import re


@dataclass
class FileResult:
    """Search result from Lightroom catalog"""
    filename: str
    catalog_name: str
    catalog_path: str
    file_path: str  # Full path to actual file
    folder_path: str  # Parent folder
    file_id: int
    capture_date: Optional[datetime]
    file_format: Optional[str]
    rating: Optional[int]
    
    def get_display_date(self) -> str:
        """Format date for display"""
        if self.capture_date:
            return self.capture_date.strftime("%Y-%m-%d")
        return "Unknown"


class MultiCatalogSearch:
    """
    Search multiple Lightroom catalog files simultaneously.
    Opens .lrcat files (SQLite databases) in READ-ONLY mode.
    """
    
    def __init__(self):
        self.catalogs: List[Path] = []
        self.last_error: Optional[str] = None
    
    def add_catalog(self, catalog_path: Path) -> bool:
        """
        Add a catalog to the search list.
        
        Args:
            catalog_path: Path to .lrcat file
            
        Returns:
            True if catalog is valid and added, False otherwise
        """
        if not catalog_path.exists():
            self.last_error = f"Catalog not found: {catalog_path}"
            return False
        
        if catalog_path.suffix.lower() != '.lrcat':
            self.last_error = f"Not a Lightroom catalog: {catalog_path}"
            return False
        
        # Test if we can open it
        try:
            conn = sqlite3.connect(f"file:{catalog_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            
            # Verify it has the expected Lightroom tables
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='AgLibraryFile'"
            )
            if not cursor.fetchone():
                self.last_error = f"Invalid Lightroom catalog (missing AgLibraryFile table): {catalog_path}"
                conn.close()
                return False
            
            conn.close()
            
            # Add to list if not already present
            if catalog_path not in self.catalogs:
                self.catalogs.append(catalog_path)
            
            return True
            
        except sqlite3.Error as e:
            self.last_error = f"Cannot open catalog {catalog_path}: {e}"
            return False
    
    def remove_catalog(self, catalog_path: Path) -> bool:
        """Remove a catalog from the search list"""
        if catalog_path in self.catalogs:
            self.catalogs.remove(catalog_path)
            return True
        return False
    
    def clear_catalogs(self):
        """Remove all catalogs from search list"""
        self.catalogs.clear()
    
    def search(
        self,
        query: str,
        search_type: Literal["exact", "contains", "wildcard"] = "contains",
        max_results: int = 500
    ) -> List[FileResult]:
        """
        Search all added catalogs for files matching the query.
        
        Args:
            query: Search string
            search_type: 
                - "exact": Exact filename match
                - "contains": Substring match (case-insensitive)
                - "wildcard": SQL LIKE pattern (% and _ wildcards)
            max_results: Maximum number of results to return
            
        Returns:
            List of FileResult objects
        """
        if not query.strip():
            self.last_error = "Empty search query"
            return []
        
        if not self.catalogs:
            self.last_error = "No catalogs added"
            return []
        
        all_results = []
        
        for catalog_path in self.catalogs:
            try:
                results = self._search_catalog(catalog_path, query, search_type, max_results)
                all_results.extend(results)
                
                # Stop if we hit max results
                if len(all_results) >= max_results:
                    all_results = all_results[:max_results]
                    break
                    
            except Exception as e:
                # Log error but continue with other catalogs
                print(f"Error searching {catalog_path}: {e}")
                continue
        
        return all_results
    
    def _search_catalog(
        self,
        catalog_path: Path,
        query: str,
        search_type: str,
        max_results: int
    ) -> List[FileResult]:
        """Search a single catalog file"""
        results = []
        
        try:
            # Open in READ-ONLY mode
            conn = sqlite3.connect(f"file:{catalog_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            
            # Build SQL query based on search type
            if search_type == "exact":
                sql = """
                    SELECT 
                        alf.idx_filename,
                        alf.id_local,
                        arf.absolutePath || '/' || arf.pathFromRoot as folder_path,
                        ai.captureTime,
                        alf.extension,
                        ai.rating
                    FROM AgLibraryFile alf
                    LEFT JOIN AgLibraryFolder arf ON alf.folder = arf.id_local
                    LEFT JOIN Adobe_images ai ON alf.id_local = ai.rootFile
                    WHERE alf.idx_filename = ?
                    LIMIT ?
                """
                params = (query, max_results)
                
            elif search_type == "wildcard":
                sql = """
                    SELECT 
                        alf.idx_filename,
                        alf.id_local,
                        arf.absolutePath || '/' || arf.pathFromRoot as folder_path,
                        ai.captureTime,
                        alf.extension,
                        ai.rating
                    FROM AgLibraryFile alf
                    LEFT JOIN AgLibraryFolder arf ON alf.folder = arf.id_local
                    LEFT JOIN Adobe_images ai ON alf.id_local = ai.rootFile
                    WHERE alf.idx_filename LIKE ?
                    LIMIT ?
                """
                params = (query, max_results)
                
            else:  # contains (default)
                sql = """
                    SELECT 
                        alf.idx_filename,
                        alf.id_local,
                        arf.absolutePath || '/' || arf.pathFromRoot as folder_path,
                        ai.captureTime,
                        alf.extension,
                        ai.rating
                    FROM AgLibraryFile alf
                    LEFT JOIN AgLibraryFolder arf ON alf.folder = arf.id_local
                    LEFT JOIN Adobe_images ai ON alf.id_local = ai.rootFile
                    WHERE alf.idx_filename LIKE ?
                    LIMIT ?
                """
                params = (f"%{query}%", max_results)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            catalog_name = catalog_path.stem
            
            for row in rows:
                filename, file_id, folder_path, capture_time, extension, rating = row
                
                # Parse capture time if present
                capture_date = None
                if capture_time:
                    try:
                        # Lightroom stores as Unix timestamp
                        capture_date = datetime.fromtimestamp(float(capture_time))
                    except (ValueError, TypeError):
                        pass
                
                # Build full file path
                file_path = str(Path(folder_path) / filename) if folder_path else filename
                
                result = FileResult(
                    filename=filename,
                    catalog_name=catalog_name,
                    catalog_path=str(catalog_path),
                    file_path=file_path,
                    folder_path=folder_path or "",
                    file_id=file_id,
                    capture_date=capture_date,
                    file_format=extension,
                    rating=rating
                )
                results.append(result)
            
            conn.close()
            
        except sqlite3.Error as e:
            raise Exception(f"SQLite error in {catalog_path.name}: {e}")
        
        return results
    
    def get_catalog_stats(self, catalog_path: Path) -> Optional[Dict[str, int]]:
        """
        Get statistics for a catalog (total files, photos, etc.)
        
        Returns:
            Dict with stats or None if error
        """
        try:
            conn = sqlite3.connect(f"file:{catalog_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            
            # Count total files
            cursor.execute("SELECT COUNT(*) FROM AgLibraryFile")
            total_files = cursor.fetchone()[0]
            
            # Count photos (images)
            cursor.execute("""
                SELECT COUNT(*) FROM AgLibraryFile alf
                JOIN Adobe_images ai ON alf.id_local = ai.rootFile
            """)
            total_photos = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_files': total_files,
                'total_photos': total_photos
            }
            
        except sqlite3.Error:
            return None


if __name__ == "__main__":
    # Test the search functionality
    searcher = MultiCatalogSearch()
    
    # Example usage:
    # searcher.add_catalog(Path("~/Photos/Lightroom_2024.lrcat").expanduser())
    # results = searcher.search("sunset", search_type="contains")
    # for result in results:
    #     print(f"{result.filename} - {result.catalog_name} - {result.get_display_date()}")
    
    print("MultiCatalogSearch module loaded successfully")
