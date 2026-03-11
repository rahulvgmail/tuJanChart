"""Webhook management API endpoints."""

from flask import Blueprint, g, jsonify, request

from stockpulse.api.auth import get_session, require_api_key
from stockpulse.models.event import Webhook

webhooks_bp = Blueprint("api_webhooks", __name__)


@webhooks_bp.route("/webhooks", methods=["GET"])
@require_api_key
def list_webhooks():
    """GET /api/webhooks - List registered webhooks."""
    session = get_session()

    webhooks = session.query(Webhook).filter(Webhook.is_active == True).all()

    return jsonify({
        "items": [
            {
                "id": w.id,
                "url": w.url,
                "event_types": w.event_types,
                "is_active": w.is_active,
                "created_at": w.created_at.isoformat(),
            }
            for w in webhooks
        ],
        "total": len(webhooks),
    })


@webhooks_bp.route("/webhooks", methods=["POST"])
@require_api_key
def create_webhook():
    """POST /api/webhooks - Register a new webhook."""
    session = get_session()
    data = request.get_json()

    if not data or not data.get("url") or not data.get("event_types"):
        return jsonify({"error": "url and event_types are required"}), 400

    webhook = Webhook(
        url=data["url"],
        secret=data.get("secret"),
        event_types=data["event_types"],
        created_by=g.current_user.id if hasattr(g, "current_user") else None,
        is_active=True,
    )
    session.add(webhook)
    session.commit()

    return jsonify({
        "id": webhook.id,
        "url": webhook.url,
        "event_types": webhook.event_types,
        "is_active": webhook.is_active,
        "created_at": webhook.created_at.isoformat(),
    }), 201


@webhooks_bp.route("/webhooks/<int:webhook_id>", methods=["DELETE"])
@require_api_key
def delete_webhook(webhook_id):
    """DELETE /api/webhooks/{id} - Deactivate a webhook."""
    session = get_session()

    webhook = session.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        return jsonify({"error": "Webhook not found"}), 404

    webhook.is_active = False
    session.commit()

    return jsonify({"status": "deactivated"})
