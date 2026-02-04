# FileOrganizerPro + LrForge — Complete Developer Handoff
## For Claude Code Takeover
### February 3, 2026

---

# ⚡ QUICK START — READ THIS FIRST

You are taking over development of the **Bart Labs Photographer Toolkit**: two interconnected products that together solve photo organization for professional photographers.

**The 30-second pitch:** Photographers have 50,000–100,000+ RAW files scattered across drives. FOP scans and classifies them using rules, keywords, and local AI. It produces an organization plan. The photographer can either execute that plan directly (copy/move files) or export a `.fopplan` file that LrForge imports inside Lightroom Classic to move files while preserving all catalog links, edits, collections, and keywords.

**What exists today:**
- `FileOrganizerPro.py` — v2.6.4, 2,390 lines, PyQt6. UI complete. Scanning works. Classification works (rules/keywords only). AI classification and file execution are NOT wired up.
- `catalog_search.py` + `catalog_search_dialog.py` — Multi-Catalog Search feature, ~1,000 lines, tested, ready to integrate as v2.6.5.
- LrForge — 627-line specification document only. Zero code.
- `fop_mockup.html` — Reference HTML mockup showing neumorphic design.

**User's environment:**
- macOS M1 Max MacBook Pro, Python 3.10+, PyQt6 installed
- LM Studio on Windows server at `http://192.168.1.93:1234` (Qwen3-VL-8B model)
- Windows Firewall rule already added for port 1234
- Test dataset: 1,346 files / 19.7 GB, mixed RAW/JPEG/documents/code

**User's preferences:**
- Lowercase filenames with underscores
- Concise responses, working code over explanations
- Rapid iteration with immediate testing
- Screenshots for UI feedback
- Requests daily logs and status reports

---

# TABLE OF CONTENTS

