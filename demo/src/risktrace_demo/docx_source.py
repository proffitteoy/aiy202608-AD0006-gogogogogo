from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .manifest import ScenarioManifest
from .models import RejectedRecord, SourceDescriptor, SourceRecord, SourceType

WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
DATE_PATTERN = re.compile(
    r"(?P<date>(?:19|20)\d{2}-\d{1,2}-\d{1,2}"
    r"(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?)"
)
AUTHOR_PATTERN = re.compile(r"(?:作者|记者)：(?P<author>.*?)(?=\s+(?:19|20)\d{2}-|$)")
HEADING_PREFIX_PATTERN = re.compile(r"^\d+(?:\.\d+)*\s+")
HEADING_SUFFIX_PATTERN = re.compile(r"[（(](?:全文|原文)照搬(?:关键段落)?[）)]$")
URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)

PROVIDER_BY_HOST = {
    "api-docs.deepseek.com": "deepseek-api-docs",
    "github.com": "github",
    "www.stcn.com": "stcn",
    "www.21jingji.com": "21jingji",
    "www.secrss.com": "secrss",
    "www.cls.cn": "cls",
    "finance.sina.com.cn": "sina-finance",
    "www.mee.gov.cn": "mee",
    "www.ccedia.com": "ccedia",
    "www.news.cn": "xinhuanet",
    "paper.people.com.cn": "people",
    "m.solarzoom.com": "solarzoom",
    "www.zhihu.com": "zhihu",
    "www.pbc.gov.cn": "pbc",
    "m.fangchan.com": "fangchan",
    "weibo.com": "weibo",
}

SOURCE_LEVEL = {
    SourceType.FACT: "official",
    SourceType.NEWS: "professional_media",
    SourceType.SOCIAL: "public_discussion",
    SourceType.MARKET: "market_data",
}


class RecordConversionError(ValueError):
    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True, slots=True)
class ArticleBlock:
    source_type: SourceType
    heading: str
    paragraph_start: int
    paragraph_end: int
    lines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConversionResult:
    records: tuple[SourceRecord, ...]
    rejected: tuple[RejectedRecord, ...]


def extract_docx_paragraphs(path: Path) -> list[str]:
    try:
        with zipfile.ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as error:
        raise ValueError(f"invalid DOCX document: {path}") from error

    root = ET.fromstring(document_xml)
    paragraphs: list[str] = []
    for paragraph in root.iter(f"{{{WORD_NAMESPACE}}}p"):
        fragments: list[str] = []
        for element in paragraph.iter():
            if element.tag == f"{{{WORD_NAMESPACE}}}t" and element.text:
                fragments.append(element.text)
            elif element.tag == f"{{{WORD_NAMESPACE}}}tab":
                fragments.append("\t")
            elif element.tag in {
                f"{{{WORD_NAMESPACE}}}br",
                f"{{{WORD_NAMESPACE}}}cr",
            }:
                fragments.append("\n")
        paragraphs.append("".join(fragments).strip())
    return paragraphs


def split_article_blocks(paragraphs: list[str]) -> list[ArticleBlock]:
    blocks: list[ArticleBlock] = []
    active_type: SourceType | None = None
    heading: str | None = None
    start = 0
    lines: list[str] = []

    def flush(end: int) -> None:
        nonlocal heading, lines
        if heading is None or active_type is None:
            return
        blocks.append(
            ArticleBlock(
                source_type=active_type,
                heading=heading,
                paragraph_start=start,
                paragraph_end=end,
                lines=tuple(lines),
            )
        )
        heading = None
        lines = []

    for index, line in enumerate(paragraphs):
        if line.startswith("### "):
            flush(index - 1)
            heading = line.removeprefix("### ").strip()
            start = index
            lines = []
            continue
        if line.startswith("## "):
            flush(index - 1)
            if "事实源" in line:
                active_type = SourceType.FACT
            elif "专业新闻源" in line:
                active_type = SourceType.NEWS
            elif "舆情源" in line:
                active_type = SourceType.SOCIAL
            else:
                active_type = None
            continue
        if heading is not None:
            lines.append(line)

    flush(len(paragraphs) - 1)
    return blocks


def _parse_local_timestamp(raw_value: str, timezone_name: str) -> tuple[datetime, str]:
    if timezone_name != "Asia/Shanghai":
        raise RecordConversionError(
            "unsupported_timezone",
            f"historical demo only supports Asia/Shanghai, got {timezone_name!r}",
        )
    source_timezone = timezone(timedelta(hours=8), name="Asia/Shanghai")
    formats = (
        ("%Y-%m-%d %H:%M:%S", "second"),
        ("%Y-%m-%d %H:%M", "minute"),
        ("%Y-%m-%d", "date"),
        ("%Y年%m月%d日", "date"),
    )
    for date_format, precision in formats:
        try:
            local_value = datetime.strptime(raw_value, date_format).replace(tzinfo=source_timezone)
            return local_value.astimezone(UTC), precision
        except ValueError:
            continue
    raise RecordConversionError(
        "invalid_timestamp",
        f"unsupported timestamp {raw_value!r}",
    )


def _published_timestamp(
    block: ArticleBlock,
    manifest: ScenarioManifest,
    source_line: str,
) -> tuple[datetime, str, str, bool, str]:
    candidates = list(DATE_PATTERN.finditer(source_line))
    for line in block.lines:
        if line.startswith("Date:"):
            candidates.extend(DATE_PATTERN.finditer(line))
    if candidates:
        raw_value = candidates[-1].group("date")
        timestamp, precision = _parse_local_timestamp(raw_value, manifest.timezone)
        return timestamp, raw_value, precision, False, "source_metadata"

    override = manifest.published_at_overrides.get(block.heading)
    if override is None:
        raise RecordConversionError(
            "missing_published_at",
            "source metadata has no publication timestamp and no reviewed override exists",
        )
    timestamp, parsed_precision = _parse_local_timestamp(override.value, manifest.timezone)
    if parsed_precision != override.precision:
        raise RecordConversionError(
            "invalid_timestamp_override",
            f"override precision {override.precision!r} does not match {override.value!r}",
        )
    return timestamp, override.value, override.precision, True, override.basis


