# ETU Demo - Python Implementation

This is the **Python demo implementation** of the AI Pipelining system for Dynamic 3D Model Creation. It provides a reference implementation for rapid prototyping and experimentation.

> ⚠️ **Note:** This is a demonstration/research implementation. For production use, see the C++ implementation in `../src/`.

## Quick Start

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Or with development tools
pip install -e ".[dev]"

# Or with visualization
pip install -e ".[full]"
```

### Usage

```bash
# Run demo
etu-demo --help

# Process an input
etu-demo input.png -o output.obj

# Run with visualization
etu-demo input.png --visualize
```

### Python API

```python
from etu_demo import Pipeline, PipelineConfig

# Create pipeline
config = PipelineConfig(use_gpu=True, quality=0.8)
pipeline = Pipeline(config)

# Process input
model = pipeline.process("input.png")

# Export result
model.export("output.obj")
```

## Project Structure

```
demo/
├── pyproject.toml      # Project configuration
├── requirements.txt    # Dependencies
├── src/
│   └── etu_demo/       # Main package
│       ├── __init__.py
│       ├── main.py     # CLI entry point
│       ├── pipeline.py # Core pipeline
│       └── utils.py    # Utilities
└── tests/
    └── test_pipeline.py
```

## Development

```bash
# Run tests
pytest

# Format code
black src/ tests/
ruff check src/ tests/

# Type checking
mypy src/
```

## License

MIT License - See LICENSE file for details.
