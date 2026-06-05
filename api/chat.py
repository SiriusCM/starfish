"""
聊天消息发送 / 历史记录 / 进化触发。
"""
from flask import Blueprint, request, jsonify
from core.orchestrator import run as chat_run
from core.chat_log import write_chat_log
from evolver.evolve import evolve

bp = Blueprint("chat", __name__, url_prefix="/api")


@bp.route("/chat", methods=["POST"])
def chat():
    """发送消息并获取 AI 回复"""
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"success": False, "detail": "Message cannot be empty"}), 400
    try:
        response = chat_run(message)
        write_chat_log(message, response)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        write_chat_log(message, str(e), error=True)
        return jsonify({"success": False, "detail": f"Chat error: {str(e)}"}), 500


@bp.route("/chat/history", methods=["GET"])
def chat_history():
    """获取聊天历史（含系统消息）"""
    try:
        from database import get_conn
        conn = get_conn()
        rows = conn.execute(
            "SELECT user_input, answer, is_error, msg_type, created_at FROM chat_logs ORDER BY id"
        ).fetchall()
        conn.close()
        items = [
            {"user": r["user_input"], "assistant": r["answer"], "isError": bool(r["is_error"]), "msgType": r["msg_type"], "time": r["created_at"]}
            for r in rows
        ]
        return jsonify({"success": True, "history": items})
    except Exception as e:
        return jsonify({"success": False, "detail": str(e)}), 500


@bp.route("/evolve", methods=["POST"])
def api_evolve():
    """触发进化（预览 dry_run 或执行 apply）"""
    data = request.get_json() or {}
    apply = bool(data.get("apply", False))
    try:
        result = evolve(dry_run=not apply)
        # 进化报告存入聊天记录（系统消息）
        from core.chat_log import write_chat_log
        write_chat_log(
            user="[进化模拟报告]" if not apply else "[进化应用报告]",
            answer=result["report"],
            msg_type="system",
        )
        return jsonify({"success": True, "apply": apply, **result})
    except Exception as e:
        return jsonify({"success": False, "detail": f"Evolve error: {str(e)}"}), 500