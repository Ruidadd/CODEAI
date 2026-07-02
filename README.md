# CODEAI

TRIAL FOR VIBE CODING

双智能体协作流水线：**Fable 动脑规划 → Codex 按计划干活 → Claude Code 验收把关**。

- 一条命令跑全流程：`./scripts/pipeline.sh "<任务描述>"`
- 用法与原理：[docs/codex-pipeline.md](docs/codex-pipeline.md)
- 交互式入口：在 Claude Code 里执行 `/codex-run <任务描述>`
- 角色协议：[CLAUDE.md](CLAUDE.md)（规划/验收方）、[AGENTS.md](AGENTS.md)（Codex 实现方）
