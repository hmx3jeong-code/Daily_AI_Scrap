import argparse
import datetime as dt
import email.utils
import html
import json
import os
import re
import threading
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None


if load_dotenv is not None:
    load_dotenv()


DEFAULT_CONFIG_PATH = Path("daily_ai_agent_config.json")
DEFAULT_OUTPUT_DIR = Path("daily_ai_reports")
DEFAULT_TIMEOUT_SEC = 20
REPORT_TZ = dt.timezone(dt.timedelta(hours=9), "KST")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0 Safari/537.36 DailyAIAgent/1.0"
)

HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
TEXT_SIG_RE = re.compile(r"[^0-9a-zA-Z가-힣]+")
REPORT_JSON_NAME_RE = re.compile(r"^daily_ai_brief_(\d{4}-\d{2}-\d{2})\.json$")

TRACKING_QUERY_KEYS = {
    "ref",
    "source",
    "output",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "spm",
    "igshid",
    "feature",
}

TITLE_STOPWORDS = {
    "a",
    "an",
    "the",
    "to",
    "for",
    "of",
    "and",
    "in",
    "on",
    "with",
    "at",
    "by",
    "is",
    "are",
    "new",
    "latest",
    "update",
    "introducing",
    "official",
    "blog",
    "news",
    "ai",
    "및",
    "에서",
    "으로",
    "에서의",
    "관련",
    "대한",
    "그리고",
    "이번",
    "최신",
    "공개",
    "출시",
    "발표",
}


@dataclass
class Source:
    name: str
    feed_url: str
    authority: str = "unknown"
    topic_hint: str = ""
    max_items: int = 20
    fallback_feed_urls: list[str] = field(default_factory=list)


@dataclass
class Article:
    source_name: str
    source_authority: str
    title: str
    link: str
    published_raw: str
    published_dt: dt.datetime | None
    summary: str
    topics: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    translated_title: str = ""
    translated_keywords: list[str] = field(default_factory=list)
    final_summary: str = ""


