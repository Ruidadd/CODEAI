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

# 临时文件清理：确保异常退出时不残留敏感数据
TEMP_FILES=()
cleanup() { for f in "${TEMP_FILES[@]}"; do rm -f "$f"; done; }
trap cleanup EXIT

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

# 格式校验：前缀 + 最小长度
if [[ ! "$MOONSHOT_API_KEY" =~ ^sk- ]]; then
    warn "API Key 格式可能不正确（通常以 sk- 开头），继续配置..."
fi
if [[ ${#MOONSHOT_API_KEY} -lt 20 ]]; then
    fail "API Key 长度不足（至少 20 字符），请检查是否复制完整"
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

    # 安全写入 JSON 配置（避免 sed 注入风险）
    # 优先级：jq > python3 > 自动安装 jq
    _safe_json_write() {
        local src="$1" dst="$2" api_key="$3" server_ip="$4"
        local tmp
        tmp=$(mktemp)
        TEMP_FILES+=("$tmp")

        if command -v jq &>/dev/null; then
            jq --arg key "$api_key" --arg ip "$server_ip" '
                .agents.primaryModel = "moonshot/kimi-k2.5" |
                .agents.imageModel = "moonshot/kimi-k2.5-vision" |
                .modelProviders.moonshot.apiKey = $key |
                .modelProviders.moonshot.baseUrl = "https://api.moonshot.cn/v1" |
                .modelProviders.moonshot.enabled = true |
                .security.allowedOrigins = [("http://" + $ip + ":18789")]
            ' "$src" > "$tmp"
        elif command -v python3 &>/dev/null; then
            python3 -c "
import json, sys
with open('$src') as f: cfg = json.load(f)
cfg.setdefault('agents', {})['primaryModel'] = 'moonshot/kimi-k2.5'
cfg['agents']['imageModel'] = 'moonshot/kimi-k2.5-vision'
cfg.setdefault('modelProviders', {}).setdefault('moonshot', {})['apiKey'] = sys.argv[1]
cfg['modelProviders']['moonshot']['baseUrl'] = 'https://api.moonshot.cn/v1'
cfg['modelProviders']['moonshot']['enabled'] = True
cfg.setdefault('security', {})['allowedOrigins'] = ['http://' + sys.argv[2] + ':18789']
with open('$tmp', 'w') as f: json.dump(cfg, f, indent=4)
" "$api_key" "$server_ip"
        else
            info "安装 jq 以安全写入 JSON..."
            apt-get install -y -qq jq 2>/dev/null || yum install -y -q jq 2>/dev/null || fail "无法安装 jq，请手动安装后重试"
            jq --arg key "$api_key" --arg ip "$server_ip" '
                .agents.primaryModel = "moonshot/kimi-k2.5" |
                .agents.imageModel = "moonshot/kimi-k2.5-vision" |
                .modelProviders.moonshot.apiKey = $key |
                .modelProviders.moonshot.baseUrl = "https://api.moonshot.cn/v1" |
                .modelProviders.moonshot.enabled = true |
                .security.allowedOrigins = [("http://" + $ip + ":18789")]
            ' "$src" > "$tmp"
        fi
        mv "$tmp" "$dst"
    }

    # 获取服务器 IP 用于 CORS 配置
    SERVER_IP=$(curl -sf http://100.100.100.200/latest/meta-data/eipv4 2>/dev/null \
        || curl -sf --max-time 5 ifconfig.me 2>/dev/null \
        || hostname -I | awk '{print $1}')

    if [[ -f "$CONFIG_FILE" ]]; then
        _safe_json_write "$CONFIG_FILE" "$CONFIG_FILE" "$MOONSHOT_API_KEY" "$SERVER_IP"
    else
        _safe_json_write "${SCRIPT_DIR}/../config/openclaw-kimi.json" "$CONFIG_FILE" "$MOONSHOT_API_KEY" "$SERVER_IP"
    fi

    chown 1000:1000 "$CONFIG_FILE" 2>/dev/null || true
    ok "模型配置文件已写入：${CONFIG_FILE}"
fi

# ── 保存 API Key 到环境变量文件（权限加固） ────────────────────────────────────
ENV_FILE="${OPENCLAW_HOME}/.env"
if [[ -f "$ENV_FILE" ]]; then
    # 安全更新：写入临时文件再原子替换，避免 sed 注入
    ENV_TMP=$(mktemp)
    TEMP_FILES+=("$ENV_TMP")
    grep -v "^MOONSHOT_API_KEY=" "$ENV_FILE" > "$ENV_TMP" 2>/dev/null || true
    echo "MOONSHOT_API_KEY=${MOONSHOT_API_KEY}" >> "$ENV_TMP"
    mv "$ENV_TMP" "$ENV_FILE"
else
    echo "MOONSHOT_API_KEY=${MOONSHOT_API_KEY}" > "$ENV_FILE"
fi
# 限制 .env 文件权限：仅 root 可读写
chmod 600 "$ENV_FILE"
ok ".env 文件权限已设置为 600（仅 root 可读）"

ok "Kimi 2.5 模型配置完成"
echo ""
echo "  Primary Model:  moonshot/kimi-k2.5"
echo "  Image Model:    moonshot/kimi-k2.5-vision"
echo "  API Base URL:   https://api.moonshot.cn/v1"
echo ""
