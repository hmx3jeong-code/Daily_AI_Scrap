import argparse
import json
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path


REPORT_JSON_RE = re.compile(r"^daily_ai_brief_(\d{4}-\d{2}-\d{2})\.json$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send the latest daily AI brief via SMTP email."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("docs/data"),
        help="Directory containing daily AI report files.",
    )
    parser.add_argument(
        "--report-date",
        type=str,
        default="",
        help="Optional report date (YYYY-MM-DD). If omitted, sends latest.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the message but do not send it.",
    )
    return parser.parse_args()


def split_recipients(raw: str) -> list[str]:
    if not raw:
        return []
    return [x.strip() for x in re.split(r"[,\n;]+", raw) if x.strip()]


def pick_report_json(input_dir: Path, report_date: str) -> Path:
    if report_date:
        target = input_dir / f"daily_ai_brief_{report_date}.json"
        if not target.exists():
            raise FileNotFoundError(f"Report JSON not found: {target}")
        return target

    latest_alias = input_dir / "latest.json"
    if latest_alias.exists():
        return latest_alias

    found: list[tuple[str, Path]] = []
    for file_path in input_dir.glob("daily_ai_brief_*.json"):
        match = REPORT_JSON_RE.match(file_path.name)
        if not match:
            continue
        found.append((match.group(1), file_path))
    if not found:
        raise FileNotFoundError(f"No daily report JSON files found in {input_dir}")
    found.sort(key=lambda x: x[0], reverse=True)
    return found[0][1]


def load_report_info(report_json_path: Path) -> dict:
    payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    report_date = payload.get("report_date") or "unknown-date"
    article_count = payload.get("article_count")
    return {
        "report_date": report_date,
        "article_count": article_count,
        "payload": payload,
    }


def pick_markdown_path(input_dir: Path, report_json_path: Path, report_date: str) -> Path | None:
    if report_json_path.name == "latest.json":
        latest_md = input_dir / "latest.md"
        return latest_md if latest_md.exists() else None

    md_path = report_json_path.with_suffix(".md")
    if md_path.exists():
        return md_path

    fallback = input_dir / f"daily_ai_brief_{report_date}.md"
    if fallback.exists():
        return fallback
    return None


def make_subject(report_date: str, article_count: int | None) -> str:
    if isinstance(article_count, int):
        return f"[Daily AI Brief] {report_date} (기사 {article_count}건)"
    return f"[Daily AI Brief] {report_date}"


def build_body(
    report_date: str,
    article_count: int | None,
    site_url: str,
    markdown_text: str,
) -> str:
    count_text = f"{article_count}건" if isinstance(article_count, int) else "N/A"
    lines = [
        f"일일 AI 브리프 ({report_date})",
        "",
        f"- 기사 수: {count_text}",
    ]
    if site_url:
        lines += [f"- 웹 보기: {site_url}", ""]
    else:
        lines += [""]
    lines += [
        "아래는 보고서 본문입니다.",
        "",
        markdown_text.strip(),
        "",
        "본 메일은 자동 발송되었습니다.",
    ]
    return "\n".join(lines)


def send_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_addr: str,
    to_addrs: list[str],
    subject: str,
    body_text: str,
    attachment_json: Path,
    attachment_md: Path | None,
    dry_run: bool,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg.set_content(body_text)

    json_bytes = attachment_json.read_bytes()
    msg.add_attachment(
        json_bytes,
        maintype="application",
        subtype="json",
        filename=attachment_json.name,
    )

    if attachment_md and attachment_md.exists():
        md_bytes = attachment_md.read_bytes()
        msg.add_attachment(
            md_bytes,
            maintype="text",
            subtype="markdown",
            filename=attachment_md.name,
        )

    if dry_run:
        print("[INFO] Dry-run mode. Email not sent.")
        print(f"[INFO] Subject: {subject}")
        print(f"[INFO] To: {msg['To']}")
        return

    if smtp_port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=30) as server:
            if smtp_user:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
    else:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            if smtp_user:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)

    print("[INFO] Email sent successfully.")


def main() -> int:
    args = parse_args()
    input_dir = args.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)

    smtp_host = os.getenv("EMAIL_SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587").strip() or "587")
    smtp_user = os.getenv("EMAIL_SMTP_USER", "").strip()
    smtp_password = os.getenv("EMAIL_SMTP_PASSWORD", "").strip()
    from_addr = os.getenv("EMAIL_FROM", "").strip() or smtp_user
    to_addrs = split_recipients(os.getenv("EMAIL_TO", "").strip())
    site_url = os.getenv("REPORT_SITE_URL", "").strip()

    required = {
        "EMAIL_SMTP_HOST": smtp_host,
        "EMAIL_SMTP_USER": smtp_user,
        "EMAIL_SMTP_PASSWORD": smtp_password,
        "EMAIL_TO": ",".join(to_addrs),
        "EMAIL_FROM": from_addr,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        print(
            "[WARN] Email step skipped. Missing required env vars: "
            + ", ".join(missing)
        )
        return 0

    report_json_path = pick_report_json(input_dir, args.report_date)
    report_info = load_report_info(report_json_path)
    report_date = report_info["report_date"]
    article_count = report_info["article_count"]
    md_path = pick_markdown_path(input_dir, report_json_path, report_date)
    md_text = md_path.read_text(encoding="utf-8") if md_path and md_path.exists() else ""
    subject = make_subject(report_date, article_count)
    body = build_body(report_date, article_count, site_url, md_text)

    send_email(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        from_addr=from_addr,
        to_addrs=to_addrs,
        subject=subject,
        body_text=body,
        attachment_json=report_json_path,
        attachment_md=md_path,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
