---
name: debug
description: File database debugging toolkit for the ETU files system. Covers index.json validation, missing/corrupted file detection, cache cleanup, schema enforcement, asset integrity checks, and import/export debugging. Use when files go missing, index is corrupt, or asset queries return wrong results.
---

# Files Database Debugging Toolkit

Debug and repair the ETU files database (`files/index.json` and associated files).

---

## Quick Diagnostic Flow

```
Issue reported?
  ├─ File not found?         → Section 1 (index validation)
  ├─ Corrupted asset?        → Section 2 (integrity check)
  ├─ index.json won't parse? → Section 3 (schema repair)
  ├─ Stale cache?            → Section 4 (cache debugging)
  ├─ Export missing?         → Section 5 (export debugging)
  └─ Unknown?                → Section 6 (full health check)
```

---

## 1. Index Validation (File Not Found)

### Validate All Entries Point to Existing Files

```python
"""
Run this from the project root to check index integrity.
Usage: python validate_index.py
"""
import json
from pathlib import Path

INDEX_PATH = Path("files/index.json")
with open(INDEX_PATH) as f:
    db = json.load(f)

issues = []

for collection_name, collection in db["collections"].items():
    base_path = Path(collection["path"])
    
    for i, entry in enumerate(collection.get("entries", [])):
        if "name" in entry:
            file_path = base_path / entry["name"]
        elif "id" in entry:
            # Try to find file by ID
            candidates = list(base_path.glob(f"{entry['id']}.*"))
            file_path = candidates[0] if candidates else None
        else:
            issues.append(f"[{collection_name}][{i}] No 'name' or 'id' field")
            continue
        
        if file_path is None:
            issues.append(f"[{collection_name}][{i}] Empty entry: {entry.get('id', 'unknown')}")
        elif not file_path.exists():
            issues.append(f"[{collection_name}][{i}] MISSING: {file_path} (entry: {entry.get('name', entry.get('id'))})")

if issues:
    print(f"Found {len(issues)} issues:")
    for issue in issues:
        print(f"  ❌ {issue}")
else:
    print("✅ All index entries reference existing files")

# Also check for orphaned files (files not in index):
for collection_name, collection in db["collections"].items():
    base_path = Path(collection["path"])
    indexed_files = set()
    for entry in collection.get("entries", []):
        name = entry.get("name", "")
        if name:
            indexed_files.add(name)
    
    for file_path in base_path.glob("*"):
        if file_path.name.endswith(".gitkeep"):
            continue
        if file_path.is_file() and file_path.name not in indexed_files:
            print(f"  ⚠️  Orphaned file: {file_path} (not in {collection_name} index)")
```

### Quick Command-Line Check

```bash
# Count entries per collection
cd files
python3 -c "
import json
with open('index.json') as f:
    db = json.load(f)
for name, col in db['collections'].items():
    entries = len(col.get('entries', []))
    files = len(list(Path(col['path']).glob('*')))
    print(f'{name}: {entries} entries, {files} files on disk')
"

# Find missing files
python3 -c "
import json
from pathlib import Path
with open('index.json') as f:
    db = json.load(f)
for name, col in db['collections'].items():
    base = Path(col['path'])
    for e in col.get('entries', []):
        p = base / e.get('name', 'unknown')
        if not p.exists():
            print(f'MISSING: {p}')
"
```

### Check for Duplicate IDs

```python
import json
from collections import Counter

with open("files/index.json") as f:
    db = json.load(f)

for collection_name, collection in db["collections"].items():
    ids = [e["id"] for e in collection.get("entries", []) if "id" in e]
    duplicates = {id_: count for id_, count in Counter(ids).items() if count > 1}
    if duplicates:
        print(f"[{collection_name}] Duplicate IDs:")
        for id_, count in duplicates.items():
            print(f"  ❌ '{id_}' appears {count} times")
```

---

## 2. File Integrity Checks

### Verify Asset Files Aren't Corrupted

