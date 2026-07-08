# Files Database Module - Agent Instructions

This directory serves as a **database-like file organization system** for managing project assets, cached data, and generated outputs.

## Directory Structure

```
files/
├── index.json          # Database index (schema + entries)
├── assets/             # Input files (models, textures, images)
├── cache/              # Intermediate results (safe to delete)
└── exports/            # Generated outputs
```

## Collections

### 📁 `assets/`
**Purpose:** Store input files for the pipeline.

Supported formats:
- 3D Models: `.obj`, `.ply`, `.fbx`, `.gltf`, `.glb`
- Textures: `.png`, `.jpg`, `.jpeg`, `.exr`, `.hdr`
- Point Clouds: `.pcd`, `.xyz`, `.las`, `.laz`
- Images: `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`

### 📁 `cache/`
**Purpose:** Store intermediate processing results.

Contents:
- Preprocessed features
- Model embeddings
- Compiled shaders
- Temporary processing files

> ⚠️ **Safe to delete** - Cache regenerates automatically.

### 📁 `exports/`
**Purpose:** Store generated output files.

Formats:
- `.obj` - Wavefront OBJ (universal)
- `.ply` - Stanford PLY (with colors)
- `.stl` - STL (3D printing)
- `.gltf`/`.glb` - glTF (web, modern)

## index.json Schema

```json
{
  "version": "1.0.0",
  "collections": {
    "assets": {
      "path": "assets/",
      "entries": [
        {
          "id": "unique-id",
          "name": "file.obj",
          "type": "model",
          "tags": ["sample"],
          "metadata": {}
        }
      ]
    }
  }
}
```

### Entry Types

| Collection | Types |
|------------|-------|
| assets | `model`, `texture`, `pointcloud`, `image`, `other` |
| cache | `features`, `embeddings`, `intermediate`, `compiled` |
| exports | By format: `obj`, `ply`, `stl`, `gltf`, `glb`, `fbx` |

## Working with Files

### Adding an Asset

1. Copy file to `assets/`
2. Add entry to `index.json`:

```json
{
  "id": "suzanne-highres",
  "name": "suzanne.obj",
  "type": "model",
  "format": "obj",
  "size_bytes": 1234567,
  "created": "2024-01-01T00:00:00Z",
  "tags": ["test", "monkey"]
}
```

### Finding Files

Query by tag:
```python
db.assets.find(tags=["test"])
```

Query by type:
```python
db.exports.find(format="obj")
```

### Managing Cache

Clear all cache:
```bash
rm -rf files/cache/*
```

Clear old entries:
```python
db.cache.clear(older_than=days(7))
```

## Naming Conventions

### Assets
- Descriptive: `suzanne-highres.obj` ✓
- Numbered: `test-001.obj` ✗

### Exports
- Include source: `suzanne-generated.obj`
- Include timestamp: `output-20240101-120000.obj`
- Include config: `output-q0.8-gpu.obj`

### IDs
- Use UUIDs: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
- Or descriptive: `suzanne-highres-v1`

## Git Considerations

### .gitignore Recommendations

```gitignore
# Large binary files
files/assets/*.obj
files/assets/*.fbx
files/exports/*

# Cache (always ignore)
files/cache/*
!files/cache/.gitkeep

# Keep index
!files/index.json
```

### Git LFS

For large files, consider Git LFS:
```bash
git lfs track "files/assets/*.obj"
git lfs track "files/exports/*.ply"
```

## For AI Agents

### When Adding Files

1. Generate unique ID
2. Calculate file size
3. Detect file type/format
4. Add timestamp
5. Update `index.json`
6. Verify file exists

### When Cleaning

1. Check dependencies before deleting
2. Update `index.json` after removal
3. Leave `.gitkeep` files
4. Cache is safe to delete
5. Exports may be valuable

### Index Validation

Verify `index.json` integrity:
- All paths exist
- IDs are unique
- Schema matches
- Dates are ISO 8601

## File Size Guidelines

| Collection | Recommended Max |
|------------|-----------------|
| Individual asset | 100 MB |
| Total assets | 1 GB |
| Individual cache | 500 MB |
| Total cache | 5 GB |
| Individual export | 50 MB |
| Total exports | 500 MB |

Monitor with:
```bash
du -sh files/*/
```
