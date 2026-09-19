#!/usr/bin/env python3
"""Create-only installation. Default: preview. No overwrite or force option.

Run in a trusted, quiescent directory. This is not a concurrent-write sandbox.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Keep preview read-only even when the caller omits Python's -B flag.
sys.dont_write_bytecode = True

from check_bundle import CONFIG_PATH, CORE_FILES, DEFAULT_CONFIG, local_path, validate_bundle


def plan_install(source: Path, target: Path) -> list[tuple[str, str, bytes]]:
    source, target = source.resolve(), target.resolve()
    if source == target or not target.is_dir():
        raise ValueError("Target must be an existing directory different from source")
    if validate_bundle(source)["fail"]:
        raise ValueError("Source bundle failed validation")
    plan: list[tuple[str, str, bytes]] = []
    for relative in CORE_FILES:
        data = local_path(source, relative).read_bytes()
        if relative == CONFIG_PATH:
            # Never transfer configured authority or project commands to another repo.
            data = (json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2) + "\n").encode()
        destination = local_path(target, relative)
        for parent in destination.parents:
            if parent == target:
                break
            if parent.exists() and not parent.is_dir():
                raise ValueError(f"Parent is not a directory: {relative}")
        if destination.exists():
            state = "SAME" if destination.is_file() and destination.read_bytes() == data else "CONFLICT"
        else:
            state = "CREATE"
        plan.append((relative, state, data))
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    created: list[str] = []
    try:
        plan = plan_install(args.source, args.target)
        for relative, state, _ in plan:
            print(f"{state}: {relative}")
        if any(state == "CONFLICT" for _, state, _ in plan):
            print("No files written. Resolve conflicts by reviewed manual merge.")
            return 1
        if not args.apply:
            print("PREVIEW ONLY: no files written. Review before using --apply.")
            return 0
        target = args.target.resolve()
        for relative, state, data in plan:
            if state != "CREATE":
                continue
            path = local_path(target, relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation refuses a file that appeared after the preview.
            with path.open("xb") as output:
                created.append(relative)
                output.write(data)
        print(f"Created {len(created)} files. No existing file was replaced.")
        return 0
    except (OSError, ValueError) as error:
        print(f"FAILED: {error}")
        if created:
            print("PARTIAL: inspect these newly created files before retrying:")
            print("\n".join(created))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
