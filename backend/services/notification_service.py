"""Notification Service

E-1 Enhancement: Webhook/email notification system for faculty risk threshold alerts.

This module provides async notification capabilities for faculty when students
cross HIGH (70) or CRITICAL (85) risk thresholds.

Notification failure is always caught and logged — never crashes prediction generation.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import httpx
from sqlalchemy.orm import Session
from redis.asyncio import Redis as AsyncRedis

from backend.database.models.faculty_notification_pref import FacultyNotificationPref
from backend.database.models.user import User
from backend.database.models.student import Student
from backend.database.models.goals_and_risks import RiskSnapshot
from backend.config import REDIS_URL

logger = logging.getLogger(__name__)

# Risk thresholds
HIGH_RISK_THRESHOLD = 70.0
CRITICAL_RISK_THRESHOLD = 85.0

# Redis key template for deduplication
NOTIFICATION_DEDUP_KEY = "notification:dedup:{user_id}:{student_id}"


class NotificationService:
    """Service for sending risk threshold notifications to faculty.

    Supports two notification channels:
    - email: Via HTTP POST to configured email provider (SendGrid/SMTP relay)
    - webhook: Via HTTP POST to user-configured webhook URL

    Features:
    - Cooldown-based deduplication (per-user, per-student)
    - Redis-backed state for distributed deployments
    - Graceful failure handling (logs only, never crashes callers)
    """

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client with reasonable timeouts."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._client

    async def _get_redis(self) -> Optional[AsyncRedis]:
        """Get async Redis client if available."""
        try:
            client = AsyncRedis.from_url(REDIS_URL, decode_responses=True)
            await client.ping()  # type: ignore[misc]
            return client
        except Exception:
            return None

    def _get_dedup_key(self, user_id: int, student_id: str) -> str:
        """Generate Redis key for notification deduplication."""
        return NOTIFICATION_DEDUP_KEY.format(user_id=user_id, student_id=student_id)

    async def _is_cooldown_active(
        self,
        pref: FacultyNotificationPref,
        student_id: str,
        redis_client: Optional[AsyncRedis],
    ) -> bool:
        """Check if notification is within cooldown period.

        First checks Redis (fast, distributed), then falls back to DB record.
        """
        now = datetime.now(timezone.utc)
        cooldown_seconds = (pref.cooldown_hours or 24) * 3600  # type: ignore[operator]

        # Check Redis first (distributed cache)
        if redis_client:
            try:
                dedup_key = self._get_dedup_key(pref.user_id or 0, student_id)  # type: ignore[arg-type]
                last_sent_str = await redis_client.get(dedup_key)
                if last_sent_str:
                    last_sent = datetime.fromisoformat(last_sent_str)
                    if (now - last_sent).total_seconds() < cooldown_seconds:
                        return True
            except Exception as exc:
                logger.warning(f"[NOTIFICATION] Redis dedup check failed: {exc}")

        # Fallback to DB check
        if pref.last_notified_at:
            if (now - pref.last_notified_at).total_seconds() < cooldown_seconds:
                return True

        return False

    async def _update_last_notified(
        self,
        pref: FacultyNotificationPref,
        student_id: str,
        db: Session,
        redis_client: Optional[AsyncRedis],
    ) -> None:
        """Update last_notified_at timestamp in both DB and Redis."""
        now = datetime.now(timezone.utc)
        pref.last_notified_at = now

        # Update Redis for distributed deduplication
        if redis_client:
            try:
                dedup_key = self._get_dedup_key(pref.user_id or 0, student_id)  # type: ignore[arg-type]
                ttl_seconds = (pref.cooldown_hours or 24) * 3600  # type: ignore[operator]
                await redis_client.setex(dedup_key, ttl_seconds, now.isoformat())
            except Exception as exc:
                logger.warning(f"[NOTIFICATION] Redis dedup update failed: {exc}")

        # Commit DB update
        try:
            db.add(pref)
            db.commit()
        except Exception as exc:
            logger.error(f"[NOTIFICATION] Failed to update last_notified_at: {exc}")
            db.rollback()

    def _build_payload(
        self,
        student_id: str,
        risk_score: float,
        previous_score: Optional[float],
        category: str,
        faculty_name: str,
    ) -> Dict[str, Any]:
        """Build notification payload."""
        now = datetime.now(timezone.utc)
        return {
            "event": "risk_threshold_crossed",
            "student_id": student_id,
            "risk_score": round(risk_score, 2),
            "previous_score": (
                round(previous_score, 2) if previous_score is not None else None
            ),
            "category": category,  # "high" or "critical"
            "threshold_crossed": (
                HIGH_RISK_THRESHOLD if category == "high" else CRITICAL_RISK_THRESHOLD
            ),
            "timestamp": now.isoformat(),
            "faculty": faculty_name,
        }

    async def _send_email_notification(
        self,
        pref: FacultyNotificationPref,
        user: User,
        payload: Dict[str, Any],
    ) -> bool:
        """Send email notification via HTTP POST to email provider.

        Uses SendGrid API if SENDGRID_API_KEY is configured, otherwise
        falls back to configured SMTP relay endpoint.

        Returns True if sent successfully, False otherwise.
        """
        import os

        api_key = os.getenv("SENDGRID_API_KEY")
        email_endpoint = os.getenv(
            "EMAIL_ENDPOINT", "https://api.sendgrid.com/v3/mail/send"
        )
        from_email = os.getenv("NOTIFICATION_FROM_EMAIL", "alerts@ews-platform.edu")

        target_email = pref.email_override or user.email
        if not target_email:
            logger.warning(f"[NOTIFICATION] No email for user {user.id}")
            return False

        subject = f"🚨 Risk Alert: {payload['category'].upper()} Risk Student"
        content_text = (
            f"Risk threshold alert:\n\n"
            f"Student: {payload['student_id']}\n"
            f"Current Risk Score: {payload['risk_score']}\n"
            f"Previous Risk Score: {payload['previous_score'] or 'N/A'}\n"
            f"Category: {payload['category'].upper()}\n"
            f"Time: {payload['timestamp']}\n"
        )

        try:
            client = await self._get_client()

            if api_key:
                # SendGrid API
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                data = {
                    "personalizations": [{"to": [{"email": target_email}]}],
                    "from": {"email": from_email},
                    "subject": subject,
                    "content": [{"type": "text/plain", "value": content_text}],
                }
                response = await client.post(email_endpoint, headers=headers, json=data)
            else:
                # Generic SMTP relay / webhook
                data = {
                    "to": target_email,
                    "from": from_email,
                    "subject": subject,
                    "text": content_text,
                    **payload,
                }
                response = await client.post(email_endpoint, json=data)

            if response.status_code in (200, 201, 202, 204):
                logger.info(
                    f"[NOTIFICATION] Email sent to {target_email} for student {payload['student_id']}"
                )
                return True
            else:
                logger.warning(
                    f"[NOTIFICATION] Email failed: HTTP {response.status_code} - {response.text[:200]}"
                )
                return False

        except Exception as exc:
            logger.exception(f"[NOTIFICATION] Email send failed: {exc}")
            return False

    async def _send_webhook_notification(
        self,
        pref: FacultyNotificationPref,
        payload: Dict[str, Any],
    ) -> bool:
        """Send webhook notification via HTTP POST to configured webhook URL.

        Returns True if sent successfully, False otherwise.
        """
        if not pref.webhook_url:
            logger.warning(
                f"[NOTIFICATION] No webhook_url configured for user {pref.user_id}"
            )
            return False

        try:
            client = await self._get_client()

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "EWS-Retention-Platform/2.1",
                "X-EWS-Event": "risk_threshold_crossed",
            }

            # Add optional signature if WEBHOOK_SECRET is configured
            import os
            import hmac
            import hashlib
            import json

            webhook_secret = os.getenv("WEBHOOK_SECRET")
            if webhook_secret:
                payload_bytes = json.dumps(payload, sort_keys=True).encode()
                signature = hmac.new(
                    webhook_secret.encode(), payload_bytes, hashlib.sha256
                ).hexdigest()
                headers["X-EWS-Signature"] = f"sha256={signature}"

            response = await client.post(
                pref.webhook_url,
                headers=headers,
                json=payload,
            )

            if response.status_code in (200, 201, 202, 204):
                logger.info(
                    f"[NOTIFICATION] Webhook sent to {pref.webhook_url} "
                    f"for student {payload['student_id']}"
                )
                return True
            else:
                logger.warning(
                    f"[NOTIFICATION] Webhook failed: HTTP {response.status_code} - {response.text[:200]}"
                )
                return False

        except Exception as exc:
            logger.exception(f"[NOTIFICATION] Webhook send failed: {exc}")
            return False

    async def _get_previous_risk_score(
        self,
        student_id: str,
        current_week: Optional[int],
        db: Session,
    ) -> Optional[float]:
        """Get the previous risk score for a student from RiskSnapshot history."""
        try:
            # Get the most recent snapshot before current week
            _base_q = db.query(RiskSnapshot).filter(
                RiskSnapshot.student_id == student_id
            )
            if current_week is not None:
                _base_q = _base_q.filter(RiskSnapshot.week_number < current_week)
            previous_snapshot = _base_q.order_by(RiskSnapshot.timestamp.desc()).first()
            if previous_snapshot and previous_snapshot.risk_score is not None:
                return float(previous_snapshot.risk_score)
            return None
        except Exception as exc:
            logger.warning(f"[NOTIFICATION] Failed to get previous risk score: {exc}")
            return None

    async def notify_risk_threshold_crossed(
        self,
        student_id: str,
        risk_score: float,
        prev_score: Optional[float],
        db: Session,
        redis_client: Optional[AsyncRedis] = None,
    ) -> List[Dict[str, Any]]:
        """Send notifications to faculty when a student crosses risk thresholds.

        This is the main entry point called by the scheduler after computing
        each student's risk score.

        Args:
            student_id: The student identifier
            risk_score: Current computed risk score (0-100)
            prev_score: Previous risk score for comparison (optional)
            db: Database session for queries and updates
            redis_client: Optional Redis client for distributed deduplication

        Returns:
            List of notification results with status for each faculty notified

        Behavior:
        - Skips if risk_score doesn't cross HIGH (70) or CRITICAL (85) threshold
        - Checks cooldown period per faculty before sending
        - Routes to email or webhook based on faculty preference
        - Updates last_notified_at on success
        - Logs all failures but never raises exceptions
        """
        results: List[Dict[str, Any]] = []

        # Determine if threshold crossed
        category = None
        if risk_score >= CRITICAL_RISK_THRESHOLD:
            category = "critical"
        elif risk_score >= HIGH_RISK_THRESHOLD:
            category = "high"
        else:
            # No threshold crossed
            return results

        # Skip if not an upward crossing (optional: could check prev_score)
        if prev_score is not None and prev_score >= risk_score:
            # Not an upward crossing
            return results

        try:
            # Get student info for notification
            student = db.query(Student).filter(Student.id == student_id).first()
            student_name = (
                f"{student.first_name or ''} {student.last_name or ''}".strip()
                if student
                else student_id
            )

            # Find all faculty with notification preferences for this threshold
            prefs = (
                db.query(FacultyNotificationPref)
                .join(User)
                .filter(
                    User.role.in_(["faculty", "admin", "retention team"]),
                    User.is_active.is_(True),
                )
                .all()
            )

            for pref in prefs:
                try:
                    # Check if this faculty wants notifications for this category
                    if category == "high" and not pref.notify_on_high_risk:
                        continue
                    if category == "critical" and not pref.notify_on_critical_risk:
                        continue

                    # Check cooldown
                    is_cooldown = await self._is_cooldown_active(
                        pref, student_id, redis_client
                    )
                    if is_cooldown:
                        results.append(
                            {
                                "user_id": pref.user_id,
                                "student_id": student_id,
                                "status": "skipped",
                                "reason": "cooldown_active",
                            }
                        )
                        continue

                    # Build payload
                    user = pref.user
                    payload = self._build_payload(
                        student_id=student_id,
                        risk_score=risk_score,
                        previous_score=prev_score,
                        category=category,
                        faculty_name=user.username or user.email,  # type: ignore[union-attr, attr-defined]
                    )
                    payload["student_name"] = student_name

                    # Route to appropriate channel
                    success = False
                    if pref.notification_channel == "webhook":
                        success = await self._send_webhook_notification(pref, payload)
                    else:  # default to email
                        success = await self._send_email_notification(
                            pref, user, payload  # type: ignore[arg-type]
                        )

                    # Update last_notified_at on success
                    if success:
                        await self._update_last_notified(
                            pref, student_id, db, redis_client
                        )

                    results.append(
                        {
                            "user_id": pref.user_id,
                            "student_id": student_id,
                            "channel": pref.notification_channel,
                            "status": "sent" if success else "failed",
                            "category": category,
                        }
                    )

                except Exception as exc:
                    logger.exception(
                        f"[NOTIFICATION] Failed to notify user {pref.user_id} for student {student_id}: {exc}"
                    )
                    results.append(
                        {
                            "user_id": pref.user_id,
                            "student_id": student_id,
                            "status": "error",
                            "error": str(exc),
                        }
                    )

        except Exception as exc:
            logger.exception(
                f"[NOTIFICATION] notify_risk_threshold_crossed failed: {exc}"
            )
            # Never crash the caller — log and return partial results

        return results

    async def close(self):
        """Close HTTP client resources."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Global instance for convenience
notification_service = NotificationService()
