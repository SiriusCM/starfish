import os
from datetime import datetime
from crewai import Agent, Task, Crew, Process, LLM
from settings import LLM_MODEL, LLM_BASE_URL, LLM_API_KEY
from . import prompts as EP
from .proposals import EVOLVER_TOOLS, get_proposals, reset_proposals
from .applier import apply_proposals


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _has_today_log():
    """检查今日是否有进化摘要（从数据库查询）。"""
    from database import get_conn
    today = _today()
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM evolve_hints WHERE created_at LIKE ?",
        (f"{today}%",)
    ).fetchone()
    conn.close()
    return row["cnt"] > 0


def _build_evolver_agent():
    llm = LLM(model=LLM_MODEL, base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    return Agent(
        role=EP.EVOLVER_ROLE,
        goal=EP.EVOLVER_GOAL,
        backstory=EP.EVOLVER_BACKSTORY,
        tools=EVOLVER_TOOLS,
        verbose=False,
        tracing=False,
        allow_delegation=False,
        llm=llm,
        max_iter=20,
    )


def _render_proposals_md(results):
    if not results:
        return "_无_"
    lines = []
    for i, p in enumerate(results, 1):
        kind = p.get("kind")
        st = p.get("status", "")
        reason = p.get("reason", "")
        if kind == "edit":
            lines.append(f"{i}. **edit** `{p['file']}`  状态：`{st}`\n   原因：{reason}\n   old: `{(p.get('old','') or '')[:80]}...`\n   new: `{(p.get('new','') or '')[:80]}...`")
        elif kind == "append_preference":
            lines.append(f"{i}. **append_preference** `CONSTITUTION.md`  状态：`{st}`\n   行：{p.get('line','')}")
        elif kind == "create_tool":
            lines.append(f"{i}. **create_tool** `{p['name']}`  状态：`{st}`\n   原因：{reason}\n   catalog_desc：{p.get('catalog_desc','')}")
        elif kind == "add_rule":
            lines.append(f"{i}. **add_rule**  状态：`{st}`\n   规则：{p.get('rule','')}\n   原因：{reason}")
        elif kind == "remove_rule":
            lines.append(f"{i}. **remove_rule**  状态：`{st}`\n   规则：{p.get('rule','')}\n   原因：{reason}")
        elif kind == "split_agent":
            lines.append(f"{i}. **split_agent** `{p.get('id','')}`({p.get('name','')})  状态：`{st}`\n   domains：{p.get('domains','')}\n   parent：{p.get('parent','')}\n   原因：{reason}")
        elif kind == "create_skill":
            lines.append(f"{i}. **create_skill** `{p.get('name','')}`  状态：`{st}`\n   summary：{p.get('summary','')}\n   domains：{p.get('domains','')}\n   原因：{reason}")
        else:
            lines.append(f"{i}. **{kind}**  状态：`{st}`")
    return "\n".join(lines)


def _write_report(today, summary, results, decision, notes):
    """将进化报告写入数据库。"""
    from database import get_conn
    md = EP.REPORT_TEMPLATE.format(
        today=today,
        summary=summary or "(无)",
        proposals_md=_render_proposals_md(results),
        phase=decision.get("phase", ""),
        result_msg=decision.get("msg", ""),
        applied_to_disk=str(decision.get("applied_to_disk", False)),
        snapshot=decision.get("snapshot") or "(无)",
        rolled_back=str(decision.get("rolled_back", False)),
        notes=notes or "(无)",
    )
    conn = get_conn()
    conn.execute(
        "INSERT INTO evolve_reports (report, created_at) VALUES (?, ?)",
        (md, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return f"[已存入数据库] evolve-{today}"


def evolve(dry_run: bool = True) -> str:
    today = _today()
    if not _has_today_log():
        print(f"⚠️ 未找到今日日志 logs/chat-{today}.md")
        return ""
    reset_proposals()
    evolver = _build_evolver_agent()
    task = Task(
        description=EP.EVOLVER_TASK_TEMPLATE,
        expected_output="调用 finalize 工具后，返回其结果字符串作为总结。",
        agent=evolver,
    )
    crew = Crew(agents=[evolver], tasks=[task], process=Process.sequential, verbose=False, tracing=False)
    print("🧠 evolver Agent 正在阅读与反思（这可能需要 30~90 秒）...")
    summary = ""
    notes = ""
    try:
        summary = str(crew.kickoff()).strip()
    except Exception as e:
        notes = f"Agent 运行异常：{type(e).__name__}: {e}"

    proposals = get_proposals()
    if not proposals:
        decision = {"phase": "no-op", "ok": True, "msg": "今日 evolver 未提交任何提案", "applied_to_disk": False, "snapshot": None, "rolled_back": False}
        results = []
    else:
        results, decision = apply_proposals(proposals, dry_run=dry_run)

    report_path = _write_report(today, summary, results, decision, notes)
    mode = "DRY-RUN" if dry_run else "APPLY"
    n = len(results)
    applied = sum(1 for p in results if p.get("status") == "ok")
    failed = n - applied
    print(f"✅ 进化完成 [{mode}]")
    print(f"   提案 : {n} 条（ok {applied} / 其他 {failed}）")
    print(f"   阶段 : {decision.get('phase')}  写盘 : {decision.get('applied_to_disk')}  快照 : {decision.get('snapshot') or '-'}  回滚 : {decision.get('rolled_back')}")
    if decision.get("msg"):
        print(f"   说明 : {decision.get('msg')}")
    print(f"   报告 : {report_path}")
    if dry_run and n > 0:
        print("👉 确认无误后执行：starfish evolve --apply")
    return report_path