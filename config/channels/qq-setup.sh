#!/usr/bin/env bash
# =============================================================================
# QQ 机器人接入配置脚本
# 通过 NapCat (OneBot 11) 协议桥接 QQ 消息到 OpenClaw
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

OPENCLAW_HOME="${OPENCLAW_HOME:-/opt/openclaw}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  OpenClaw QQ 机器人接入配置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  本脚本通过 NapCat 框架实现 QQ 消息接入 OpenClaw。"
echo "  NapCat 使用 OneBot 11 协议，是目前最稳定的 QQ 协议实现。"
echo ""
echo "  准备工作："
echo "  1. 准备一个用于机器人的 QQ 号"
echo "  2. 确保该 QQ 号已完成实名认证"
echo ""

# ── 选择接入方式 ─────────────────────────────────────────────────────────────
echo "请选择 QQ 接入方式："
echo "  1) NapCat Docker（推荐，最简单）"
echo "  2) QQ 官方机器人 API（需要企业资质）"
echo ""
read -rp "请输入选项 [1/2，默认 1]: " QQ_METHOD
QQ_METHOD="${QQ_METHOD:-1}"

case "$QQ_METHOD" in
    1)
        # ── NapCat Docker 方式 ────────────────────────────────────────────
        info "使用 NapCat Docker 方式接入 QQ..."

        read -rp "请输入 QQ 机器人号码: " QQ_ACCOUNT
        if [[ -z "$QQ_ACCOUNT" ]]; then
            fail "QQ 号码不能为空"
        fi

        # 创建 NapCat 配置目录
        NAPCAT_DIR="${OPENCLAW_HOME}/napcat"
        mkdir -p "${NAPCAT_DIR}/config" "${NAPCAT_DIR}/data"

        # 生成 NapCat 配置
        cat > "${NAPCAT_DIR}/config/onebot11.json" <<NAPCAT_CONF
{
    "http": {
        "enable": false
    },
    "ws": {
        "enable": false
    },
    "reverseWs": {
        "enable": true,
        "urls": ["ws://openclaw-gateway:18789/ws/onebot"]
    },
    "heartInterval": 30000,
    "token": "",
    "musicSignUrl": ""
}
NAPCAT_CONF

        # 检查是否已有 NapCat 容器
        if docker ps -a --format '{{.Names}}' | grep -q "napcat"; then
            info "更新已有 NapCat 容器..."
            docker stop napcat 2>/dev/null || true
            docker rm napcat 2>/dev/null || true
        fi

        # 获取 OpenClaw 的 Docker 网络
        NETWORK_NAME=$(docker inspect openclaw-gateway --format='{{range $net, $conf := .NetworkSettings.Networks}}{{$net}}{{end}}' 2>/dev/null || echo "bridge")

        # 启动 NapCat 容器
        info "启动 NapCat 容器..."
        docker run -d \
            --name napcat \
            --restart unless-stopped \
            --network "${NETWORK_NAME}" \
            -e ACCOUNT="${QQ_ACCOUNT}" \
            -v "${NAPCAT_DIR}/config:/app/napcat/config" \
            -v "${NAPCAT_DIR}/data:/app/.config/QQ" \
            -p 6099:6099 \
            mlikiowa/napcat-docker:latest

        ok "NapCat 容器已启动"

        # 安装 OneBot 插件
        info "安装 OpenClaw OneBot 插件..."
        if command -v openclaw &>/dev/null; then
            openclaw plugins install onebot 2>/dev/null || true
            openclaw config set channels.onebot.enabled true
            openclaw config set channels.onebot.dmPolicy open
            openclaw config set channels.onebot.groupPolicy open
        else
            CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep "openclaw" | head -1)
            if [[ -n "$CONTAINER_NAME" ]]; then
                docker exec "$CONTAINER_NAME" openclaw plugins install onebot 2>/dev/null || true
                docker exec "$CONTAINER_NAME" openclaw config set channels.onebot.enabled true
                docker exec "$CONTAINER_NAME" openclaw config set channels.onebot.dmPolicy open
                docker exec "$CONTAINER_NAME" openclaw config set channels.onebot.groupPolicy open
            fi
        fi

        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo -e "  ${GREEN}NapCat QQ 接入配置完成!${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "  下一步 - QQ 登录："
        echo "  1. 查看 NapCat 日志获取登录二维码："
        echo "     docker logs -f napcat"
        echo ""
        echo "  2. 使用手机 QQ 扫描二维码完成登录"
        echo ""
        echo "  3. 登录成功后，在 QQ 中向机器人发消息测试"
        echo ""
        echo "  NapCat Web 管理面板: http://<服务器IP>:6099"
        echo ""
        ;;

    2)
        # ── QQ 官方机器人 API ─────────────────────────────────────────────
        info "使用 QQ 官方机器人 API..."
        echo ""
        echo "  请前往 QQ 开放平台注册机器人："
        echo "  https://q.qq.com/"
        echo ""

        read -rp "请输入 QQ 机器人 App ID: " QQ_APP_ID
        read -rsp "请输入 QQ 机器人 App Secret: " QQ_APP_SECRET
        echo ""

        if [[ -z "$QQ_APP_ID" || -z "$QQ_APP_SECRET" ]]; then
            fail "App ID 和 App Secret 不能为空"
        fi

        if command -v openclaw &>/dev/null; then
            openclaw config set channels.qq.appId "$QQ_APP_ID"
            openclaw config set channels.qq.appSecret "$QQ_APP_SECRET"
            openclaw config set channels.qq.enabled true
            openclaw config set channels.qq.dmPolicy open
        else
            CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep "openclaw" | head -1)
            if [[ -n "$CONTAINER_NAME" ]]; then
                docker exec "$CONTAINER_NAME" openclaw config set channels.qq.appId "$QQ_APP_ID"
                docker exec "$CONTAINER_NAME" openclaw config set channels.qq.appSecret "$QQ_APP_SECRET"
                docker exec "$CONTAINER_NAME" openclaw config set channels.qq.enabled true
                docker exec "$CONTAINER_NAME" openclaw config set channels.qq.dmPolicy open
            fi
        fi

        echo ""
        ok "QQ 官方机器人配置完成"
        echo ""
        ;;

    *)
        fail "无效选项：${QQ_METHOD}"
        ;;
esac

# ── 重启 OpenClaw ────────────────────────────────────────────────────────────
info "重启 OpenClaw 服务以加载 QQ 配置..."
if command -v openclaw &>/dev/null; then
    openclaw restart 2>/dev/null || true
else
    CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep "openclaw" | head -1)
    if [[ -n "$CONTAINER_NAME" ]]; then
        docker restart "$CONTAINER_NAME"
    fi
fi

sleep 5
ok "OpenClaw 服务已重启"

echo ""
echo "  排查日志: docker compose logs -f openclaw-gateway | grep -i qq"
echo ""
