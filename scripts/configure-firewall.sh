#!/usr/bin/env bash
# =============================================================================
# 防火墙配置脚本
# 开放 OpenClaw 所需端口（18789 Gateway / 18790 Bridge）
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

PORTS=("18789" "18790")

# ── firewalld（CentOS / Alibaba Cloud Linux） ─────────────────────────────
if command -v firewall-cmd &>/dev/null && systemctl is-active firewalld &>/dev/null; then
    info "检测到 firewalld，配置端口放通..."
    for port in "${PORTS[@]}"; do
        if ! firewall-cmd --query-port="${port}/tcp" --quiet 2>/dev/null; then
            firewall-cmd --permanent --add-port="${port}/tcp"
            info "已添加端口 ${port}/tcp"
        else
            ok "端口 ${port}/tcp 已开放"
        fi
    done
    firewall-cmd --reload
    ok "firewalld 配置完成"

# ── ufw（Ubuntu / Debian） ──────────────────────────────────────────────
elif command -v ufw &>/dev/null; then
    info "检测到 ufw，配置端口放通..."
    for port in "${PORTS[@]}"; do
        ufw allow "${port}/tcp" 2>/dev/null || true
        ok "端口 ${port}/tcp 已允许"
    done

    # 确保 SSH 端口保持开放
    ufw allow 22/tcp 2>/dev/null || true

    # 启用 ufw（如果未启用）
    if ! ufw status | grep -q "Status: active"; then
        echo "y" | ufw enable 2>/dev/null || true
    fi
    ok "ufw 配置完成"

# ── iptables 回退 ──────────────────────────────────────────────────────
elif command -v iptables &>/dev/null; then
    info "使用 iptables 配置端口放通..."
    for port in "${PORTS[@]}"; do
        if ! iptables -C INPUT -p tcp --dport "${port}" -j ACCEPT 2>/dev/null; then
            iptables -I INPUT -p tcp --dport "${port}" -j ACCEPT
            ok "iptables: 已开放端口 ${port}/tcp"
        else
            ok "iptables: 端口 ${port}/tcp 已开放"
        fi
    done

    # 持久化 iptables 规则
    if command -v iptables-save &>/dev/null; then
        iptables-save > /etc/iptables.rules 2>/dev/null || true
    fi
    ok "iptables 配置完成"
else
    warn "未检测到防火墙管理工具，跳过系统防火墙配置"
fi

# ── 提醒用户配置阿里云安全组 ──────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  ${YELLOW}重要提醒：阿里云安全组/防火墙配置${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  系统防火墙已配置完成。"
echo "  如果是轻量应用服务器且使用 OpenClaw 预装镜像，"
echo "  请在服务器详情页 → 应用详情 → 点击「一键放通」按钮。"
echo ""
echo "  如果是手动配置，请在阿里云控制台添加以下安全组规则："
echo ""
echo "  ┌──────────┬──────────┬──────────┬──────────┐"
echo "  │ 协议类型  │ 端口范围  │ 授权对象  │ 说明     │"
echo "  ├──────────┼──────────┼──────────┼──────────┤"
echo "  │ TCP      │ 18789    │ 0.0.0.0/0│ Gateway  │"
echo "  │ TCP      │ 18790    │ 0.0.0.0/0│ Bridge   │"
echo "  └──────────┴──────────┴──────────┴──────────┘"
echo ""
echo "  控制台路径：轻量应用服务器 → 实例详情 → 防火墙 → 添加规则"
echo ""
