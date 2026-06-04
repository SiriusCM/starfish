"""
快照列表 / 创建 / 回滚。
"""
from flask import Blueprint, request, jsonify
from evolver.snapshot import take_snapshot, list_snapshots, rollback

bp = Blueprint("snapshot", __name__, url_prefix="/api")


@bp.route("/snapshots", methods=["GET"])
def api_list_snapshots():
    """获取快照列表"""
    try:
        return jsonify({"success": True, "snapshots": list_snapshots()})
    except Exception as e:
        return jsonify({"success": False, "detail": f"List error: {e}"}), 500


@bp.route("/snapshot/take", methods=["POST"])
def api_take_snapshot():
    """创建快照"""
    try:
        import os
        path = take_snapshot()
        return jsonify({"success": True, "snapshot": os.path.basename(path)})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Take snapshot error: {e}"}), 500


@bp.route("/rollback", methods=["POST"])
def api_rollback():
    """回滚到指定快照"""
    data = request.get_json() or {}
    tag = data.get("tag", "")
    try:
        result = rollback(tag)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Rollback error: {e}"}), 500