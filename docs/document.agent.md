# Documentation Module - Agent Instructions

This directory contains all **documentation** for the ETU project, organized into wiki pages and research materials.

## Directory Structure

```
docs/
├── wiki/               # Wiki-style documentation pages
│   └── (markdown files)
└── materials/          # Research materials, papers, figures
    └── (papers, slides, figures)
```

## Wiki (`wiki/`)

Wiki documentation should follow this structure:

### Suggested Pages

| Page | Description |
|------|-------------|
| `Home.md` | Landing page, overview |
| `Getting-Started.md` | Quick start guide |
| `Installation.md` | Detailed installation |
| `API-Reference.md` | API documentation |
| `Architecture.md` | System architecture |
| `Pipeline-Stages.md` | Pipeline documentation |
| `GPU-Acceleration.md` | GPU setup and usage |
| `Troubleshooting.md` | Common issues |
| `FAQ.md` | Frequently asked questions |
| `Contributing.md` | Contribution guidelines |
| `Changelog.md` | Version history |

### Wiki Page Template

```markdown
# Page Title

Brief description of this page.

## Overview

[Main content]

## Subsection

[More content]

## See Also

- [Related Page](Related-Page.md)
- [Another Page](Another-Page.md)
```

## Materials (`materials/`)

Research and presentation materials:

### Organization

```
materials/
├── papers/             # Research papers
│   ├── main-paper.pdf
│   └── references/
├── slides/             # Presentations
│   ├── conference-talk.pptx
│   └── lab-meeting.pdf
├── figures/            # Diagrams and figures
│   ├── architecture.png
│   ├── pipeline-flow.svg
│   └── results/
├── data/               # Benchmark data, tables
└── media/              # Demo videos, screenshots
```

### Naming Conventions

- Papers: `author-year-title.pdf` or `venue-year-title.pdf`
- Slides: `event-date-title.pptx`
- Figures: `descriptive-name.{png,svg,pdf}`
- Use lowercase with hyphens

## Documentation Guidelines

### Writing Style

1. **Clear and concise** - Get to the point
2. **Active voice** - "The pipeline processes..." not "The data is processed by..."
3. **Present tense** - For describing current behavior
4. **Code examples** - Include working examples
5. **Screenshots** - Show UI when relevant

### Code Examples

Always use proper code blocks with language:

````markdown
```python
from etu_demo import Pipeline

pipeline = Pipeline()
model = pipeline.process("input.png")
```
````

### Cross-References

Link to other documentation:
- Wiki pages: `[Page Name](Page-Name.md)`
- Source code: Link to GitHub or use code references
- Materials: `[Paper](../materials/papers/name.pdf)`

## For AI Agents

When updating documentation:

1. **Check accuracy** - Verify code examples work
2. **Update versions** - Keep version numbers current
3. **Add examples** - Include practical usage examples
4. **Link related** - Cross-reference related pages
5. **Date changes** - Note when pages were last updated

## Building Documentation

If using a documentation generator (MkDocs, Sphinx, etc.):

```bash
# Install tools
pip install mkdocs mkdocs-material

# Serve locally
mkdocs serve

# Build static site
mkdocs build
```

## Assets for Documentation

Store documentation assets in `materials/figures/`:

- Diagrams: SVG preferred (scalable)
- Screenshots: PNG (lossless)
- Photos: JPEG (compressed)
- Animations: GIF or WebM

## Changelog Format

Follow Keep a Changelog format:

```markdown
## [Unreleased]
### Added
- New feature X

### Changed
- Updated behavior of Y

### Fixed
- Bug in Z

## [0.1.0] - 2024-01-01
### Added
- Initial release
```