```python
"""
Check common file formats for basic integrity.
Run from project root.
"""
import json
import struct
from pathlib import Path

def check_png(path: Path) -> bool:
    """Verify PNG header."""
    try:
        with open(path, "rb") as f:
            header = f.read(8)
        return header == b"\x89PNG\r\n\x1a\n"
    except Exception as e:
        print(f"  ❌ Cannot read {path.name}: {e}")
        return False

def check_obj(path: Path) -> bool:
    """Verify OBJ has vertices and faces."""
    try:
        content = path.read_text()
        has_v = "v " in content
        has_f = "f " in content
        return has_v and has_f
    except Exception as e:
        print(f"  ❌ Cannot read {path.name}: {e}")
        return False

def check_ply(path: Path) -> bool:
    """Verify PLY header."""
    try:
        with open(path, "rb") as f:
            header = f.read(4)
        return header == b"ply\n" or header == b"PLY\n"
    except Exception as e:
        print(f"  ❌ Cannot read {path.name}: {e}")
        return False

def check_file_size(path: Path, expected_size: int, tolerance: float = 0.1) -> bool:
    """Check file is within expected size range."""
    actual = path.stat().st_size
    if expected_size == 0:
        return True
    diff = abs(actual - expected_size) / expected_size
    return diff <= tolerance

# Run checks
with open("files/index.json") as f:
    db = json.load(f)

for collection_name in ["assets", "exports"]:
    collection = db["collections"][collection_name]
    base = Path(collection["path"])
    
    for entry in collection.get("entries", []):
        name = entry.get("name")
        if not name:
            continue
            
        file_path = base / name
        if not file_path.exists():
            continue  # Already caught by index validation
        
        # Size check
        if "size_bytes" in entry and entry["size_bytes"] > 0:
            if not check_file_size(file_path, entry["size_bytes"]):
                expected = entry["size_bytes"]
                actual = file_path.stat().st_size
                print(f"  ⚠️  Size mismatch: {name}: expected {expected}, got {actual}")
        
        # Format-specific checks
        suffix = file_path.suffix.lower()
        if suffix == ".png":
            check_png(file_path)
        elif suffix == ".obj":
            check_obj(file_path)
        elif suffix == ".ply":
            check_ply(file_path)

print("✅ Integrity check complete")
```

### Checksum Validation (Add to index.json)

If you want to track file integrity over time, add SHA-256 hashes:

```python
import hashlib
import json
from pathlib import Path

def add_checksums():
    """Add SHA-256 checksums to all entries in index.json."""
    with open("files/index.json") as f:
        db = json.load(f)
    
    modified = False
    for collection in db["collections"].values():
        base = Path(collection["path"])
        for entry in collection.get("entries", []):
            name = entry.get("name")
            if not name:
                continue
            file_path = base / name
            if not file_path.exists():
                continue
            
            sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
            if entry.get("sha256") != sha:
                entry["sha256"] = sha
                modified = True
                print(f"  Updated: {name} → {sha[:16]}...")
    
    if modified:
        with open("files/index.json", "w") as f:
            json.dump(db, f, indent=2)
        print("✅ Checksums updated")

def verify_checksums():
    """Verify all checksums in index.json."""
    with open("files/index.json") as f:
        db = json.load(f)
    
    issues = []
    for col_name, collection in db["collections"].items():
        base = Path(collection["path"])
        for entry in collection.get("entries", []):
            if "sha256" not in entry:
                continue
            name = entry.get("name")
            if not name:
                continue
            file_path = base / name
            if not file_path.exists():
                continue
            
            expected = entry["sha256"]
            actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
            if expected != actual:
                issues.append(f"[{col_name}] {name}: checksum mismatch")
    
    if issues:
        print(f"❌ {len(issues)} checksum mismatches:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✅ All checksums valid")
```

---

## 3. Schema Repair (index.json Won't Parse)

### Validate JSON Syntax

```bash
# Check if JSON is valid
python3 -c "import json; json.load(open('files/index.json')); print('✅ Valid JSON')"

# If broken, find the error:
python3 -c "import json; json.load(open('files/index.json'))"
# Python will show the exact line and column of the error

# Pretty-print to check structure:
python3 -m json.tool files/index.json > /dev/null && echo "✅ Valid" || echo "❌ Broken"
```

