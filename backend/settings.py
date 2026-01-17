from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .config import DATA_DIR, COUNCIL_MODELS, CHAIRMAN_MODEL, TITLE_MODEL


def get_settings_path() -> Path:
    """Primary settings path under the backend folder."""
    backend_dir = Path(__file__).resolve().parent
    backend_dir.mkdir(parents=True, exist_ok=True)
    return backend_dir / "settings.json"


def get_legacy_settings_path() -> Path:
    """Legacy settings path under DATA_DIR for backward compatibility."""
    data_dir = Path(DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "settings.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_mode_settings() -> Dict[str, Any]:
    """Default block for a single collaboration mode."""
    return {
        "council_models": [{"name": m} for m in COUNCIL_MODELS],
        "chairman_model": CHAIRMAN_MODEL,
        "title_model": TITLE_MODEL,
    }


def default_settings() -> Dict[str, Any]:
    """Default settings covering all collaboration modes.

    Modes supported: council, dxo, sequential, ensemble.
    For now, each mode inherits the same defaults; can diverge later.
    """
    return {
        "modes": {
            "council": _default_mode_settings(),
            "dxo": _default_mode_settings(),
            "sequential": _default_mode_settings(),
            "ensemble": _default_mode_settings(),
        },
        "default_mode": "council",
        "updated_at": _now_iso(),
    }


def load_settings() -> Dict[str, Any]:
    """Load settings from disk if present, else return defaults.

    This does not persist defaults to disk; callers can decide whether to save.
    """
    spath = get_settings_path()
    if not spath.exists():
        # Attempt legacy path migration
        legacy = get_legacy_settings_path()
        if legacy.exists():
            try:
                with legacy.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                # Save to new location for future writes
                save_settings(data)
                return data if isinstance(data, dict) else default_settings()
            except Exception:
                return default_settings()
        return default_settings()

    try:
        with spath.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Basic shape validation
        if not isinstance(data, dict):
            return default_settings()

        # Legacy shape migration: top-level council fields -> modes.council
        if "modes" not in data and (
            "council_models" in data
            or "chairman_model" in data
            or "title_model" in data
        ):
            council_block = {
                "council_models": data.get("council_models")
                or _default_mode_settings()["council_models"],
                "chairman_model": data.get("chairman_model") or CHAIRMAN_MODEL,
                "title_model": data.get("title_model") or TITLE_MODEL,
            }
            migrated = default_settings()
            migrated["modes"]["council"] = council_block
            migrated["updated_at"] = data.get("updated_at") or _now_iso()
            save_settings(migrated)
            return migrated

        return data
    except Exception:
        # On any error, use safe defaults
        return default_settings()


def save_settings(data: Dict[str, Any]) -> None:
    """Atomically write settings to disk."""
    spath = get_settings_path()
    tmp_path = spath.with_suffix(".json.tmp")
    data = dict(data)
    data["updated_at"] = _now_iso()
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(spath)


def _effective_mode_block(
    mode_data: Dict[str, Any], defaults: Dict[str, Any]
) -> Dict[str, Any]:
    """Compute effective settings for a single mode by merging defaults and filtering."""
    # Council models: ensure array of {name, system_prompt?}
    models: List[Dict[str, Any]] = []
    for item in mode_data.get("council_models") or []:
        if (
            isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and item["name"].strip()
        ):
            models.append(
                {k: v for k, v in item.items() if k in ("name", "system_prompt")}
            )
    if not models:
        models = (
            defaults.get("council_models") or _default_mode_settings()["council_models"]
        )

    # Chairman/title fallbacks
    chairman_model = (
        mode_data.get("chairman_model")
        or defaults.get("chairman_model")
        or CHAIRMAN_MODEL
    )
    if not isinstance(chairman_model, str) or not chairman_model.strip():
        chairman_model = CHAIRMAN_MODEL

    title_model = (
        mode_data.get("title_model") or defaults.get("title_model") or TITLE_MODEL
    )
    if not isinstance(title_model, str) or not title_model.strip():
        title_model = TITLE_MODEL

    return {
        "council_models": models,
        "chairman_model": chairman_model,
        "title_model": title_model,
    }


def get_all_settings_effective() -> Dict[str, Any]:
    """Return effective settings for all modes, plus legacy top-level compatibility fields.

    Includes:
    - modes: { council|dxo|sequential|ensemble: {...} }
    - default_mode
    - updated_at
    - legacy top-level: council_models, chairman_model, title_model (mirror council)
    """
    defaults = default_settings()
    current = load_settings()

    modes_current = current.get("modes") or {}
    modes_defaults = defaults.get("modes") or {}

    effective_modes: Dict[str, Any] = {}
    for key in ("council", "dxo", "sequential", "ensemble"):
        effective_modes[key] = _effective_mode_block(
            modes_current.get(key, {}), modes_defaults.get(key, {})
        )

    # Legacy top-level mirrors council for backwards compatibility
    council = effective_modes["council"]
    return {
        "modes": effective_modes,
        "default_mode": current.get("default_mode")
        or defaults.get("default_mode")
        or "council",
        "updated_at": current.get("updated_at") or defaults.get("updated_at"),
        # legacy top-level
        "council_models": council["council_models"],
        "chairman_model": council["chairman_model"],
        "title_model": council["title_model"],
    }


def get_effective_settings(mode: str = "council") -> Dict[str, Any]:
    """Return effective settings for a specific mode (default 'council')."""
    all_eff = get_all_settings_effective()
    if mode not in all_eff.get("modes", {}):
        mode = all_eff.get("default_mode") or "council"
    return all_eff["modes"][mode]
