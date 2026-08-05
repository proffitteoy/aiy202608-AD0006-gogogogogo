from __future__ import annotations

import sys
import unittest
from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_ROOT = REPO_ROOT / "demo"
DEMO_SRC = DEMO_ROOT / "src"
if str(DEMO_SRC) not in sys.path:
    sys.path.insert(0, str(DEMO_SRC))

from risktrace_demo.docx_source import (  # noqa: E402
    convert_manifest,
    extract_docx_paragraphs,
    split_article_blocks,
)
from risktrace_demo.manifest import load_manifest  # noqa: E402


def all_mapping_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key) for key in value}
        for nested in value.values():
            keys.update(all_mapping_keys(nested))
        return keys
    if isinstance(value, (list, tuple)):
        keys: set[str] = set()
        for nested in value:
            keys.update(all_mapping_keys(nested))
        return keys
    return set()


class DocxSourceConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        manifest_paths = sorted((DEMO_ROOT / "scenarios").glob("*/manifest.json"))
        manifests = [load_manifest(path) for path in manifest_paths]
        cls.manifests = {manifest.id: manifest for manifest in manifests}
        cls.results = {
            scenario_id: convert_manifest(manifest)
            for scenario_id, manifest in cls.manifests.items()
        }

        expected_ids = {"deepseek-r1", "energy-transition", "real-estate-policy"}
        if set(cls.manifests) != expected_ids:
            raise AssertionError(
                f"expected manifests {sorted(expected_ids)}, got {sorted(cls.manifests)}"
            )

    def test_three_manifests_produce_expected_candidate_and_source_counts(self) -> None:
        accepted = sum(len(result.records) for result in self.results.values())
        rejected = sum(len(result.rejected) for result in self.results.values())

        self.assertEqual(accepted + rejected, 24)
        self.assertEqual(accepted, 22)
        self.assertEqual(rejected, 2)

        source_types = Counter(
            record.source.type.value
            for result in self.results.values()
            for record in result.records
        )
        self.assertEqual(
            source_types,
            {"fact": 4, "news": 15, "social": 3},
        )

    def test_missing_publication_dates_reject_only_github_and_zhihu(self) -> None:
        rejected = [record for result in self.results.values() for record in result.rejected]

        self.assertEqual({record.reason for record in rejected}, {"missing_published_at"})
        self.assertEqual(sum("GitHub" in record.heading for record in rejected), 1)
        self.assertEqual(sum("知乎" in record.heading for record in rejected), 1)

    def test_duplicate_real_estate_section_heading_does_not_create_empty_record(self) -> None:
        manifest = self.manifests["real-estate-policy"]
        paragraphs = extract_docx_paragraphs(manifest.source_document)
        blocks = split_article_blocks(paragraphs)

        repeated_sections = [
            paragraph for paragraph in paragraphs if paragraph.startswith("## 第二层：专业新闻源")
        ]
        self.assertEqual(len(repeated_sections), 2)
        self.assertEqual(len(blocks), 7)
        self.assertEqual(len(self.results["real-estate-policy"].records), 7)
        self.assertTrue(
            all(
                block.heading.strip() and any(line.strip() for line in block.lines)
                for block in blocks
            )
        )

    def test_timestamps_are_utc_and_preserve_precision_and_inference_metadata(self) -> None:
        deepseek_records = self.results["deepseek-r1"].records
        announcement = next(
            record
            for record in deepseek_records
            if record.url == "https://api-docs.deepseek.com/zh-cn/news/news250120"
        )
        update_log = next(
            record
            for record in deepseek_records
            if record.url == "https://api-docs.deepseek.com/updates"
        )
        minute_record = next(
            record
            for record in deepseek_records
            if record.url == "https://www.stcn.com/article/detail/1511051.html"
        )
        pbc_record = next(
            record
            for record in self.results["real-estate-policy"].records
            if record.source.provider == "pbc"
        )

        self.assertEqual(announcement.published_at, datetime(2025, 1, 19, 16, tzinfo=UTC))
        self.assertEqual(announcement.metadata["published_at_precision"], "date")
        self.assertIs(announcement.metadata["published_at_inferred"], True)
        self.assertNotEqual(announcement.metadata["published_at_basis"], "source_metadata")

        self.assertEqual(update_log.published_at, datetime(2025, 1, 19, 16, tzinfo=UTC))
        self.assertEqual(update_log.metadata["published_at_precision"], "date")
        self.assertIs(update_log.metadata["published_at_inferred"], False)
        self.assertEqual(update_log.metadata["published_at_basis"], "source_metadata")

        self.assertEqual(minute_record.published_at, datetime(2025, 1, 26, 23, 47, tzinfo=UTC))
        self.assertEqual(minute_record.metadata["published_at_precision"], "minute")
        self.assertIs(minute_record.metadata["published_at_inferred"], False)

        self.assertEqual(pbc_record.published_at, datetime(2025, 9, 11, 16, tzinfo=UTC))
        self.assertEqual(pbc_record.metadata["published_at_precision"], "date")
        self.assertIs(pbc_record.metadata["published_at_inferred"], True)

        for result in self.results.values():
            for record in result.records:
                self.assertEqual(record.published_at.utcoffset(), UTC.utcoffset(None))
                self.assertEqual(record.collected_at, datetime(2026, 8, 3, 16, tzinfo=UTC))
                self.assertEqual(record.metadata["collected_at_precision"], "date")

    def test_external_id_and_content_hash_are_stable_across_conversions(self) -> None:
        for manifest in self.manifests.values():
            first = convert_manifest(manifest)
            second = convert_manifest(manifest)
            first_signature = tuple(
                (record.external_id, record.content_hash) for record in first.records
            )
            second_signature = tuple(
                (record.external_id, record.content_hash) for record in second.records
            )

            self.assertEqual(first_signature, second_signature)
            self.assertEqual(len({item[0] for item in first_signature}), len(first_signature))

    def test_ingestion_payload_has_audit_times_and_no_authoritative_fields(self) -> None:
        replay_at = datetime(2026, 8, 5, 4, 30, tzinfo=UTC)
        required_times = {"published_at", "collected_at", "replay_at"}
        forbidden = {"event_id", "sentiment", "risk", "topic", "tenant_id"}

        for scenario_id, result in self.results.items():
            for sequence, record in enumerate(result.records):
                payload = record.to_ingestion_payload(
                    replay_at=replay_at,
                    scenario_id=scenario_id,
                    sequence=sequence,
                )

                self.assertTrue(required_times.issubset(payload))
                self.assertNotIn("received_at", payload)
                self.assertTrue(forbidden.isdisjoint(all_mapping_keys(payload)))
                self.assertEqual(payload["replay_at"], "2026-08-05T04:30:00Z")
                self.assertEqual(payload["source"]["stream"], f"demo:{scenario_id}")
                self.assertEqual(
                    payload["source"]["collection_method"],
                    "historical_docx_import",
                )
                self.assertEqual(
                    payload["source"]["license_scope"],
                    "unknown_internal_demo_only",
                )
                for field in required_times:
                    parsed = datetime.fromisoformat(payload[field].replace("Z", "+00:00"))
                    self.assertEqual(parsed.utcoffset(), UTC.utcoffset(None))


if __name__ == "__main__":
    unittest.main()
