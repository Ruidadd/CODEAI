# OpenClaw 阿里云一键部署方案

基于阿里云轻量应用服务器，快速部署 [OpenClaw](https://github.com/openclaw/openclaw) 个人 AI 助手，集成 Kimi 2.5 模型，接入钉钉和 QQ 消息平台。

## 前提条件

- 阿里云账号（已完成实名认证）
- [Moonshot 平台](https://platform.moonshot.cn/) API Key（用于 Kimi 2.5 模型）
- 钉钉开放平台开发者账号（可选，用于钉钉接入）
- QQ 开放平台机器人凭证（可选，用于 QQ 接入）

## 快速开始

### 第一步：购买阿里云轻量应用服务器

1. 访问[阿里云 OpenClaw 一键部署页面](https://www.aliyun.com/activity/ecs/clawdbot)
2. 点击 **一键购买并部署**
3. 选择 **OpenClaw (Moltbot) 镜像**，套餐建议 2 核 4G 及以上
4. 地域推荐选择 **美国（弗吉尼亚）**（中国内地域联网搜索功能受限）

### 第二步：SSH 登录并运行部署脚本

```bash
ssh root@<你的服务器公网IP>

git clone https://github.com/Ruidadd/CODEAI.git
cd CODEAI
bash setup.sh
```

脚本将自动完成：环境检查 → OpenClaw 安装 → Kimi 2.5 模型配置 → 防火墙放通 → 服务启动 → 健康检查。

### 第三步：接入消息平台（可选）

```bash
# 接入钉钉
bash config/channels/dingtalk-setup.sh

# 接入 QQ
bash config/channels/qq-setup.sh
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `setup.sh` | 主部署脚本，一键完成全部配置 |
| `scripts/install-openclaw.sh` | OpenClaw 安装与初始化 |
| `scripts/configure-model.sh` | Kimi 2.5 模型配置 |
| `scripts/configure-firewall.sh` | 防火墙端口放通 |
| `scripts/health-check.sh` | 部署后健康检查 |
| `config/openclaw-kimi.json` | Kimi 2.5 模型配置模板 |
| `config/channels/dingtalk-setup.sh` | 钉钉机器人接入 |
| `config/channels/qq-setup.sh` | QQ 机器人接入 |
| `docs/DEPLOYMENT_GUIDE.md` | 详细部署文档 |

## 常用运维命令

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f openclaw-gateway

# 重启服务
docker compose restart openclaw-gateway

# 更新到最新版
cd ~/openclaw/openclaw && git pull && docker compose up -d --build
```

## 参考链接

- [OpenClaw 官方文档](https://docs.openclaw.ai/)
- [阿里云 OpenClaw 部署指南](https://help.aliyun.com/zh/simple-application-server/use-cases/quickly-deploy-and-use-openclaw)
- [Moonshot 开放平台](https://platform.moonshot.cn/)
- [钉钉开放平台](https://open.dingtalk.com/)
