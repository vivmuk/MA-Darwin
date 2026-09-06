"""Startup font presence checks (PRD §7.5 / Prompt 3)."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from app.paths import CONFIG_DIR

_FONT_SUFFIXES = {".ttf", ".otf", ".ttc", ".otc"}


def load_required_fonts(fonts_config: Path | str | None = None) -> list[str]:
    """Load the required font family names from ``config/fonts.yaml``."""
    cfg_path = Path(fonts_config) if fonts_config is not None else CONFIG_DIR / "fonts.yaml"
    with cfg_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"fonts config must be a mapping: {cfg_path}")
    names = data.get("required_fonts") or []
    if not isinstance(names, list) or not names:
        raise ValueError(f"fonts config has no required_fonts: {cfg_path}")
    return [str(n).strip() for n in names if str(n).strip()]


def _search_paths(fonts_config: Path | str | None = None) -> list[Path]:
    defaults = [
        Path("C:/Windows/Fonts"),
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        Path.home() / ".fonts",
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts"),
        Path.home() / "Library/Fonts",
    ]
    cfg_path = Path(fonts_config) if fonts_config is not None else CONFIG_DIR / "fonts.yaml"
    extra: list[Path] = []
    if cfg_path.is_file():
        with cfg_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        for raw in data.get("search_paths") or []:
            extra.append(Path(str(raw)))
    seen: set[Path] = set()
    out: list[Path] = []
    for path in extra + defaults:
        resolved = path.expanduser()
        if resolved in seen or not resolved.is_dir():
            continue
        seen.add(resolved)
        out.append(resolved)
    return out


def _family_from_filename(path: Path) -> str:
    stem = path.stem
    # Windows files like arialbd / calibrib / timesbd.
    for suffix in ("bd", "bi", "i", "z", "b"):
        if len(stem) > 4 and stem.lower().endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem.replace("_", " ").strip()


def _read_u16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big")


def _read_u32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def _ttf_family_from_offset(data: bytes, offset: int) -> list[str]:
    if offset + 12 > len(data):
        return []
    num_tables = _read_u16(data, offset + 4)
    records = offset + 12
    name_off = name_len = None
    for i in range(num_tables):
        rec = records + i * 16
        if rec + 16 > len(data):
            break
        tag = data[rec : rec + 4]
        if tag == b"name":
            name_off = _read_u32(data, rec + 8)
            name_len = _read_u32(data, rec + 12)
            break
    if name_off is None or name_len is None:
        return []
    table = data[name_off : name_off + name_len]
    if len(table) < 6:
        return []
    count = _read_u16(table, 2)
    string_off = _read_u16(table, 4)
    names: list[str] = []
    for i in range(count):
        rec = 6 + i * 12
        if rec + 12 > len(table):
            break
        platform = _read_u16(table, rec)
        name_id = _read_u16(table, rec + 6)
        length = _read_u16(table, rec + 8)
        soff = _read_u16(table, rec + 10)
        if name_id not in (1, 4, 16):  # family, full, typographic family
            continue
        start = string_off + soff
        raw = table[start : start + length]
        try:
            text = raw.decode("utf-16-be" if platform in (0, 3) else "latin-1")
        except UnicodeDecodeError:
            continue
        text = text.strip()
        if text:
            names.append(text)
    return names


def _families_from_font_file(path: Path) -> list[str]:
    try:
        data = path.read_bytes()
    except OSError:
        return [_family_from_filename(path)]
    names: list[str] = []
    if data[:4] == b"ttcf":
        if len(data) >= 12:
            num_fonts = _read_u32(data, 8)
            for i in range(min(num_fonts, 16)):
                off_pos = 12 + i * 4
                if off_pos + 4 > len(data):
                    break
                names.extend(_ttf_family_from_offset(data, _read_u32(data, off_pos)))
    elif data[:4] in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
        names.extend(_ttf_family_from_offset(data, 0))
    names.append(_family_from_filename(path))
    return names


def _list_fonts_windows_registry() -> list[str]:
    if sys.platform != "win32":
        return []
    try:
        import winreg
    except ImportError:
        return []
    names: list[str] = []
    for hive, sub in (
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
    ):
        try:
            key = winreg.OpenKey(hive, sub)
        except OSError:
            continue
        try:
            i = 0
            while True:
                try:
                    value_name, _, _ = winreg.EnumValue(key, i)
                except OSError:
                    break
                i += 1
                family = value_name.split("(")[0].strip()
                if family:
                    names.append(family)
        finally:
            key.Close()
    return names


def list_installed_fonts() -> list[str]:
    """Return font family names available on this host."""
    names: set[str] = set()
    for raw in _list_fonts_windows_registry():
        names.add(raw)
        names.add(raw.lower())
    for directory in _search_paths():
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in _FONT_SUFFIXES:
                continue
            for family in _families_from_font_file(path):
                names.add(family)
                names.add(family.lower())
    # Preserve original-case entries plus lowercase keys for matching.
    return sorted({n for n in names if n and n != n.lower()} | {n for n in names if n == n.lower()})


def _is_installed(required: str, installed: list[str]) -> bool:
    target = required.strip().lower()
    installed_lower = {name.lower() for name in installed}
    if target in installed_lower:
        return True
    # "Arial" matches "Arial Black" only as a prefix-with-space? Require exact
    # family or "Family (TrueType)" already stripped. Also accept startswith
    # when the next char is missing (exact) — already handled.
    for name in installed_lower:
        if name == target or name.startswith(target + " "):
            return True
    return False


def check_required_fonts(fonts_config: Path | str | None = None) -> None:
    """Verify every font named in ``fonts.yaml`` is installed.

    Raises loudly on missing fonts — do not degrade silently.
    """
    required = load_required_fonts(fonts_config)
    installed = list_installed_fonts()
    missing = [name for name in required if not _is_installed(name, installed)]
    if missing:
        searched = ", ".join(str(p) for p in _search_paths(fonts_config)) or "(no font directories found)"
        raise RuntimeError(
            "Required render fonts are missing and will not be substituted: "
            + ", ".join(missing)
            + f". Install them in the render environment. Searched: {searched}"
        )
