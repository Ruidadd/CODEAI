# AI Leaders Radar

自动更新的 dashboard：汇总 Digital AI / Physical AI 主要公司及一线负责人的
**技术博客、YouTube、X** 最新动态（美 / 中 / 日，共 36 家公司）。

- 页面：`docs/index.html`（纯静态，读取 `docs/data/feed.json`，浏览器每 10 分钟自动重新拉取）
- 抓取：`scripts/fetch.py`（只用 Python 标准库）
- 名单：`config/sources.json`（公司、负责人、博客 RSS、YouTube handle、X 账号）
- 定时：`.github/workflows/update-feed.yml`，每 3 小时抓一次，提交数据并部署到 GitHub Pages

## 启用步骤

1. 把这些文件合并到默认分支（`main`）。GitHub 的定时任务只在默认分支上运行。
2. 仓库 **Settings → Pages → Build and deployment → Source** 选 **GitHub Actions**。
   私有仓库用 Pages 需要付费方案；否则可以把仓库设为 public，或把 `docs/` 部署到 Vercel / Cloudflare Pages。
3. **Actions → Update feed & deploy dashboard → Run workflow** 手动跑第一次。
4. 打开 Pages 地址即可。页面底部「数据源状态」会列出每个源是否抓取成功。

## X（Twitter）

X 没有免费的公开接口，默认不抓取 X，页面上只提供每个人 X 主页的链接。可在
**Settings → Secrets and variables → Actions** 里二选一配置：

| Secret | 说明 |
|---|---|
| `X_BEARER_TOKEN` | X 官方 API v2 的 Bearer Token（按量付费）。约 50 个账号 × 每天 8 次，注意用量 |
| `NITTER_BASE` | 自建 Nitter 或 RSSHub 实例的地址，脚本会请求 `{NITTER_BASE}/{handle}/rss`。公共 Nitter 实例大多已失效，建议自建 |

## 维护名单

编辑 `config/sources.json`：

```json
{"id":"openai","name":"OpenAI","region":"US","domain":"digital",
 "people":[{"name":"Sam Altman","role":"CEO","x":"sama"}],
 "blog":["https://openai.com/news/rss.xml"],
 "youtube":["OpenAI"],
 "x":["OpenAI"]}
```

- `region`：`US` / `CN` / `JP`；`domain`：`digital` / `physical` / `both`
- `youtube` 填 `@` 后面的 handle，或直接填 `UC…` 开头的频道 ID。handle 第一次解析后缓存在 `docs/data/id_cache.json`
- 没有 RSS 的博客（如 Anthropic）可以用社区维护的 feed，或 RSSHub 路由
- 抓取失败的源会保留上次的内容，不会把页面清空

本地运行：

```bash
python3 scripts/fetch.py
python3 -m http.server -d docs 8000   # 打开 http://localhost:8000
```
