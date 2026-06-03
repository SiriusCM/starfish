"""
MCP 服务端增删改启停 + MCP 工具列表（内置 / MCP / 聚合）。
"""
from flask import Blueprint, request, jsonify
from core import mcp_client
from registry import mcp_registry
from web.state import (
    MCP_STATE, MCP_LOCK, BUILTIN_CACHE, BUILTIN_TTL,
    invalidate_tools_cache, ensure_mcp_loading,
)

bp = Blueprint("mcp", __name__, url_prefix="/api/mcp")


def _list_builtin_tools():
    """同步加载内置工具。"""
    from core.orchestrator import _load_script
    out = []
    try:
        tools_mod = _load_script("tools")
        for t in getattr(tools_mod, "ALL_TOOLS", []):
            out.append({
                "name": getattr(t, "name", t.__class__.__name__),
                "description": getattr(t, "description", "") or "",
                "source": "builtin",
                "server": "",
            })
    except Exception as e:
        out.append({"name": "(builtin load error)", "description": str(e), "source": "error", "server": ""})
    return out


# ── 服务端 CRUD ────────────────────────────────────────

@bp.route("/servers", methods=["GET"])
def api_mcp_list():
    try:
        return jsonify({"success": True, "servers": mcp_registry.list_servers()})
    except Exception as e:
        return jsonify({"success": False, "detail": f"List error: {e}"}), 500


@bp.route("/servers", methods=["POST"])
def api_mcp_add():
    data = request.get_json() or {}
    try:
        sid = mcp_registry.add_server(data)
        invalidate_tools_cache()
        return jsonify({"success": True, "id": sid})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Add error: {e}"}), 400


@bp.route("/servers/<int:sid>", methods=["PUT"])
def api_mcp_update(sid: int):
    data = request.get_json() or {}
    try:
        ok = mcp_registry.update_server(sid, data)
        invalidate_tools_cache()
        return jsonify({"success": ok})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Update error: {e}"}), 400


@bp.route("/servers/<int:sid>", methods=["DELETE"])
def api_mcp_delete(sid: int):
    try:
        ok = mcp_registry.delete_server(sid)
        invalidate_tools_cache()
        return jsonify({"success": ok})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Delete error: {e}"}), 500


@bp.route("/servers/<int:sid>/toggle", methods=["POST"])
def api_mcp_toggle(sid: int):
    data = request.get_json() or {}
    enabled = bool(data.get("enabled", True))
    try:
        ok = mcp_registry.set_enabled(sid, enabled)
        invalidate_tools_cache()
        return jsonify({"success": ok})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Toggle error: {e}"}), 500


@bp.route("/reload", methods=["POST"])
def api_mcp_reload():
    """强制重连所有启用的 MCP server。"""
    try:
        count = mcp_client.reload()
        invalidate_tools_cache()
        return jsonify({"success": True, "tools": count})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Reload error: {e}"}), 500


# ── 工具列表 ─────────────────────────────────────────

@bp.route("/tools", methods=["GET"])
def api_mcp_tools():
    """返回当前已加载的 MCP 工具清单。"""
    try:
        tools = mcp_client.get_mcp_tools()
        return jsonify({
            "success": True,
            "tools": [{"name": t.name, "description": t.description} for t in tools],
        })
    except Exception as e:
        return jsonify({"success": False, "detail": f"Tools error: {e}"}), 500


# ── 工具列表独立端点（内置 / MCP / 聚合）───────────────

_tools_bp = Blueprint("tools", __name__, url_prefix="/api")


@_tools_bp.route("/tools/builtin", methods=["GET"])
def api_tools_builtin():
    """同步返回内置工具，带 30s TTL 缓存。"""
    import time as _time
    now = _time.time()
    cached = BUILTIN_CACHE["data"]
    if cached is None or (now - BUILTIN_CACHE["ts"] >= BUILTIN_TTL):
        cached = _list_builtin_tools()
        BUILTIN_CACHE["data"] = cached
        BUILTIN_CACHE["ts"] = now
    return jsonify({"success": True, "tools": cached, "count": len(cached)})


@_tools_bp.route("/tools/mcp", methods=["GET"])
def api_tools_mcp():
    """异步 MCP 工具：触发后台加载后立即返回状态，前端轮询。"""
    force = (request.args.get("force") or "").lower() in ("1", "true", "yes")
    if force:
        with MCP_LOCK:
            MCP_STATE["status"] = "idle"
    if MCP_STATE["status"] == "idle":
        ensure_mcp_loading()
    with MCP_LOCK:
        snapshot = {
            "status": MCP_STATE["status"],
            "tools": list(MCP_STATE["tools"]),
            "error": MCP_STATE["error"],
            "ts": MCP_STATE["ts"],
        }
    snapshot["success"] = True
    snapshot["count"] = len(snapshot["tools"])
    return jsonify(snapshot)


@_tools_bp.route("/tools", methods=["GET"])
def api_tools_list():
    """聚合接口：内置同步 + MCP 当前状态。"""
    builtin = _list_builtin_tools()
    if MCP_STATE["status"] == "idle":
        ensure_mcp_loading()
    with MCP_LOCK:
        mcp_status = MCP_STATE["status"]
        mcp_tools = list(MCP_STATE["tools"])
        mcp_error = MCP_STATE["error"]
    return jsonify({
        "success": True,
        "tools": builtin + mcp_tools,
        "count": len(builtin) + len(mcp_tools),
        "mcp_status": mcp_status,
        "mcp_error": mcp_error,
    })