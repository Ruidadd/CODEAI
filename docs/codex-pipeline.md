# Fable × Codex 协作流水线

本仓库把两个编码智能体连接成一条流水线，各司其职：

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Claude (Fable)  │ →  │   Codex CLI       │ →  │  Claude Code     │
│  动脑：探索+规划  │     │  干活：按计划实现  │     │  验收：diff+测试  │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
        ↑                                                  │
        └────────────── 验收不通过 → 反馈返工（≤3轮）←──────┘
```

- **Fable（架构师）**：读代码、想方案，把任务拆成带验收标准的计划，写入
  `codex-plans/*.md`。
- **Codex（实现者）**：通过 `codex exec` 非交互执行，严格按计划逐步实现。
  它的行为约束写在仓库根目录的 `AGENTS.md`（Codex 会自动读取，等价于
  Claude 的 CLAUDE.md）。
- **Claude Code（验收方）**：每步完成后审查 `git diff`、跑验收命令；不通过
  就用 `codex exec resume` 把精确反馈发回同一个 Codex 会话返工，最多 3 轮，
  仍失败则自己接手并记录。**git 提交权只在 CC 手里，Codex 禁止 commit。**

## 一次性准备

```bash
# 1. 安装 Codex CLI
npm install -g @openai/codex

# 2. 登录（ChatGPT 账号 OAuth，或设置 OPENAI_API_KEY）
codex login

# 3. 可选：指定 Codex 用的模型（不设则用 ~/.codex/config.toml 的默认值）
export CODEX_MODEL=gpt-5.5-codex
```

## 日常用法

在本仓库打开 Claude Code，直接用斜杠命令：

```
/codex-run 给项目加一个带单元测试的 TODO REST API
```

Claude 会自动完成：写计划 → 逐步调用 Codex 实现 → 每步验收 → 通过后提交。

也可以手动驱动单次执行：

```bash
# 派工：让 Codex 实现某个计划的某一步
bash scripts/codex-exec.sh codex-plans/20260702-todo-api.md "Implement step 1"

# 返工：把验收反馈发回上一个 Codex 会话
bash scripts/codex-exec.sh --resume "step 1 的测试 test_create_todo 失败：返回 200 应为 201，请修正"
```

Codex 的最终答复会同时打印到终端并保存在 `.codex-out/last-message.txt`
（已 gitignore）。

## 备选通道：MCP

`.mcp.json` 把 Codex 注册成了 Claude Code 的 MCP server（`codex mcp-server`），
首次使用时 Claude Code 会请求批准。这条通道适合轻量的一问一答式调用；
批量按计划施工仍推荐走 `scripts/codex-exec.sh`，因为它能拿到会话续接
（resume）和最终消息落盘。

## 安全与边界

- Codex 以 `--sandbox workspace-write` 运行：只能写工作区，不能越界写系统。
- Codex 不 commit、不 push、不改 `codex-plans/`、`CLAUDE.md`、`AGENTS.md`、
  `scripts/`（除非计划明确要求）。
- 每一步的验收标准必须是可运行的命令 + 预期结果，验收才有据可依。
