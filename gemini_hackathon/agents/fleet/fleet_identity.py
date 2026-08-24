"""gemini_hackathon.agents.fleet.fleet_identity — auth + identity context.

The 2nd Fleet primitive (per the openspec
``2026-08-24-gemini-hackathon-public-v1``). Provides the canonical
authentication + identity layer for the gemini_hackathon fleet.

The :class:`FleetIdentity` class resolves the caller's identity
from one of three sources (in priority order):

1. **Bearer token** — JWT or opaque token, validated against the
   configured JWT secret or introspection endpoint.
2. **Session cookie** — used by the TanStack Start frontend when
   the call comes through the SSR pipeline.
3. **Anonymous fallback** — used when no credentials are present
   (the OpenChamber channel-fanout gateway defaults to this).

Every resolved identity is wrapped in an :class:`IdentityContext`
that flows through the agent invocation. The context includes:

* ``user_id`` (stable ID)
* ``role`` (``"pupil"`` / ``"teacher"`` / ``"admin"`` / ``"anonymous"``)
* ``jurisdiction`` (the jurisdiction the user is viewing, drives
  the per-source palette injection)
* ``level`` (LC / JC / GCSE / A-Level / …)
* ``permissions`` (the RBAC bitmask)

The module is a wholesale port of the Cianfhoghlaim
``agents/fleet/identity.py`` (per the
``wholesale-copy-convention``) with one adaptation: the ``roles``
are aligned to the gemini_hackathon vocabulary
(``pupil`` / ``teacher`` / ``safeguarding_lead`` / ``admin``).
"""

from __future__ import annotations

import hashlib
import os
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Optional PyJWT dependency (graceful degradation)
# ---------------------------------------------------------------------------

_JWT_AVAILABLE: bool = False
try:
    import jwt as _pyjwt  # type: ignore[import-not-found]

    _JWT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _pyjwt = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Roles + permissions
# ---------------------------------------------------------------------------

#: The canonical role roster for the gemini_hackathon fleet.
ROLES: tuple[str, ...] = (
    "anonymous",
    "pupil",
    "teacher",
    "safeguarding_lead",
    "researcher",
    "admin",
)


#: Permission bitmasks (1 << n). Used to gate high-risk operations
#: (e.g. ``admin_only`` gates the curriculum-change sensor).
PERMISSIONS: dict[str, int] = {
    "read_themes": 1 << 0,
    "read_equivalencies": 1 << 1,
    "run_marking_grader": 1 << 2,
    "view_personalisation": 1 << 3,
    "trigger_change_sensor": 1 << 4,
    "admin_only": 1 << 30,
}


#: Per-role permission grants.
#:
#: The anonymous role gets ``view_personalisation`` + ``read_themes`` +
#: ``read_equivalencies`` so the public-facing demo (the TanStack Start
#: landing page) can invoke the adaptive tutor + the equivalency
#: generator without authentication. The high-risk gates
#: (``run_marking_grader``, ``trigger_change_sensor``) remain
#: restricted to authenticated roles.
_ANON_PERMS: int = (
    PERMISSIONS["read_themes"]
    | PERMISSIONS["read_equivalencies"]
    | PERMISSIONS["view_personalisation"]
)