class LlmSummarizer:
    def __init__(self, llm_config: dict[str, Any]) -> None:
        self.enabled = bool(llm_config.get("enabled", False))
        self.provider = "gemini"
        self.model = "gemini-3.1-flash-lite-preview"
        self.temperature = float(llm_config.get("temperature", 0.1))
        self.max_articles_per_run = int(llm_config.get("max_articles_per_run", 20))
        self.client: Any | None = None
        self._init_error = ""
        self.config_notes: list[str] = []
        self.calls_attempted = 0
        self.calls_success_json = 0
        self.calls_success_freeform = 0
        self.calls_fallback = 0
        self.last_error = ""

        if not self.enabled:
            return

        requested_provider = str(llm_config.get("provider", "")).strip().lower()
        if requested_provider and requested_provider != self.provider:
            self.config_notes.append(
                f"llm.provider='{requested_provider}' is ignored. Using '{self.provider}' only."
            )
        requested_model = str(llm_config.get("model", "")).strip()
        if requested_model and requested_model != self.model:
            self.config_notes.append(
                f"llm.model='{requested_model}' is ignored. Using '{self.model}' only."
            )

        try:
            from openai import OpenAI  # type: ignore
        except ImportError:
            self.enabled = False
            self._init_error = "openai package is not installed."
            return

        try:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                self.enabled = False
                self._init_error = "Missing GEMINI_API_KEY (or GOOGLE_API_KEY)."
                return

            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        except Exception as exc:  # pragma: no cover - network/client init variability
            self.enabled = False
            self._init_error = f"Failed to initialize LLM client: {exc}"

    @property
    def init_error(self) -> str:
        return self._init_error

    def stats(self) -> dict[str, Any]:
        return {
            "attempted": self.calls_attempted,
            "success_json": self.calls_success_json,
            "success_freeform": self.calls_success_freeform,
            "fallback": self.calls_fallback,
            "enabled_after_run": self.enabled,
            "last_error": self.last_error,
            "init_error": self._init_error,
        }

    @staticmethod
    def _extract_json_dict(raw_text: str) -> dict[str, Any]:
        text = (raw_text or "").strip()
        if not text:
            return {}
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return {}
        text = text[start : end + 1]
        try:
            parsed = json.loads(text)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def localize_article(self, article: Article) -> dict[str, Any]:
        default_summary = fallback_summary(article)
        default_payload = {
            "title_ko": article.title,
            "summary_ko": default_summary,
            "keywords_ko": article.keywords[:5],
        }
        if not self.enabled or self.client is None:
            self.calls_fallback += 1
            return default_payload
        self.calls_attempted += 1

        prompt = (
            "다음 AI 기사 정보를 한국어로 자연스럽게 번역/요약해라.\n"
            "반드시 JSON만 반환하고 코드블록은 쓰지 마라.\n"
            "출력 형식:\n"
            '{"title_ko":"...", "summary_ko":"...", "keywords_ko":["...", "..."]}\n\n'
            "규칙:\n"
            "- title_ko: 어색하지 않은 한국어 제목으로 번역 (고유명사/제품명은 유지)\n"
            "- summary_ko: 한국어 10~12문장 상세 요약\n"
            "- summary_ko에는 다음을 포함: 핵심 발표/사실, 기능/수치/일정(가능한 경우), 배경/맥락, 실무 영향\n"
            "- summary_ko 분량: 450~550자\n"
            "- keywords_ko: 한국어 핵심 키워드 5~7개\n"
            "- 과장/추측 금지, 숫자/기관명/모델명은 최대한 보존\n\n"
            f"제목: {article.title}\n"
            f"출처: {article.source_name}\n"
            f"본문요약: {article.summary}\n"
            f"기존키워드: {', '.join(article.keywords)}\n"
            f"링크: {article.link}\n"
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": "당신은 사실 중심의 AI 뉴스 에디터다."},
                    {"role": "user", "content": prompt},
                ],
            )
            content = (
                response.choices[0].message.content
                if response and response.choices
                else ""
            )
            parsed = self._extract_json_dict(content)
            if not parsed:
                guessed_summary = normalize_whitespace(content)
                if guessed_summary:
                    self.calls_success_freeform += 1
                    return {
                        "title_ko": article.title,
                        "summary_ko": truncate_text(guessed_summary, 800),
                        "keywords_ko": article.keywords[:5],
                    }
            title_ko = normalize_whitespace(str(parsed.get("title_ko", "")))
            summary_ko = normalize_whitespace(str(parsed.get("summary_ko", "")))
            keywords_raw = parsed.get("keywords_ko", [])
            keywords_ko: list[str] = []
            if isinstance(keywords_raw, list):
                for keyword in keywords_raw:
                    cleaned = normalize_whitespace(str(keyword))
                    if cleaned:
                        keywords_ko.append(cleaned)
            if not title_ko:
                title_ko = article.title
            if not summary_ko:
                summary_ko = default_summary
            if not keywords_ko:
                keywords_ko = article.keywords[:5]
            self.calls_success_json += 1
            return {
                "title_ko": title_ko,
                "summary_ko": summary_ko,
                "keywords_ko": keywords_ko[:5],
            }
        except Exception as exc:
            error_message = str(exc).lower()
            self.last_error = str(exc)
            if (
                "429" in error_message
                or "quota" in error_message
                or "resource_exhausted" in error_message
                or "rate limit" in error_message
            ):
                self.enabled = False
                self._init_error = (
                    "LLM quota/rate limit reached. "
                    "The rest of this run will use fallback summaries."
                )
            self.calls_fallback += 1
            return default_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect daily AI news from RSS/Atom feeds and generate topic/keyword summaries."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to config JSON (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for reports (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--report-date",
        type=str,
        default="",
        help="Report date in YYYY-MM-DD. Default: local today.",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=None,
        help=(
            "Include items from [report_date - lookback_days + 1, report_date]. "
            "Default comes from config.report_options.default_lookback_days (fallback: 7)."
        ),
    )
    parser.add_argument(
        "--target-articles",
        type=int,
        default=None,
        help=(
            "Preferred minimum number of articles. "
            "Default comes from config.report_options.target_articles (fallback: 10)."
        ),
    )
    parser.add_argument(
        "--max-total-articles",
        type=int,
        default=None,
        help=(
            "Upper bound for total articles in the final report. "
            "Default comes from config.report_options.max_total_articles (fallback: 10)."
        ),
    )
    parser.add_argument(
        "--max-per-source",
        type=int,
        default=15,
        help="Maximum items to keep per source after date filtering.",
    )
    parser.add_argument(
        "--timeout-sec",
        type=int,
        default=DEFAULT_TIMEOUT_SEC,
        help=f"Network timeout in seconds (default: {DEFAULT_TIMEOUT_SEC}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show execution plan without network requests or file outputs.",
    )
    return parser.parse_args()


def normalize_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", (text or "").strip())


def now_in_report_tz() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).astimezone(REPORT_TZ)


def strip_html(raw_html: str) -> str:
    text = html.unescape(raw_html or "")
    text = HTML_TAG_RE.sub(" ", text)
    return normalize_whitespace(text)


