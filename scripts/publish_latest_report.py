import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any


REPORT_JSON_RE = re.compile(r"^daily_ai_brief_(\d{4}-\d{2}-\d{2})\.json$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish latest daily AI report aliases for static UI."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("docs/data"),
        help="Directory containing daily_ai_brief_YYYY-MM-DD.{json,md}",
    )
    return parser.parse_args()


def list_reports(input_dir: Path) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    for file_path in input_dir.glob("daily_ai_brief_*.json"):
        match = REPORT_JSON_RE.match(file_path.name)
        if not match:
            continue
        report_date = match.group(1)
        found.append((report_date, file_path))
    found.sort(key=lambda x: x[0], reverse=True)
    return found


def build_index(reports: list[tuple[str, Path]]) -> list[dict[str, Any]]:
    index: list[dict[str, Any]] = []
    for report_date, json_path in reports:
        md_path = json_path.with_suffix(".md")
        article_count = None
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            article_count = data.get("article_count")
        except Exception:
            article_count = None
        index.append(
            {
                "date": report_date,
                "json": json_path.name,
                "md": md_path.name if md_path.exists() else None,
                "article_count": article_count,
            }
        )
    return index


def main() -> int:
    args = parse_args()
    input_dir = args.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)

    reports = list_reports(input_dir)
    if not reports:
        print(f"[WARN] No report JSON files found in {input_dir}")
        return 0

    latest_date, latest_json = reports[0]
    latest_md = latest_json.with_suffix(".md")
    latest_json_alias = input_dir / "latest.json"
    latest_md_alias = input_dir / "latest.md"
    index_path = input_dir / "index.json"

    shutil.copyfile(latest_json, latest_json_alias)
    if latest_md.exists():
        shutil.copyfile(latest_md, latest_md_alias)

    index_payload = {
        "latest_date": latest_date,
        "reports": build_index(reports),
    }
    index_path.write_text(
        json.dumps(index_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[INFO] latest.json -> {latest_json.name}")
    if latest_md.exists():
        print(f"[INFO] latest.md -> {latest_md.name}")
    print(f"[INFO] index.json updated ({len(reports)} report(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