_ROLE_PERMISSIONS: dict[str, int] = {
    "anonymous": _ANON_PERMS,
    "pupil": _ANON_PERMS,
    "teacher": _ANON_PERMS | PERMISSIONS["run_marking_grader"],
    "safeguarding_lead": _ANON_PERMS | PERMISSIONS["trigger_change_sensor"],
    "researcher": _ANON_PERMS,
    "admin": (1 << 31) - 1,  # all bits set
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class IdentityError(RuntimeError):
    """Base class for identity-resolution failures."""


class AuthenticationError(IdentityError):
    """Raised when a token cannot be validated."""


class AuthorisationError(IdentityError):
    """Raised when an identity lacks the required permission."""


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IdentityContext:
    """The resolved identity for a single agent invocation.

    Attributes:
        user_id: Stable user ID (or ``"anonymous"``).
        role: One of :data:`ROLES`.
        jurisdiction: The jurisdiction the user is viewing (drives
            the per-source palette + the equivalency generator's
            source anchor).
        level: The curriculum level (``"LC"`` / ``"JC"`` / ``"GCSE"``
            / ``"A-Level"`` / ``""``).
        permissions: The permission bitmask (see :data:`PERMISSIONS`).
        source_palette_key: The active source key (e.g.
            ``"ncca.ie"``) — drives the theming injection.
        authenticated: Whether the identity was authenticated
            (vs. anonymous fallback).
        expires_at: Unix timestamp for token expiry (``0`` =
            non-expiring).
        metadata: Free-form per-identity metadata.
    """

    user_id: str
    role: str = "anonymous"
    jurisdiction: str = "Ireland"
    level: str = "LC"
    permissions: int = field(
        default_factory=lambda: _ROLE_PERMISSIONS["anonymous"]
    )
    source_palette_key: str = "ncca.ie"
    authenticated: bool = False
    expires_at: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_permission(self, perm: str) -> bool:
        """Return whether this identity has the given permission.

        Args:
            perm: The permission key (e.g. ``"run_marking_grader"``).

        Returns:
            ``True`` if the bit is set, ``False`` otherwise.
        """
        mask = PERMISSIONS.get(perm, 0)
        return bool(self.permissions & mask)


# ---------------------------------------------------------------------------
# The FleetIdentity class
# ---------------------------------------------------------------------------


class FleetIdentity:
    """The fleet-wide authentication + identity resolver.

    Constructed once at process start. The :meth:`resolve` method
    accepts any of the supported credential formats and returns
    an :class:`IdentityContext` that flows through the agent
    invocation.
    """

    def __init__(
        self,
        *,
        jwt_secret: str | None = None,
        jwt_algorithm: str = "HS256",
        jwt_issuer: str | None = None,
        allow_anonymous: bool = True,
        default_jurisdiction: str = "Ireland",
        default_level: str = "LC",
        default_source_palette: str = "ncca.ie",
    ) -> None:
        """Initialise the identity layer.

        Args:
            jwt_secret: The JWT signing secret (defaults to
                ``IDENTITY_JWT_SECRET``).
            jwt_algorithm: The JWT signing algorithm (default
                ``"HS256"``).
            jwt_issuer: Optional JWT issuer for the ``iss`` claim
                check.
            allow_anonymous: Whether anonymous identities are
                permitted (default ``True``).
            default_jurisdiction: The default jurisdiction for
                anonymous identities.
            default_level: The default curriculum level.
            default_source_palette: The default source palette key.
        """
        self.jwt_secret = jwt_secret or os.getenv("IDENTITY_JWT_SECRET", "")
        self.jwt_algorithm = jwt_algorithm
        self.jwt_issuer = jwt_issuer
        self.allow_anonymous = allow_anonymous
        self.default_jurisdiction = default_jurisdiction
        self.default_level = default_level
        self.default_source_palette = default_source_palette

        if not self.jwt_secret and not self.allow_anonymous:
            logger.warning(
                "identity.jwt_secret_missing",
                detail="IDENTITY_JWT_SECRET not set; anonymous identities will be rejected",
            )

    # ------------------------------------------------------------------
    # Public API: resolve
    # ------------------------------------------------------------------

    def resolve(
        self,
        *,
        bearer_token: str | None = None,
        session_cookie: str | None = None,
        user_id_hint: str | None = None,
    ) -> IdentityContext:
        """Resolve an :class:`IdentityContext` from the supplied credentials.

        Args:
            bearer_token: The ``Authorization: Bearer <token>`` value.
            session_cookie: The session cookie value (validated as
                a JWT for parity with the bearer path).
            user_id_hint: Optional user ID hint (used when falling
                back to anonymous — the caller can pre-attach a
                ``device-123`` style ID).

        Returns:
            The resolved :class:`IdentityContext`.

        Raises:
            AuthenticationError: If a token is supplied but invalid.
            AuthorisationError: If ``allow_anonymous=False`` and no
                token is supplied.
        """
        token = bearer_token or session_cookie
        if token:
            return self._resolve_token(token)

        if not self.allow_anonymous:
            raise AuthorisationError(
                "No credentials supplied and anonymous identities are disabled."
            )

        # Anonymous fallback.
        user_id = user_id_hint or self._hash_anonymous_id(
            bearer_token, session_cookie
        )
        return self._make_context(
            user_id=user_id,
            role="anonymous",
            authenticated=False,
        )

    def require_permission(
        self, ctx: IdentityContext, perm: str
    ) -> None:
        """Raise :class:`AuthorisationError` if ``ctx`` lacks ``perm``.

        Args:
            ctx: The :class:`IdentityContext` to check.
            perm: The permission key.

        Raises:
            AuthorisationError: If the bit is not set.
        """
        if not ctx.has_permission(perm):
            logger.warning(
                "identity.permission_denied",
                user_id=ctx.user_id,
                role=ctx.role,
                permission=perm,
            )
            raise AuthorisationError(
                f"Role '{ctx.role}' lacks permission '{perm}'"
            )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_token(self, token: str) -> IdentityContext:
        """Validate a JWT (or opaque token) and return the context."""
        if not _JWT_AVAILABLE:
            # No JWT library — we can't validate the token.
            raise AuthenticationError(
                "Token validation requires PyJWT; install with `uv add pyjwt`."
            )
        if not self.jwt_secret:
            raise AuthenticationError(
                "IDENTITY_JWT_SECRET not configured; cannot validate tokens."
            )
        try:
            decode_kwargs: dict[str, Any] = {
                "algorithms": [self.jwt_algorithm],
                "options": {"verify_aud": False},
            }
            if self.jwt_issuer:
                decode_kwargs["issuer"] = self.jwt_issuer
            payload = _pyjwt.decode(token, self.jwt_secret, **decode_kwargs)
        except Exception as e:  # noqa: BLE001
            raise AuthenticationError(
                f"Token validation failed: {type(e).__name__}: {e}"
            ) from e

        return self._context_from_payload(payload)

    def _context_from_payload(self, payload: dict[str, Any]) -> IdentityContext:
        """Build an :class:`IdentityContext` from a JWT payload dict."""
        user_id = str(payload.get("sub", "anonymous"))
        role = str(payload.get("role", "pupil"))
        if role not in ROLES:
            logger.warning(
                "identity.unknown_role_in_token",
                role=role,
                user_id=user_id,
            )
            role = "pupil"
        permissions = payload.get("permissions")
        if permissions is None:
            permissions = _ROLE_PERMISSIONS[role]
        else:
            permissions = int(permissions)
        return self._make_context(
            user_id=user_id,
            role=role,
            authenticated=True,
            jurisdiction=str(payload.get("jurisdiction", self.default_jurisdiction)),
            level=str(payload.get("level", self.default_level)),
            source_palette_key=str(
                payload.get("source_palette_key", self.default_source_palette)
            ),
            permissions=permissions,
            expires_at=int(payload.get("exp", 0)),
            metadata={
                k: v
                for k, v in payload.items()
                if k
                not in {
                    "sub",
                    "role",
                    "permissions",
                    "jurisdiction",
                    "level",
                    "source_palette_key",
                    "exp",
                }
            },
        )

    def _make_context(
        self,
        *,
        user_id: str,
        role: str,
        authenticated: bool,
        jurisdiction: str | None = None,
        level: str | None = None,
        source_palette_key: str | None = None,
        permissions: int | None = None,
        expires_at: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> IdentityContext:
        """Construct an :class:`IdentityContext` with safe defaults."""
        if role not in ROLES:
            role = "anonymous"
        return IdentityContext(
            user_id=user_id,
            role=role,
            jurisdiction=jurisdiction or self.default_jurisdiction,
            level=level or self.default_level,
            permissions=(
                permissions
                if permissions is not None
                else _ROLE_PERMISSIONS[role]
            ),
            source_palette_key=(
                source_palette_key or self.default_source_palette
            ),
            authenticated=authenticated,
            expires_at=expires_at,
            metadata=dict(metadata or {}),
        )

    def _hash_anonymous_id(
        self, bearer_token: str | None, session_cookie: str | None
    ) -> str:
        """Return a stable hashed user ID for the anonymous fallback."""
        seed = (bearer_token or session_cookie or "anon").encode("utf-8")
        digest = hashlib.sha256(seed).hexdigest()[:16]
        return f"anon-{digest}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_token(
    *,
    user_id: str,
    role: str = "pupil",
    jurisdiction: str = "Ireland",
    level: str = "LC",
    source_palette_key: str = "ncca.ie",
    expires_in_seconds: int = 3600,
    jwt_secret: str | None = None,
    jwt_algorithm: str = "HS256",
) -> str:
    """Mint a short-lived JWT for testing + development.

    Args:
        user_id: The subject claim.
        role: The role claim.
        jurisdiction: The jurisdiction claim.
        level: The level claim.
        source_palette_key: The source palette claim.
        expires_in_seconds: Token lifetime in seconds (default 3600).
        jwt_secret: The signing secret (defaults to
            ``IDENTITY_JWT_SECRET``).
        jwt_algorithm: The signing algorithm (default ``"HS256"``).

    Returns:
        A signed JWT string.

    Raises:
        RuntimeError: If PyJWT is not installed.
    """
    if not _JWT_AVAILABLE:
        raise RuntimeError(
            "make_token() requires PyJWT; install with `uv add pyjwt`."
        )
    secret = jwt_secret or os.getenv("IDENTITY_JWT_SECRET", "")
    if not secret:
        raise RuntimeError("IDENTITY_JWT_SECRET is not set.")
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "jurisdiction": jurisdiction,
        "level": level,
        "source_palette_key": source_palette_key,
        "permissions": _ROLE_PERMISSIONS.get(role, 0),
        "iat": now,
        "exp": now + expires_in_seconds,
    }
    return _pyjwt.encode(payload, secret, algorithm=jwt_algorithm)


def roles_with_permission(perm: str) -> list[str]:
    """Return the list of roles that have ``perm`` set."""
    mask = PERMISSIONS.get(perm, 0)
    return [r for r, perms in _ROLE_PERMISSIONS.items() if perms & mask]


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "AuthenticationError",
    "AuthorisationError",
    "FleetIdentity",
    "IdentityContext",
    "IdentityError",
    "PERMISSIONS",
    "ROLES",
    "make_token",
    "roles_with_permission",
]