1. [Product Architecture — The Big Picture](#1-product-architecture--the-big-picture)
2. [The Holistic Workflow — How Everything Connects](#2-the-holistic-workflow--how-everything-connects)
3. [FileOrganizerPro — Complete Technical Reference](#3-fileorganizerpro--complete-technical-reference)
4. [Multi-Catalog Search — New Feature (Ready to Ship)](#4-multi-catalog-search--new-feature-ready-to-ship)
5. [LrForge — Lightroom Plugin Specification](#5-lrforge--lightroom-plugin-specification)
6. [The .fopplan Contract — Shared Data Format](#6-the-fopplan-contract--shared-data-format)
7. [LLM Integration — Implementation Guide](#7-llm-integration--implementation-guide)
8. [File Execution — Implementation Guide](#8-file-execution--implementation-guide)
9. [Classification Pipeline — Full Logic](#9-classification-pipeline--full-logic)
10. [Color System & Design Language](#10-color-system--design-language)
11. [Known Issues, Bugs, and Debt](#11-known-issues-bugs-and-debt)
12. [File Inventory](#12-file-inventory)
13. [Build & Test Instructions](#13-build--test-instructions)
14. [Decision Log](#14-decision-log)
15. [Prioritized Task List](#15-prioritized-task-list)

---

# 1. PRODUCT ARCHITECTURE — THE BIG PICTURE

## The Bart Labs Ecosystem

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        BART LABS PHOTOGRAPHER TOOLKIT                   │
│                                                                         │
│   ┌───────────────────────────────┐    ┌──────────────────────────────┐ │
│   │     FileOrganizerPro (FOP)    │    │     LrForge (LrC Plugin)    │ │
│   │                               │    │                              │ │
│   │  • Scans files                │    │  • Runs inside Lightroom     │ │
│   │  • Reads metadata (READ-ONLY) │    │  • Imports .fopplan files    │ │
│   │  • AI classification (LLM)    │    │  • Moves files via LR SDK    │ │
│   │  • Rule/keyword classification│    │  • Preserves ALL catalog data│ │
│   │  • Duplicate detection        │    │  • Preserves ALL edits       │ │
│   │  • Suggests folder structure  │    │  • Preserves ALL collections │ │
│   │  • Exports .fopplan           │    │  • Preserves ALL keywords    │ │
│   │  • Direct copy/move (non-LrC) │    │                              │ │
│   │  • Multi-catalog search       │    │  Future: AI keywording       │ │
│   │                               │    │                              │ │
│   │  Python/PyQt6 desktop app     │    │  Lua plugin (.lrplugin)      │ │
│   └──────────────┬────────────────┘    └──────────────┬───────────────┘ │
│                  │                                    │                  │
│                  │         .fopplan (JSON)             │                  │
│                  └────────────────────────────────────┘                  │
│                                                                         │
│   Planned pricing: FOP standalone $19 / LrForge standalone $29          │
│                    Bundle $39                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| FOP Language | Python 3.10+ | Single-file architecture (for now) |
| FOP GUI | PyQt6 | Neumorphic "maximalist 2026" design |
| Metadata | exiftool (subprocess) | READ-ONLY, never writes |
| LLM | LM Studio (OpenAI-compatible API) | Local, privacy-first |
| LLM Model | Qwen3-VL-8B | Vision-language model |
| Image AI | CLIP (planned, not implemented) | Content classification |
| Catalog Search | SQLite (READ-ONLY) | Queries .lrcat files directly |
| LrForge Language | Lua | Required by Lightroom SDK |
| LrForge JSON | dkjson library | Pure Lua, MIT license |
| Data Exchange | .fopplan (JSON) | Contract between FOP and LrForge |

---

# 2. THE HOLISTIC WORKFLOW — HOW EVERYTHING CONNECTS

This section is the most critical. It explains the end-to-end user journey and how every piece fits together.

## User Journey — Photographer with 50,000 Photos

### Phase 1: Organization Planning (FOP)

```
PHOTOGRAPHER                          FileOrganizerPro
     │                                       │
     │  1. Launches FOP                      │
     │─────────────────────────────────────>│
     │                                       │  Shows Welcome page
     │                                       │  (Bart Labs branding, feature cards)
     │                                       │
     │  2. Clicks "Let's Get Organized"      │
     │─────────────────────────────────────>│
     │                                       │  Shows Setup page
     │                                       │
     │  3. Selects source folder             │
     │     (e.g., ~/Photos/Unsorted)         │
     │─────────────────────────────────────>│
     │                                       │
     │  4. Selects organization preset       │
     │     (e.g., "Photographer")            │
     │─────────────────────────────────────>│
     │                                       │  Loads preset prompt:
     │                                       │  Wildlife → Photos/Wildlife/[Species]/YYYY
     │                                       │  Weddings → Photos/Weddings/YYYY-MM
     │                                       │  etc.
     │                                       │
     │  5. Selects keyword trust level       │
     │     (Trust / Verify / Ignore)         │
     │─────────────────────────────────────>│
     │                                       │
     │  6. Clicks "Analyze Files"            │
     │─────────────────────────────────────>│
     │                                       │
     │                              ┌────────┴────────┐
     │                              │  SCAN PHASE     │
     │                              │                 │
     │                              │  • Walk dirs    │
     │                              │  • Read metadata│
     │                              │    (exiftool)   │
     │                              │  • Calc hashes  │
     │                              │  • ~0.4 sec for │
     │                              │    1,346 files  │
     │                              └────────┬────────┘
     │                                       │
     │                              ┌────────┴────────┐
     │                              │ CLASSIFY PHASE  │
     │                              │                 │
     │                              │ Priority order: │
     │                              │ 1. Duplicates   │
     │                              │    (hash match) │
     │                              │ 2. Keywords     │
     │                              │    (if trusted) │
     │                              │ 3. Rules        │
     │                              │    (50+ patterns│
     │                              │ 4. LLM/AI       │
     │                              │    (TODO!)      │
     │                              │ 5. Unsorted     │
     │                              │    (fallback)   │
     │                              └────────┬────────┘
     │                                       │
     │  7. Views Results page                │
     │<─────────────────────────────────────│
     │                                       │
     │  Sees: folder tree, file table,       │
     │  confidence badges, source badges,    │
     │  metrics (total files, size, dupes)   │
     │                                       │
```

### Phase 2A: Direct Execution (Non-Lightroom Users)

```
     │  8a. Clicks "Execute Organization"    │
     │─────────────────────────────────────>│
     │                                       │  Shows ExecuteDialog:
     │                                       │  • Choose: Copy or Move
     │                                       │  • Select target folder
     │                                       │  • Confirm file count
     │                                       │
     │  9a. Confirms execution               │
     │─────────────────────────────────────>│
     │                                       │  TODO: Actually copy/move files
     │                                       │  Currently shows "coming soon"
     │                                       │
     │  10a. Files organized on disk         │
     │<─────────────────────────────────────│
     │                                       │
     │  DONE (no Lightroom involved)         │
```

### Phase 2B: LrForge Execution (Lightroom Users — THE CRITICAL PATH)

```
     │  8b. Clicks "Export Plan"              │
     │─────────────────────────────────────>│
     │                                       │  Shows ExportDialog:
     │                                       │  • .fopplan (for LrForge) ← RECOMMENDED
     │                                       │  • CSV (spreadsheet)
     │                                       │  • TXT (human-readable)
     │                                       │  • Shell Script (bash)
     │                                       │
     │  9b. Exports .fopplan file            │
     │─────────────────────────────────────>│
     │                                       │  Writes JSON file containing:
     │                                       │  • Every file's source path
     │                                       │  • Every file's destination
     │                                       │  • Confidence levels
     │                                       │  • Classification reasoning
     │                                       │  • Duplicate info
     │                                       │  • Folder structure to create
     │                                       │
```

```
PHOTOGRAPHER                           LrForge (inside Lightroom)
     │                                       │
     │  10b. Opens Lightroom Classic         │
     │─────────────────────────────────────>│
     │                                       │
     │  11b. File → Plug-in Extras →        │
     │        LrForge → Import Plan          │
     │─────────────────────────────────────>│
     │                                       │  Reads .fopplan JSON
     │                                       │  Validates version/schema
     │                                       │  Checks: are source files in catalog?
     │                                       │
     │  12b. Reviews plan in LrForge UI      │
     │<─────────────────────────────────────│
     │                                       │  Shows:
     │                                       │  • File count, total size
     │                                       │  • Folder structure preview
     │                                       │  • Confidence breakdown
     │                                       │  • Files not found in catalog
     │                                       │  • Checkbox: create backup?
     │                                       │
     │  13b. Clicks "Execute" in LrForge     │
     │─────────────────────────────────────>│
     │                                       │
     │                              ┌────────┴────────┐
     │                              │ MOVE PHASE      │
     │                              │                 │
     │                              │ For each file:  │
     │                              │ 1. Find photo   │
     │                              │    in catalog   │
     │                              │    (findPhoto   │
     │                              │     ByPath)     │
     │                              │ 2. Create dest  │
     │                              │    folder if    │
     │                              │    needed       │
     │                              │ 3. Move via     │
     │                              │    photo:move   │
     │                              │    ToFolder()   │
     │                              │ 4. Catalog link │
     │                              │    PRESERVED    │
     │                              │ 5. All edits    │
     │                              │    PRESERVED    │
     │                              │ 6. All keywords │
     │                              │    PRESERVED    │
     │                              │ 7. Collections  │
     │                              │    PRESERVED    │
     │                              └────────┬────────┘
     │                                       │
     │  14b. Sees results summary            │
     │<─────────────────────────────────────│
     │                                       │  Shows: X moved, Y failed, Z skipped
     │                                       │  Generates undo manifest
     │                                       │
     │  DONE — All photos organized,         │
     │  catalog intact, edits preserved      │
```

## WHY This Architecture Matters

The single most important thing to understand:

**Moving files outside Lightroom breaks catalog links.** If you `mv IMG_001.CR3 ~/Organized/Wildlife/`, Lightroom shows a "?" icon and the photographer loses access to all their edits, ratings, keywords, and collections for that file until they manually re-link it — one file at a time.

For a photographer with 50,000 files, re-linking is not an option. That's why LrForge exists: it uses Lightroom's own SDK method `photo:moveToFolder()` which moves the file on disk AND updates the catalog reference in one atomic operation.

**FOP handles the brain (classification). LrForge handles the hands (execution inside LrC).**

## The Keyword Trust System

Photographers often have existing keywords on their photos (from tools like AnyVision, manual tagging, or import presets). FOP gives them three trust levels:

| Trust Level | Behavior | Use Case | Speed |
|-------------|----------|----------|-------|
| **TRUST** | Use existing keywords as-is for classification | "I've meticulously tagged everything" | ⚡ Fastest |
| **VERIFY** | Read keywords, cross-check with AI, flag conflicts | "My keywords are okay but not perfect" | ⚡ Fast |
| **IGNORE** | Disregard all existing keywords, AI-only classification | "My keywords are garbage, start fresh" | Standard |

This is set on the Setup page via radio buttons.

---

# 3. FILEORGANIZERPRO — COMPLETE TECHNICAL REFERENCE

## Code Architecture

Single file: `FileOrganizerPro.py` (v2.6.4, 2,390 lines)

```
Lines 1-60:       Imports and constants
                   - VERSION = "2.6.4"
                   - Python stdlib + PyQt6 imports

Lines 61-82:      Colors class
                   - Full color palette (see Section 10)
                   - Brand colors, pastels, semantic colors

Lines 83-170:     PROMPT_PRESETS dict
                   - 5 presets: General, Photographer, Developer, Work/Personal, Custom
                   - Each has: name, icon, preview text, full prompt

Lines 171-220:    Enums
                   - TrustLevel: TRUST, VERIFY, IGNORE
                   - ClassificationSource: RULE, KEYWORD, AI, VISION, CLIP, HASH
                   - Confidence: HIGH, MEDIUM, LOW

Lines 221-320:    DataClasses
                   - FileInfo: All file metadata + classification result
                   - OrganizationPlan: Complete plan with export methods

Lines 321-450:    MetadataReader class
                   - exiftool subprocess wrapper
                   - PHOTO_EXTENSIONS, RAW_EXTENSIONS sets
                   - read_metadata() → dict with keywords, description, GPS

Lines 451-550:    FileScanner (QThread)
                   - Recursive directory walk
                   - Progress signals (current, total, filename)
                   - Hash calculation (first+last 8KB chunks + size)

Lines 551-630:    FileClassifier (QThread)
                   - Classification pipeline (see Section 9)
                   - Duplicate detection
                   - Rule matching, keyword mapping
                   - TODO: LLM classification placeholder

Lines 631-880:    PreferencesDialog (QDialog)
                   - LLM URL input
                   - Connection test (socket + HTTP)
                   - Performance settings (threads, batch size, max files)
                   - Feature toggles (subfolders, duplicates, vision)
                   - Logging settings
                   - NOTE: Was rebuilt 3 times, v2.6.4 layout needs verification

Lines 881-1000:   ExecuteDialog (QDialog)
                   - Copy vs Move radio buttons
                   - Target folder selection
                   - TODO: Actual execution not implemented

Lines 1001-1100:  ExportDialog (QDialog)
                   - 4 format options: CSV, TXT, Shell Script, .fopplan
                   - File save dialog
                   - All 4 export methods work

Lines 1101-2390:  FileOrganizerPro (QMainWindow)
                   - QStackedWidget with 3 pages
                   - create_welcome_page() — branding, feature cards, CTA
                   - create_setup_page() — folders, presets, options
                   - create_results_page() — metrics, tree, table, actions
                   - Signal/slot wiring
                   - Folder tree click filtering
```

## Key DataClasses

### FileInfo

```python
@dataclass
class FileInfo:
    path: Path                    # Absolute path to file
    name: str                     # Filename only (e.g., "IMG_001.CR3")
    size: int                     # Size in bytes
    extension: str                # Lowercase with dot (e.g., ".cr3")
    modified: datetime            # Last modified timestamp
    destination: str = ""         # Suggested relative path (e.g., "Photos/Wildlife/Eagle/2025")
    confidence: Confidence = Confidence.MEDIUM
    source: ClassificationSource = ClassificationSource.RULE
    reasoning: str = ""           # Human-readable (e.g., "From keywords: eagle, bird")
    keywords: List[str] = field(default_factory=list)  # From IPTC/XMP
    description: str = ""         # From IPTC description
    gps: Optional[Tuple[float, float]] = None
    file_hash: str = ""           # For duplicate detection
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None  # Path to original
    is_photo: bool = False        # True if extension in PHOTO_EXTENSIONS
    thumbnail_path: Optional[Path] = None  # Not implemented
```

### OrganizationPlan

```python
@dataclass
class OrganizationPlan:
    fopplan_version: str = "1.0"
    created_by: str = "FileOrganizerPro"
    created_at: str = ""                # ISO 8601 timestamp
    fop_version: str = VERSION
    source_root: str = ""               # Absolute path
    target_root: str = ""               # Absolute path
    action: str = "copy"                # "copy" or "move"
    statistics: Dict[str, Any]          # {total_files, total_size_bytes, ...}
    folders: List[str]                  # Relative folder paths to create
    moves: List[Dict[str, Any]]         # Individual file operations
    options: Dict[str, Any]             # Settings used for this plan

    def to_json(self) -> str            # .fopplan format (for LrForge)
    def to_csv(self) -> str             # Spreadsheet format
    def to_summary(self) -> str         # Human-readable TXT
    def to_shell_script(self) -> str    # Executable bash script
    def save(self, filepath: Path)      # Write to disk
```

## UI Pages — Detailed Layout

### Page 0: Welcome

Layout: Left side has hero text + CTA button. Right side has 4 feature cards.

Feature cards:
1. 🤖 **AI Powered** — "Local LLM + CLIP"
2. 📸 **Photo Mode** — "RAW + Vision"
3. 🔗 **LrForge Ready** — "LrC integration"
4. 🔒 **100% Private** — "Nothing uploaded"

Top bar: Bart Labs logo (left), Settings gear (right), version number.

CTA: Orange button "Let's Get Organized →"

Footer: "FileOrganizerPro v2.6.4 — Built with ♥ by Bart Labs"

### Page 1: Setup

Three sections with colored left borders:

**FOLDERS** (orange border):
- Source folder: text input + Browse button
- Target folder: text input + Browse button

**ORGANIZATION GUIDANCE** (purple border):
- 5 preset buttons: General, Photographer, Developer, Work/Personal, Custom
- Clicking preset loads prompt into editable text area below
- Keyword trust level: 3 radio buttons (Trust ⚡ FASTEST / Verify ⚡ FAST / Ignore — Standard)

**OPTIONS** (teal border):
- Checkboxes: Include subfolders ✓, Detect duplicates ✓, Photo Mode ✓, Vision AI ☐

Bottom: Orange button "📸 Analyze Files →"

### Page 2: Results

Header: Back arrow, "Organization Preview", file count + total size

5 metric cards (pastel backgrounds):
- Total Files (blue), Total Size (green), Folders (purple), Duplicates (orange), Time (red)

Two-panel layout:
- Left (320px): Folder tree. Clicking a folder filters the file table.
- Right (remaining): File table with columns: File (name + destination + reasoning), Confidence (HIGH/MEDIUM/LOW badge), Source (Rule/AI/Vision/Keywords badge), Size

Action bar:
- Left: Export Plan button, Logging toggle
- Right: LLM status dot (green/yellow/red), Execute Organization button

## 5 Organization Presets

```python
PROMPT_PRESETS = {
    1: {
        "name": "🗂️ General Cleanup",
        "prompt": """Organize files by type:
📁 Images → Images/[Type]/YYYY
📁 Documents → Documents/[Type]/YYYY
📁 Videos → Videos/YYYY
📁 Music → Music/YYYY
📁 Archives → Archives/[Type]/YYYY
📁 Code → Code/[Language]
📁 Other → Other/YYYY
Flag duplicates for review."""
    },
    2: {
        "name": "📸 Photographer",
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
        "name": "💻 Developer",
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
        "name": "💼 Work/Personal",
        "prompt": """Split files by context:
💼 Work files → Work/[Category]/YYYY/
🏠 Personal files → Personal/[Category]/YYYY/
⚠️ Flag sensitive files for manual review.
Organize by type within each category."""
    },
    5: {
        "name": "✏️ Custom",
        "prompt": ""  # User writes their own
    }
}
```

---

# 4. MULTI-CATALOG SEARCH — NEW FEATURE (READY TO SHIP)

## What It Does

Photographers often have multiple Lightroom catalogs (one per year, one per client, etc.). This feature searches across ALL of them simultaneously from a single dialog.

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `catalog_search.py` | ~350 | Core search engine (SQLite queries against .lrcat files) |
| `catalog_search_dialog.py` | ~550 | Full PyQt6 UI dialog with thumbnail grid |
| `catalog_search_demo.py` | ~100 | Standalone demo app for testing |
| `test_catalog_search.py` | ~150 | Unit tests (all passing) |
| `fop_catalog_search_integration.py` | ~100 | Integration guide with copy-paste code |
| `README_catalog_search.md` | ~200 | Complete feature documentation |

## Key Classes

### MultiCatalogSearch (catalog_search.py)

```python
class MultiCatalogSearch:
    catalogs: List[Path]          # List of .lrcat files
    last_error: Optional[str]

    def add_catalog(path: Path) -> bool      # Validates it's a real .lrcat
    def remove_catalog(path: Path) -> bool
    def search(query: str, mode: str, max_results: int) -> List[FileResult]
    # mode: "contains" | "exact" | "wildcard"
    # Opens each .lrcat as SQLite (READ-ONLY), queries AgLibraryFile table
```

### FileResult (catalog_search.py)

```python
@dataclass
class FileResult:
    filename: str
    catalog_name: str
    catalog_path: str
    file_path: str        # Full path to actual file on disk
    folder_path: str      # Parent folder
    file_id: int          # Lightroom internal ID
    capture_date: Optional[datetime]
    file_format: Optional[str]
    rating: Optional[int]
```

### CatalogSearchDialog (catalog_search_dialog.py)

- Add/remove .lrcat catalogs via file picker
- Search bar with mode dropdown (Contains/Exact/Wildcard)
- Results displayed as 4-column grid of thumbnail cards
- Click card → shows details in info panel
- "Show in Finder" button opens file location
- Catalog list persists via QSettings("BartLabs", "FileOrganizerPro")

## Integration Into FOP

Requires ~25 lines of changes to `FileOrganizerPro.py`:

```python
# 1. Add import at top
from catalog_search_dialog import CatalogSearchDialog

# 2. Add button to Welcome page (in create_welcome_page())
search_btn = QPushButton("🔍 Search Catalogs")
search_btn.clicked.connect(self.open_catalog_search)
# ... styling code ...

# 3. Add method to FileOrganizerPro class
def open_catalog_search(self):
    dialog = CatalogSearchDialog(self)
    dialog.exec()

# 4. Update version
VERSION = "2.6.5"
```

## Status

- All Phase 1 features complete and tested
- Zero bugs found
- Ready to ship as v2.6.5
- Phase 2 (real thumbnails from .lrprev) planned for v2.6.6
- Phase 3 (Open in Lightroom via AppleScript/COM) planned for v2.7.0

---

# 5. LRFORGE — LIGHTROOM PLUGIN SPECIFICATION

## Status: Specification Complete, Zero Code Written

LrForge is a Lightroom Classic plugin (Lua) that imports `.fopplan` files exported by FOP and executes the file moves inside Lightroom, preserving all catalog data.

## Why LrForge Must Exist

When a photographer moves files outside Lightroom (Finder, Terminal, any app), Lightroom loses track of the file. The catalog entry shows "?" and the photographer loses access to:

1. ✂️ All Develop edits (crops, exposure, color grading)
2. ⭐ Ratings and flags
3. 🏷️ Keywords and metadata
4. 📁 Collection membership
5. 📸 Virtual copies
6. 🖼️ Smart previews
7. 📐 Crop overlays
8. 🎨 Presets applied
9. 📝 Captions and titles
10. 🗺️ Map locations
11. 👤 Face recognition data
12. 📊 Edit history

For 50,000 files, manual re-linking is catastrophic. LrForge solves this by using `photo:moveToFolder()` which is Lightroom's own atomic move operation.

## Plugin Structure

```
LrForge.lrplugin/
├── Info.lua                    # Plugin metadata (required by LrC)
├── dkjson.lua                  # JSON parser (pure Lua, MIT license)
├── LrForgeMain.lua             # Entry point
├── FopPlanParser.lua           # Parse + validate .fopplan JSON
├── PlanExecutor.lua            # Execute moves via LR SDK
├── UI/
│   ├── MainDialog.lua          # Main plugin dialog
│   ├── PreviewPanel.lua        # Plan preview before execution
│   └── ResultsDialog.lua       # Post-execution results
└── Resources/
    └── icon.png                # Plugin icon
```

## Info.lua

```lua
return {
    LrSdkVersion = 10.0,
    LrSdkMinimumVersion = 6.0,
    LrToolkitIdentifier = 'com.bartlabs.lrforge',
    LrPluginName = "LrForge",
    LrPluginInfoUrl = "https://bartlabs.com/lrforge",

    LrLibraryMenuItems = {
        {
            title = "LrForge - Import Organization Plan...",
            file = "LrForgeMain.lua",
            enabledWhen = "anythingSelected",
        },
    },

    LrExportMenuItems = {
        {
            title = "LrForge - Import Organization Plan...",
            file = "LrForgeMain.lua",
        },
    },

    VERSION = { major=1, minor=0, revision=0 },
}
```

## Core Lua Implementation

### Loading a .fopplan file

```lua
local json = require 'dkjson'

local function loadFopPlan(filepath)
    local file = io.open(filepath, "r")
    if not file then
        return nil, "Could not open file: " .. filepath
    end

    local content = file:read("*all")
    file:close()

    local plan, pos, err = json.decode(content)
    if err then
        return nil, "JSON parse error: " .. err
    end

    if plan.fopplan_version ~= "1.0" then
        return nil, "Unsupported fopplan version: " .. (plan.fopplan_version or "unknown")
    end

    return plan, nil
end
```

### Finding photos in catalog

```lua
local LrApplication = import 'LrApplication'
local catalog = LrApplication.activeCatalog()

local function findPhotoByPath(absolutePath)
    return catalog:findPhotoByPath(absolutePath)
end
```

### Moving photos (THE KEY METHOD)

```lua
local function movePhoto(photo, destinationFolder, newFilename)
    catalog:withWriteAccessDo("LrForge: Move file", function()
        -- Create destination folder if needed
        local folder = catalog:createFolder(destinationFolder, true) -- true = create parents

        -- THIS IS THE MAGIC LINE
        -- Moves file on disk AND updates catalog in one atomic operation
        photo:moveToFolder(folder)

        -- Rename if needed
        if newFilename and newFilename ~= photo:getFormattedMetadata('fileName') then
            photo:setRawMetadata('fileName', newFilename)
        end
    end)
end
```

### Full execution loop

```lua
local function executeFopPlan(plan)
    local LrTasks = import 'LrTasks'
    local LrDialogs = import 'LrDialogs'
    local LrProgressScope = import 'LrProgressScope'

    LrTasks.startAsyncTask(function()
        local progress = LrProgressScope({
            title = "LrForge: Organizing " .. #plan.moves .. " files",
            functionContext = context
        })

        local success, failed, skipped = 0, 0, 0
        local errors = {}

        for i, move in ipairs(plan.moves) do
            if progress:isCanceled() then break end
            progress:setPortionComplete(i, #plan.moves)
            progress:setCaption(move.filename)

            -- Skip duplicates if configured
            if move.is_duplicate and plan.options.handle_duplicates == "skip" then
                skipped = skipped + 1
            else
                local photo = catalog:findPhotoByPath(move.source)
                if photo then
                    local destFolder = move.destination:match("(.*/)")
                    local ok, err = pcall(function()
                        movePhoto(photo, destFolder, move.filename)
                    end)
                    if ok then
                        success = success + 1
                    else
                        failed = failed + 1
                        table.insert(errors, {file = move.filename, error = err})
                    end
                else
                    failed = failed + 1
                    table.insert(errors, {
                        file = move.filename,
                        error = "Not found in Lightroom catalog"
                    })
                end
            end
        end

        progress:done()
        showResultsDialog(success, failed, skipped, errors)
    end)
end
```

## LrForge UI Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                    LrForge - Import Organization Plan                 │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Plan: ~/Desktop/photo_organization.fopplan                          │
│  Created: 2026-02-03 by FileOrganizerPro v2.6.5                    │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  SUMMARY                                                       │  │
│  │  Total files: 1,346       Action: MOVE                        │  │
│  │  Total size: 19.7 GB      Folders to create: 24               │  │
│  │  Duplicates: 172          Source: ~/Photos/Unsorted            │  │
│  │                           Target: ~/Photos/Organized           │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  CONFIDENCE BREAKDOWN                                          │  │
│  │  ████████████████████████████░░░  HIGH: 892 (66%)             │  │
│  │  ████████████░░░░░░░░░░░░░░░░░░  MEDIUM: 282 (21%)           │  │
│  │  █████░░░░░░░░░░░░░░░░░░░░░░░░░  LOW: 172 (13%)              │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ☐ Create backup manifest (undo file)                                │
│  ☑ Skip files not found in catalog                                   │
│  ☑ Create destination folders automatically                          │
│                                                                      │
│  ⚠️  172 files classified as LOW confidence. Review recommended.     │
│                                                                      │
│                          [Cancel]  [Execute Plan →]                   │
└──────────────────────────────────────────────────────────────────────┘
```

## Open Design Questions for LrForge

These need decisions before coding begins:

1. **Files not in catalog:** Should LrForge (A) skip them, (B) offer to import them first, or (C) move them outside Lightroom?
2. **Duplicate handling:** Should LrForge (A) move to _Duplicates as specified, (B) skip entirely, or (C) ask user?
3. **Progress updates:** Per-file (most responsive) or per-batch-of-10 (less UI overhead)?
4. **Backup:** (A) Copy all files first, (B) just generate undo .fopplan, or (C) skip for v1?
5. **LrC version support:** What's the minimum version? SDK 6.0+ covers LrC 6+.

---

# 6. THE .FOPPLAN CONTRACT — SHARED DATA FORMAT

This is the JSON schema that FOP writes and LrForge reads. It's the contract between the two products.

## Complete Schema

```json
{
    "fopplan_version": "1.0",
    "created_by": "FileOrganizerPro",
    "created_at": "2026-02-03T14:30:00Z",
    "fop_version": "2.6.5",

    "source_root": "/Users/photographer/Photos/Unsorted",
    "target_root": "/Users/photographer/Photos/Organized",

    "action": "move",

    "statistics": {
        "total_files": 1346,
        "total_size_bytes": 21156249600,
        "folders_to_create": 24,
        "duplicates_flagged": 172,
        "confidence_high": 892,
        "confidence_medium": 282,
        "confidence_low": 172
    },

    "folders": [
        "Photos/Wildlife/Eagle/2025",
        "Photos/Wildlife/Bear/2025",
        "Photos/Weddings/2025-06",
        "Photos/Portraits/2025",
        "Photos/Landscapes/2025",
        "Documents/PDF/2025",
        "_Duplicates"
    ],

    "moves": [
        {
            "source": "/Users/photographer/Photos/Unsorted/IMG_4521.CR3",
            "destination": "Photos/Wildlife/Eagle/2025/IMG_4521.CR3",
            "filename": "IMG_4521.CR3",
            "size_bytes": 47382016,
            "confidence": "high",
            "classification_source": "keywords",
            "reasoning": "From keywords: eagle, bird, wildlife",
            "is_duplicate": false,
            "duplicate_of": null
        },
        {
            "source": "/Users/photographer/Photos/Unsorted/DSC_0042.NEF",
            "destination": "Photos/Weddings/2025-06/DSC_0042.NEF",
            "filename": "DSC_0042.NEF",
            "size_bytes": 40587264,
            "confidence": "high",
            "classification_source": "vision",
            "reasoning": "Vision AI: wedding ceremony, bride, outdoor",
            "is_duplicate": false,
            "duplicate_of": null
        },
        {
            "source": "/Users/photographer/Photos/Unsorted/IMG_4521_copy.CR3",
            "destination": "_Duplicates/IMG_4521_copy.CR3",
            "filename": "IMG_4521_copy.CR3",
            "size_bytes": 47382016,
            "confidence": "high",
            "classification_source": "hash",
            "reasoning": "Duplicate of IMG_4521.CR3 (hash match)",
            "is_duplicate": true,
            "duplicate_of": "/Users/photographer/Photos/Unsorted/IMG_4521.CR3"
        }
    ],

    "options": {
        "handle_duplicates": "move_to_duplicates_folder",
        "create_folders": true,
        "on_conflict": "rename",
        "preserve_folder_dates": false
    }
}
```

## Field Reference — Top Level

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `fopplan_version` | string | Yes | Schema version. LrForge checks this for compatibility. Currently "1.0" |
| `created_by` | string | Yes | Always "FileOrganizerPro" |
| `created_at` | string (ISO 8601) | Yes | When the plan was created |
| `fop_version` | string | Yes | FOP version that created this plan |
| `source_root` | string | Yes | Absolute path to the source directory |
| `target_root` | string | Yes | Absolute path to the target directory |
| `action` | string | Yes | "move" or "copy" |
| `statistics` | object | Yes | Summary stats for display in LrForge UI |
| `folders` | array of strings | Yes | Relative paths (from target_root) of folders to create |
| `moves` | array of objects | Yes | Individual file operations |
| `options` | object | Yes | Execution preferences selected by user |

## Field Reference — Move Objects

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | Yes | Absolute path to source file |
| `destination` | string | Yes | Relative path from target_root (includes filename) |
| `filename` | string | Yes | Just the filename (for UI display) |
| `size_bytes` | integer | Yes | File size for progress calculation |
| `confidence` | string | Yes | "high", "medium", or "low" |
| `classification_source` | string | Yes | "keywords", "vision", "clip", "rule", "hash", "ai" |
| `reasoning` | string | Yes | Human-readable explanation of classification |
| `is_duplicate` | boolean | Yes | True if this file is a detected duplicate |
| `duplicate_of` | string or null | Yes | Absolute path to the original if duplicate, else null |

## Field Reference — Options Object

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `handle_duplicates` | string | "move_to_duplicates_folder", "skip", "ask" | What to do with files where is_duplicate=true |
| `create_folders` | boolean | true/false | Whether to auto-create destination folders |
| `on_conflict` | string | "rename", "skip", "overwrite" | If a file already exists at destination |
| `preserve_folder_dates` | boolean | true/false | Preserve original folder modification timestamps |

---

# 7. LLM INTEGRATION — IMPLEMENTATION GUIDE

## Current State

- Connection test works: Socket probe to `192.168.1.93:1234` + HTTP GET to `/v1/models`
- API call structure is designed but NOT coded
- Model loaded: Qwen3-VL-8B (vision-language model)
- LM Studio exposes OpenAI-compatible API

## Where to Add Code

In `FileClassifier.run()`, the classification pipeline currently falls through to "Unsorted" for any file that doesn't match rules or keywords. The LLM call goes here:

```python
# Current code in FileClassifier.run():
for file in files:
    if file.is_duplicate:
        file.destination = "_Duplicates"
        file.source = ClassificationSource.HASH

    elif file.keywords and trust_level == TRUST:
        self._classify_from_keywords(file)

    elif self._classify_by_rules(file):
        pass  # Rule set destination

    elif file.is_photo and photo_mode:
        self._classify_photo(file)

    else:
        # ← LLM CLASSIFICATION GOES HERE
        # Currently falls through to:
        file.destination = f"Unsorted/{year}"
        file.confidence = Confidence.LOW
```

## Implementation

```python
def _classify_with_llm(self, files_batch: List[FileInfo]) -> None:
    """
    Send a batch of unclassified files to LLM for classification.
    Uses OpenAI-compatible API at LM Studio endpoint.
    """
    import urllib.request
    import json

    url = f"{self.options['llm_url']}/v1/chat/completions"

    # Build file list for prompt
    file_list = []
    for f in files_batch:
        entry = {
            'name': f.name,
            'extension': f.extension,
            'size': f.size,
            'modified': f.modified.isoformat(),
            'is_photo': f.is_photo,
        }
        if f.keywords:
            entry['keywords'] = f.keywords
        if f.description:
            entry['description'] = f.description
        file_list.append(entry)

    system_prompt = """You are a file organization assistant.
Given a list of files and organization rules, suggest the best destination folder for each file.

IMPORTANT:
- Respond ONLY with valid JSON, no markdown, no explanations
- Use the exact format shown below
- confidence must be "high", "medium", or "low"
- destination must be a relative folder path using / separators
- Include {year} based on the file's modified date

Response format:
{
    "classifications": [
        {
            "filename": "example.jpg",
            "destination": "Photos/Wildlife/Eagle/2025",
            "confidence": "high",
            "reasoning": "Keywords indicate eagle photography"
        }
    ]
}"""

    user_prompt = f"""Organize these files according to these rules:

{self.prompt}

Files to classify:
{json.dumps(file_list, indent=2)}"""

    payload = {
        "model": "qwen/qwen3-vl-8b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 2000
    }

    try:
        req = urllib.request.Request(url, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.data = json.dumps(payload).encode()

        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read())
            content = result['choices'][0]['message']['content']

            # Parse JSON response (handle markdown fencing)
            content = content.strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[1]
                content = content.rsplit('```', 1)[0]

            classifications = json.loads(content)

            # Apply classifications to FileInfo objects
            filename_map = {f.name: f for f in files_batch}
            for c in classifications.get('classifications', []):
                fname = c.get('filename', '')
                if fname in filename_map:
                    f = filename_map[fname]
                    f.destination = c.get('destination', f'Unsorted/{f.modified.year}')
                    f.confidence = Confidence[c.get('confidence', 'medium').upper()]
                    f.source = ClassificationSource.AI
                    f.reasoning = c.get('reasoning', 'AI classification')

    except Exception as e:
        # On failure, mark all as unsorted with low confidence
        for f in files_batch:
            if not f.destination:
                f.destination = f"Unsorted/{f.modified.year}"
                f.confidence = Confidence.LOW
                f.reasoning = f"LLM error: {str(e)}"
```

## Batch Processing

For large file sets, batch into groups of 20-50 files per API call:

```python
def _classify_all_with_llm(self, unclassified: List[FileInfo]) -> None:
    batch_size = self.options.get('ai_batch_size', 20)
    for i in range(0, len(unclassified), batch_size):
        batch = unclassified[i:i + batch_size]
        self._classify_with_llm(batch)
        self.progress.emit(i + len(batch), len(unclassified), f"AI classifying batch...")
```

---

# 8. FILE EXECUTION — IMPLEMENTATION GUIDE

## Current State

ExecuteDialog exists with Copy/Move radio buttons and target folder selection, but clicking "Execute" shows "coming soon."

## Implementation

```python
def execute_organization(self, plan: OrganizationPlan) -> None:
    """
    Execute the organization plan: create folders and copy/move files.
    """
    import shutil
    from pathlib import Path

    target = Path(plan.target_root)
    action = plan.action  # "copy" or "move"
    results = {"success": 0, "failed": 0, "skipped": 0, "errors": []}

    # 1. Create folder structure
    for folder in plan.folders:
        folder_path = target / folder
        folder_path.mkdir(parents=True, exist_ok=True)

    # 2. Process each file
    total = len(plan.moves)
    for i, move in enumerate(plan.moves):
        self.progress.emit(i + 1, total, move['filename'])

        source_path = Path(move['source'])
        dest_path = target / move['destination']

        # Skip if source doesn't exist
        if not source_path.exists():
            results["failed"] += 1
            results["errors"].append(f"Not found: {move['filename']}")
            continue

        # Handle conflicts
        if dest_path.exists():
            conflict = plan.options.get('on_conflict', 'rename')
            if conflict == 'skip':
                results["skipped"] += 1
                continue
            elif conflict == 'rename':
                # Add (1), (2), etc.
                stem = dest_path.stem
                suffix = dest_path.suffix
                counter = 1
                while dest_path.exists():
                    dest_path = dest_path.parent / f"{stem} ({counter}){suffix}"
                    counter += 1
            # "overwrite" just proceeds

        # Ensure parent directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if action == "copy":
                shutil.copy2(str(source_path), str(dest_path))
            else:  # move
                shutil.move(str(source_path), str(dest_path))
            results["success"] += 1
        except PermissionError:
            results["failed"] += 1
            results["errors"].append(f"Permission denied: {move['filename']}")
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{move['filename']}: {str(e)}")

    return results
```

This should run in a QThread with progress signals back to a dialog.

---

# 9. CLASSIFICATION PIPELINE — FULL LOGIC

## Priority Order

```
┌─────────────────────────────────────────────────────────────┐
│                   CLASSIFICATION PIPELINE                     │
│                                                               │
│  For each file, try in order (first match wins):              │
│                                                               │
│  1. DUPLICATE CHECK (hash)                                    │
│     If file_hash matches another file → _Duplicates/          │
│     Source: HASH, Confidence: HIGH                            │
│                                                               │
│  2. KEYWORD CLASSIFICATION (if trust_level == TRUST)          │
│     If file has IPTC/XMP keywords → map to category           │
│     Source: KEYWORD, Confidence: HIGH                         │
│                                                               │
│  3. RULE CLASSIFICATION (pattern match)                       │
│     If filename/extension matches rule → use rule dest        │
│     Source: RULE, Confidence: HIGH                            │
│     50+ rules covering all common file types                  │
│                                                               │
│  4. PHOTO MODE (if enabled and file is photo)                 │
│     Special handling for image files                          │
│     Source: varies, Confidence: MEDIUM                        │
│                                                               │
│  5. LLM CLASSIFICATION (TODO — not implemented)               │
│     Send to local LLM for AI classification                   │
│     Source: AI, Confidence: varies                            │
│                                                               │
│  6. FALLBACK                                                  │
│     file → Unsorted/{year}                                    │
│     Source: RULE, Confidence: LOW                             │
└─────────────────────────────────────────────────────────────┘
```

## Rule Examples (50+ total)

```python
rules = [
    # Archives
    {'pattern': r'\.(dmg|iso|img)$',     'dest': 'Archives/Disk Images/{year}'},
    {'pattern': r'\.(zip|rar|7z|gz|tar)$', 'dest': 'Archives/Compressed/{year}'},

    # Documents
    {'pattern': r'\.(pdf)$',              'dest': 'Documents/PDF/{year}'},
    {'pattern': r'\.(docx?|rtf)$',        'dest': 'Documents/Word/{year}'},
    {'pattern': r'\.(xlsx?|csv)$',        'dest': 'Documents/Spreadsheets/{year}'},
    {'pattern': r'\.(pptx?)$',            'dest': 'Documents/Presentations/{year}'},
    {'pattern': r'\.(md|txt)$',           'dest': 'Documents/Text/{year}'},

    # Code
    {'pattern': r'\.(py|pyw)$',           'dest': 'Code/Python'},
    {'pattern': r'\.(js|ts|jsx|tsx)$',    'dest': 'Code/JavaScript'},
    {'pattern': r'\.(html|css|scss)$',    'dest': 'Code/Web'},
    {'pattern': r'\.(java|kt)$',          'dest': 'Code/Java'},
    {'pattern': r'\.(swift|m)$',          'dest': 'Code/Swift'},
    {'pattern': r'\.(c|cpp|h|hpp)$',      'dest': 'Code/C_CPP'},

    # Media
    {'pattern': r'\.(mp4|mov|avi|mkv)$',  'dest': 'Videos/{year}'},
    {'pattern': r'\.(mp3|wav|flac|aac)$', 'dest': 'Music/{year}'},
    {'pattern': r'\.(gif)$',              'dest': 'Images/GIFs/{year}'},

    # Photos (if not handled by keyword/AI)
    {'pattern': r'\.(jpg|jpeg|png|tiff?)$', 'dest': 'Images/{year}'},
    {'pattern': r'\.(cr2|cr3|nef|arw|dng|orf|rw2)$', 'dest': 'Photos/RAW/{year}'},

    # Filename-based rules
    {'pattern': r'screenshot',  'dest': 'Images/Screenshots/{year}',  'check_name': True},
    {'pattern': r'receipt',     'dest': 'Documents/Receipts/{year}',  'check_name': True},
    {'pattern': r'invoice',     'dest': 'Documents/Invoices/{year}',  'check_name': True},

    # Applications
    {'pattern': r'\.(app|exe|msi)$',      'dest': 'Applications/{year}'},
    {'pattern': r'\.(pkg|deb|rpm)$',      'dest': 'Applications/Installers/{year}'},

    # Fonts
    {'pattern': r'\.(ttf|otf|woff2?)$',   'dest': 'Fonts'},

    # Design
    {'pattern': r'\.(psd|ai|sketch|fig)$','dest': 'Design/{year}'},
    {'pattern': r'\.(svg)$',              'dest': 'Design/SVG'},
]
```

## Keyword-to-Category Mapping (Photos)

```python
photo_categories = {
    'Wildlife':   ['wildlife', 'bird', 'eagle', 'hawk', 'owl', 'bear', 'deer',
                   'fox', 'wolf', 'moose', 'elk', 'bison', 'animal', 'nature'],
    'Weddings':   ['wedding', 'bride', 'groom', 'ceremony', 'reception',
                   'engagement', 'bridal', 'bouquet', 'vows'],
    'Sports':     ['sports', 'racing', 'football', 'basketball', 'soccer',
                   'baseball', 'tennis', 'golf', 'swimming', 'track'],
    'Portraits':  ['portrait', 'headshot', 'people', 'person', 'face',
                   'family', 'couple', 'senior', 'maternity'],
    'Landscapes': ['landscape', 'mountain', 'beach', 'sunset', 'sunrise',
                   'ocean', 'lake', 'forest', 'desert', 'sky', 'clouds'],
    'Pets':       ['pet', 'dog', 'cat', 'puppy', 'kitten', 'horse'],
    'Food':       ['food', 'restaurant', 'cuisine', 'cooking', 'recipe'],
    'Travel':     ['travel', 'vacation', 'tourism', 'hotel', 'airport'],
    'Events':     ['event', 'concert', 'festival', 'party', 'conference'],
    'Real Estate':['real estate', 'property', 'house', 'interior', 'architecture'],
}
```

When a file has keywords and trust_level == TRUST, FOP checks each keyword against these category maps. First category match wins. Destination becomes `Photos/{Category}/{Year}`. If keywords contain a species name (e.g., "eagle"), it adds a sublevel: `Photos/Wildlife/Eagle/{Year}`.

---

# 10. COLOR SYSTEM & DESIGN LANGUAGE

## Color Palette

```python
class Colors:
    # Brand
    ORANGE = "#FF6B35"          # Primary accent, CTAs, links
    ORANGE_DARK = "#E85A2A"     # Hover states
    TEAL = "#00D4AA"            # Success, primary action buttons
    TEAL_DARK = "#00B894"       # Hover

    # Secondary
    PURPLE = "#6C5CE7"          # Section headers, accents
    PURPLE_DARK = "#5B4CC7"
    GOLD = "#FDCB6E"            # Warnings, highlights
    MAGENTA = "#E84393"         # Photo mode accent

    # Neutrals
    NAVY = "#2D3436"            # Primary text, borders
    CHARCOAL = "#4a5568"        # Secondary text
    SLATE = "#64748b"           # Tertiary text, labels
    CREAM = "#FDF8F3"           # Page background
    WARM = "#FFFAF5"            # Input backgrounds

    # Pastel (metric cards on Results page)
    PURPLE_PASTEL = "#A29BDB"   # Total Files card
    TEAL_PASTEL = "#6EE7C8"     # Total Size card
    ORANGE_PASTEL = "#FFB088"   # Duplicates card
    GOLD_PASTEL = "#FDE5A0"     # Folders card

    # Semantic
    SUCCESS = "#10B981"
    WARNING = "#F59E0B"
    ERROR = "#EF4444"
```

## Design System — "Maximalist 2026"

- Rounded corners: 8-12px on elements, 20px on major panels
- Colored left borders: 5px on section frames (orange for folders, purple for guidance, teal for options)
- Pastel metric cards with colored values
- Neumorphic shadows on the reference HTML mockup (PyQt6 version is flatter)
- SF Pro Display / system-ui font stack
- Orange/charcoal brand identity
- Confidence badges: Green (HIGH), Yellow (MEDIUM), Red (LOW)
- Source badges: Gray pill (Rule / AI / Vision / Keywords / CLIP / Hash)

---

# 11. KNOWN ISSUES, BUGS, AND DEBT

## Critical (Blocking Ship)

| Issue | Description | Effort |
|-------|-------------|--------|
| LLM classification not wired | API structure exists, no actual HTTP calls | 4-8 hrs |
| File execution not wired | ExecuteDialog exists, no shutil calls | 4-6 hrs |
| LrForge not built | 627-line spec, zero Lua code | 20-40 hrs |

## High Priority

| Issue | Description | Effort |
|-------|-------------|--------|
| Settings don't persist | LLM URL, folders, options reset on restart. Use QSettings | 2-3 hrs |
| Multi-Catalog Search not integrated | Built and tested, needs 25 lines in main app | 1 hr |
| Preferences dialog layout | Rebuilt in v2.6.4 but never visually verified | 1-2 hrs |

## Medium Priority

| Issue | Description | Effort |
|-------|-------------|--------|
| No error handling for permissions | Scan fails silently on permission denied | 2-3 hrs |
| exiftool not found | No graceful fallback, just crashes | 1-2 hrs |
| Vision AI toggle shown but not implemented | Either implement or hide | 1 hr (hide) |
| CLIP not integrated | Image content classification missing | 8-16 hrs |

## Low Priority / Debt

| Issue | Description | Effort |
|-------|-------------|--------|
| Single-file architecture | 2,390 lines in one .py file | 4-6 hrs to split |
| No automated tests (main app) | Only catalog search has tests | 8-12 hrs |
| App not packaged | No PyInstaller / .app / .exe | 4-6 hrs |
| RAW thumbnails | Not extracting previews from RAW files | 4-6 hrs |

---

# 12. FILE INVENTORY

## Source Code

| File | Location | Lines | Status |
|------|----------|-------|--------|
| FileOrganizerPro.py | /mnt/user-data/outputs/ | 2,390 | v2.6.4, working |
| catalog_search.py | /mnt/user-data/outputs/ | ~350 | Production ready |
| catalog_search_dialog.py | /mnt/user-data/outputs/ | ~550 | Production ready |
| catalog_search_demo.py | /mnt/user-data/outputs/ | ~100 | Demo/test app |
| test_catalog_search.py | /mnt/user-data/outputs/ | ~150 | All tests passing |
| fop_catalog_search_integration.py | /mnt/user-data/outputs/ | ~100 | Integration guide |

## Documentation

| File | Location | Lines | Purpose |
|------|----------|-------|---------|
| FOP_Developer_Handoff_For_New_Session.md | /mnt/project/ | 905 | Previous handoff (Jan 31) |
| LRFORGE_PLUGIN_REQUIREMENTS.md | /mnt/user-data/outputs/ | 627 | LrForge spec |
| FOP_Status_Report_2026-01-31.md | /mnt/user-data/outputs/ | 293 | Status report |
| README_catalog_search.md | /mnt/user-data/outputs/ | ~200 | Catalog search docs |
| IMPLEMENTATION_SUMMARY.md | /mnt/user-data/outputs/ | ~100 | Catalog search summary |
| daily_log_2026-01-31.md | /mnt/user-data/outputs/ | 120 | Session log |

## Design References

| File | Location | Purpose |
|------|----------|---------|
| fop_mockup.html | /mnt/project/ | Original neumorphic mockup (Results page + Settings) |
| fop_complete_mockup.html | /mnt/user-data/outputs/ | Full mockup with all pages |

---

# 13. BUILD & TEST INSTRUCTIONS

## Prerequisites

```bash
# Python 3.10+
python3 --version

# Install PyQt6
pip install PyQt6

# exiftool (for metadata reading)
# macOS:
brew install exiftool
# Linux:
sudo apt install libimage-exiftool-perl
```

## Running FOP

```bash
cd /path/to/fop/
python FileOrganizerPro.py
```

## Testing Catalog Search (Standalone)

```bash
# Demo app (no FOP integration needed)
python catalog_search_demo.py

# Unit tests
python test_catalog_search.py
```

## Testing LLM Connection

1. Ensure LM Studio is running on `192.168.1.93:1234`
2. Ensure Windows Firewall rule exists for port 1234
3. In FOP: Settings gear → Preferences → AI Connection → Test Connection
4. Should show: "Connected to http://192.168.1.93:1234"

```bash
# Manual test from command line:
curl http://192.168.1.93:1234/v1/models
# Should return JSON with loaded model info
```

## Test Data Results

| Metric | Value |
|--------|-------|
| Test files | 1,346 files / 19.7 GB |
| Scan time | 0.4 seconds |
| Duplicates found | 529 |
| Folder categories created | 11 |
| Rule classification | < 1 second |
| Export .fopplan | < 0.1 seconds |

---

# 14. DECISION LOG

| # | Decision | Rationale | Date | Reversible? |
|---|----------|-----------|------|-------------|
| 1 | READ-ONLY metadata | Writing XMP causes Lightroom to re-scan 70k+ files (hours). Hard requirement. | Jan 30 | No |
| 2 | Local-first LLM | Privacy for sensitive photo collections. Works offline. | Jan 30 | No |
| 3 | Single-file architecture | Simplifies rapid iteration. Will split for v2. | Jan 30 | Yes |
| 4 | Three keyword trust levels | Photographers have varying confidence in existing keywords. | Jan 31 | No |
| 5 | .fopplan as JSON | Enables FOP → LrForge workflow. Separation of concerns. | Jan 31 | No |
| 6 | Charcoal/orange branding | Bart Labs visual identity. Evolved from purple/orange. | Jan 30 | Yes |
| 7 | 5px colored left borders | User preferred thin (5px) over thick (8px) section borders. | Jan 31 | Yes |
| 8 | AI Connection in Preferences only | Was duplicated on Setup page AND Preferences. Consolidated. | Jan 31 | Yes |
| 9 | Multi-Catalog Search as standalone | Can ship independently without LLM dependency. | Feb 1 | Yes |
| 10 | No DuckDB for v1 | In-memory + export is sufficient. Consider for v2. | Jan 31 | Yes |
| 11 | dkjson for LrForge JSON | Pure Lua, 15KB, MIT license. No C dependencies. | Jan 31 | Yes |
| 12 | Qwen3-VL-8B as LLM | Vision-language model supports future photo content analysis. | Jan 30 | Yes |

---

# 15. PRIORITIZED TASK LIST

## Tier 1: Ship v2.6.5 (Today)
1. Integrate Multi-Catalog Search into FOP (25 lines, 1 hour)
2. Verify Preferences dialog layout (v2.6.4 rebuild)
3. Bump version to 2.6.5, test full flow

## Tier 2: Core Functionality (This Week)
4. Implement LLM classification API calls (4-8 hours)
5. Implement file copy/move execution (4-6 hours)
6. Add QSettings persistence for all preferences (2-3 hours)
7. Add exiftool missing fallback / error handling (1-2 hours)
8. Ship v2.7.0 with AI classification + file execution

## Tier 3: Polish (Next Week)
9. Add scan error handling (permission denied, etc.)
10. Hide or implement Vision AI toggle
11. Add progress dialog for file execution
12. Improve LLM error handling and retry logic
13. Ship v2.8.0

## Tier 4: LrForge Plugin (Week 3+)
14. Set up Lua plugin scaffold (Info.lua, structure)
15. Implement .fopplan parser
16. Build LrForge UI (import dialog, preview, results)
17. Implement photo:moveToFolder() execution loop
18. Test with real Lightroom catalogs
19. Ship LrForge v1.0

## Tier 5: Future
20. CLIP integration for image content classification
21. RAW thumbnail extraction
22. App packaging (PyInstaller)
23. Multi-catalog search Phase 2 (real thumbnails)
24. Multi-catalog search Phase 3 (Open in Lightroom)
25. Split single file into modules

---

# END OF HANDOFF DOCUMENT

## For Claude Code: Start Here

1. Read this entire document
2. Examine `FileOrganizerPro.py` (v2.6.4, 2,390 lines)
3. Examine `catalog_search.py` and `catalog_search_dialog.py`
4. Check the user's LM Studio connection: `http://192.168.1.93:1234`
5. Start with Tier 1 tasks (integrate catalog search, verify preferences)
6. Then move to Tier 2 (LLM classification, file execution)

## Key Reminders

- **NEVER write metadata to files** — READ-ONLY is a hard requirement
- **Test with user's dataset** — 1,346 files in their source folder
- **User prefers lowercase filenames** with underscores
- **User wants working code, not explanations**
- **Orange/charcoal branding** — Bart Labs identity
- **LM Studio at 192.168.1.93:1234** — Qwen3-VL-8B model

**Good luck! 🚀**

*— Claude (PM), February 3, 2026*
