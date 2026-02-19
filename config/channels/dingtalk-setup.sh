#!/usr/bin/env bash
# =============================================================================
# 钉钉机器人接入配置脚本
# 通过 Stream 模式（WebSocket）连接，无需公网 IP 或 Webhook
# =============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  OpenClaw 钉钉机器人接入配置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  准备工作："
echo "  1. 登录钉钉开放平台: https://open.dingtalk.com/"
echo "  2. 创建应用 → 获取 Client ID 和 Client Secret"
echo "  3. 在应用中添加「机器人」能力"
echo "  4. 配置机器人的消息接收模式为「Stream 模式」"
echo ""

# ── 安装钉钉插件 ─────────────────────────────────────────────────────────────
info "安装钉钉 Channel 插件..."

if command -v openclaw &>/dev/null; then
    # 检查是否已安装
    if openclaw plugins list 2>/dev/null | grep -qi "dingtalk"; then
        ok "钉钉插件已安装"
    else
        openclaw plugins install https://github.com/soimy/clawdbot-channel-dingtalk.git
        ok "钉钉插件安装完成"
    fi
else
    # Docker 场景：在容器内执行
    CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep "openclaw" | head -1)
    if [[ -z "$CONTAINER_NAME" ]]; then
        fail "未找到运行中的 OpenClaw 容器。请先运行 setup.sh"
    fi
    docker exec "$CONTAINER_NAME" openclaw plugins install https://github.com/soimy/clawdbot-channel-dingtalk.git
    ok "钉钉插件已在容器内安装"
fi

# ── 获取钉钉凭证 ─────────────────────────────────────────────────────────────
echo ""
DINGTALK_CLIENT_ID="${DINGTALK_CLIENT_ID:-}"
DINGTALK_CLIENT_SECRET="${DINGTALK_CLIENT_SECRET:-}"

if [[ -z "$DINGTALK_CLIENT_ID" ]]; then
    read -rp "请输入钉钉 Client ID: " DINGTALK_CLIENT_ID
fi
if [[ -z "$DINGTALK_CLIENT_SECRET" ]]; then
    read -rsp "请输入钉钉 Client Secret: " DINGTALK_CLIENT_SECRET
    echo ""
fi

if [[ -z "$DINGTALK_CLIENT_ID" || -z "$DINGTALK_CLIENT_SECRET" ]]; then
    fail "Client ID 和 Client Secret 不能为空"
fi

# ── 配置钉钉 Channel ─────────────────────────────────────────────────────────
info "配置钉钉 Channel..."

if command -v openclaw &>/dev/null; then
    openclaw config set channels.dingtalk.clientId "$DINGTALK_CLIENT_ID"
    openclaw config set channels.dingtalk.clientSecret "$DINGTALK_CLIENT_SECRET"
    openclaw config set channels.dingtalk.enabled true
    openclaw config set channels.dingtalk.dmPolicy pairing
    openclaw config set channels.dingtalk.groupPolicy open
    openclaw config set channels.dingtalk.messageType open
else
    CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep "openclaw" | head -1)
    docker exec "$CONTAINER_NAME" openclaw config set channels.dingtalk.clientId "$DINGTALK_CLIENT_ID"
    docker exec "$CONTAINER_NAME" openclaw config set channels.dingtalk.clientSecret "$DINGTALK_CLIENT_SECRET"
    docker exec "$CONTAINER_NAME" openclaw config set channels.dingtalk.enabled true
    docker exec "$CONTAINER_NAME" openclaw config set channels.dingtalk.dmPolicy open
    docker exec "$CONTAINER_NAME" openclaw config set channels.dingtalk.groupPolicy open
    docker exec "$CONTAINER_NAME" openclaw config set channels.dingtalk.messageType open
fi

ok "钉钉 Channel 配置完成"

# ── 重启服务 ─────────────────────────────────────────────────────────────────
info "重启 OpenClaw 服务以应用钉钉配置..."
if command -v openclaw &>/dev/null; then
    openclaw restart 2>/dev/null || true
else
    CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep "openclaw" | head -1)
    docker restart "$CONTAINER_NAME"
fi

# 等待服务就绪
sleep 5

# ── 验证 ─────────────────────────────────────────────────────────────────────
info "验证钉钉插件状态..."
if command -v openclaw &>/dev/null; then
    if openclaw plugins list 2>/dev/null | grep -qi "dingtalk"; then
        ok "钉钉插件运行正常"
    else
        warn "钉钉插件可能未正确加载，请检查日志"
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  ${GREEN}钉钉接入配置完成!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  配置说明："
echo "    - 模式: Stream（WebSocket 长连接）"
echo "    - 私聊: 已启用（pairing 模式，需在 Web 面板配对用户）"
echo "    - 群聊: 已启用"
echo ""
echo "  如需允许所有人直接使用（降低安全性）："
echo "    openclaw config set channels.dingtalk.dmPolicy open"
echo ""
echo "  测试方式："
echo "    1. 在钉钉中搜索并打开你创建的机器人应用"
echo "    2. 发送一条消息（如「你好」）"
echo "    3. 等待 AI 回复"
echo ""
echo "  如果没有收到回复，请检查日志："
echo "    docker compose logs -f openclaw-gateway | grep dingtalk"
echo ""