def parse_report_date(raw: str) -> dt.date:
    if not raw:
        return now_in_report_tz().date()
    try:
        return dt.date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid --report-date '{raw}'. Use YYYY-MM-DD.") from exc


def load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}. "
            "Create it or pass --config with a valid path."
        )
    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if "sources" not in data or not isinstance(data["sources"], list):
        raise ValueError("Config must contain a 'sources' array.")
    return data


def parse_sources(config: dict[str, Any], global_max_per_source: int) -> list[Source]:
    sources: list[Source] = []
    for raw in config.get("sources", []):
        name = str(raw.get("name", "")).strip()
        feed_url = str(raw.get("feed_url", "")).strip()
        if not name or not feed_url:
            continue
        per_source = int(raw.get("max_items", global_max_per_source))
        if per_source <= 0:
            per_source = global_max_per_source
        fallback_feed_urls: list[str] = []
        raw_fallbacks = raw.get("fallback_feed_urls", [])
        if isinstance(raw_fallbacks, list):
            for fallback_url in raw_fallbacks:
                cleaned = str(fallback_url).strip()
                if cleaned:
                    fallback_feed_urls.append(cleaned)
        sources.append(
            Source(
                name=name,
                feed_url=feed_url,
                authority=str(raw.get("authority", "unknown")).strip() or "unknown",
                topic_hint=str(raw.get("topic_hint", "")).strip(),
                max_items=per_source,
                fallback_feed_urls=fallback_feed_urls,
            )
        )
    return sources


def _fetch_feed_xml_once(feed_url: str, timeout_sec: int) -> bytes:
    request = urllib.request.Request(
        feed_url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml"},
    )
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        return response.read()


def fetch_feed_xml(feed_url: str, timeout_sec: int, hard_timeout_sec: int | None = None) -> bytes:
    # urlopen timeout may not always cap DNS resolution delays on all environments.
    # Use a daemon thread join timeout so one blocked source does not stop the whole run.
    max_wait = hard_timeout_sec if hard_timeout_sec is not None else max(timeout_sec + 5, 10)
    payload: dict[str, Any] = {"data": None, "error": None}

    def _worker() -> None:
        try:
            payload["data"] = _fetch_feed_xml_once(feed_url, timeout_sec)
        except Exception as exc:
            payload["error"] = exc

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()
    worker.join(max_wait)
    if worker.is_alive():
        raise TimeoutError(f"Timeout while fetching {feed_url} (>{max_wait}s)")
    if payload["error"] is not None:
        raise payload["error"]
    data = payload.get("data")
    if not isinstance(data, (bytes, bytearray)):
        raise RuntimeError(f"Invalid response payload for {feed_url}")
    return bytes(data)


def fetch_with_fallback(source: Source, timeout_sec: int) -> tuple[str, bytes]:
    candidates = [source.feed_url, *source.fallback_feed_urls]
    seen: set[str] = set()
    last_error: Exception | None = None
    for url in candidates:
        normalized = url.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        try:
            return normalized, fetch_feed_xml(normalized, timeout_sec)
        except Exception as exc:
            last_error = exc
            continue
    if last_error is None:
        raise RuntimeError(f"No fetchable URL candidates for source: {source.name}")
    raise last_error


def parse_feed_datetime(raw: str) -> dt.datetime | None:
    if not raw:
        return None

    raw = raw.strip()
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        if parsed is not None:
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=dt.timezone.utc)
            return parsed
    except Exception:
        pass

    iso_candidates = [
        raw,
        raw.replace("Z", "+00:00"),
        raw.split(".")[0].replace("Z", "+00:00"),
    ]
    for candidate in iso_candidates:
        try:
            parsed = dt.datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return parsed
        except Exception:
            continue
    return None


def rss_text(elem: ET.Element, tag: str) -> str:
    found = elem.find(tag)
    if found is not None and found.text:
        return found.text
    return ""


def atom_text(elem: ET.Element, namespace: str, tag: str) -> str:
    found = elem.find(f"{namespace}{tag}")
    if found is not None and found.text:
        return found.text
    return ""


def parse_rss_items(root: ET.Element, source: Source) -> list[Article]:
    channel = root.find("channel")
    if channel is None:
        return []

    items = channel.findall("item")
    out: list[Article] = []
    for item in items:
        title = strip_html(rss_text(item, "title"))
        link = normalize_feed_url(rss_text(item, "link"))
        if not title or not link:
            continue

        pub_raw = (
            rss_text(item, "pubDate")
            or rss_text(item, "dc:date")
            or rss_text(item, "published")
        )
        description = (
            rss_text(item, "description")
            or rss_text(item, "content:encoded")
            or rss_text(item, "summary")
        )
        out.append(
            Article(
                source_name=source.name,
                source_authority=source.authority,
                title=title,
                link=link,
                published_raw=pub_raw,
                published_dt=parse_feed_datetime(pub_raw),
                summary=strip_html(description),
            )
        )
    return out


