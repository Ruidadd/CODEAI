#!/usr/bin/env bash
# =============================================================================
# Kimi 2.5 (Moonshot AI) 模型配置脚本
# 为 OpenClaw 配置 Kimi 2.5 作为 Primary Model
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
CONFIG_DIR="${OPENCLAW_HOME}/config"
CONFIG_FILE="${CONFIG_DIR}/openclaw.json"

# ── 获取 Moonshot API Key ────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  配置 Kimi 2.5 模型 (Moonshot AI)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  请前往 Moonshot 开放平台获取 API Key:"
echo "  https://platform.moonshot.cn/console/api-keys"
echo ""

MOONSHOT_API_KEY="${MOONSHOT_API_KEY:-}"

if [[ -z "$MOONSHOT_API_KEY" ]]; then
    read -rp "请输入 Moonshot API Key: " MOONSHOT_API_KEY
fi

if [[ -z "$MOONSHOT_API_KEY" ]]; then
    fail "Moonshot API Key 不能为空"
fi

# 简单格式校验
if [[ ! "$MOONSHOT_API_KEY" =~ ^sk- ]]; then
    warn "API Key 格式可能不正确（通常以 sk- 开头），继续配置..."
fi

# ── 测试 API 连通性 ──────────────────────────────────────────────────────────
info "测试 Moonshot API 连通性..."
HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${MOONSHOT_API_KEY}" \
    "https://api.moonshot.cn/v1/models" 2>/dev/null || echo "000")

if [[ "$HTTP_CODE" == "200" ]]; then
    ok "Moonshot API 连通正常"
elif [[ "$HTTP_CODE" == "401" ]]; then
    fail "API Key 无效（HTTP 401），请检查后重试"
elif [[ "$HTTP_CODE" == "000" ]]; then
    warn "无法连接 Moonshot API（网络问题），将继续配置。请稍后手动验证。"
else
    warn "Moonshot API 返回 HTTP ${HTTP_CODE}，将继续配置"
fi

# ── 写入配置 ─────────────────────────────────────────────────────────────────
mkdir -p "${CONFIG_DIR}"

# 方式 1：通过 openclaw CLI 配置（预装镜像场景）
if command -v openclaw &>/dev/null; then
    info "通过 OpenClaw CLI 配置模型..."

    openclaw config set agents.primaryModel "moonshot/kimi-k2.5"
    openclaw config set agents.imageModel "moonshot/kimi-k2.5-vision"
    openclaw config set modelProviders.moonshot.apiKey "${MOONSHOT_API_KEY}"
    openclaw config set modelProviders.moonshot.baseUrl "https://api.moonshot.cn/v1"
    openclaw config set modelProviders.moonshot.enabled true

    ok "模型配置已通过 CLI 写入"
else
    # 方式 2：直接写入 JSON 配置文件（Docker 场景）
    info "写入模型配置文件..."

    # 如果已有配置文件则合并，否则从模板创建
    if [[ -f "$CONFIG_FILE" ]]; then
        # 使用临时文件安全写入
        TEMP_CONFIG=$(mktemp)
        # 尝试使用 jq 合并配置
        if command -v jq &>/dev/null; then
            jq --arg key "$MOONSHOT_API_KEY" '
                .agents.primaryModel = "moonshot/kimi-k2.5" |
                .agents.imageModel = "moonshot/kimi-k2.5-vision" |
                .modelProviders.moonshot.apiKey = $key |
                .modelProviders.moonshot.baseUrl = "https://api.moonshot.cn/v1" |
                .modelProviders.moonshot.enabled = true
            ' "$CONFIG_FILE" > "$TEMP_CONFIG"
            mv "$TEMP_CONFIG" "$CONFIG_FILE"
        else
            warn "未安装 jq，将覆盖配置文件"
            cp "${SCRIPT_DIR}/../config/openclaw-kimi.json" "$TEMP_CONFIG"
            sed -i "s|YOUR_MOONSHOT_API_KEY|${MOONSHOT_API_KEY}|g" "$TEMP_CONFIG"
            mv "$TEMP_CONFIG" "$CONFIG_FILE"
        fi
    else
        cp "${SCRIPT_DIR}/../config/openclaw-kimi.json" "$CONFIG_FILE"
        sed -i "s|YOUR_MOONSHOT_API_KEY|${MOONSHOT_API_KEY}|g" "$CONFIG_FILE"
    fi

    chown 1000:1000 "$CONFIG_FILE" 2>/dev/null || true
    ok "模型配置文件已写入：${CONFIG_FILE}"
fi

# ── 保存 API Key 到环境变量文件 ──────────────────────────────────────────────
ENV_FILE="${OPENCLAW_HOME}/.env"
if [[ -f "$ENV_FILE" ]]; then
    # 追加或更新 MOONSHOT_API_KEY
    if grep -q "MOONSHOT_API_KEY" "$ENV_FILE" 2>/dev/null; then
        sed -i "s|^MOONSHOT_API_KEY=.*|MOONSHOT_API_KEY=${MOONSHOT_API_KEY}|" "$ENV_FILE"
    else
        echo "MOONSHOT_API_KEY=${MOONSHOT_API_KEY}" >> "$ENV_FILE"
    fi
else
    echo "MOONSHOT_API_KEY=${MOONSHOT_API_KEY}" > "$ENV_FILE"
fi

ok "Kimi 2.5 模型配置完成"
echo ""
echo "  Primary Model:  moonshot/kimi-k2.5"
echo "  Image Model:    moonshot/kimi-k2.5-vision"
echo "  API Base URL:   https://api.moonshot.cn/v1"
echo ""