### Repair Script for Common Schema Issues

```python
"""
Repair common issues in index.json.
BACKUP THE FILE FIRST: cp files/index.json files/index.json.bak
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

INDEX_PATH = Path("files/index.json")

# Load with a backup
backup = INDEX_PATH.read_text()
INDEX_PATH.rename(INDEX_PATH.with_suffix(".json.bak"))
print("✅ Backup saved to index.json.bak")

db = json.loads(backup)

# Repair 1: Add missing required fields to entries
required_fields = {
    "assets": ["id", "name", "type", "format"],
    "cache": ["id", "source_id", "type"],
    "exports": ["id", "name", "format"],
}

for col_name, fields in required_fields.items():
    if col_name not in db["collections"]:
        continue
    for entry in db["collections"][col_name].get("entries", []):
        for field in fields:
            if field not in entry:
                if field == "id":
                    entry["id"] = str(uuid.uuid4())
                    print(f"  Added missing id to entry in {col_name}")
                elif field == "name":
                    entry["name"] = f"unknown-{entry['id'][:8]}"
                elif field == "type":
                    entry["type"] = "other"
                elif field == "format":
                    entry["format"] = "unknown"
                else:
                    entry[field] = ""

# Repair 2: Add timestamps if missing
for collection in db["collections"].values():
    for entry in collection.get("entries", []):
        if "created" not in entry:
            entry["created"] = datetime.now(timezone.utc).isoformat()

# Repair 3: Ensure arrays are actually arrays
for collection in db["collections"].values():
    for entry in collection.get("entries", []):
        if "tags" in entry and not isinstance(entry["tags"], list):
            entry["tags"] = [str(entry["tags"])]
        if "source_assets" in entry and not isinstance(entry["source_assets"], list):
            entry["source_assets"] = [str(entry["source_assets"])]

# Repair 4: Remove entries pointing to non-existent files
for col_name, collection in db["collections"].items():
    base = Path(collection["path"])
    valid_entries = []
    removed = 0
    for entry in collection.get("entries", []):
        name = entry.get("name")
        if name and not (base / name).exists():
            print(f"  Removing: {col_name}/{name} (file missing)")
            removed += 1
            continue
        valid_entries.append(entry)
    if removed > 0:
        collection["entries"] = valid_entries
        print(f"  Removed {removed} stale entries from {col_name}")

# Write repaired index
with open(INDEX_PATH, "w") as f:
    json.dump(db, f, indent=2)
print("✅ Index repaired and saved")
```

### Schema Validation Against Expected Types

```python
"""
Validate entry fields match expected types from the schema.
"""
import json

with open("files/index.json") as f:
    db = json.load(f)

type_checks = {
    "id": str,
    "name": str,
    "type": str,
    "format": str,
    "size_bytes": int,
    "created": str,
    "tags": list,
    "source_assets": list,
    "vertices": int,
    "faces": int,
}

for col_name, collection in db["collections"].items():
    for i, entry in enumerate(collection.get("entries", [])):
        for field, expected_type in type_checks.items():
            if field in entry and not isinstance(entry[field], expected_type):
                actual = type(entry[field]).__name__
                print(f"  ❌ [{col_name}][{i}] {field}: expected {expected_type.__name__}, got {actual}")

print("✅ Type validation complete")
```

---

## 4. Cache Debugging

### Check Cache Status

```bash
# Disk usage per collection
du -sh files/cache/ files/assets/ files/exports/

# File count and type breakdown
find files/cache -type f | wc -l  # total files
find files/cache -name "*.npy" | wc -l  # numpy caches
find files/cache -name "*.pt" | wc -l   # torch caches
```

### Analyze Cache Freshness

