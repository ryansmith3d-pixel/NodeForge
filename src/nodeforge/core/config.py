import tomllib
from pathlib import Path

_DEFAULTS: dict = {
    "log_level": "INFO",
    "default_graph": "",
}


def load_config(path: Path | None = None) -> dict:
    """
    Load nodeforge.toml from the given path (or the project root by default).
    Falls back to defaults silently if the file is absent — never crashes on missing config.
    """
    if path is None:
        path = Path("nodeforge.toml")

    if not path.exists():
        return dict(_DEFAULTS)

    with open(path, "rb") as f:  # tomllib requires binary mode
        raw = tomllib.load(f)

    config = dict(_DEFAULTS)
    config.update(raw.get("nodeforge", {}))
    return config