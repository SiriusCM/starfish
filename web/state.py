"""
工具列表的共享状态（内置 TTL 缓存 + MCP 异步状态机）。
"""
import time as _time
import threading as _threading

# 内置工具 30s TTL 缓存
BUILTIN_CACHE: dict = {"data": None, "ts": 0.0}
BUILTIN_TTL = 30.0

# MCP 工具状态机
MCP_STATE: dict = {
    "status": "idle",   # idle | loading | ready | error
    "tools": [],
    "error": "",
    "ts": 0.0,
}
MCP_LOCK = _threading.Lock()


def invalidate_tools_cache():
    """MCP 配置变动后调用：清空内置 TTL 缓存，重置 MCP 为 idle，下次请求自动重拉。"""
    BUILTIN_CACHE["data"] = None
    BUILTIN_CACHE["ts"] = 0.0
    with MCP_LOCK:
        MCP_STATE["status"] = "idle"
        MCP_STATE["tools"] = []
        MCP_STATE["error"] = ""


def ensure_mcp_loading():
    """触发后台加载，返回是否真正启动了新任务。"""
    with MCP_LOCK:
        if MCP_STATE["status"] == "loading":
            return False
        MCP_STATE["status"] = "loading"
        MCP_STATE["error"] = ""
    _threading.Thread(target=_mcp_loader_worker, name="mcp-tools-loader", daemon=True).start()
    return True


def _mcp_loader_worker():
    """后台线程：实际拉取 MCP 工具。"""
    try:
        from core import mcp_client
        items = []
        for t in mcp_client.get_mcp_tools():
            full = getattr(t, "name", "")
            server = full.split(".", 1)[0] if "." in full else ""
            short = full.split(".", 1)[1] if "." in full else full
            items.append({
                "name": short,
                "full_name": full,
                "description": getattr(t, "description", "") or "",
                "source": "mcp",
                "server": server,
            })
        with MCP_LOCK:
            MCP_STATE["status"] = "ready"
            MCP_STATE["tools"] = items
            MCP_STATE["error"] = ""
            MCP_STATE["ts"] = _time.time()
    except Exception as e:
        with MCP_LOCK:
            MCP_STATE["status"] = "error"
            MCP_STATE["tools"] = []
            MCP_STATE["error"] = str(e)
            MCP_STATE["ts"] = _time.time()