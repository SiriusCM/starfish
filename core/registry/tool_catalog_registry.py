"""
工具目录注册表：数据库是主存储，prompts.py 的 TOOL_CATALOG 是内置默认值。
注册表负责读写数据库，运行时合并两者生成完整工具描述。
"""
from datetime import datetime
from database import get_conn

_version = 0


def current_version() -> int:
    return _version


def _invalidate():
    global _version
    _version += 1


def add_tool(name: str, description: str, server: str = "", source: str = "builtin"):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO tool_catalog (name, description, api, source, updated_at) VALUES (?, ?, ?, ?, ?)",
        (name, description, server, source, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    _invalidate()


def remove_tool(name: str):
    conn = get_conn()
    conn.execute("DELETE FROM tool_catalog WHERE name=?", (name,))
    conn.commit()
    conn.close()
    _invalidate()


def list_tools() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT name, description, api, source, updated_at FROM tool_catalog ORDER BY name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def build_tool_catalog_text() -> str:
    from core.prompts import TOOL_CATALOG as DEFAULT_CATALOG
    db_tools = list_tools()
    if not db_tools:
        return DEFAULT_CATALOG
    lines = DEFAULT_CATALOG.splitlines()
    for i, line in enumerate(lines):
        if "可用工具：" in line:
            parts = [
                t["name"] + "(" + t["api"] + ")" if t["source"] == "mcp" else t["name"] + "()"
                for t in db_tools
            ]
            lines[i] = "可用工具：" + ", ".join(parts)
            break
    return "\n".join(lines)


def apply_to_module(P):
    P.TOOL_CATALOG = build_tool_catalog_text()