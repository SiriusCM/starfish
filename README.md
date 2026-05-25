# Starfish Agent

可自我进化的智能 CLI 助手。基于 CrewAI 框架，通过对话学习用户偏好，自动优化自身行为。

## 特性

- **双阶段架构**：Planner 规划 + Executor 执行，自动路由到最匹配的领域智能体
- **自我进化**：从对话中提取用户偏好，自动生成改进提案并应用
- **多智能体**：支持智能体裂变，高频领域自动分裂出专业子智能体
- **安全机制**：行为宪法约束 + 快照回滚，进化不会失控

## 安装

```bash
pip install starfish-agent
```

## 配置

首次运行会在 `~/.starfish/` 下生成 `.env` 配置文件，请填入你的 LLM API Key：

```bash
LLM_MODEL=MiniMax-M2.7
LLM_BASE_URL=http://ai-api.jdcloud.com/v1
LLM_API_KEY=your-api-key-here
```

## 使用

```bash
# 进入对话模式
starfish

# 触发进化（预览）
starfish evolve

# 触发进化并生效
starfish evolve --apply

# 查看快照
starfish snapshots

# 回滚到指定快照
starfish rollback [tag]

# 重置 script 为初始版本
starfish reset
```

## 进化机制

每次对话后，Executor 会自动生成进化摘要。运行 `starfish evolve` 时：

1. Evolver Agent 分析对话日志，识别用户纠正和偏好
2. 生成提案（修改提示词 / 添加规则 / 创建工具 / 裂变智能体）
3. 语法校验 + import 冒烟测试，失败自动回滚

## 项目结构

```
starfish/
├── app.py          # CLI 入口
├── settings.py     # 配置管理
├── database.py     # SQLite 数据层
├── core/           # 框架核心（不可被进化修改）
├── evolver/        # 进化引擎
└── script/         # 可进化的提示词和工具
```

## License

MIT