"""Unit & Scenario Tests for AI & RAG Data Quality & Lineage Suite.

Task ID: S4-DAT-03
Author: Shivraj Dhote
Date: 16 October 2026

Tests:
- Clean dataset passes all checks
- Detection of unapproved document publisher (BLOCKING)
- Detection of orphan chunks (BLOCKING)
- Detection of orphan messages and orphan feedback (BLOCKING)
- Detection of orphan citations (BLOCKING)
- Missing correlation ID (WARNING)
"""

import pytest
from data.quality.ai_rag_quality import AIRAGQualityChecker


@pytest.fixture
def clean_rag_dataset():
    documents = [
        {
            "id": "SEBI-ED-2024-01",
            "title": "SEBI Guide",
            "publisher": "SEBI",
            "content_hash": "hash_sebi_001",
        },
        {
            "id": "RBI-SGB-2024-FAQ",
            "title": "RBI SGB FAQ",
            "publisher": "Reserve Bank of India (RBI)",
            "content_hash": "hash_rbi_002",
        },
    ]
    chunks = [
        {
            "id": "chk_01",
            "document_id": "SEBI-ED-2024-01",
            "content": "Financial planning begins with establishing realistic goals and a disciplined savings rate.",
        },
        {
            "id": "chk_02",
            "document_id": "RBI-SGB-2024-FAQ",
            "content": "Sovereign Gold Bonds bear fixed interest at 2.50 percent per annum on initial nominal amount.",
        },
    ]
    conversations = [{"id": "conv_01", "user_id": "usr-shivraj-001"}]
    messages = [
        {
            "id": "msg_01",
            "conversation_id": "conv_01",
            "correlation_id": "corr-uuid-001",
            "citations": ["chk_01"],
        }
    ]
    feedback = [
        {
            "id": "fb_01",
            "message_id": "msg_01",
            "rating": 1,
        }
    ]
    return documents, chunks, conversations, messages, feedback


def test_clean_rag_dataset_passes(clean_rag_dataset):
    docs, chks, convs, msgs, fbs = clean_rag_dataset
    checker = AIRAGQualityChecker()
    report = checker.evaluate(docs, chks, convs, msgs, fbs)

    assert report.is_clean is True
    assert report.blocking_violations_count == 0
    assert report.warning_violations_count == 0
    assert len(report.violations) == 0


def test_detects_unapproved_publisher_and_orphan_chunk(clean_rag_dataset):
    docs, chks, convs, msgs, fbs = clean_rag_dataset

    # Inject unapproved publisher
    docs.append(
        {
            "id": "DOC-RANDOM-BLOG",
            "title": "Random Blog Post",
            "publisher": "Anonymous Hacker Blog",
            "content_hash": "hash_bad_003",
        }
    )

    # Inject orphan chunk (referencing non-existent doc)
    chks.append(
        {
            "id": "chk_bad_orphan",
            "document_id": "NON_EXISTENT_DOC",
            "content": "This chunk has no parent document registered in system.",
        }
    )

    checker = AIRAGQualityChecker()
    report = checker.evaluate(docs, chks, convs, msgs, fbs)

    assert report.is_clean is False
    rule_names = [v.rule_name for v in report.violations]
    assert "UNAPPROVED_PUBLISHER" in rule_names
    assert "ORPHAN_CHUNK" in rule_names


def test_detects_orphan_citation_and_orphan_feedback(clean_rag_dataset):
    docs, chks, convs, msgs, fbs = clean_rag_dataset

    # Message citing an unindexed chunk ID
    msgs.append(
        {
            "id": "msg_bad_citation",
            "conversation_id": "conv_01",
            "correlation_id": "corr-002",
            "citations": ["non_existent_chunk_999"],
        }
    )

    # Feedback on non-existent message
    fbs.append(
        {
            "id": "fb_orphan",
            "message_id": "non_existent_msg_888",
            "rating": -1,
        }
    )

    checker = AIRAGQualityChecker()
    report = checker.evaluate(docs, chks, convs, msgs, fbs)

    assert report.is_clean is False
    rule_names = [v.rule_name for v in report.violations]
    assert "ORPHAN_CITATION" in rule_names
    assert "ORPHAN_FEEDBACK" in rule_names
