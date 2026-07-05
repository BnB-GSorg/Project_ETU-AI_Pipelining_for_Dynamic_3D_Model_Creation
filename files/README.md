# ETU Files Database

This directory serves as a **database-like file organization system** for the ETU project. It provides structured storage for assets, cached data, and exports.

## Structure

```
files/
├── index.json          # Database index and schema definitions
├── assets/             # Input assets (models, textures, point clouds)
├── cache/              # Cached intermediate results
└── exports/            # Generated outputs
```

## Collections

### 📁 Assets (`assets/`)
Input files for the pipeline:
- 3D models (`.obj`, `.ply`, `.fbx`)
- Textures (`.png`, `.jpg`, `.exr`)
- Point clouds (`.pcd`, `.xyz`, `.las`)
- Images (`.png`, `.jpg`)

### 📁 Cache (`cache/`)
Intermediate processing results:
- Preprocessed features
- Model embeddings
- Compiled shaders
- Temporary files

> ⚠️ Cache files can be safely deleted to free space. They will be regenerated when needed.

### 📁 Exports (`exports/`)
Generated output files:
- Generated 3D models
- Rendered images
- Export bundles

## Usage

### Python
```python
from etu_demo.files import FilesDB

db = FilesDB("../files")

# Add an asset
asset_id = db.assets.add("input.png", tags=["sample"])

# Get cached data
features = db.cache.get(asset_id, type="features")

# List exports
for export in db.exports.list(format="obj"):
    print(export.name, export.vertices)
```

### C++
```cpp
#include <etu/files_db.hpp>

etu::FilesDB db("../files");

// Add asset
auto id = db.assets().add("input.png", {"sample"});

// Query exports
for (const auto& exp : db.exports().list()) {
    std::cout << exp.name << ": " << exp.vertices << " verts\n";
}
```

## Index Schema

The `index.json` file defines:
- **Collections**: Named groups of related files
- **Schemas**: Structure for each collection's entries
- **Tags**: Global tags for organization
- **Metadata**: Project-level metadata

### Adding Entries

Entries can be added manually to `index.json` or programmatically through the API. Each entry requires:
- `id`: Unique identifier (UUID or custom)
- Collection-specific fields as defined in the schema

## Best Practices

1. **Use descriptive IDs**: `input_suzanne_highres` > `file001`
2. **Tag everything**: Makes filtering and searching easier
3. **Clean cache regularly**: Run `etu-clean-cache` or delete `cache/` contents
4. **Back up exports**: These are your valuable outputs
5. **Don't commit large files**: Use `.gitignore` for binaries