```python
from pathlib import Path
import json
from datetime import datetime, timezone, timedelta

with open("files/index.json") as f:
    db = json.load(f)

now = datetime.now(timezone.utc)
cache = db["collections"]["cache"]

stale = []
missing_source = []

for entry in cache.get("entries", []):
    # Check expiration
    if "expires" in entry:
        expires = datetime.fromisoformat(entry["expires"])
        if expires < now:
            stale.append(entry["id"])
    
    # Check source asset still exists
    if "source_id" in entry:
        source_found = False
        assets = db["collections"]["assets"].get("entries", [])
        for asset in assets:
            if asset.get("id") == entry["source_id"]:
                source_found = True
                break
        if not source_found:
            missing_source.append(entry["id"])

if stale:
    print(f"⚠️  {len(stale)} stale cache entries (expired):")
    for sid in stale:
        print(f"  {sid}")
else:
    print("✅ No stale cache entries")

if missing_source:
    print(f"⚠️  {len(missing_source)} orphaned cache entries (source deleted):")
    for sid in missing_source:
        print(f"  {sid}")
else:
    print("✅ All cache entries reference existing sources")

# Cache size report
cache_path = Path("files/cache")
total_size = sum(f.stat().st_size for f in cache_path.rglob("*") if f.is_file())
print(f"\nTotal cache size: {total_size / 1024 / 1024:.1f} MB")
print(f"Total cache files: {sum(1 for f in cache_path.rglob('*') if f.is_file())}")
```

### Safe Cache Cleanup

```bash
# Remove only expired cache entries (safe)
python3 -c "
import json
from pathlib import Path
from datetime import datetime, timezone

with open('files/index.json') as f:
    db = json.load(f)

cache = db['collections']['cache']
cache_path = Path(cache['path'])
now = datetime.now(timezone.utc)

removed = 0
kept_entries = []
for entry in cache.get('entries', []):
    expires = entry.get('expires')
    if expires and datetime.fromisoformat(expires) < now:
        # Remove expired cache files
        for f in cache_path.glob(f\"{entry['id']}.*\"):
            f.unlink()
            removed += 1
    else:
        kept_entries.append(entry)

cache['entries'] = kept_entries
with open('files/index.json', 'w') as f:
    json.dump(db, f, indent=2)
print(f'Removed {removed} expired cache files')
print(f'Kept {len(kept_entries)} valid entries')
"
```

### Nuclear Option (Reset Cache)

```bash
# When cache is completely corrupted:
rm -rf files/cache/*
touch files/cache/.gitkeep

# Reset cache entries in index.json
python3 -c "
import json
with open('files/index.json') as f:
    db = json.load(f)
db['collections']['cache']['entries'] = []
with open('files/index.json', 'w') as f:
    json.dump(db, f, indent=2)
print('✅ Cache reset')
"
```

---

## 5. Export Debugging

### Check Export Completeness

```python
"""Verify exports have expected vertex/face counts."""
import json
from pathlib import Path

with open("files/index.json") as f:
    db = json.load(f)

exports = db["collections"]["exports"]
base = Path(exports["path"])

for entry in exports.get("entries", []):
    name = entry.get("name", "unknown")
    file_path = base / name
    
    if not file_path.exists():
        print(f"  ❌ Missing export: {name}")
        continue
    
    # Check vertices/faces match if OBJ
    if file_path.suffix.lower() == ".obj":
        content = file_path.read_text()
        actual_v = content.count("\nv ")
        actual_f = content.count("\nf ")
        
        expected_v = entry.get("vertices")
        expected_f = entry.get("faces")
        
        if expected_v is not None and actual_v != expected_v:
            print(f"  ⚠️  {name}: vertex count mismatch (expected {expected_v}, got {actual_v})")
        if expected_f is not None and actual_f != expected_f:
            print(f"  ⚠️  {name}: face count mismatch (expected {expected_f}, got {actual_f})")
    
    # Check size
    if "size_bytes" in entry and entry["size_bytes"] > 0:
        actual_size = file_path.stat().st_size
        diff_pct = abs(actual_size - entry["size_bytes"]) / entry["size_bytes"]
        if diff_pct > 0.2:
            print(f"  ⚠️  {name}: large size difference ({diff_pct:.0%})")

print("✅ Export check complete")
```

### Trace Export to Source

