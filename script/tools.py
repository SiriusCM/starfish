import subprocess
from crewai_tools import FileReadTool, FileWriterTool, ScrapeWebsiteTool
from crewai.tools import tool
from settings import SHELL_BLACKLIST

file_read_tool = FileReadTool()
file_write_tool = FileWriterTool()
scrape_website_tool = ScrapeWebsiteTool()


@tool("delete_file")
def delete_file(path: str) -> str:
    """删除指定文件或文件夹（危险操作，请先确认路径）。path 必须是绝对路径。"""
    import os, shutil
    if not os.path.exists(path):
        return f"失败：路径不存在 {path}"
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
            return f"成功：已删除目录 {path}"
        os.remove(path)
        return f"成功：已删除文件 {path}"
    except Exception as e:
        return f"失败：{e}"


@tool("run_shell")
def run_shell(command: str) -> str:
    """在本地执行Shell命令并返回结果。可用于打开文件夹、打开应用、搜索文件等任意操作。危险命令会被拒绝。"""
    cmd = command.strip()
    for bad in SHELL_BLACKLIST:
        if bad in cmd:
            return f"拒绝执行：命令包含危险关键词 '{bad}'"
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        out = (r.stdout or "") + (r.stderr or "")
        return out.strip() or "成功：命令已执行，无输出。"
    except subprocess.TimeoutExpired:
        return "失败：命令执行超时(30s)"
    except Exception as e:
        return f"失败：{e}"


ALL_TOOLS = [
    file_read_tool, file_write_tool, scrape_website_tool,
    delete_file, run_shell,
]