def parse_atom_items(root: ET.Element, source: Source) -> list[Article]:
    namespace = "{http://www.w3.org/2005/Atom}"
    entries = root.findall(f"{namespace}entry")
    out: list[Article] = []
    for entry in entries:
        title = strip_html(atom_text(entry, namespace, "title"))
        if not title:
            continue

        link = ""
        for link_elem in entry.findall(f"{namespace}link"):
            rel = (link_elem.attrib.get("rel", "") or "alternate").strip()
            href = (link_elem.attrib.get("href", "") or "").strip()
            if rel == "alternate" and href:
                link = href
                break
            if not link and href:
                link = href
        link = normalize_feed_url(link)
        if not link:
            continue

        pub_raw = (
            atom_text(entry, namespace, "published")
            or atom_text(entry, namespace, "updated")
        )
        summary_raw = (
            atom_text(entry, namespace, "summary")
            or atom_text(entry, namespace, "content")
        )

        out.append(
            Article(
                source_name=source.name,
                source_authority=source.authority,
                title=title,
                link=link,
                published_raw=pub_raw,
                published_dt=parse_feed_datetime(pub_raw),
                summary=strip_html(summary_raw),
            )
        )
    return out


def parse_feed_items(raw_xml: bytes, source: Source) -> list[Article]:
    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError:
        return []

    root_tag = root.tag.lower()
    if root_tag.endswith("rss") or root.find("channel") is not None:
        return parse_rss_items(root, source)
    if root_tag.endswith("feed"):
        return parse_atom_items(root, source)
    return []


def normalize_feed_url(link: str) -> str:
    if not link:
        return ""
    parsed = urllib.parse.urlsplit(link.strip())
    if not parsed.scheme:
        return ""
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    filtered = [
        (k, v)
        for (k, v) in query
        if not k.lower().startswith("utm_") and k.lower() not in {"ref", "source"}
    ]
    normalized_query = urllib.parse.urlencode(filtered, doseq=True)
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, normalized_query, "")
    )


def normalize_signature_text(text: str) -> str:
    cleaned = normalize_whitespace(strip_html(text)).lower()
    cleaned = TEXT_SIG_RE.sub(" ", cleaned)
    return normalize_whitespace(cleaned)


def title_token_set(title: str) -> set[str]:
    tokens = []
    for token in normalize_signature_text(title).split():
        if len(token) <= 1:
            continue
        if token in TITLE_STOPWORDS:
            continue
        tokens.append(token)
    return set(tokens)


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    if union == 0:
        return 0.0
    return intersection / union


def canonical_article_url_signature(link: str) -> str:
    if not link:
        return ""
    parsed = urllib.parse.urlsplit(link.strip())
    if not parsed.scheme or not parsed.netloc:
        return ""
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/+", "/", (parsed.path or "/").rstrip("/"))
    if not path:
        path = "/"
    if path.endswith("/amp"):
        path = path[: -len("/amp")] or "/"
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    filtered = []
    for key, value in query:
        lowered = key.lower()
        if lowered.startswith("utm_"):
            continue
        if lowered in TRACKING_QUERY_KEYS:
            continue
        filtered.append((lowered, value))
    filtered.sort()
    normalized_query = urllib.parse.urlencode(filtered, doseq=True)
    if normalized_query:
        return f"{host}{path}?{normalized_query}"
    return f"{host}{path}"


def article_title_signature(title: str) -> str:
    normalized = normalize_signature_text(title)
    if not normalized:
        return ""
    tokens = [t for t in normalized.split() if t not in TITLE_STOPWORDS]
    if tokens:
        return " ".join(tokens[:12])
    return normalized


def article_primary_dedupe_key(article: Article) -> str:
    url_sig = canonical_article_url_signature(article.link)
    if url_sig:
        return f"url:{url_sig}"
    title_sig = article_title_signature(article.title)
    if title_sig:
        return f"title:{title_sig}"
    fallback = normalize_signature_text(article.title)
    return f"title:{fallback}" if fallback else ""


