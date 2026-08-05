"""Live source adapters built around the unified SourceRecord contract."""

from risktrace.ingestion.adapters.a_share import (
    CailianpressTelegraphAdapter,
    CailianpressTelegraphClient,
    TencentQuoteAdapter,
    TencentQuoteClient,
)
from risktrace.ingestion.adapters.base import AdapterHealth, SourceAdapter
from risktrace.ingestion.adapters.snowball import SnowballClient, SnowballHotPostsAdapter

__all__ = [
    "AdapterHealth",
    "CailianpressTelegraphAdapter",
    "CailianpressTelegraphClient",
    "SnowballClient",
    "SnowballHotPostsAdapter",
    "SourceAdapter",
    "TencentQuoteAdapter",
    "TencentQuoteClient",
]