```python
"""For each export, show which assets it came from."""
import json

with open("files/index.json") as f:
    db = json.load(f)

assets_by_id = {a["id"]: a.get("name", a["id"]) for a in db["collections"]["assets"].get("entries", [])}

for export in db["collections"]["exports"].get("entries", []):
    name = export.get("name", export.get("id", "unknown"))
    sources = export.get("source_assets", [])
    
    if not sources:
        print(f"  {name} ← [no source recorded]")
        continue
    
    print(f"  {name} ←")
    for src_id in sources:
        src_name = assets_by_id.get(src_id, src_id)
        print(f"    └─ {src_name}")
```

---

## 6. Full Health Check

```bash
"""
Run from project root for a complete files database health report.
"""
python3 -c '
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

INDEX = Path("files/index.json")

print("=" * 50)
print("FILES DATABASE HEALTH CHECK")
print("=" * 50)

# 1. Can we parse it?
try:
    with open(INDEX) as f:
        db = json.load(f)
    print(f"\n✅ index.json: valid JSON ({db.get(\"version\", \"unknown\")})")
except json.JSONDecodeError as e:
    print(f"\n❌ index.json: INVALID JSON — {e}")
    sys.exit(1)
except FileNotFoundError:
    print(f"\n❌ index.json: NOT FOUND")
    sys.exit(1)

# 2. Check collections
collections = db.get("collections", {})
for name, col in collections.items():
    entries = len(col.get("entries", []))
    base_path = Path(col["path"])
    files_on_disk = sum(1 for f in base_path.glob("*") if f.name != ".gitkeep")
    status = "✅" if entries <= files_on_disk + 1 else "⚠️"
    print(f"\n{status} {name}: {entries} indexed, {files_on_disk} files on disk")

# 3. Missing files
missing = 0
for col_name, col in collections.items():
    base = Path(col["path"])
    for entry in col.get("entries", []):
        name = entry.get("name")
        if name and not (base / name).exists():
            print(f"  ❌ MISSING: {col_name}/{name}")
            missing += 1

if missing == 0:
    print("\n✅ All indexed files present on disk")
else:
    print(f"\n❌ {missing} missing files")

# 4. Orphaned files (on disk, not in index)
orphaned = 0
for col_name, col in collections.items():
    base = Path(col["path"])
    indexed = {e.get("name") for e in col.get("entries", []) if e.get("name")}
    for f in base.glob("*"):
        if f.name.endswith(".gitkeep"):
            continue
        if f.is_file() and f.name not in indexed:
            print(f"  ⚠️  ORPHAN: {col_name}/{f.name} (on disk, not indexed)")
            orphaned += 1

if orphaned == 0:
    print("✅ No orphaned files")
else:
    print(f"\n⚠️  {orphaned} orphaned files")

# 5. Size summary
for col_name, col in collections.items():
    base = Path(col["path"])
    total = sum(f.stat().st_size for f in base.rglob("*") if f.is_file())
    print(f"\n📦 {col_name}: {total / 1024 / 1024:.1f} MB")

print("\n" + "=" * 50)
print("HEALTH CHECK COMPLETE")
print("=" * 50)
'
```

---

## Common Issues & Quick Fixes

| Symptom | Quick Fix |
|---------|-----------|
| `index.json` is blank or corrupted | Restore from backup: `cp files/index.json.bak files/index.json` |
| File added to `assets/` but `etu-demo` can't find it | Add entry to `index.json` (see Section 1) |
| Cache files taking too much space | Run nuclear option (Section 4) |
| Export says 0 vertices | Check source asset is valid; re-run pipeline |
| Duplicate IDs in index | Run duplicate ID checker (Section 1) |
| `Permission denied` on exports | `chmod 755 files/exports/` |
| Git shows huge diff in `index.json` | `git diff --stat files/index.json` to check; consider `.gitattributes` for merge strategy |

## Prevention Checklist

After every pipeline run:
1. ✅ Export was written to `files/exports/`
2. ✅ Entry was added to `index.json` under `exports`
3. ✅ Source asset IDs are recorded in `source_assets`
4. ✅ Vertex/face counts are populated
5. ✅ File size is recorded
6. ✅ Timestamp is set
