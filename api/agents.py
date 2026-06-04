"""
Agent 增删改查、启停。
"""
from flask import Blueprint, request, jsonify
from core.registry import agent_registry

bp = Blueprint("agents", __name__, url_prefix="/api/agents")


@bp.route("", methods=["GET"])
def api_agent_list():
    try:
        return jsonify({"success": True, "agents": agent_registry.list_agents()})
    except Exception as e:
        return jsonify({"success": False, "detail": f"List error: {e}"}), 500


@bp.route("", methods=["POST"])
def api_agent_add():
    data = request.get_json() or {}
    required = ["id", "name", "role", "goal", "backstory"]
    for k in required:
        if not data.get(k):
            return jsonify({"success": False, "detail": f"缺少字段 {k}"}), 400
    if not data.get("domains"):
        data["domains"] = ["*"]
    try:
        ok = agent_registry.add_agent(data)
        return jsonify({"success": ok, "detail": "" if ok else "id 已存在或写入失败"})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Add error: {e}"}), 400


@bp.route("/<agent_id>", methods=["PUT"])
def api_agent_update(agent_id: str):
    data = request.get_json() or {}
    try:
        ok = agent_registry.update_agent(agent_id, data)
        return jsonify({"success": ok})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Update error: {e}"}), 400


@bp.route("/<agent_id>", methods=["DELETE"])
def api_agent_delete(agent_id: str):
    try:
        ok = agent_registry.delete_agent(agent_id)
        return jsonify({"success": ok, "detail": "" if ok else "通用助手不可删除或 id 不存在"})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Delete error: {e}"}), 500


@bp.route("/<agent_id>/toggle", methods=["POST"])
def api_agent_toggle(agent_id: str):
    data = request.get_json() or {}
    enabled = bool(data.get("enabled", True))
    try:
        ok = agent_registry.set_enabled(agent_id, enabled)
        return jsonify({"success": ok, "detail": "" if ok else "通用助手不可禁用"})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Toggle error: {e}"}), 500