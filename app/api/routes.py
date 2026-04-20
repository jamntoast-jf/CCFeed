import uuid
from datetime import datetime, timezone

from flask import request, jsonify, current_app
from app.api import bp
from app.db import insert_note


def _check_auth():
    expected = current_app.config.get("API_KEY", "")
    if not expected:
        return False, (jsonify({"error": "API_KEY not configured on server"}), 500)
    provided = request.headers.get("X-Api-Key", "")
    if provided != expected:
        return False, (jsonify({"error": "Unauthorized"}), 401)
    return True, None


@bp.route("/api/ingest", methods=["POST"])
def ingest():
    ok, err = _check_auth()
    if not ok:
        return err

    body = request.get_json(silent=True) or {}
    text = body.get("text", "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    service    = body.get("service", "claude-code")
    tags_raw   = body.get("tags", "")
    created_at = body.get("created_at") or datetime.now(timezone.utc).isoformat()

    # Normalise tags to a comma-separated string regardless of input type
    if isinstance(tags_raw, list):
        tags_str = ",".join(tags_raw)
    else:
        tags_str = str(tags_raw)

    rkey = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + "-" + uuid.uuid4().hex[:6]

    row_id = insert_note(
        current_app.config["DB_PATH"],
        rkey=rkey,
        text=text,
        service=service,
        tags=tags_str,
        created_at=created_at,
    )

    return jsonify({"id": row_id, "rkey": rkey}), 201
