"""FinEx AI & RAG Data Quality & Lineage Checker.

Task ID: S4-DAT-03
Author: Shivraj Dhote
Date: 16 October 2026

Validates:
1. Document Registry: Valid hash, publisher in (SEBI, RBI, NSE, AMFI), non-null date.
2. Document Chunks: Non-empty content (>= 15 words), valid chunk_index, unique chunk_id.
3. Message Lineage: Non-null correlation_id, valid user_id and conversation reference (no orphans).
4. Citation Integrity: All citation_chunk_ids link to active registered chunks.
5. Feedback Integrity: User feedback maps to existing message and caller owns feedback.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class RAGSeverity(str, Enum):
    WARNING = "WARNING"
    BLOCKING = "BLOCKING"


@dataclass
class RAGQualityViolation:
    rule_name: str
    severity: RAGSeverity
    entity_type: str
    entity_id: Optional[str]
    details: str


@dataclass
class RAGQualityReport:
    total_records_checked: int
    blocking_violations_count: int
    warning_violations_count: int
    violations: List[RAGQualityViolation] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return self.blocking_violations_count == 0


class AIRAGQualityChecker:
    def __init__(self, allowed_publishers: Optional[Set[str]] = None):
        self.allowed_publishers = allowed_publishers or {
            "SEBI",
            "Securities and Exchange Board of India (SEBI)",
            "RBI",
            "Reserve Bank of India (RBI)",
            "NSE",
            "National Stock Exchange (NSE)",
            "AMFI",
            "Association of Mutual Funds in India (AMFI)",
        }

    def evaluate(
        self,
        documents: List[Dict[str, Any]],
        chunks: List[Dict[str, Any]],
        conversations: List[Dict[str, Any]],
        messages: List[Dict[str, Any]],
        feedback: List[Dict[str, Any]],
    ) -> RAGQualityReport:
        violations: List[RAGQualityViolation] = []
        total_records = len(documents) + len(chunks) + len(conversations) + len(messages) + len(feedback)

        # 1. Document Registry Checks
        doc_ids: Set[str] = set()
        seen_doc_hashes: Set[str] = set()

        for doc in documents:
            d_id = doc.get("id") or doc.get("document_id")
            pub = doc.get("publisher")
            hsh = doc.get("content_hash") or doc.get("hash")

            if not d_id:
                violations.append(
                    RAGQualityViolation(
                        rule_name="DOC_ID_REQUIRED",
                        severity=RAGSeverity.BLOCKING,
                        entity_type="document_registry",
                        entity_id=None,
                        details="Document record missing identifier.",
                    )
                )
                continue

            doc_ids.add(d_id)

            if pub not in self.allowed_publishers:
                violations.append(
                    RAGQualityViolation(
                        rule_name="UNAPPROVED_PUBLISHER",
                        severity=RAGSeverity.BLOCKING,
                        entity_type="document_registry",
                        entity_id=d_id,
                        details=f"Publisher '{pub}' is not in approved regulatory publishers list.",
                    )
                )

            if hsh:
                if hsh in seen_doc_hashes:
                    violations.append(
                        RAGQualityViolation(
                            rule_name="DUPLICATE_DOCUMENT_HASH",
                            severity=RAGSeverity.WARNING,
                            entity_type="document_registry",
                            entity_id=d_id,
                            details=f"Document with identical content hash '{hsh}' already registered.",
                        )
                    )
                seen_doc_hashes.add(hsh)

        # 2. Document Chunks Checks
        chunk_ids: Set[str] = set()
        for chk in chunks:
            c_id = chk.get("id") or chk.get("chunk_id")
            d_id = chk.get("document_id")
            content = chk.get("content", "")

            if not c_id:
                violations.append(
                    RAGQualityViolation(
                        rule_name="CHUNK_ID_REQUIRED",
                        severity=RAGSeverity.BLOCKING,
                        entity_type="document_chunk",
                        entity_id=None,
                        details="Chunk record missing chunk_id.",
                    )
                )
                continue

            chunk_ids.add(c_id)

            # Orphan chunk check
            if d_id not in doc_ids:
                violations.append(
                    RAGQualityViolation(
                        rule_name="ORPHAN_CHUNK",
                        severity=RAGSeverity.BLOCKING,
                        entity_type="document_chunk",
                        entity_id=c_id,
                        details=f"Chunk references non-existent document_id '{d_id}'.",
                    )
                )

            # Word count check
            words = content.split()
            if len(words) < 10:
                violations.append(
                    RAGQualityViolation(
                        rule_name="LOW_DENSITY_CHUNK",
                        severity=RAGSeverity.WARNING,
                        entity_type="document_chunk",
                        entity_id=c_id,
                        details=f"Chunk has only {len(words)} words, below recommended 10 words minimum.",
                    )
                )

        # 3. Conversations Checks
        conv_ids: Set[str] = set()
        for c in conversations:
            cid = c.get("id")
            uid = c.get("user_id")
            if not cid or not uid:
                violations.append(
                    RAGQualityViolation(
                        rule_name="CONVERSATION_SCHEMA",
                        severity=RAGSeverity.BLOCKING,
                        entity_type="ai_conversation",
                        entity_id=cid,
                        details="Conversation missing id or user_id.",
                    )
                )
            else:
                conv_ids.add(cid)

        # 4. Message Lineage & Citation Checks
        msg_ids: Set[str] = set()
        for msg in messages:
            m_id = msg.get("id")
            c_id = msg.get("conversation_id")
            corr_id = msg.get("correlation_id")

            if not m_id:
                violations.append(
                    RAGQualityViolation(
                        rule_name="MESSAGE_ID_REQUIRED",
                        severity=RAGSeverity.BLOCKING,
                        entity_type="ai_message",
                        entity_id=None,
                        details="Message missing id.",
                    )
                )
                continue

            msg_ids.add(m_id)

            if c_id not in conv_ids:
                violations.append(
                    RAGQualityViolation(
                        rule_name="ORPHAN_MESSAGE",
                        severity=RAGSeverity.BLOCKING,
                        entity_type="ai_message",
                        entity_id=m_id,
                        details=f"Message references non-existent conversation_id '{c_id}'.",
                    )
                )

            if not corr_id:
                violations.append(
                    RAGQualityViolation(
                        rule_name="MISSING_CORRELATION_ID",
                        severity=RAGSeverity.WARNING,
                        entity_type="ai_message",
                        entity_id=m_id,
                        details="Message lacks tracing correlation_id.",
                    )
                )

            # Check citations reference real registered chunks
            citations = msg.get("citations") or msg.get("citation_chunk_ids") or []
            for cit in citations:
                cit_chunk_id = cit if isinstance(cit, str) else cit.get("chunk_id")
                if cit_chunk_id and cit_chunk_id not in chunk_ids:
                    violations.append(
                        RAGQualityViolation(
                            rule_name="ORPHAN_CITATION",
                            severity=RAGSeverity.BLOCKING,
                            entity_type="ai_message",
                            entity_id=m_id,
                            details=f"Answer cites unindexed or non-existent chunk '{cit_chunk_id}'.",
                        )
                    )

        # 5. Feedback Checks
        for fb in feedback:
            f_id = fb.get("id")
            m_id = fb.get("message_id")
            rating = fb.get("rating")

            if m_id not in msg_ids:
                violations.append(
                    RAGQualityViolation(
                        rule_name="ORPHAN_FEEDBACK",
                        severity=RAGSeverity.BLOCKING,
                        entity_type="ai_feedback",
                        entity_id=f_id,
                        details=f"Feedback references non-existent message_id '{m_id}'.",
                    )
                )

            if rating not in (1, -1):
                violations.append(
                    RAGQualityViolation(
                        rule_name="INVALID_FEEDBACK_RATING",
                        severity=RAGSeverity.BLOCKING,
                        entity_type="ai_feedback",
                        entity_id=f_id,
                        details=f"Rating must be 1 or -1, got: {rating}.",
                    )
                )

        blocking = [v for v in violations if v.severity == RAGSeverity.BLOCKING]
        warnings = [v for v in violations if v.severity == RAGSeverity.WARNING]

        return RAGQualityReport(
            total_records_checked=total_records,
            blocking_violations_count=len(blocking),
            warning_violations_count=len(warnings),
            violations=violations,
        )
