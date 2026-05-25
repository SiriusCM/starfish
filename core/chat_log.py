"""
对话日志和进化摘要管理。数据存储在 SQLite。
"""
from datetime import datetime
from settings import MEMORY_ENABLED, MAX_HISTORY
from database import get_conn

_history = []


def append_history(user, answer):
    _history.append({"user": user, "answer": str(answer)})
    if len(_history) > MAX_HISTORY:
        del _history[: len(_history) - MAX_HISTORY]


def write_chat_log(user, answer, error=False):
    """记录一条对话日志到数据库。"""
    conn = get_conn()
    conn.execute(
        "INSERT INTO chat_logs (user_input, answer, is_error, created_at) VALUES (?, ?, ?, ?)",
        (user, answer, 1 if error else 0, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def write_evolve_hint(user_input, hint):
    """记录进化摘要到数据库。"""
    conn = get_conn()
    conn.execute(
        "INSERT INTO evolve_hints (user_input, hint, created_at) VALUES (?, ?, ?)",
        (user_input, hint, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_today_hints() -> str:
    """获取今日的进化摘要（供 evolver 读取）。"""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_conn()
    rows = conn.execute(
        "SELECT user_input, hint, created_at FROM evolve_hints WHERE created_at LIKE ? ORDER BY id",
        (f"{today}%",)
    ).fetchall()
    conn.close()
    if not rows:
        return f"(今日 {today} 暂无进化摘要)"
    lines = [f"# 进化摘要 ({today})\n"]
    for r in rows:
        ts = r["created_at"][11:19]
        lines.append(f"## {ts}\n- 用户指令：{r['user_input']}\n- 摘要：{r['hint']}\n")
    return "\n".join(lines)


def history_context():
    if not MEMORY_ENABLED or not _history:
        return ""
    lines = [f"[历史 {i+1}] 用户: {h['user']}\n    回复: {h['answer']}" for i, h in enumerate(_history)]
    return "以下是历史对话上下文，可作为参考：\n" + "\n".join(lines) + "\n\n"