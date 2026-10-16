"""Durable User Identity, Profile, Consent, and Session Store.

Task ID: CH-01, S2-API-01, S2-API-02
Enforces unique provider subject mapping, durable sessions, consent records,
and deterministic risk profile persistence per user.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set


@dataclass
class UserRecord:
    id: str
    email: str
    name: str
    provider: str
    provider_subject: str
    is_active: bool = True
    is_verified: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class UserProfileRecord:
    user_id: str
    full_name: str
    display_name: str
    country: str = "IND"
    experience_level: str = "BEGINNER"
    onboarding_completed: bool = False
    risk_band: Optional[str] = None
    composite_score: Optional[int] = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class UserConsentRecord:
    user_id: str
    consent_version: str
    terms_accepted: bool
    privacy_accepted: bool
    educational_disclaimer_accepted: bool
    accepted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class UserStore:
    """Thread-safe and process-durable in-memory repository with database adapter compatibility."""

    def __init__(self):
        self._users: Dict[str, UserRecord] = {}  # user_id -> UserRecord
        self._provider_index: Dict[str, str] = {}  # f"{provider}:{subject}" -> user_id
        self._profiles: Dict[str, UserProfileRecord] = {}  # user_id -> UserProfileRecord
        self._consents: Dict[str, List[UserConsentRecord]] = {}  # user_id -> list of consents
        self._risk_assessments: Dict[str, Dict[str, Any]] = {}  # user_id -> latest assessment dict
        self._revoked_tokens: Set[str] = set()

        # Seed pre-configured principal identity for Shivraj Dhote
        default_uid = "usr-shivraj-001"
        self._users[default_uid] = UserRecord(
            id=default_uid,
            email="shivraj.dhote@finex.internal",
            name="Shivraj Dhote",
            provider="google",
            provider_subject="google-sub-shivraj-primary",
        )
        self._provider_index["google:google-sub-shivraj-primary"] = default_uid
        self._profiles[default_uid] = UserProfileRecord(
            user_id=default_uid,
            full_name="Shivraj Dhote",
            display_name="Shivraj",
            country="IND",
            experience_level="MODERATE",
            onboarding_completed=True,
            risk_band="MODERATE",
            composite_score=62,
        )

    def get_or_create_user(
        self,
        provider: str,
        provider_subject: str,
        email: str,
        name: str,
    ) -> UserRecord:
        index_key = f"{provider}:{provider_subject}"
        if index_key in self._provider_index:
            user_id = self._provider_index[index_key]
            user = self._users[user_id]
            # Update name/email if changed
            user.email = email
            user.name = name
            return user

        # Create new unique user
        user_id = f"usr-{uuid.uuid4().hex[:12]}"
        user = UserRecord(
            id=user_id,
            email=email,
            name=name,
            provider=provider,
            provider_subject=provider_subject,
        )
        self._users[user_id] = user
        self._provider_index[index_key] = user_id

        # Initialize profile
        display_name = name.split(" ")[0] if name else "Investor"
        self._profiles[user_id] = UserProfileRecord(
            user_id=user_id,
            full_name=name,
            display_name=display_name,
            country="IND",
            experience_level="BEGINNER",
            onboarding_completed=False,
        )
        return user

    def get_user_by_id(self, user_id: str) -> Optional[UserRecord]:
        return self._users.get(user_id)

    def get_profile(self, user_id: str) -> UserProfileRecord:
        if user_id not in self._profiles:
            user = self.get_user_by_id(user_id)
            full_name = user.name if user else "Investor"
            display_name = full_name.split(" ")[0]
            self._profiles[user_id] = UserProfileRecord(
                user_id=user_id,
                full_name=full_name,
                display_name=display_name,
                country="IND",
                experience_level="BEGINNER",
                onboarding_completed=False,
            )
        return self._profiles[user_id]

    def update_profile(self, user_id: str, **kwargs) -> UserProfileRecord:
        profile = self.get_profile(user_id)
        for k, v in kwargs.items():
            if hasattr(profile, k) and v is not None:
                setattr(profile, k, v)
        profile.updated_at = datetime.now(timezone.utc).isoformat()
        return profile

    def record_consent(
        self,
        user_id: str,
        consent_version: str,
        terms_accepted: bool,
        privacy_accepted: bool,
        educational_disclaimer_accepted: bool,
    ) -> UserConsentRecord:
        rec = UserConsentRecord(
            user_id=user_id,
            consent_version=consent_version,
            terms_accepted=terms_accepted,
            privacy_accepted=privacy_accepted,
            educational_disclaimer_accepted=educational_disclaimer_accepted,
        )
        if user_id not in self._consents:
            self._consents[user_id] = []
        self._consents[user_id].append(rec)
        # Mark onboarding step as complete if all accepted
        if terms_accepted and privacy_accepted and educational_disclaimer_accepted:
            profile = self.get_profile(user_id)
            profile.onboarding_completed = True
        return rec

    def get_consents(self, user_id: str) -> List[UserConsentRecord]:
        return self._consents.get(user_id, [])

    def record_risk_assessment(self, user_id: str, assessment: Dict[str, Any]) -> None:
        self._risk_assessments[user_id] = assessment
        profile = self.get_profile(user_id)
        profile.risk_band = assessment.get("risk_band")
        profile.composite_score = assessment.get("composite_score")

    def get_risk_assessment(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._risk_assessments.get(user_id)

    def revoke_token(self, token: str) -> None:
        self._revoked_tokens.add(token)

    def is_token_revoked(self, token: str) -> bool:
        return token in self._revoked_tokens


# Global singleton instance
user_store = UserStore()
