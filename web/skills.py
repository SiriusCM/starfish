"""
Skill 增删改查、导入导出。
"""
from flask import Blueprint, request, jsonify, Response
from registry import skill_registry

bp = Blueprint("skills", __name__, url_prefix="/api/skills")


@bp.route("", methods=["GET"])
def api_skill_list():
    try:
        return jsonify({"success": True, "skills": skill_registry.list_skills()})
    except Exception as e:
        return jsonify({"success": False, "detail": f"List error: {e}"}), 500


@bp.route("", methods=["POST"])
def api_skill_add():
    data = request.get_json() or {}
    try:
        sid = skill_registry.add_skill(data)
        return jsonify({"success": True, "id": sid})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Add error: {e}"}), 400


@bp.route("/<int:sid>", methods=["PUT"])
def api_skill_update(sid: int):
    data = request.get_json() or {}
    try:
        ok = skill_registry.update_skill(sid, data)
        return jsonify({"success": ok})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Update error: {e}"}), 400


@bp.route("/<int:sid>", methods=["DELETE"])
def api_skill_delete(sid: int):
    try:
        ok = skill_registry.delete_skill(sid)
        return jsonify({"success": ok})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Delete error: {e}"}), 500


@bp.route("/<int:sid>/toggle", methods=["POST"])
def api_skill_toggle(sid: int):
    data = request.get_json() or {}
    enabled = bool(data.get("enabled", True))
    try:
        ok = skill_registry.set_enabled(sid, enabled)
        return jsonify({"success": ok})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Toggle error: {e}"}), 500


@bp.route("/<int:sid>/export", methods=["GET"])
def api_skill_export(sid: int):
    """下载某个 skill 的 zip 包"""
    try:
        filename, payload = skill_registry.export_skill_zip(sid)
        return Response(
            payload,
            mimetype="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(payload)),
            },
        )
    except Exception as e:
        return jsonify({"success": False, "detail": f"Export error: {e}"}), 400


@bp.route("/import", methods=["POST"])
def api_skill_import():
    """上传 skill zip 包导入，overwrite=1 覆盖同名"""
    if "file" not in request.files:
        return jsonify({"success": False, "detail": "缺少 file 字段"}), 400
    f = request.files["file"]
    overwrite = (request.form.get("overwrite") or "").lower() in ("1", "true", "yes")
    try:
        result = skill_registry.import_skill_zip(f.read(), overwrite=overwrite)
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Import error: {e}"}), 400