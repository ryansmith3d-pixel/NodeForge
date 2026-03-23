# Phase 0 Summary — Environment & Tooling Lock-in

## What Was Built
A working Python project with a CLI entry point, installed as a real package, ready to grow.

## Environment
- OS: Windows
- Python: 3.13.12 (installed via `uv`)
- uv: 0.10.12
- Project location: `E:\projects\nodeforge`

## Project Structure
```
E:\projects\nodeforge
│   pyproject.toml
│   .python-version
│   README.md
│
└───src
    └───nodeforge
            __init__.py
            main.py
```

## Key Decisions
- **`src/nodeforge/` layout** — keeps the installable package separate from scripts and tests. Matters later when agents need to import it cleanly.
- **`uv` for everything** — dependency management, Python version management, running the package. Single tool, no Conda conflicts.
- **Typer for CLI** — clean command interface that will expand naturally as we add subcommands in Phase 1.
- **Editable install** (`-e .`) — changes to source are immediately reflected without reinstalling.

## Dependencies Installed
- `typer>=0.12.0` — CLI framework
- `rich`, `click`, `colorama` — pulled in automatically by Typer

## Files

### `pyproject.toml`
```toml
[project]
name = "nodeforge"
version = "0.1.0"
description = "Semantic graph system for VFX and AI workflows"
requires-python = ">=3.13"
dependencies = [
    "typer>=0.12.0",
]

[project.scripts]
nodeforge = "nodeforge.main:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/nodeforge"]
```

### `src/nodeforge/main.py`
```python
import typer

app = typer.Typer()


@app.command()
def hello():
    """NodeForge is alive."""
    typer.echo("NodeForge v0.1.0 — semantic graph system online.")


if __name__ == "__main__":
    app()
```

### `src/nodeforge/__init__.py`
```python
# empty
```

## Verified Working
```
uv run nodeforge
NodeForge v0.1.0 — semantic graph system online.
```

## Note on Typer Behavior
With a single command defined, Typer makes the app itself the command — `nodeforge` runs directly. Once we add multiple subcommands in Phase 1, the pattern becomes `nodeforge stats`, `nodeforge workflows`, etc. This is expected Typer behavior.

## Next: Phase 1
Produce structured JSON output instead of print statements. Add `stats` and `workflows` CLI commands. Establish the pattern of machine-readable output that both pipelines and AI agents can consume.
