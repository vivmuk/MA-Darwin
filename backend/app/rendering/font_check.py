"""Startup font presence checks (PRD §7.5 / Prompt 3)."""

from __future__ import annotations

from pathlib import Path


def load_required_fonts(fonts_config: Path | str | None = None) -> list[str]:
    """Load the required font family names from ``config/fonts.yaml``.

    Parameters
    ----------
    fonts_config:
        Optional explicit path; defaults to ``backend/config/fonts.yaml``.

    Returns
    -------
    list[str]
        Font family names that must be installed in the render environment.
    """
    raise NotImplementedError


def list_installed_fonts() -> list[str]:
    """Return font family names available on this host.

    Returns
    -------
    list[str]
        Installed family names (platform-specific discovery).
    """
    raise NotImplementedError


def check_required_fonts(fonts_config: Path | str | None = None) -> None:
    """Verify every font named in ``fonts.yaml`` is installed.

    Raises loudly on missing fonts — do not degrade silently.

    Parameters
    ----------
    fonts_config:
        Optional explicit path to ``fonts.yaml``.

    Raises
    ------
    RuntimeError
        If one or more required fonts are missing.
    """
    raise NotImplementedError
