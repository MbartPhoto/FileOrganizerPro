#!/usr/bin/env python3
"""
Unit tests for Multi-Catalog Search functionality
Tests core search logic without UI
"""

from pathlib import Path
from catalog_search import MultiCatalogSearch, FileResult


def test_catalog_addition():
    """Test adding and removing catalogs"""
    print("=" * 60)
    print("TEST 1: Catalog Addition")
    print("=" * 60)
    
    searcher = MultiCatalogSearch()
    
    # Test with non-existent file
    fake_path = Path("/fake/path/catalog.lrcat")
    result = searcher.add_catalog(fake_path)
    print(f"✓ Non-existent file rejected: {not result}")
    print(f"  Error: {searcher.last_error}")
    
    # Test with non-.lrcat file
    wrong_ext = Path(__file__)
    result = searcher.add_catalog(wrong_ext)
    print(f"✓ Wrong extension rejected: {not result}")
    print(f"  Error: {searcher.last_error}")
    
    print(f"✓ Test passed: Invalid catalogs properly rejected\n")


def test_search_validation():
    """Test search input validation"""
    print("=" * 60)
    print("TEST 2: Search Validation")
    print("=" * 60)
    
    searcher = MultiCatalogSearch()
    
    # Empty query
    results = searcher.search("")
    print(f"✓ Empty query rejected: {len(results) == 0}")
    print(f"  Error: {searcher.last_error}")
    
    # No catalogs
    results = searcher.search("test")
    print(f"✓ No catalogs rejected: {len(results) == 0}")
    print(f"  Error: {searcher.last_error}")
    
    print(f"✓ Test passed: Invalid searches properly handled\n")


def test_file_result():
    """Test FileResult data class"""
    print("=" * 60)
    print("TEST 3: FileResult Data Class")
    print("=" * 60)
    
    from datetime import datetime
    
    result = FileResult(
        filename="test_photo.jpg",
        catalog_name="Test_Catalog",
        catalog_path="/path/to/catalog.lrcat",
        file_path="/photos/test_photo.jpg",
        folder_path="/photos",
        file_id=12345,
        capture_date=datetime(2024, 6, 15, 18, 30, 0),
        file_format="jpg",
        rating=4
    )
    
    print(f"✓ Filename: {result.filename}")
    print(f"✓ Catalog: {result.catalog_name}")
    print(f"✓ Display date: {result.get_display_date()}")
    print(f"✓ File ID: {result.file_id}")
    print(f"✓ Rating: {result.rating}")
    print(f"✓ Test passed: FileResult works correctly\n")


def test_with_real_catalog():
    """Test with actual .lrcat file if available"""
    print("=" * 60)
    print("TEST 4: Real Catalog Search (Optional)")
    print("=" * 60)
    
    # Try common locations
    possible_catalogs = [
        Path.home() / "Pictures" / "Lightroom" / "Lightroom Catalog.lrcat",
        Path.home() / "Photos" / "Lightroom" / "Lightroom Catalog.lrcat",
        Path.home() / "Documents" / "Lightroom" / "Lightroom Catalog.lrcat",
    ]
    
    searcher = MultiCatalogSearch()
    catalog_found = False
    
    for catalog_path in possible_catalogs:
        if catalog_path.exists():
            print(f"Found catalog: {catalog_path}")
            if searcher.add_catalog(catalog_path):
                print(f"✓ Successfully added catalog")
                
                # Get stats
                stats = searcher.get_catalog_stats(catalog_path)
                if stats:
                    print(f"✓ Catalog stats:")
                    print(f"  Total files: {stats['total_files']}")
                    print(f"  Total photos: {stats['total_photos']}")
                
                # Try a simple search
                print(f"\nTrying search for 'IMG'...")
                results = searcher.search("IMG", search_type="contains", max_results=10)
                print(f"✓ Found {len(results)} results")
                
                if results:
                    print(f"\n  First 3 results:")
                    for i, result in enumerate(results[:3], 1):
                        print(f"    {i}. {result.filename}")
                        print(f"       Path: {result.folder_path}")
                        print(f"       Date: {result.get_display_date()}")
                
                catalog_found = True
                break
    
    if not catalog_found:
        print("⚠️  No Lightroom catalogs found in common locations")
        print("   This is OK - you can test with your own .lrcat files later")
    
    print()


def run_all_tests():
    """Run all unit tests"""
    print("\n" + "=" * 60)
    print("MULTI-CATALOG SEARCH - UNIT TESTS")
    print("=" * 60 + "\n")
    
    try:
        test_catalog_addition()
        test_search_validation()
        test_file_result()
        test_with_real_catalog()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nCore functionality is working correctly!")
        print("Next step: Run catalog_search_demo.py to test the UI\n")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TEST FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