def _clean_title(heading: str) -> str:
    title = HEADING_PREFIX_PATTERN.sub("", heading).strip()
    return HEADING_SUFFIX_PATTERN.sub("", title).strip()


def _provider_from_url(url: str) -> str:
    hostname = (urlsplit(url).hostname or "").lower()
    if not hostname:
        raise RecordConversionError("invalid_url", f"URL has no hostname: {url!r}")
    if hostname in PROVIDER_BY_HOST:
        return PROVIDER_BY_HOST[hostname]
    normalized = hostname.removeprefix("www.").removeprefix("m.")
    return normalized.replace(".", "-")


def _content_hash(title: str, content: str) -> str:
    value = f"{title}\n\n{content}"
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = URL_PATTERN.sub(" ", normalized)
    normalized = " ".join(normalized.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _article_content(lines: tuple[str, ...]) -> str:
    content_lines = [
        line
        for line in lines
        if line
        and line != "---"
        and not line.startswith("来源：")
        and not line.startswith("URL：")
        and not line.startswith("Date:")
    ]
    return "\n\n".join(content_lines).strip()


def _build_record(
    block: ArticleBlock,
    manifest: ScenarioManifest,
    source_order: int,
) -> SourceRecord:
    source_line = next((line for line in block.lines if line.startswith("来源：")), None)
    if source_line is None:
        raise RecordConversionError("missing_source", "record has no 来源 metadata")
    url_line = next((line for line in block.lines if line.startswith("URL：")), None)
    if url_line is None:
        raise RecordConversionError("missing_url", "record has no URL metadata")

    url = url_line.removeprefix("URL：").strip()
    provider = _provider_from_url(url)
    published_at, published_raw, precision, inferred, basis = _published_timestamp(
        block,
        manifest,
        source_line,
    )
    collected_at, collected_precision = _parse_local_timestamp(
        manifest.collected_at,
        manifest.timezone,
    )
    content = _article_content(block.lines)
    if not content:
        raise RecordConversionError("missing_content", "record has no article content")

    title = _clean_title(block.heading)
    content_hash = _content_hash(title, content)
    identity = f"{provider}\n{url}"
    external_id = f"{provider}:{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]}"
    author_match = AUTHOR_PATTERN.search(source_line)
    author = author_match.group("author").strip() if author_match else None

    return SourceRecord(
        external_id=external_id,
        source=SourceDescriptor(
            provider=provider,
            stream=f"demo:{manifest.id}",
            type=block.source_type,
            level=SOURCE_LEVEL[block.source_type],
            collection_method=manifest.collection_method,
            license_scope=manifest.license_scope,
        ),
        published_at=published_at,
        collected_at=collected_at,
        title=title,
        content=content,
        url=url,
        language="zh-CN",
        content_hash=content_hash,
        raw_payload_ref=(
            f"{manifest.source_document.name}#paragraphs="
            f"{block.paragraph_start + 1}-{block.paragraph_end + 1}"
        ),
        author=author,
        engagement=None,
        is_original=None,
        metadata={
            "source_attribution": source_line.removeprefix("来源：").strip(),
            "source_order": source_order,
            "published_at_raw": published_raw,
            "published_at_precision": precision,
            "published_at_inferred": inferred,
            "published_at_basis": basis,
            "collected_at_raw": manifest.collected_at,
            "collected_at_precision": collected_precision,
            "collected_at_semantics": "historical_compilation_date",
            "provenance_status": manifest.provenance_status,
            "data_quality": manifest.data_quality,
        },
    )


def convert_manifest(manifest: ScenarioManifest) -> ConversionResult:
    paragraphs = extract_docx_paragraphs(manifest.source_document)
    blocks = split_article_blocks(paragraphs)
    records: list[SourceRecord] = []
    rejected: list[RejectedRecord] = []

    for source_order, block in enumerate(blocks):
        try:
            records.append(_build_record(block, manifest, source_order))
        except RecordConversionError as error:
            rejected.append(
                RejectedRecord(
                    source_document=manifest.source_document.name,
                    paragraph_start=block.paragraph_start + 1,
                    heading=block.heading,
                    reason=error.reason,
                    detail=error.detail,
                )
            )

    headings = {block.heading for block in blocks}
    unused_overrides = set(manifest.published_at_overrides) - headings
    if unused_overrides:
        raise ValueError(
            f"manifest contains unused timestamp overrides: {sorted(unused_overrides)}"
        )

    records.sort(key=lambda record: (record.published_at, record.metadata["source_order"]))
    return ConversionResult(records=tuple(records), rejected=tuple(rejected))


def write_conversion(manifest: ScenarioManifest, result: ConversionResult) -> None:
    _write_jsonl(
        manifest.path.parent / "records.jsonl",
        [record.to_dict() for record in result.records],
    )
    _write_jsonl(
        manifest.path.parent / "rejected.jsonl",
        [record.to_dict() for record in result.rejected],
    )


def _write_jsonl(path: Path, values: list[dict[str, object]]) -> None:
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    serialized = "".join(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n" for value in values
    )
    temporary_path.write_text(serialized, encoding="utf-8", newline="\n")
    temporary_path.replace(path)
