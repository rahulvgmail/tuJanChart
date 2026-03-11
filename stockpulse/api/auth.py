"""API authentication via Bearer token (API key)."""

import functools
from datetime import datetime, timezone

from flask import g, jsonify, request

from stockpulse.extensions import get_db
from stockpulse.models.user import APIKey, User


def require_api_key(f):
    """Decorator that requires a valid API key in the Authorization header.

    Sets g.current_user to the authenticated user.
    """

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        raw_key = auth_header[7:]  # Strip "Bearer "

        session = get_db()
        try:
            # Check all active API keys
            api_keys = (
                session.query(APIKey)
                .join(User)
                .filter(APIKey.is_active == True, User.is_active == True)
                .all()
            )

            matched_key = None
            for ak in api_keys:
                if ak.verify_key(raw_key):
                    matched_key = ak
                    break

            if not matched_key:
                return jsonify({"error": "Invalid API key"}), 401

            # Update last used timestamp
            matched_key.last_used_at = datetime.now(timezone.utc)
            session.commit()

            g.current_user = matched_key.user
            g.db_session = session

            return f(*args, **kwargs)
        except Exception:
            session.rollback()
            raise
        finally:
            if "db_session" not in g:
                session.close()

    return decorated


def get_session():
    """Get the DB session, reusing one from auth if available."""
    if hasattr(g, "db_session"):
        return g.db_session
    return get_db()
