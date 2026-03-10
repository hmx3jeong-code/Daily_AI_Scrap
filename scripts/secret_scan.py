#!/usr/bin/env python3
"""Lightweight secret scanner for pre-commit."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]


ROOT = pathlib.Path.cwd()

IGNORED_DIRS = {
    ".git",
    ".venv",
    ".venv2",
    ".venv_new",
    "__pycache__",
    "node_modules",
}

IGNORED_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".7z",
    ".dll",
    ".exe",
    ".so",
    ".dylib",
    ".mp3",
    ".mp4",
    ".mov",
    ".avi",
}

PLACEHOLDER_HINTS = (
    "your_",
    "replace_",
    "example",
    "sample",
    "dummy",
    "test",
    "changeme",
    "xxxxx",
    "todo",
    "none",
)

RULES = [
    Rule(
        name="google_api_key",
        pattern=re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    ),
    Rule(
        name="openai_key",
        pattern=re.compile(r"sk-[A-Za-z0-9]{20,}"),
    ),
    Rule(
        name="anthropic_key",
        pattern=re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}"),
    ),
    Rule(
        name="github_pat",
        pattern=re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    ),
    Rule(
        name="github_token",
        pattern=re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    ),
    Rule(
        name="aws_access_key_id",
        pattern=re.compile(r"AKIA[0-9A-Z]{16}"),
    ),
    Rule(
        name="slack_token",
        pattern=re.compile(r"xox[baprs]-[0-9A-Za-z\-]{10,}"),
    ),
    Rule(
        name="generic_key_assignment",
        pattern=re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|access[_-]?key)\b"
            r"\s*[:=]\s*[\"']([^\n\"']{10,})[\"']"
        ),
    ),
]


def should_ignore(path: pathlib.Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    if any(d.lower() in lowered_parts for d in IGNORED_DIRS):
        return True
    if path.suffix.lower() in IGNORED_EXTS:
        return True
    return False


def is_placeholder(value: str) -> bool:
    cleaned = value.strip().strip("'\"").lower()
    if not cleaned:
        return True
    if cleaned in {"null", "none", "true", "false"}:
        return True
    return any(hint in cleaned for hint in PLACEHOLDER_HINTS)


def iter_files(paths: list[str]) -> Iterable[pathlib.Path]:
    if paths:
        for raw in paths:
            path = pathlib.Path(raw)
            if not path.exists() or path.is_dir():
                continue
            if should_ignore(path):
                continue
            yield path
        return

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if should_ignore(path):
            continue
        yield path


def read_lines(path: pathlib.Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            return []
    except OSError:
        return []


def scan_file(path: pathlib.Path) -> list[tuple[int, str, str]]:
    findings: list[tuple[int, str, str]] = []
    for line_no, line in enumerate(read_lines(path), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for rule in RULES:
            for match in rule.pattern.finditer(line):
                # Generic assignment captures the candidate value in group(1).
                value = match.group(1) if rule.name == "generic_key_assignment" else match.group(0)
                if is_placeholder(value):
                    continue
                findings.append((line_no, rule.name, value[:6] + "***"))
    return findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan files for potential secrets.")
    parser.add_argument("files", nargs="*", help="Optional file list. If omitted, scans repository files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_files = list(iter_files(args.files))
    if not target_files:
        print("[secret-scan] No files to scan.")
        return 0

    total_findings = 0
    for path in target_files:
        findings = scan_file(path)
        if not findings:
            continue
        total_findings += len(findings)
        for line_no, rule_name, masked in findings:
            print(f"[secret-scan] {path}:{line_no} {rule_name} ({masked})")

    if total_findings:
        print(f"[secret-scan] Found {total_findings} potential secret(s).")
        return 1

    print(f"[secret-scan] OK ({len(target_files)} file(s) scanned, no secrets found).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