def article_signature_keys_from_values(title: str, link: str) -> set[str]:
    signatures: set[str] = set()
    url_sig = canonical_article_url_signature(link)
    title_sig = article_title_signature(title)
    if url_sig:
        signatures.add(f"url:{url_sig}")
    if title_sig:
        signatures.add(f"title:{title_sig}")
    return signatures


def article_signature_keys(article: Article) -> set[str]:
    return article_signature_keys_from_values(article.title, article.link)


def dedupe_articles(articles: list[Article]) -> list[Article]:
    seen_primary_keys: set[str] = set()
    seen_title_signatures: set[str] = set()
    kept_title_tokens: list[tuple[set[str], str]] = []
    out: list[Article] = []
    for article in articles:
        primary_key = article_primary_dedupe_key(article)
        if primary_key and primary_key in seen_primary_keys:
            continue

        title_sig = article_title_signature(article.title)
        if title_sig and title_sig in seen_title_signatures:
            continue

        current_tokens = title_token_set(article.title)
        is_near_duplicate = False
        if current_tokens:
            for previous_tokens, previous_source in kept_title_tokens:
                similarity = jaccard_similarity(current_tokens, previous_tokens)
                # Same-title variants often appear with slightly different URLs/categories.
                # For same source we use a lower threshold, cross-source keeps stricter threshold.
                if similarity >= 0.88 and article.source_name == previous_source:
                    is_near_duplicate = True
                    break
                if similarity >= 0.94:
                    is_near_duplicate = True
                    break
        if is_near_duplicate:
            continue

        out.append(article)
        if primary_key:
            seen_primary_keys.add(primary_key)
        if title_sig:
            seen_title_signatures.add(title_sig)
        kept_title_tokens.append((current_tokens, article.source_name))
    return out


def load_historical_article_signatures(
    output_dir: Path,
    report_date: dt.date,
    history_days: int,
) -> set[str]:
    if history_days <= 0 or not output_dir.exists():
        return set()
    lower_bound = report_date - dt.timedelta(days=history_days)
    signatures: set[str] = set()
    for report_path in output_dir.glob("daily_ai_brief_*.json"):
        match = REPORT_JSON_NAME_RE.match(report_path.name)
        if not match:
            continue
        try:
            past_date = dt.date.fromisoformat(match.group(1))
        except ValueError:
            continue
        if past_date >= report_date or past_date < lower_bound:
            continue
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        raw_articles = payload.get("articles", [])
        if not isinstance(raw_articles, list):
            continue
        for raw_article in raw_articles:
            if not isinstance(raw_article, dict):
                continue
            title = str(raw_article.get("title_original") or raw_article.get("title") or "")
            link = str(raw_article.get("link") or "")
            signatures.update(article_signature_keys_from_values(title, link))
    return signatures


def filter_previously_reported_articles(
    articles: list[Article],
    historical_signatures: set[str],
) -> tuple[list[Article], int]:
    if not historical_signatures:
        return articles, 0
    filtered: list[Article] = []
    dropped = 0
    for article in articles:
        signatures = article_signature_keys(article)
        if signatures and any(sig in historical_signatures for sig in signatures):
            dropped += 1
            continue
        filtered.append(article)
    return filtered, dropped


def in_date_window(
    published_dt: dt.datetime | None, report_date: dt.date, lookback_days: int
) -> bool:
    if published_dt is None:
        return True
    converted = published_dt.astimezone(REPORT_TZ) if published_dt.tzinfo else published_dt
    lower = report_date - dt.timedelta(days=max(lookback_days, 1) - 1)
    upper = report_date
    return lower <= converted.date() <= upper


def article_sort_key(article: Article) -> dt.datetime:
    if article.published_dt is None:
        return dt.datetime.min.replace(tzinfo=dt.timezone.utc)
    if article.published_dt.tzinfo is None:
        return article.published_dt.replace(tzinfo=dt.timezone.utc)
    return article.published_dt


def sort_articles_desc(articles: list[Article]) -> list[Article]:
    return sorted(articles, key=article_sort_key, reverse=True)


