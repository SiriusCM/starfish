"""
Prompt 常量覆盖的读取、写入、重置。
"""
from flask import Blueprint, request, jsonify
from core.registry import prompt_registry

bp = Blueprint("prompts", __name__, url_prefix="/api/prompts")


@bp.route("", methods=["GET"])
def api_prompt_list():
    """列出所有可覆盖的 prompt 常量及当前生效值。"""
    try:
        items = prompt_registry.list_overrides()
        from core.orchestrator import _load_prompts
        eff = _load_prompts()
        for it in items:
            it["effective"] = getattr(eff, it["key"], "")
        return jsonify({
            "success": True,
            "items": items,
            "allowed_keys": list(prompt_registry.ALLOWED_KEYS),
        })
    except Exception as e:
        return jsonify({"success": False, "detail": f"List error: {e}"}), 500


@bp.route("/<key>", methods=["PUT"])
def api_prompt_set(key: str):
    data = request.get_json() or {}
    value = data.get("value", "")
    try:
        prompt_registry.set_override(key, value)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "detail": f"{e}"}), 400


@bp.route("/<key>", methods=["DELETE"])
def api_prompt_delete(key: str):
    try:
        ok = prompt_registry.delete_override(key)
        return jsonify({"success": ok})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Delete error: {e}"}), 500