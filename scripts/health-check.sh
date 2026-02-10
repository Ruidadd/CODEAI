#!/usr/bin/env bash
# =============================================================================
# OpenClaw 健康检查脚本
# 检查服务状态、端口可达性、模型连通性、插件状态
# =============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
WARN=0
FAIL=0

check_pass() { echo -e "  ${GREEN}[PASS]${NC} $*"; ((PASS++)); }
check_warn() { echo -e "  ${YELLOW}[WARN]${NC} $*"; ((WARN++)); }
check_fail() { echo -e "  ${RED}[FAIL]${NC} $*"; ((FAIL++)); }

OPENCLAW_HOME="${OPENCLAW_HOME:-/opt/openclaw}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  OpenClaw 健康检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 1. Docker 服务 ──────────────────────────────────────────────────────────
echo "1. Docker 服务状态"
if systemctl is-active docker &>/dev/null; then
    check_pass "Docker 服务运行中"
else
    check_fail "Docker 服务未运行"
fi

# ── 2. 容器状态 ─────────────────────────────────────────────────────────────
echo "2. OpenClaw 容器状态"
if docker ps --format '{{.Names}} {{.Status}}' | grep -q "openclaw"; then
    CONTAINER_STATUS=$(docker ps --format '{{.Names}}: {{.Status}}' | grep "openclaw")
    check_pass "容器运行中 - ${CONTAINER_STATUS}"
else
    check_fail "未找到运行中的 OpenClaw 容器"
fi

# ── 3. Gateway 端口 ─────────────────────────────────────────────────────────
echo "3. Gateway 端口检测"
if ss -tlnp | grep -q ":18789"; then
    check_pass "端口 18789 正在监听"
else
    check_fail "端口 18789 未监听"
fi

# ── 4. HTTP 健康端点 ────────────────────────────────────────────────────────
echo "4. HTTP 健康检查"
HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:18789/health 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
    check_pass "健康端点响应正常 (HTTP 200)"
elif [[ "$HTTP_CODE" == "000" ]]; then
    check_fail "无法连接健康端点 http://localhost:18789/health"
else
    check_warn "健康端点返回 HTTP ${HTTP_CODE}"
fi

# ── 5. 模型 API 连通性 ──────────────────────────────────────────────────────
echo "5. Moonshot API 连通性"
MOONSHOT_API_KEY=""
if [[ -f "${OPENCLAW_HOME}/.env" ]]; then
    MOONSHOT_API_KEY=$(grep "MOONSHOT_API_KEY" "${OPENCLAW_HOME}/.env" 2>/dev/null | cut -d'=' -f2 || true)
fi

if [[ -n "$MOONSHOT_API_KEY" ]]; then
    API_CODE=$(curl -sf -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer ${MOONSHOT_API_KEY}" \
        "https://api.moonshot.cn/v1/models" 2>/dev/null || echo "000")
    if [[ "$API_CODE" == "200" ]]; then
        check_pass "Moonshot API 连通正常"
    elif [[ "$API_CODE" == "000" ]]; then
        check_warn "无法连接 Moonshot API（可能是网络问题）"
    elif [[ "$API_CODE" == "401" ]]; then
        check_fail "Moonshot API Key 无效 (HTTP 401)"
    else
        check_warn "Moonshot API 返回 HTTP ${API_CODE}"
    fi
else
    check_warn "未找到 Moonshot API Key，跳过 API 检查"
fi

# ── 6. 插件状态 ─────────────────────────────────────────────────────────────
echo "6. 插件状态"
if command -v openclaw &>/dev/null; then
    PLUGINS=$(openclaw plugins list 2>/dev/null || echo "")
    if echo "$PLUGINS" | grep -qi "dingtalk"; then
        check_pass "钉钉插件已安装"
    else
        check_warn "钉钉插件未安装（可运行 config/channels/dingtalk-setup.sh）"
    fi
    if echo "$PLUGINS" | grep -qi "qq\|napcat\|onebot"; then
        check_pass "QQ 插件已安装"
    else
        check_warn "QQ 插件未安装（可运行 config/channels/qq-setup.sh）"
    fi
else
    check_warn "openclaw CLI 不可用，跳过插件检查"
fi

# ── 7. 磁盘空间 ────────────────────────────────────────────────────────────
echo "7. 系统资源"
AVAIL_DISK=$(df / --output=avail -BG | tail -1 | tr -d ' G')
if [[ $AVAIL_DISK -gt 5 ]]; then
    check_pass "磁盘空间充足：${AVAIL_DISK}GB 可用"
else
    check_warn "磁盘空间较低：${AVAIL_DISK}GB 可用"
fi

MEM_AVAIL=$(grep MemAvailable /proc/meminfo | awk '{printf "%.0f", $2/1024}')
if [[ $MEM_AVAIL -gt 500 ]]; then
    check_pass "可用内存：${MEM_AVAIL}MB"
else
    check_warn "可用内存较低：${MEM_AVAIL}MB"
fi

# ── 汇总 ────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  检查结果: ${GREEN}${PASS} 通过${NC}  ${YELLOW}${WARN} 警告${NC}  ${RED}${FAIL} 失败${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "  ${RED}存在失败项，请根据上述提示排查问题。${NC}"
    echo "  查看日志: docker compose logs -f openclaw-gateway"
    exit 1
elif [[ $WARN -gt 0 ]]; then
    echo -e "  ${YELLOW}有警告项，服务基本可用但建议关注。${NC}"
else
    echo -e "  ${GREEN}所有检查通过，OpenClaw 运行正常!${NC}"
fi
echo ""
