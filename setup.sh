#!/usr/bin/env bash
# =============================================================================
# OpenClaw 阿里云一键部署脚本
# 适用于阿里云轻量应用服务器（OpenClaw 预装镜像 / 全新 Linux 系统）
# 模型：Kimi 2.5 (Moonshot AI)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── 颜色输出 ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

# ── 权限检查 ──────────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    fail "请使用 root 用户执行此脚本：sudo bash setup.sh"
fi

echo ""
echo "=============================================="
echo "   OpenClaw 阿里云一键部署"
echo "   模型：Kimi 2.5 (Moonshot AI)"
echo "   消息平台：钉钉 / QQ"
echo "=============================================="
echo ""

# ── Step 1: 环境预检 ─────────────────────────────────────────────────────────
info "Step 1/7: 环境预检..."

# 检查内存
TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_MEM_MB=$((TOTAL_MEM_KB / 1024))
if [[ $TOTAL_MEM_MB -lt 1800 ]]; then
    fail "内存不足：当前 ${TOTAL_MEM_MB}MB，最低要求 2GB。请升级服务器配置。"
fi
ok "内存检查通过：${TOTAL_MEM_MB}MB"

# 检查磁盘空间
AVAIL_DISK_GB=$(df / --output=avail -BG | tail -1 | tr -d ' G')
if [[ $AVAIL_DISK_GB -lt 8 ]]; then
    fail "磁盘空间不足：当前 ${AVAIL_DISK_GB}GB，最低要求 10GB。"
fi
ok "磁盘空间检查通过：${AVAIL_DISK_GB}GB 可用"

# ── Step 2: 安装 OpenClaw ────────────────────────────────────────────────────
info "Step 2/7: 安装 OpenClaw..."
bash "${SCRIPT_DIR}/scripts/install-openclaw.sh"

# ── Step 3: 配置 Kimi 2.5 模型 ──────────────────────────────────────────────
info "Step 3/7: 配置 Kimi 2.5 模型..."
bash "${SCRIPT_DIR}/scripts/configure-model.sh"

# ── Step 4: 配置防火墙 ──────────────────────────────────────────────────────
info "Step 4/7: 配置防火墙..."
bash "${SCRIPT_DIR}/scripts/configure-firewall.sh"

# ── Step 5: 启动服务 ────────────────────────────────────────────────────────
info "Step 5/7: 启动 OpenClaw 服务..."

OPENCLAW_HOME="${OPENCLAW_HOME:-/opt/openclaw}"

if command -v openclaw &>/dev/null; then
    # 预装镜像场景：使用 openclaw 命令启动
    openclaw start || true
    ok "OpenClaw 服务已通过 CLI 启动"
elif [[ -f "${OPENCLAW_HOME}/docker-compose.yml" ]]; then
    # Docker Compose 场景
    cd "${OPENCLAW_HOME}"
    docker compose up -d
    ok "OpenClaw 服务已通过 Docker Compose 启动"
else
    # 单容器场景
    if docker ps -a --format '{{.Names}}' | grep -q "openclaw-gateway"; then
        docker start openclaw-gateway
    else
        warn "未找到 OpenClaw 容器，尝试创建..."
        source "${OPENCLAW_HOME}/.env" 2>/dev/null || true
        docker run -d \
            --name openclaw-gateway \
            --restart unless-stopped \
            --cpus=1 \
            --memory=2048m \
            -p 18789:18789 \
            -v "${OPENCLAW_HOME}/config:/home/node/.openclaw" \
            -v "${OPENCLAW_HOME}/workspace:/home/node/.openclaw/workspace" \
            -e "OPENCLAW_GATEWAY_TOKEN=${OPENCLAW_GATEWAY_TOKEN:-}" \
            -e "TZ=Asia/Shanghai" \
            openclaw:latest
    fi
    ok "OpenClaw Gateway 容器已启动"
fi

