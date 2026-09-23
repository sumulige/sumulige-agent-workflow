"""Deterministic distribution contents; project facts are locally owned."""
from __future__ import annotations

import json
from pathlib import Path

from check_bundle import CONFIG_PATH, CORE_FILES, DEFAULT_CONFIG, local_path, validate_bundle

VERSION = "2.3.0-dev"
PROFILES = ("core", "web", "registry")
PROJECT_DOCS = {
    "core": ("README.md", "CHANGELOG.md", "TODO.md", "docs/PROJECT-SPEC.md",
             "docs/ARCHITECTURE.md", "docs/DEVELOPMENT.md", "docs/TESTING.md", ".agent/project-rules.md"),
    "web": ("DESIGN.md", "docs/PAGE-STRUCTURE.md", "docs/DEPLOYMENT.md"),
    "registry": ("docs/COMPONENT-GUIDELINES.md", "docs/REGISTRY.md"),
}


def distribution(source: Path, profile: str) -> dict[str, tuple[bytes, str]]:
    if profile not in PROFILES:
        raise ValueError("Unknown profile")
    if validate_bundle(source)["fail"]:
        raise ValueError("Source bundle failed validation")
    result = {p: (local_path(source, p).read_bytes(), "managed") for p in CORE_FILES}
    result[CONFIG_PATH] = ((json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2) + "\n").encode(), "local")
    result["GEMINI.md"] = (b"# Shared project workflow\n\n@AGENTS.md\n", "managed")
    for path in ("validation/tasks.py", "validation/task_contract.py", "validation/storage.py", "docs/agent/maintenance.md"):
        result[path] = (local_path(source, path).read_bytes(), "managed")
    for name in PROFILES[:PROFILES.index(profile) + 1]:
        for relative in PROJECT_DOCS[name]:
            result[relative] = (local_path(source, "templates/" + name + "/" + relative).read_bytes(), "local")
    for relative, (content, _) in result.items():
        if not content.decode("utf-8").strip():
            raise ValueError(f"Empty distribution file: {relative}")
    return result
