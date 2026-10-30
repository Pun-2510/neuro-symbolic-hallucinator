"""Unit tests for automated SemVer 2.0.0 & Conventional Commits versioning."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "bump_version.py"
spec = importlib.util.spec_from_file_location("bump_version", SCRIPT_PATH)
assert spec and spec.loader
bump_version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bump_version)


def test_detect_bump_from_conventional_commits() -> None:
    # PATCH bumps
    assert bump_version.detect_bump_from_message("fix: resolve crash on empty PDF") == "patch"
    assert bump_version.detect_bump_from_message("fix(ui): align header badge") == "patch"
    assert bump_version.detect_bump_from_message("perf(landing): optimize 120fps scroll") == "patch"
    assert bump_version.detect_bump_from_message("refactor(api): simplify auth dependency") == "patch"

    # MINOR bumps
    assert bump_version.detect_bump_from_message("feat: add live citation sandbox") == "minor"
    assert bump_version.detect_bump_from_message("feat(pricing): unify PricingPage UI") == "minor"

    # MAJOR bumps (breaking changes)
    assert bump_version.detect_bump_from_message("feat!: drop legacy v1 API") == "major"
    assert bump_version.detect_bump_from_message("fix(auth)!: change token payload schema") == "major"
    assert (
        bump_version.detect_bump_from_message(
            "feat(api): overhaul report schema\n\nBREAKING CHANGE: report response format changed"
        )
        == "major"
    )

    # Non-bumping commits
    assert bump_version.detect_bump_from_message("chore: update dependencies") is None
    assert bump_version.detect_bump_from_message("docs(readme): update install guide") is None
    assert bump_version.detect_bump_from_message("test(unit): add parser tests") is None
    assert bump_version.detect_bump_from_message("ci: update github workflow") is None


def test_bump_semver_calculations() -> None:
    assert bump_version.bump_semver("3.1.18", "patch") == "3.1.19"
    assert bump_version.bump_semver("3.1.18", "minor") == "3.2.0"
    assert bump_version.bump_semver("3.1.18", "major") == "4.0.0"