# 等待服务就绪
info "等待服务就绪..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:18789/health &>/dev/null; then
        ok "服务已就绪"
        break
    fi
    if [[ $i -eq 30 ]]; then
        warn "服务启动超时，请检查日志：docker compose logs -f openclaw-gateway"
    fi
    sleep 2
done

# ── Step 6: 健康检查 ────────────────────────────────────────────────────────
info "Step 6/7: 执行健康检查..."
bash "${SCRIPT_DIR}/scripts/health-check.sh"

# ── Step 7: 安全审计 ────────────────────────────────────────────────────────
info "Step 7/7: 安全审计..."
if command -v openclaw &>/dev/null; then
    CURRENT_VER=$(openclaw --version 2>/dev/null || echo "0.0.0")
    # 检查是否 >= v2026.1.29（修复 CVE-2026-25253）
    if [[ "$(printf '%s\n' "2026.1.29" "$CURRENT_VER" | sort -V | head -1)" != "2026.1.29" ]]; then
        warn "当前版本 ${CURRENT_VER} 低于 v2026.1.29，存在 CVE-2026-25253 漏洞"
        warn "强烈建议更新：cd ~/openclaw/openclaw && git pull && docker compose up -d --build"
    else
        ok "版本安全检查通过：${CURRENT_VER}"
    fi
    openclaw security audit --deep 2>/dev/null && ok "安全审计完成" || warn "安全审计命令不可用，请手动检查"
else
    warn "openclaw CLI 不可用，跳过安全审计。部署后请手动运行：openclaw security audit --deep"
fi

# 检查 .env 权限
if [[ -f "${OPENCLAW_HOME}/.env" ]]; then
    ENV_PERMS=$(stat -c "%a" "${OPENCLAW_HOME}/.env" 2>/dev/null || echo "unknown")
    if [[ "$ENV_PERMS" == "600" ]]; then
        ok ".env 文件权限安全 (600)"
    else
        warn ".env 文件权限为 ${ENV_PERMS}，正在修复为 600..."
        chmod 600 "${OPENCLAW_HOME}/.env"
    fi
fi

# ── 完成 ────────────────────────────────────────────────────────────────────
SERVER_IP=$(curl -sf http://100.100.100.200/latest/meta-data/eipv4 2>/dev/null \
    || curl -sf ifconfig.me 2>/dev/null \
    || hostname -I | awk '{print $1}')

GATEWAY_TOKEN=""
if [[ -f "${OPENCLAW_HOME}/.env" ]]; then
    GATEWAY_TOKEN=$(grep "OPENCLAW_GATEWAY_TOKEN" "${OPENCLAW_HOME}/.env" 2>/dev/null | cut -d'=' -f2 || true)
fi

echo ""
echo "=============================================="
echo -e "  ${GREEN}OpenClaw 部署完成!${NC}"
echo "=============================================="
echo ""
echo "  访问地址: http://${SERVER_IP}:18789"
if [[ -n "$GATEWAY_TOKEN" ]]; then
    echo "  带 Token:  http://${SERVER_IP}:18789/?token=${GATEWAY_TOKEN}"
fi
echo ""
echo "  模型:     Kimi 2.5 (Moonshot AI)"
echo ""
echo "  接入消息平台（可选）:"
echo "    钉钉:   bash config/channels/dingtalk-setup.sh"
echo "    QQ:     bash config/channels/qq-setup.sh"
echo ""
echo "  查看日志:  docker compose logs -f openclaw-gateway"
echo ""
echo -e "  ${YELLOW}安全提醒:${NC}"
echo "    - 请在 Moonshot 平台设置 API 支出限额，防止 Key 泄露后被刷"
echo "    - 建议配置 Nginx 反向代理 + HTTPS（见 docs/DEPLOYMENT_GUIDE.md）"
echo "    - 定期更新 OpenClaw 获取安全补丁"
echo "    - 请勿在存有敏感数据的服务器上运行 OpenClaw"
echo "=============================================="
