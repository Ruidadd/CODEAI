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

### 方式一：一条命令的本地工作流（推荐）

不用打开交互界面，终端里一条命令跑完全流程：

```bash
# 全流程：规划 → 施工 → 逐步验收 → 终验 + 提交
./scripts/pipeline.sh "给项目加一个带单元测试的 TODO REST API"

# 或者跳过规划，直接执行一份已有计划
./scripts/pipeline.sh --plan codex-plans/20260702-slugify-trial.md
```

流程由 bash 做确定性调度，每个节点调用对应的智能体：

1. **PLAN**：无头 `claude -p` 探索代码库并写计划到 `codex-plans/`；
2. **EXECUTE**：`codex exec` 逐步施工；
3. **VERIFY**：无头 `claude -p` 审 diff、跑验收命令，按「最后一行
   `PASS` / `FAIL: <反馈>`」协议裁决；FAIL 时自动把反馈 resume 回
   Codex 同一会话返工，默认最多 3 轮（`MAX_ROUNDS` 可调），超限即停，
   留给人工接管；
4. **ACCEPT**：终验通过后填写计划的验收记录并 `git commit`（不 push）。

全程日志落盘在 `.codex-out/pipeline-*.log`。要求干净的工作区起跑
（验收依赖 `git diff`），可用 `PIPELINE_ALLOW_DIRTY=1` 覆盖。
可选环境变量：`CC_MODEL`（Claude 用的模型）、`CODEX_MODEL`（Codex 用的模型）。

> 注意：脚本给无头 Claude 授了 `Bash` 权限（验收要跑测试、终验要
> commit），只在你信任的本地仓库里使用。

### 方式二：交互式斜杠命令

在本仓库打开 Claude Code，直接用斜杠命令：

```
/codex-run 给项目加一个带单元测试的 TODO REST API
```

Claude 会自动完成：写计划 → 逐步调用 Codex 实现 → 每步验收 → 通过后提交。

### 方式三：手动驱动单次执行

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