def classify_keywords(
    article: Article,
    topic_rules: dict[str, list[str]],
    issue_rules: dict[str, list[str]],
    default_topic: str = "기타",
) -> None:
    content = f"{article.title} {article.summary}".lower()

    topic_scores: list[tuple[str, int, list[str]]] = []
    for topic, words in topic_rules.items():
        hits = [w for w in words if w.lower() in content]
        if hits:
            topic_scores.append((topic, len(hits), hits))

    topic_scores.sort(key=lambda x: x[1], reverse=True)
    if topic_scores:
        article.topics = [t for (t, _, _) in topic_scores[:2]]
    else:
        article.topics = [default_topic]

    issue_hits: list[str] = []
    for issue, words in issue_rules.items():
        if any(w.lower() in content for w in words):
            issue_hits.append(issue)
    article.issues = issue_hits[:3]

    matched_keywords: list[str] = []
    for _, _, hits in topic_scores[:2]:
        matched_keywords.extend(hits)
    for issue in article.issues:
        matched_keywords.append(issue)
    deduped_keywords = []
    keyword_seen = set()
    for kw in matched_keywords:
        key = kw.lower().strip()
        if not key or key in keyword_seen:
            continue
        keyword_seen.add(key)
        deduped_keywords.append(kw)
    article.keywords = deduped_keywords[:6]


def fallback_summary(article: Article) -> str:
    title = truncate_text(article.title, 200)
    if article.summary:
        excerpt = truncate_text(article.summary, 300)
        return normalize_whitespace(
            f"이 기사는 '{title}' 관련 내용을 다룬다. "
            f"공개된 기사 요약에 따르면 {excerpt} "
            "핵심 배경과 세부 수치, 실제 적용 영향은 원문 링크에서 함께 확인하는 것이 좋다."
        )
    return normalize_whitespace(
        f"이 기사는 '{title}' 주제를 다룬다. "
        "제공된 본문 요약이 짧아 세부 내용은 원문 확인이 필요하다."
    )


def truncate_text(text: str, max_len: int) -> str:
    text = normalize_whitespace(text)
    if len(text) <= max_len:
        return text
    return text[: max(0, max_len - 1)] + "…"


def format_dt(value: dt.datetime | None) -> str:
    if value is None:
        return "Unknown"
    converted = value.astimezone(REPORT_TZ) if value.tzinfo else value
    return converted.strftime("%Y-%m-%d %H:%M")


