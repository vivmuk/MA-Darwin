"""Gate 1 — content & compliance checks (PRD §7.6 / Prompt 4)."""

from __future__ import annotations

from pathlib import Path

from app.models.claim import ClaimLedger
from app.models.common import CheckLocation
from app.models.gates import Gate1Result, GateCheckResult
from app.models.numbers import NumbersIndex
from app.models.slide import SlideMap


def check_claim_mapping(slide_map: SlideMap) -> GateCheckResult:
    """Every text run in ``slide_map`` must have ≥ 1 claim_id."""
    raise NotImplementedError


def check_number_sweep(
    pptx_path: Path | str,
    numbers_index: NumbersIndex,
    *,
    relative_tolerance: float,
    absolute_tolerance: float,
) -> GateCheckResult:
    """Every numeral in the deck must exist in ``numbers_index`` (with tolerances).

    Derived numbers are flagged (``flagged=True``), not failed.
    """
    raise NotImplementedError


def check_endpoint_labelling(slide_map: SlideMap, ledger: ClaimLedger) -> GateCheckResult:
    """Secondary / exploratory / post-hoc claims must be labelled in slide text."""
    raise NotImplementedError


def check_fair_balance(slide_map: SlideMap, blueprint_roles: list[str]) -> GateCheckResult:
    """Safety and limitations roles must be present and non-empty."""
    raise NotImplementedError


def check_comparative_claims(slide_map: SlideMap, ledger: ClaimLedger) -> GateCheckResult:
    """Comparative language requires a supporting head-to-head primary_endpoint claim."""
    raise NotImplementedError


def check_promotional_language(
    slide_map: SlideMap,
    blocklist: list[str],
) -> GateCheckResult:
    """Fail if any promotional blocklist term appears in deck text."""
    raise NotImplementedError


def check_population_extrapolation(slide_map: SlideMap, ledger: ClaimLedger) -> GateCheckResult:
    """No claim may generalize beyond the ledger's stated population."""
    raise NotImplementedError


def check_references_complete(slide_map: SlideMap, ledger: ClaimLedger) -> GateCheckResult:
    """Reference slide present; every cited claim listed."""
    raise NotImplementedError


def check_synthesized_flags(slide_map: SlideMap, ledger: ClaimLedger) -> GateCheckResult:
    """Every ``synthesized`` claim is flagged for explicit human approval."""
    raise NotImplementedError


def run_gate1(
    *,
    pptx_path: Path | str,
    slide_map: SlideMap,
    ledger: ClaimLedger,
    numbers_index: NumbersIndex,
    compliance_config: Path | str | None = None,
    blueprint_roles: list[str] | None = None,
) -> Gate1Result:
    """Run all Gate 1 checks and write-compatible ``gate1.json`` payload.

    Deterministic only — no LLM calls. Any failure blocks Gate 2.

    Parameters
    ----------
    pptx_path:
        Generated deck.
    slide_map:
        Element → claim mapping.
    ledger:
        Source claim ledger.
    numbers_index:
        Ground-truth numbers index.
    compliance_config:
        Optional path to ``compliance.yaml``.
    blueprint_roles:
        Ordered slide roles for fair-balance checks.

    Returns
    -------
    Gate1Result
        Artifact suitable for ``gate1.json``.
    """
    raise NotImplementedError


def locations_for_element(slide: int, element_id: str, detail: str = "") -> list[CheckLocation]:
    """Helper signature for building element-level failure locations."""
    raise NotImplementedError
