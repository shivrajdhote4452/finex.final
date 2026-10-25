import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from backend.app.database import AsyncSessionLocal
from backend.app.models.core import RevokedToken, User, UserConsent, UserProfile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


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
    risk_assessment: Optional[Dict[str, Any]] = None
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
    """Thread-safe and process-durable repository with PostgreSQL database persistence."""

    def __init__(self):
        self._users: Dict[str, UserRecord] = {}  # user_id -> UserRecord
        self._provider_index: Dict[str, str] = {}  # f"{provider}:{subject}" -> user_id
        self._profiles: Dict[str, UserProfileRecord] = {}  # user_id -> UserProfileRecord
        self._consents: Dict[str, List[UserConsentRecord]] = {}  # user_id -> list of consents
        self._risk_assessments: Dict[str, Dict[str, Any]] = {}  # user_id -> latest assessment dict
        self._revoked_tokens: Set[str] = set()

        # Seed pre-configured principal identity for Shivraj Dhote (Platform Owner)
        default_uid = "usr-shivraj-001"
        self._users[default_uid] = UserRecord(
            id=default_uid,
            email="shivrajdhote4452@gmail.com",
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

        # Seed tenant user 2 for isolation testing
        tenant2_uid = "usr-other-002"
        self._users[tenant2_uid] = UserRecord(
            id=tenant2_uid,
            email="other.investor@finex.internal",
            name="Other Investor",
            provider="google",
            provider_subject="google-sub-other-tenant",
        )
        self._provider_index["google:google-sub-other-tenant"] = tenant2_uid
        self._profiles[tenant2_uid] = UserProfileRecord(
            user_id=tenant2_uid,
            full_name="Other Investor",
            display_name="Other",
            country="IND",
            experience_level="BEGINNER",
            onboarding_completed=False,
        )

    async def ensure_seed_users_db(self, db: Optional[AsyncSession] = None) -> None:
        """Seed default principal identities into PostgreSQL if not already present."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            for uid, urec in self._users.items():
                res = await session.execute(select(User).where(User.id == uid))
                existing_user = res.scalar_one_or_none()
                if not existing_user:
                    new_u = User(
                        id=urec.id,
                        email=urec.email,
                        provider=urec.provider,
                        provider_subject=urec.provider_subject,
                        is_active=urec.is_active,
                        is_verified=urec.is_verified,
                    )
                    session.add(new_u)
                    await session.flush()

                res_prof = await session.execute(select(UserProfile).where(UserProfile.user_id == uid))
                existing_prof = res_prof.scalar_one_or_none()
                if not existing_prof:
                    prec = self._profiles.get(uid)
                    new_prof = UserProfile(
                        id=str(uuid.uuid4()),
                        user_id=uid,
                        full_name=prec.full_name if prec else urec.name,
                        display_name=prec.display_name if prec else urec.name.split(" ")[0],
                        country=prec.country if prec else "IND",
                        experience_level=prec.experience_level if prec else "BEGINNER",
                        onboarding_completed=prec.onboarding_completed if prec else False,
                        risk_band=prec.risk_band if prec else None,
                        composite_score=prec.composite_score if prec else None,
                    )
                    session.add(new_prof)
                    await session.flush()
            if owns_session:
                await session.commit()
        except Exception:
            if owns_session:
                await session.rollback()
            raise
        finally:
            if owns_session:
                await session.close()

    async def get_or_create_user_db(
        self,
        provider: str,
        provider_subject: str,
        email: str,
        name: str,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> UserRecord:
        """Find or create persistent user record in PostgreSQL."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            # Query by provider + subject or by email
            stmt = select(User).where((User.provider == provider) & (User.provider_subject == provider_subject))
            res = await session.execute(stmt)
            user_entity = res.scalar_one_or_none()

            if not user_entity:
                # Also check by email to prevent duplicate accounts
                res_email = await session.execute(select(User).where(User.email == email))
                user_entity = res_email.scalar_one_or_none()

            if user_entity:
                user_id = user_entity.id
                # Backfill missing/placeholder email on existing user without overwriting valid email with blank
                incoming_email = email.strip() if email else ""
                if (
                    not user_entity.email or "@google.user" in user_entity.email or "@finex.local" in user_entity.email
                ) and incoming_email:
                    user_entity.email = incoming_email
                    await session.flush()

                # Check and backfill UserProfile
                res_prof = await session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
                user_prof = res_prof.scalar_one_or_none()
                incoming_name = name.strip() if name else ""

                if not user_prof:
                    display_name = incoming_name.split(" ")[0] if incoming_name else "Investor"
                    user_prof = UserProfile(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        full_name=incoming_name or "Investor",
                        display_name=display_name,
                        country="IND",
                        experience_level="BEGINNER",
                        onboarding_completed=False,
                    )
                    session.add(user_prof)
                    await session.flush()
                else:
                    if (
                        incoming_name
                        and incoming_name != "Investor"
                        and (not user_prof.full_name or user_prof.full_name == "Investor")
                    ):
                        user_prof.full_name = incoming_name
                        if not user_prof.display_name or user_prof.display_name == "Investor":
                            user_prof.display_name = incoming_name.split(" ")[0]
                        await session.flush()

                if owns_session:
                    await session.commit()

                final_name = (
                    (user_prof.full_name if user_prof and user_prof.full_name else None)
                    or incoming_name
                    or user_entity.email.split("@")[0]
                )
                user_rec = UserRecord(
                    id=user_id,
                    email=user_entity.email,
                    name=final_name,
                    provider=user_entity.provider,
                    provider_subject=user_entity.provider_subject,
                    is_active=user_entity.is_active,
                    is_verified=user_entity.is_verified,
                )
                self._users[user_id] = user_rec
                self._provider_index[f"{provider}:{provider_subject}"] = user_id
                if user_prof:
                    self._profiles[user_id] = UserProfileRecord(
                        user_id=user_id,
                        full_name=user_prof.full_name or final_name,
                        display_name=user_prof.display_name or final_name.split(" ")[0],
                        country=user_prof.country or "IND",
                        experience_level=user_prof.experience_level or "BEGINNER",
                        onboarding_completed=user_prof.onboarding_completed,
                    )
                return user_rec

            # Create new user: persist verified name and email
            uid = user_id or f"usr-{uuid.uuid4().hex[:12]}"
            clean_email = email.strip() if email else f"{uid}@finex.local"
            clean_name = name.strip() if name else "Investor"
            new_user = User(
                id=uid,
                email=clean_email,
                provider=provider,
                provider_subject=provider_subject,
                is_active=True,
                is_verified=True,
            )
            session.add(new_user)
            await session.flush()

            # Create initial profile with captured name
            display_name = clean_name.split(" ")[0] if clean_name else "Investor"
            new_profile = UserProfile(
                id=str(uuid.uuid4()),
                user_id=uid,
                full_name=clean_name,
                display_name=display_name,
                country="IND",
                experience_level="BEGINNER",
                onboarding_completed=False,
            )
            session.add(new_profile)
            if owns_session:
                await session.commit()

            user_rec = UserRecord(
                id=uid,
                email=clean_email,
                name=clean_name,
                provider=provider,
                provider_subject=provider_subject,
                is_active=True,
                is_verified=True,
            )
            self._users[uid] = user_rec
            self._provider_index[f"{provider}:{provider_subject}"] = uid
            self._profiles[uid] = UserProfileRecord(
                user_id=uid,
                full_name=clean_name,
                display_name=display_name,
                country="IND",
                experience_level="BEGINNER",
                onboarding_completed=False,
            )
            return user_rec
        except Exception as e:
            if owns_session:
                try:
                    await session.rollback()
                except Exception:
                    pass
            logger.warning(f"Database query failed in get_or_create_user_db: {e}. Falling back to memory store.")
            return self.get_or_create_user(
                provider=provider,
                provider_subject=provider_subject,
                email=email,
                name=name,
                user_id=user_id,
            )
        finally:
            if owns_session:
                try:
                    await session.close()
                except Exception:
                    pass

    async def get_user_by_id_db(self, user_id: str, db: Optional[AsyncSession] = None) -> Optional[UserRecord]:
        """Fetch user record from PostgreSQL by ID with memory fallback."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            res = await session.execute(select(User).where(User.id == user_id))
            u = res.scalar_one_or_none()
            if u:
                res_prof = await session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
                p = res_prof.scalar_one_or_none()
                resolved_name = (p.full_name if p and p.full_name else None) or (
                    self._users[u.id].name if u.id in self._users and self._users[u.id].name else u.email.split("@")[0]
                )
                rec = UserRecord(
                    id=u.id,
                    email=u.email,
                    name=resolved_name,
                    provider=u.provider,
                    provider_subject=u.provider_subject,
                    is_active=u.is_active,
                    is_verified=u.is_verified,
                )
                self._users[u.id] = rec
                return rec
            return self._users.get(user_id)
        except Exception as e:
            logger.warning(f"Database unavailable for get_user_by_id ({e}). Using memory store.")
            return self._users.get(user_id)
        finally:
            if owns_session:
                try:
                    await session.close()
                except Exception:
                    pass

    async def get_profile_db(self, user_id: str, db: Optional[AsyncSession] = None) -> UserProfileRecord:
        """Fetch investor profile from PostgreSQL with memory fallback."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            res = await session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
            p = res.scalar_one_or_none()
            if p:
                rec = UserProfileRecord(
                    user_id=p.user_id,
                    full_name=p.full_name or "Investor",
                    display_name=p.display_name or "Investor",
                    country=p.country,
                    experience_level=p.experience_level,
                    onboarding_completed=p.onboarding_completed,
                    risk_band=p.risk_band,
                    composite_score=int(p.composite_score) if p.composite_score is not None else None,
                    risk_assessment=p.risk_assessment,
                )
                self._profiles[user_id] = rec
                return rec
            return self.get_profile(user_id)
        except Exception as e:
            logger.warning(f"Database unavailable for get_profile ({e}). Using memory store.")
            return self.get_profile(user_id)
        finally:
            if owns_session:
                try:
                    await session.close()
                except Exception:
                    pass

    async def record_consent_db(
        self,
        user_id: str,
        consent_version: str,
        terms_accepted: bool,
        privacy_accepted: bool,
        educational_disclaimer_accepted: bool,
        db: Optional[AsyncSession] = None,
    ) -> UserConsentRecord:
        """Persist explicit user consent with memory fallback."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            # Ensure user exists in users table first
            res_u = await session.execute(select(User).where(User.id == user_id))
            if not res_u.scalar_one_or_none():
                new_u = User(
                    id=user_id,
                    email=f"{user_id}@finex.local",
                    provider="internal",
                    provider_subject=user_id,
                    is_active=True,
                    is_verified=True,
                )
                session.add(new_u)
                await session.flush()

            stmt_c = select(UserConsent).where(
                UserConsent.user_id == user_id,
                UserConsent.consent_version == consent_version,
            )
            res_c = await session.execute(stmt_c)
            consent = res_c.scalar_one_or_none()
            if consent:
                consent.terms_accepted = terms_accepted
                consent.privacy_accepted = privacy_accepted
                consent.educational_disclaimer_accepted = educational_disclaimer_accepted
                consent.accepted_at = datetime.now(timezone.utc)
            else:
                consent = UserConsent(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    consent_version=consent_version,
                    terms_accepted=terms_accepted,
                    privacy_accepted=privacy_accepted,
                    educational_disclaimer_accepted=educational_disclaimer_accepted,
                    accepted_at=datetime.now(timezone.utc),
                )
                session.add(consent)
            if owns_session:
                await session.commit()

            rec = UserConsentRecord(
                user_id=user_id,
                consent_version=consent_version,
                terms_accepted=terms_accepted,
                privacy_accepted=privacy_accepted,
                educational_disclaimer_accepted=educational_disclaimer_accepted,
            )
            self._consents.setdefault(user_id, []).append(rec)
            return rec
        except Exception as e:
            if owns_session:
                try:
                    await session.rollback()
                except Exception:
                    pass
            logger.warning(f"Database unavailable for record_consent ({e}). Using memory store.")
            return self.record_consent(
                user_id=user_id,
                consent_version=consent_version,
                terms_accepted=terms_accepted,
                privacy_accepted=privacy_accepted,
                educational_disclaimer_accepted=educational_disclaimer_accepted,
            )
        finally:
            if owns_session:
                try:
                    await session.close()
                except Exception:
                    pass

    async def record_risk_assessment_db(
        self,
        user_id: str,
        assessment: Dict[str, Any],
        db: Optional[AsyncSession] = None,
    ) -> None:
        """Persist completed risk assessment with memory fallback."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            res_u = await session.execute(select(User).where(User.id == user_id))
            if not res_u.scalar_one_or_none():
                new_u = User(
                    id=user_id,
                    email=f"{user_id}@finex.local",
                    provider="internal",
                    provider_subject=user_id,
                    is_active=True,
                    is_verified=True,
                )
                session.add(new_u)
                await session.flush()
            risk_band = assessment.get("risk_band")
            composite_score = assessment.get("composite_score")

            res = await session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
            prof = res.scalar_one_or_none()
            if prof:
                prof.risk_band = risk_band
                prof.composite_score = composite_score
                prof.risk_assessment = assessment
                prof.onboarding_completed = True
                prof.updated_at = datetime.now(timezone.utc)
            else:
                prof = UserProfile(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    full_name="Investor",
                    display_name="Investor",
                    country="IND",
                    experience_level="BEGINNER",
                    risk_band=risk_band,
                    composite_score=composite_score,
                    risk_assessment=assessment,
                    onboarding_completed=True,
                )
                session.add(prof)

            if owns_session:
                await session.commit()

            self._risk_assessments[user_id] = assessment
            p = self.get_profile(user_id)
            p.risk_band = risk_band
            p.composite_score = composite_score
            p.risk_assessment = assessment
            p.onboarding_completed = True
        except Exception as e:
            if owns_session:
                try:
                    await session.rollback()
                except Exception:
                    pass
            logger.warning(f"Database unavailable for record_risk_assessment ({e}). Using memory store.")
            self.record_risk_assessment(user_id, assessment)
        finally:
            if owns_session:
                try:
                    await session.close()
                except Exception:
                    pass

    async def revoke_token_db(
        self,
        token: str,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> None:
        """Persist revoked token with memory fallback."""
        self._revoked_tokens.add(token)
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            res = await session.execute(select(RevokedToken).where(RevokedToken.token == token))
            if not res.scalar_one_or_none():
                entry = RevokedToken(
                    id=str(uuid.uuid4()),
                    token=token,
                    user_id=user_id,
                    revoked_at=datetime.now(timezone.utc),
                )
                session.add(entry)
                if owns_session:
                    await session.commit()
        except Exception as e:
            if owns_session:
                try:
                    await session.rollback()
                except Exception:
                    pass
            logger.warning(f"Database unavailable for revoke_token ({e}). Using memory store.")
        finally:
            if owns_session:
                try:
                    await session.close()
                except Exception:
                    pass

    async def is_token_revoked_db(self, token: str, db: Optional[AsyncSession] = None) -> bool:
        """Check token revocation against memory and PostgreSQL database."""
        if token in self._revoked_tokens:
            return True
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            res = await session.execute(select(RevokedToken).where(RevokedToken.token == token))
            if res.scalar_one_or_none() is not None:
                self._revoked_tokens.add(token)
                return True
            return False
        except Exception as e:
            logger.debug(f"Database check in is_token_revoked failed: {e}. Using memory revocation list.")
            return token in self._revoked_tokens
        finally:
            if owns_session:
                try:
                    await session.close()
                except Exception:
                    pass

    # Synchronous adapter methods for backward compatibility
    def get_or_create_user(
        self,
        provider: str,
        provider_subject: str,
        email: str,
        name: str,
        user_id: Optional[str] = None,
    ) -> UserRecord:
        index_key = f"{provider}:{provider_subject}"
        if index_key in self._provider_index:
            existing_uid = self._provider_index[index_key]
            user = self._users[existing_uid]
            incoming_email = email.strip() if email else ""
            if (not user.email or "@google.user" in user.email or "@finex.local" in user.email) and incoming_email:
                user.email = incoming_email
            incoming_name = name.strip() if name else ""
            if incoming_name and incoming_name != "Investor" and (not user.name or user.name == "Investor"):
                user.name = incoming_name
            prof = self._profiles.get(existing_uid)
            if prof:
                if (
                    incoming_name
                    and incoming_name != "Investor"
                    and (not prof.full_name or prof.full_name == "Investor")
                ):
                    prof.full_name = incoming_name
                    if not prof.display_name or prof.display_name == "Investor":
                        prof.display_name = incoming_name.split(" ")[0]
            return user

        uid = user_id or f"usr-{uuid.uuid4().hex[:12]}"
        clean_email = email.strip() if email else f"{uid}@finex.local"
        clean_name = name.strip() if name else "Investor"
        user = UserRecord(
            id=uid,
            email=clean_email,
            name=clean_name,
            provider=provider,
            provider_subject=provider_subject,
        )
        self._users[uid] = user
        self._provider_index[index_key] = uid

        display_name = clean_name.split(" ")[0] if clean_name else "Investor"
        self._profiles[uid] = UserProfileRecord(
            user_id=uid,
            full_name=clean_name,
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
        # Onboarding is NOT complete merely because consent is accepted!
        return rec

    def get_consents(self, user_id: str) -> List[UserConsentRecord]:
        return self._consents.get(user_id, [])

    def record_risk_assessment(self, user_id: str, assessment: Dict[str, Any]) -> None:
        self._risk_assessments[user_id] = assessment
        profile = self.get_profile(user_id)
        profile.risk_band = assessment.get("risk_band")
        profile.composite_score = assessment.get("composite_score")
        profile.risk_assessment = assessment
        profile.onboarding_completed = True

    def get_risk_assessment(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._risk_assessments.get(user_id)

    def revoke_token(self, token: str) -> None:
        self._revoked_tokens.add(token)

    def is_token_revoked(self, token: str) -> bool:
        return token in self._revoked_tokens


# Global singleton instance
user_store = UserStore()
