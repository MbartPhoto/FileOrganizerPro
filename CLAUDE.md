# CLAUDE.md - FileOrganizerPro

This file provides guidance to Claude Code when working on FileOrganizerPro.

---

## ⚠️ STOP AND READ — BE CONSERVATIVE

**This codebase is part of the Bart Labs product suite. New sessions MUST be careful.**

### Before Making ANY Changes

1. **Check git status** — `git status && git branch -v`
2. **Ask the user** — Confirm what they want before modifying code
3. **ONE change at a time** — Small incremental changes, test after each
4. **Don't "fix" working code** — If it's validated, don't refactor or improve it

### Golden Rules

- **ASK BEFORE MODIFYING** — Don't assume you know what's needed
- **Don't overwrite without asking** — Files may be in specific states intentionally
- **Preserve debugging code** — Logging, test code, etc. may be intentional
- **When in doubt, ASK**

---

## Overview

FileOrganizerPro is a desktop application for AI-powered file organization with Lightroom integration.

### Run

```bash
cd ~/Documents/BartLabs/FileOrganizerPro
pip install PyQt6
python FileOrganizerPro.py
```

### Run Tests

```bash
python -m pytest test_catalog_search.py
```

### Architecture

Single-file application (`FileOrganizerPro.py`, ~2,677 lines) with supporting modules:
- `catalog_search_dialog.py` / `catalog_search.py` — Multi-catalog search
- `test_catalog_search.py` — Unit tests

Key classes:
- `MetadataReader` (exiftool subprocess)
- `FileScanner` (async scanning)
- `FileClassifier` (rule engine + LLM)
- `OrganizationPlan` (folder tree generation)

### FOP-LrForge Bridge

FOP generates `.fopplan` JSON files describing file moves. LrForge imports them via `fopimport.lua` for catalog-safe moves within Lightroom.

### Status

**Working:**
- LLM classification (`_classify_batch_with_llm()`)
- File execution (`FileExecutor` — move/copy with progress UI)
- Rule-based + keyword classification
- Duplicate detection, folder tree, export formats

**Missing:**
- No settings persistence (QSettings)
- No packaging (PyInstaller)
- FOP-LrForge .fopplan bridge not tested end-to-end
