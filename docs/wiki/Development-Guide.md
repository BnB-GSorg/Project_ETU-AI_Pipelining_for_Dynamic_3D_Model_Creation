# Development Guide

Coding standards, workflows, and contribution practices for ETU.

---

## 1. Repository Layout

```
Project-ETU/
├── demo/          # Python demo (prototyping, research)
│   ├── AGENTS.md
│   └── .agents/skills/debug/
├── src/           # C++23 core (production)
│   └── AGENTS.md
├── docs/          # Documentation
│   ├── wiki/      # This page lives here
│   └── materials/ # Papers, slides, figures
└── files/         # Database-like asset storage
    ├── AGENTS.md
    └── .agents/skills/debug/
```

Each module (`demo/`, `src/`, `files/`) has its own `AGENTS.md` with module-specific conventions — read those before making changes in that module.

---

## 2. Coding Standards

### Python (`demo/`)

| Rule | Tool/Convention |
|------|------------------|
| Formatting | `black` (line length 100) |
| Linting | `ruff` (`E`, `W`, `F`, `I`, `B`, `C4`, `UP` rule sets) |
| Type hints | Required on all public functions; checked with `mypy` |
| Docstrings | Google-style, required on public API |
| Data containers | Use `@dataclass` |
| Arrays | Use `numpy`, not Python lists |
| Heavy imports | Import `torch`/`trimesh`/`open3d` lazily inside functions |

Run before committing:
```bash
cd demo
black src/ tests/
ruff check src/ tests/
mypy src/
pytest
```

### C++ (`src/`)

| Rule | Convention |
|------|------------|
| Standard | C++23 required — use `std::expected`, `std::span`, concepts |
| Memory | RAII everywhere; smart pointers over raw `new`/`delete` |
| Errors | `std::expected<T, Error>` — avoid exceptions in hot paths |
| Attributes | `[[nodiscard]]` on value-returning functions, `noexcept` where applicable |
| ABI stability | Pimpl pattern for public classes |
| Naming | `PascalCase` classes, `snake_case` functions/variables, `SCREAMING_SNAKE_CASE` or `kPascalCase` constants |
| Files | `snake_case.hpp` / `snake_case.cpp`, tests as `test_*.cpp` |

Run before committing:
```bash
cd src
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
```

### Editor Config

`.editorconfig` at the repo root enforces indentation and charset consistently — make sure your editor respects it (most do automatically).

---

## 3. Git Workflow

### Branching

- `main` — stable, always buildable
- Feature branches: `feature/<short-description>`
- Fix branches: `fix/<short-description>`

### Commit Messages

Prefer [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(demo): add point cloud loader for .pcd files
fix(src): correct normal calculation in marching cubes postprocess
docs(wiki): add compile guide for Windows
test(demo): add coverage for quality scaling
```

### Pull Requests

1. Ensure tests pass for any module you touched (`pytest` and/or `ctest`).
2. Keep changes scoped — don't mix `demo/` and `src/` changes unless the feature spans both.
3. Update relevant `AGENTS.md` if you introduce new conventions.
4. Update [Reference](Reference.md) if you add/change public API.

---

## 4. Adding a New Feature

### To the Python Demo

1. Implement in `demo/src/etu_demo/<module>.py`.
2. Add type hints + docstrings.
3. Add unit tests in `demo/tests/`.
4. Run `pytest`, `ruff`, `mypy`.
5. Update `demo/README.md` and [Reference](Reference.md) if public API changed.

### To the C++ Core

1. Declare the interface in `src/include/etu/<module>.hpp`.
2. Implement in `src/src/<module>.cpp`.
3. Add test cases in `src/tests/test_main.cpp` (or a new test file registered in `CMakeLists.txt`).
4. Rebuild and run `ctest`.
5. Update [Reference](Reference.md) and `src/AGENTS.md` if conventions changed.

### Adding a New Rendering Backend

See `src/AGENTS.md` § "Adding New Renderer Backend" — in short:
1. Create a class inheriting `IRenderer`.
2. Implement all virtual methods.
3. Register in `create_renderer()` factory (`src/src/renderer.cpp`).
4. Add CMake detection logic in `src/CMakeLists.txt`.
5. Update `get_available_backends()`.

### Adding a New Pipeline Stage

Applies to both Python and C++ pipelines:
1. Add the stage to the `PipelineStage` enum.
2. Implement stage logic in the pipeline's execute method.
3. Report progress at the start and end of the stage.
4. Support cancellation (`cancel_requested` check in C++, similar pattern in Python).
5. Add a test covering the new stage.

---

## 5. Testing Philosophy

- **Unit tests are mandatory** for new public functions/classes.
- **Integration tests**: prefer running the full pipeline (`process()` / `process_array()`) with dummy input over mocking internals.
- **Determinism**: seed random generators (`np.random.seed(42)` pattern already used in `pipeline.py`) so tests are reproducible.
- **GPU tests**: must gracefully skip or fall back to CPU if no GPU is present (see `PipelineConfig(use_gpu=False)` pattern).

---

## 6. Debugging

Use the project's built-in debugging skills instead of ad-hoc troubleshooting:

- `demo/.agents/skills/debug/SKILL.md` — Python debugging (pytest, pdb, profiling, GPU/torch, data validation)
- `files/.agents/skills/debug/SKILL.md` — Files database debugging (index validation, integrity checks, cache cleanup)

These are automatically available to AI agents working in this repo, and can also be read manually as a troubleshooting reference.

---

## 7. Documentation Standards

When updating docs in `docs/wiki/`:

1. Use clear, present-tense, active-voice writing.
2. Include working code examples — verify they run before committing.
3. Cross-link related pages (`[Page Name](Page-Name.md)`).
4. Update the [Home](Home.md) index if you add a new page.

---

## 8. Release Checklist

Before tagging a release:

- [ ] `pytest` passes in `demo/`
- [ ] `ctest` passes in `src/build/`
- [ ] `ruff check` and `mypy` clean in `demo/`
- [ ] No compiler warnings introduced in `src/` (check `cmake --build build` output)
- [ ] [Reference](Reference.md) reflects current public API
- [ ] Version bumped in `demo/pyproject.toml` (`project.version`) and `src/CMakeLists.txt` (`project(ETU VERSION ...)`)
- [ ] Changelog updated (see `docs/AGENTS.md` § Changelog Format)