def build_markdown_report(
    report_date: dt.date,
    articles: list[Article],
    issues_counter: Counter[str],
    topic_to_articles: dict[str, list[Article]],
    source_totals: dict[str, int],
    source_kept: dict[str, int],
) -> str:
    lines: list[str] = []
    created_at = now_in_report_tz().strftime("%Y-%m-%d %H:%M:%S KST")
    lines.append(f"# Daily AI Brief - {report_date.isoformat()}")
    lines.append("")
    lines.append(f"- Generated at: {created_at}")
    lines.append(f"- Total articles: {len(articles)}")
    lines.append(f"- Sources scanned: {len(source_totals)}")
    lines.append("")
    lines.append("## 오늘의 주요 이슈")
    if issues_counter:
        for issue, count in issues_counter.most_common(8):
            lines.append(f"- {issue}: {count}건")
    else:
        lines.append("- 이슈 태그가 충분히 감지되지 않았습니다.")
    lines.append("")
    lines.append("## 주제별 요약")
    if not topic_to_articles:
        lines.append("- 분류된 기사가 없습니다.")
    else:
        for topic, topic_articles in sorted(
            topic_to_articles.items(),
            key=lambda x: len(x[1]),
            reverse=True,
        ):
            lines.append(f"### {topic} ({len(topic_articles)})")
            for article in topic_articles:
                published = format_dt(article.published_dt)
                display_title = article.translated_title or article.title
                display_keywords = (
                    article.translated_keywords
                    if article.translated_keywords
                    else article.keywords
                )
                keywords = ", ".join(display_keywords) if display_keywords else "-"
                lines.append(
                    f"- [{display_title}]({article.link}) | "
                    f"{article.source_name} | {published}"
                )
                lines.append(f"  - 요약: {article.final_summary}")
                lines.append(f"  - 키워드: {keywords}")
            lines.append("")

    lines.append("## 소스 커버리지")
    lines.append("| Source | Collected | Included |")
    lines.append("|---|---:|---:|")
    for source_name in sorted(source_totals.keys()):
        lines.append(
            f"| {source_name} | {source_totals[source_name]} | {source_kept.get(source_name, 0)} |"
        )
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_json_report(
    report_date: dt.date,
    articles: list[Article],
    issues_counter: Counter[str],
    source_totals: dict[str, int],
    source_kept: dict[str, int],
    llm_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    generated_at_kst = now_in_report_tz()
    generated_at_utc = generated_at_kst.astimezone(dt.timezone.utc)
    report_date_kst = generated_at_kst.date().isoformat()

    serialized_articles = []
    for article in articles:
        display_title = article.translated_title or article.title
        display_keywords = (
            article.translated_keywords
            if article.translated_keywords
            else article.keywords
        )
        serialized_articles.append(
            {
                "source": article.source_name,
                "authority": article.source_authority,
                "title": display_title,
                "title_original": article.title,
                "link": article.link,
                "published_raw": article.published_raw,
                "published_local": format_dt(article.published_dt),
                "primary_topic": article.topics[0] if article.topics else "기타",
                "topics": article.topics,
                "issues": article.issues,
                "keywords": display_keywords,
                "keywords_original": article.keywords,
                "summary": article.final_summary,
                "summary_original": article.summary,
            }
        )

    return {
        "report_date": report_date.isoformat(),
        "report_date_kst": report_date_kst,
        "generated_at": generated_at_utc.isoformat(),
        "generated_at_kst": generated_at_kst.isoformat(),
        "article_count": len(articles),
        "issues_top": issues_counter.most_common(20),
        "source_totals": source_totals,
        "source_kept": source_kept,
        "llm_stats": llm_stats or {},
        "articles": serialized_articles,
    }


def run() -> int:
    args = parse_args()

    try:
        report_date = parse_report_date(args.report_date)
        config = load_config(args.config)
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 2

    sources = parse_sources(config, args.max_per_source)
    if not sources:
        print("[ERROR] No valid sources found in config.")
        return 2

    topic_rules = config.get("topic_rules", {})
    issue_rules = config.get("issue_rules", {})
    report_options = config.get("report_options", {})
    if not isinstance(topic_rules, dict):
        topic_rules = {}
    if not isinstance(issue_rules, dict):
        issue_rules = {}
    if not isinstance(report_options, dict):
        report_options = {}

    lookback_days = (
        int(args.lookback_days)
        if args.lookback_days is not None
        else int(report_options.get("default_lookback_days", 7))
    )
    target_articles = (
        int(args.target_articles)
        if args.target_articles is not None
        else int(report_options.get("target_articles", 10))
    )
    max_total_articles = (
        int(args.max_total_articles)
        if args.max_total_articles is not None
        else int(report_options.get("max_total_articles", 10))
    )
    history_dedupe_days = int(report_options.get("history_dedupe_days", 14))
    lookback_days = max(1, lookback_days)
    target_articles = max(1, target_articles)
    max_total_articles = max(target_articles, max_total_articles)
    history_dedupe_days = max(0, history_dedupe_days)

    print(
        f"[INFO] report_date={report_date.isoformat()} "
        f"lookback_days={lookback_days} "
        f"target_articles={target_articles} "
        f"max_total_articles={max_total_articles} "
        f"history_dedupe_days={history_dedupe_days} "
        f"sources={len(sources)}"
    )

    if args.dry_run:
        print("[INFO] Dry run mode. No network requests or file writes.")
        for source in sources:
            fallback_count = len(source.fallback_feed_urls)
            print(
                f"- {source.name} | {source.feed_url} | "
                f"fallbacks={fallback_count} | max_items={source.max_items}"
            )
        return 0

    source_totals: dict[str, int] = {}
    source_kept: dict[str, int] = {}
    all_articles: list[Article] = []
    backfill_pool: list[Article] = []

    for source in sources:
        print(f"[INFO] Fetching: {source.name}")
        try:
            fetched_url, raw_xml = fetch_with_fallback(source, args.timeout_sec)
            parsed = parse_feed_items(raw_xml, source)
            if fetched_url != source.feed_url:
                print(f"[INFO] Fallback URL used for {source.name}: {fetched_url}")
        except Exception as exc:
            print(f"[WARN] Failed to fetch/parse {source.name}: {exc}")
            source_totals[source.name] = 0
            source_kept[source.name] = 0
            continue

        parsed = dedupe_articles(parsed)
        source_totals[source.name] = len(parsed)
        filtered = [
            item
            for item in parsed
            if in_date_window(item.published_dt, report_date, lookback_days)
        ]
        older = [item for item in parsed if item not in filtered]
        filtered = dedupe_articles(filtered)[: source.max_items]
        older = dedupe_articles(older)[: source.max_items]
        source_kept[source.name] = len(filtered)
        all_articles.extend(filtered)
        backfill_pool.extend(older)

    all_articles = sort_articles_desc(dedupe_articles(all_articles))
    backfill_pool = sort_articles_desc(dedupe_articles(backfill_pool))

    historical_signatures = load_historical_article_signatures(
        output_dir=args.output_dir,
        report_date=report_date,
        history_days=history_dedupe_days,
    )
    if historical_signatures:
        all_articles, dropped_current = filter_previously_reported_articles(
            all_articles, historical_signatures
        )
        backfill_pool, dropped_backfill = filter_previously_reported_articles(
            backfill_pool, historical_signatures
        )
        if dropped_current or dropped_backfill:
            print(
                "[INFO] Historical dedupe removed "
                f"{dropped_current + dropped_backfill} article(s) "
                f"(current={dropped_current}, backfill={dropped_backfill}) "
                f"from last {history_dedupe_days} day(s)."
            )

    if len(all_articles) < target_articles and backfill_pool:
        seen_keys: set[str] = set()
        for item in all_articles:
            item_key = article_primary_dedupe_key(item)
            if item_key:
                seen_keys.add(item_key)
        added = 0
        for candidate in backfill_pool:
            candidate_key = article_primary_dedupe_key(candidate)
            if candidate_key in seen_keys:
                continue
            all_articles.append(candidate)
            if candidate_key:
                seen_keys.add(candidate_key)
            added += 1
            if len(all_articles) >= target_articles:
                break
        if added > 0:
            print(
                f"[INFO] Added {added} older article(s) as backfill "
                f"to reach target_articles={target_articles}."
            )

    all_articles = sort_articles_desc(dedupe_articles(all_articles))
    if len(all_articles) > max_total_articles:
        all_articles = all_articles[:max_total_articles]

    for article in all_articles:
        classify_keywords(article, topic_rules, issue_rules)

    llm = LlmSummarizer(config.get("llm", {}))
    if llm.config_notes:
        for note in llm.config_notes:
            print(f"[WARN] {note}")
    if llm.enabled:
        print(f"[INFO] LLM summarization enabled: provider={llm.provider}, model={llm.model}")
    elif llm.init_error:
        print(f"[WARN] LLM disabled: {llm.init_error}")
    else:
        print("[INFO] LLM summarization disabled.")

    summarize_budget = llm.max_articles_per_run if llm.enabled else 0
    for idx, article in enumerate(all_articles):
        article.translated_title = article.title
        article.translated_keywords = article.keywords[:]
        if llm.enabled and idx < summarize_budget:
            localized = llm.localize_article(article)
            article.translated_title = normalize_whitespace(
                str(localized.get("title_ko", article.title))
            )
            article.final_summary = normalize_whitespace(
                str(localized.get("summary_ko", fallback_summary(article)))
            )
            localized_keywords = localized.get("keywords_ko", [])
            if isinstance(localized_keywords, list):
                article.translated_keywords = [
                    normalize_whitespace(str(keyword))
                    for keyword in localized_keywords
                    if normalize_whitespace(str(keyword))
                ][:5]
            if not article.translated_keywords:
                article.translated_keywords = article.keywords[:]
        else:
            article.final_summary = fallback_summary(article)

    llm_run_stats = llm.stats()
    if summarize_budget > 0:
        print(
            "[INFO] LLM stats: "
            f"attempted={llm_run_stats['attempted']} "
            f"success_json={llm_run_stats['success_json']} "
            f"success_freeform={llm_run_stats['success_freeform']} "
            f"fallback={llm_run_stats['fallback']}"
        )
        if llm_run_stats.get("last_error"):
            print(f"[WARN] Last LLM error: {llm_run_stats['last_error']}")
        if llm_run_stats.get("init_error"):
            print(f"[WARN] LLM status: {llm_run_stats['init_error']}")

    issues_counter: Counter[str] = Counter()
    topic_to_articles: dict[str, list[Article]] = defaultdict(list)
    for article in all_articles:
        for issue in article.issues:
            issues_counter[issue] += 1
        primary_topic = article.topics[0] if article.topics else "기타"
        topic_to_articles[primary_topic].append(article)

    for topic in topic_to_articles:
        topic_to_articles[topic].sort(
            key=lambda x: x.published_dt or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
            reverse=True,
        )

    markdown = build_markdown_report(
        report_date=report_date,
        articles=all_articles,
        issues_counter=issues_counter,
        topic_to_articles=topic_to_articles,
        source_totals=source_totals,
        source_kept=source_kept,
    )
    json_report = build_json_report(
        report_date=report_date,
        articles=all_articles,
        issues_counter=issues_counter,
        source_totals=source_totals,
        source_kept=source_kept,
        llm_stats=llm_run_stats,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    md_path = args.output_dir / f"daily_ai_brief_{report_date.isoformat()}.md"
    json_path = args.output_dir / f"daily_ai_brief_{report_date.isoformat()}.json"
    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(
        json.dumps(json_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[INFO] Report written: {md_path}")
    print(f"[INFO] JSON written: {json_path}")
    print(f"[INFO] Included articles: {len(all_articles)}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
