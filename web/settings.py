"""
LLM 设置的读取与保存。
"""
from flask import Blueprint, request, jsonify
from settings import LLM_MODEL, LLM_BASE_URL, LLM_API_KEY, _user_env

bp = Blueprint("settings", __name__, url_prefix="/api")


@bp.route("/settings", methods=["GET"])
def get_settings():
    """获取当前 LLM 设置"""
    return jsonify({
        "success": True,
        "settings": {
            "model": LLM_MODEL,
            "base_url": LLM_BASE_URL,
            "api_key": LLM_API_KEY,
        }
    })


@bp.route("/settings", methods=["POST"])
def save_settings():
    """保存 LLM 设置到用户环境变量文件"""
    data = request.get_json() or {}
    model = data.get("model", "")
    base_url = data.get("base_url", "")
    api_key = data.get("api_key", "")

    try:
        lines = []
        if model:
            lines.append(f"LLM_MODEL={model}")
        if base_url:
            lines.append(f"LLM_BASE_URL={base_url}")
        if api_key:
            lines.append(f"LLM_API_KEY={api_key}")

        with open(_user_env, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        from dotenv import load_dotenv
        load_dotenv(_user_env, override=True)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Save settings error: {str(e)}"}), 500