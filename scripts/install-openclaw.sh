#!/usr/bin/env bash
# =============================================================================
# OpenClaw 安装/初始化脚本
# 支持两种场景：阿里云预装镜像 / 全新 Linux 系统
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

# ── 场景 1：阿里云预装镜像已存在 ─────────────────────────────────────────────
if command -v openclaw &>/dev/null; then
    CURRENT_VERSION=$(openclaw --version 2>/dev/null || echo "unknown")
    ok "检测到已安装 OpenClaw（版本: ${CURRENT_VERSION}），跳过安装步骤"

    # 确保持久化目录存在
    mkdir -p "${OPENCLAW_HOME}"/{config,workspace,certs,logs}
    chown -R 1000:1000 "${OPENCLAW_HOME}"/{config,workspace} 2>/dev/null || true

    exit 0
fi

# ── 场景 2：全新系统 → Docker 安装 ──────────────────────────────────────────
info "未检测到 OpenClaw，将通过 Docker 方式安装..."

# ─── 安装 Docker ──────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    info "安装 Docker..."

    # 尝试阿里云镜像源（国内加速）
    if curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg 2>/dev/null | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg 2>/dev/null; then
        . /etc/os-release
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://mirrors.aliyun.com/docker-ce/linux/${ID} ${VERSION_CODENAME} stable" \
            > /etc/apt/sources.list.d/docker.list
        apt-get update -qq
        apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    else
        # 回退到官方安装脚本
        curl -fsSL https://get.docker.com | sh
    fi

    systemctl enable docker
    systemctl start docker
    ok "Docker 安装完成"
else
    ok "Docker 已安装：$(docker --version)"
fi

# 检查 Docker Compose
if ! docker compose version &>/dev/null; then
    info "安装 Docker Compose 插件..."
    apt-get install -y -qq docker-compose-plugin 2>/dev/null \
        || pip3 install docker-compose 2>/dev/null \
        || fail "Docker Compose 安装失败，请手动安装"
    ok "Docker Compose 安装完成"
else
    ok "Docker Compose 已安装"
fi

# 配置 Docker 镜像加速（阿里云）
if [[ ! -f /etc/docker/daemon.json ]] || ! grep -q "mirror" /etc/docker/daemon.json 2>/dev/null; then
    info "配置 Docker 镜像加速..."
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json <<'DAEMON_JSON'
{
    "registry-mirrors": [
        "https://mirror.ccs.tencentyun.com",
        "https://docker.mirrors.ustc.edu.cn"
    ],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "50m",
        "max-file": "3"
    }
}
DAEMON_JSON
    systemctl daemon-reload
    systemctl restart docker
    ok "Docker 镜像加速已配置"
fi

# ─── 克隆 OpenClaw 仓库 ──────────────────────────────────────────────────
OPENCLAW_SRC="${HOME}/openclaw"
if [[ -d "${OPENCLAW_SRC}/openclaw/.git" ]]; then
    info "更新 OpenClaw 源码..."
    cd "${OPENCLAW_SRC}/openclaw"
    git pull --ff-only || warn "源码更新失败，将使用当前版本"
else
    info "克隆 OpenClaw 源码..."
    mkdir -p "${OPENCLAW_SRC}"
    cd "${OPENCLAW_SRC}"
    git clone https://github.com/openclaw/openclaw.git
    cd openclaw
fi

# ─── 构建 Docker 镜像 ────────────────────────────────────────────────────
info "构建 OpenClaw Docker 镜像..."
LATEST_TAG=$(git tag --sort=-creatordate | head -1)
if [[ -z "$LATEST_TAG" ]]; then
    warn "未找到 Git 标签，使用 main 分支"
    LATEST_TAG="main"
    TAG_LABEL="latest"
else
    git checkout "$LATEST_TAG"
    TAG_LABEL="${LATEST_TAG#v}"
fi

docker build -t "openclaw:${TAG_LABEL}" -t "openclaw:latest" .
ok "OpenClaw 镜像构建完成：openclaw:${TAG_LABEL}"

# ─── 创建持久化目录和配置 ─────────────────────────────────────────────────
info "创建持久化目录..."
mkdir -p "${OPENCLAW_HOME}"/{config,workspace,certs,logs}
chown -R 1000:1000 "${OPENCLAW_HOME}"/{config,workspace}

# 生成 Gateway Token
if [[ ! -f "${OPENCLAW_HOME}/.env" ]] || ! grep -q "OPENCLAW_GATEWAY_TOKEN" "${OPENCLAW_HOME}/.env" 2>/dev/null; then
    GATEWAY_TOKEN=$(openssl rand -hex 32)
    cat > "${OPENCLAW_HOME}/.env" <<ENV_FILE
# OpenClaw 环境变量
OPENCLAW_GATEWAY_TOKEN=${GATEWAY_TOKEN}
OPENCLAW_HOME=${OPENCLAW_HOME}
TZ=Asia/Shanghai
ENV_FILE
    ok "Gateway Token 已生成"
else
    ok "Gateway Token 已存在"
fi

# ─── 生成 Docker Compose 文件 ─────────────────────────────────────────────
info "生成 Docker Compose 配置..."
cat > "${OPENCLAW_HOME}/docker-compose.yml" <<'COMPOSE'
services:
  openclaw-gateway:
    image: openclaw:latest
    container_name: openclaw-gateway
    restart: unless-stopped
    ports:
      - "18789:18789"
    volumes:
      - ./config:/home/node/.openclaw
      - ./workspace:/home/node/.openclaw/workspace
      - ./logs:/home/node/.openclaw/logs
    env_file:
      - .env
    environment:
      - TERM=xterm-256color
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 2048M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:18789/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
COMPOSE
ok "Docker Compose 配置已生成：${OPENCLAW_HOME}/docker-compose.yml"

# ─── 生成自签名 SSL 证书（可选） ──────────────────────────────────────────
if [[ ! -f "${OPENCLAW_HOME}/certs/openclaw.pem" ]]; then
    info "生成自签名 SSL 证书..."
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout "${OPENCLAW_HOME}/certs/openclaw.pem" \
        -out "${OPENCLAW_HOME}/certs/openclaw.pem" \
        -subj "/C=CN/ST=Beijing/L=Beijing/O=OpenClaw/CN=openclaw.local" \
        2>/dev/null
    ok "SSL 证书已生成"
fi

ok "OpenClaw 安装完成"
