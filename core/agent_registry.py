"""
智能体注册表 —— 管理多智能体的加载、领域路由、命中统计。
数据存储在 SQLite（~/.starfish/starfish.db）。
"""
import json
from datetime import datetime
from database import get_conn

_DEFAULT_AGENT = {
    "id": "general", "name": "通用助手",
    "role": "智能助手", "goal": "帮助用户完成任务。",
    "backstory": "你是一个智能助手。", "domains": ["*"]
}


def _row_to_dict(row) -> dict:
    """将数据库行转为字典，domains 从 JSON 字符串还原为列表。"""
    d = dict(row)
    d["domains"] = json.loads(d.get("domains", '["*"]'))
    return d


def list_agents() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM agents ORDER BY created_at").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_agent_by_id(agent_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def route(domain: str) -> dict:
    """根据领域标签路由到最匹配的智能体。"""
    agents = list_agents()
    for a in agents:
        if domain in a.get("domains", []):
            return a
    for a in agents:
        if "*" in a.get("domains", []):
            return a
    return agents[0] if agents else _DEFAULT_AGENT


def record_hit(domain: str, agent_id: str):
    """记录一次领域命中。"""
    conn = get_conn()
    conn.execute(
        "INSERT INTO domain_stats (domain, hit_count) VALUES (?, 1) "
        "ON CONFLICT(domain) DO UPDATE SET hit_count = hit_count + 1",
        (domain,)
    )
    conn.execute(
        "UPDATE agents SET hit_count = hit_count + 1 WHERE id = ?",
        (agent_id,)
    )
    conn.commit()
    conn.close()


def get_domain_stats() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT domain, hit_count FROM domain_stats ORDER BY hit_count DESC").fetchall()
    conn.close()
    return {r["domain"]: r["hit_count"] for r in rows}


def get_split_threshold() -> int:
    conn = get_conn()
    row = conn.execute("SELECT value FROM config WHERE key = 'split_threshold'").fetchone()
    conn.close()
    return int(row["value"]) if row else 10


def add_agent(agent_def: dict) -> bool:
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO agents (id, name, description, domains, role, goal, backstory, hit_count, created_at, parent)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        """, (
            agent_def["id"], agent_def["name"], agent_def.get("description", ""),
            json.dumps(agent_def["domains"], ensure_ascii=False),
            agent_def["role"], agent_def["goal"], agent_def["backstory"],
            agent_def.get("created_at", datetime.now().strftime("%Y-%m-%d")),
            agent_def.get("parent"),
        ))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def get_agent_rules(agent_id: str) -> list[str]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT rule FROM agent_rules WHERE agent_id = ? ORDER BY id", (agent_id,)
    ).fetchall()
    conn.close()
    return [r["rule"] for r in rows]


def add_agent_rule(agent_id: str, rule: str) -> bool:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO agent_rules (agent_id, rule, created_at) VALUES (?, ?, ?)",
            (agent_id, rule, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def remove_agent_rule(agent_id: str, rule: str) -> bool:
    conn = get_conn()
    cur = conn.execute(
        "DELETE FROM agent_rules WHERE agent_id = ? AND rule = ?", (agent_id, rule)
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed