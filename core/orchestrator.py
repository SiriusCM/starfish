import re
import importlib.util
from crewai import Agent, Task, Crew, Process, LLM
from settings import LLM_MODEL, LLM_BASE_URL, LLM_API_KEY, SCRIPT_DIR
from .chat_log import append_history, write_chat_log, write_evolve_hint, history_context
from .user_profile import rules_context
from .agent_registry import list_agents, route, record_hit


def _load_script(name):
    """从用户 script 目录动态加载模块。"""
    import os
    path = os.path.join(SCRIPT_DIR, f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_HINT_RE = re.compile(r'\[EVOLVE_HINT\](.*?)\[/EVOLVE_HINT\]', re.DOTALL)
_DOMAIN_RE = re.compile(r'\[DOMAIN\](.*?)\[/DOMAIN\]', re.DOTALL)

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = LLM(model=LLM_MODEL, base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    return _llm


def _build_agent_list() -> str:
    """构建智能体列表文本供 planner 选择领域。"""
    agents = list_agents()
    if not agents:
        return "- general(通用助手): 处理所有问题, domains=[*]"
    lines = []
    for a in agents:
        domains = ", ".join(a.get("domains", ["*"]))
        lines.append(f"- {a['id']}({a['name']}): {a.get('description', '')}, domains=[{domains}]")
    return "\n".join(lines)


def _build_executor(agent_def: dict) -> Agent:
    """根据智能体定义动态构建 executor Agent。"""
    tools_mod = _load_script("tools")
    return Agent(
        role=agent_def.get("role", "智能助手"),
        goal=agent_def.get("goal", "帮助用户完成任务。"),
        backstory=agent_def.get("backstory", "你是一个智能助手。"),
        tools=tools_mod.ALL_TOOLS,
        verbose=False,
        tracing=False,
        allow_delegation=False,
        llm=_get_llm(),
    )


def run(user_input: str) -> str:
    P = _load_script("prompts")
    ctx = history_context()
    global_rules = rules_context()  # planner 阶段只用全局规则
    agent_list = _build_agent_list()

    planner = Agent(
        role=P.PLANNER_ROLE,
        goal=P.PLANNER_GOAL,
        backstory=P.PLANNER_BACKSTORY,
        tools=[],
        verbose=False,
        tracing=False,
        allow_delegation=False,
        llm=_get_llm(),
    )

    plan_task = Task(
        description=P.PLAN_TASK_TEMPLATE.format(
            user_rules=global_rules, history_context=ctx,
            user_input=user_input, tool_catalog=P.TOOL_CATALOG,
            agent_list=agent_list,
        ),
        expected_output=P.PLAN_TASK_EXPECTED,
        agent=planner,
    )

    # 第一阶段：让 planner 运行，拿到领域标签
    plan_crew = Crew(
        agents=[planner], tasks=[plan_task],
        process=Process.sequential, verbose=False, tracing=False,
    )
    plan_result = str(plan_crew.kickoff()).strip()

    # 解析领域标签
    domain_match = _DOMAIN_RE.search(plan_result)
    domain = domain_match.group(1).strip() if domain_match else "general"

    # 路由到对应智能体
    agent_def = route(domain)
    executor = _build_executor(agent_def)

    # 记录命中
    record_hit(domain, agent_def["id"])

    # executor 阶段合并全局规则 + 智能体专属规则
    merged_rules = rules_context(agent_def["id"])

    exec_task = Task(
        description=P.EXEC_TASK_TEMPLATE.format(
            user_rules=merged_rules, user_input=user_input,
            agent_name=agent_def.get("name", "通用助手"),
            domain=domain,
        ),
        expected_output=P.EXEC_TASK_EXPECTED,
        agent=executor,
        context=[plan_task],
    )

    exec_crew = Crew(
        agents=[executor], tasks=[exec_task],
        process=Process.sequential, verbose=False, tracing=False,
    )

    try:
        result = exec_crew.kickoff()
        raw = str(result)
        # 拆分：提取摘要，剩余部分作为用户可见回答
        hint_match = _HINT_RE.search(raw)
        if hint_match:
            hint = hint_match.group(1).strip()
            answer = _HINT_RE.sub('', raw).strip()
            write_evolve_hint(user_input, hint)
        else:
            answer = raw.strip()
        append_history(user_input, answer)
        write_chat_log(user_input, answer)
        return answer
    except Exception as e:
        err = f"执行出错：{type(e).__name__}: {e}"
        write_chat_log(user_input, err, error=True)
        raisenswer = raw.strip()
        append_history(user_input, answer)
        write_chat_log(user_input, answer)
        return answer
    except Exception as e:
        err = f"执行出错：{type(e).__name__}: {e}"
        write_chat_log(user_input, err, error=True)
        raise