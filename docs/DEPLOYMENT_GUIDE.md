# OpenClaw 阿里云部署详细指南

## 目录

- [一、购买阿里云轻量应用服务器](#一购买阿里云轻量应用服务器)
- [二、获取 Moonshot API Key](#二获取-moonshot-api-key)
- [三、SSH 连接服务器并部署](#三ssh-连接服务器并部署)
- [四、配置钉钉机器人](#四配置钉钉机器人)
- [五、配置 QQ 机器人](#五配置-qq-机器人)
- [六、常见问题排查](#六常见问题排查)
- [七、运维命令速查表](#七运维命令速查表)
- [八、安全加固](#八安全加固)

---

## 一、购买阿里云轻量应用服务器

### 推荐配置

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| 镜像 | OpenClaw (Moltbot) | 预装 OpenClaw 运行环境 |
| CPU | 2 核 | 最低要求 |
| 内存 | 4 GB | 2GB 可运行，4GB 更流畅 |
| 磁盘 | 40 GB SSD | 10GB 最低 |
| 地域 | 美国（弗吉尼亚） | **重要**：中国内地域联网搜索受限 |
| 带宽 | 30 Mbps | 默认即可 |

### 操作步骤

1. **访问一键部署页面**
   - 打开 https://www.aliyun.com/activity/ecs/clawdbot
   - 点击 **「一键购买并部署」**

2. **选择配置**
   - 镜像选择 **OpenClaw (Moltbot)**（如已有服务器，可在实例管理中重置系统选择该镜像）
   - 套餐选择 2 核 4G 或以上
   - 地域选择 **美国（弗吉尼亚）**

3. **完成购买**
   - 确认订单并支付
   - 等待实例创建完成（约 1-3 分钟）

4. **获取服务器信息**
   - 在控制台找到该实例
   - 记录 **公网 IP 地址**
   - 设置 **root 密码**（或上传 SSH 密钥）

---

## 二、获取 Moonshot API Key

Kimi 2.5 由 Moonshot AI 提供，需要获取 API Key。

### 操作步骤

1. **注册/登录 Moonshot 平台**
   - 打开 https://platform.moonshot.cn/
   - 注册账号并完成手机验证

2. **获取 API Key**
   - 登录后进入控制台
   - 点击左侧「API 密钥」菜单
   - 点击「创建新密钥」
   - **立即复制并保存** API Key（只显示一次）
   - API Key 格式类似：`sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

3. **充值额度**（可选）
   - 新用户有免费额度
   - 如需更多调用量，在「账户管理」中充值

---

## 三、SSH 连接服务器并部署

### 3.1 连接服务器

**Windows 用户**（使用 PowerShell 或 Xshell）：
```bash
ssh root@你的服务器公网IP
```

**macOS / Linux 用户**：
```bash
ssh root@你的服务器公网IP
```

### 3.2 一键部署

```bash
# 克隆部署脚本仓库
git clone https://github.com/Ruidadd/CODEAI.git
cd CODEAI

# 运行一键部署脚本
bash setup.sh
```

脚本会依次执行：
1. 环境预检（内存、磁盘）
2. OpenClaw 安装/检测
3. Kimi 2.5 模型配置（**需输入 API Key**）
4. 防火墙端口放通
5. 服务启动
6. 健康检查

### 3.3 放通阿里云安全组

如果使用 OpenClaw 预装镜像：
- 进入服务器实例详情页
- 点击 **「应用详情」** 标签
- 在「使用步骤」区域找到 **「一键放通」** 按钮并点击

如果手动配置：
- 进入实例详情 → **防火墙** 标签
- 添加规则：TCP 端口 18789、18790，授权对象 0.0.0.0/0

### 3.4 访问 OpenClaw

部署完成后，在浏览器中访问：
```
http://你的服务器公网IP:18789/?token=你的Token
```

Token 会在部署脚本结束时显示。

---

## 四、配置钉钉机器人

### 4.1 创建钉钉应用

1. 登录 [钉钉开放平台](https://open.dingtalk.com/)
2. 点击 **「创建应用」**（需要开发者权限）
3. 填写应用名称（如「AI 助手」）
4. 进入应用管理页面

### 4.2 添加机器人能力

1. 在应用管理页面，点击 **「添加应用能力」**
2. 选择 **「机器人」**
3. 配置机器人信息：
   - 消息接收模式：选择 **Stream 模式**
   - 这样无需配置公网回调地址

### 4.3 获取凭证

在应用的 **「凭证与基础信息」** 页面：
- 记录 **Client ID**（AppKey）
- 记录 **Client Secret**（AppSecret）

### 4.4 运行配置脚本

```bash
cd /root/CODEAI  # 或你克隆仓库的路径
bash config/channels/dingtalk-setup.sh
```

按提示输入 Client ID 和 Client Secret。

### 4.5 测试

1. 在钉钉中搜索你创建的应用/机器人
2. 发送消息「你好」
3. 等待 AI 回复

---

## 五、配置 QQ 机器人

### 方式一：NapCat（推荐）

NapCat 使用 OneBot 11 协议，通过扫码登录 QQ，是目前最稳定的方案。

```bash
cd /root/CODEAI
bash config/channels/qq-setup.sh
# 选择选项 1: NapCat Docker
```

配置完成后：
1. 查看 NapCat 登录二维码：`docker logs -f napcat`
2. 使用手机 QQ 扫码登录
3. 登录成功后，向机器人 QQ 号发送消息测试

NapCat 管理面板：`http://服务器IP:6099`

### 方式二：QQ 官方机器人 API

需要企业资质，在 [QQ 开放平台](https://q.qq.com/) 注册。

```bash
bash config/channels/qq-setup.sh
# 选择选项 2: QQ 官方机器人 API
```

---

## 六、常见问题排查

### 问题 1：无法访问 18789 端口

**排查步骤：**
```bash
# 检查服务是否在运行
docker ps | grep openclaw

# 检查端口是否在监听
ss -tlnp | grep 18789

# 检查系统防火墙
firewall-cmd --list-ports  # CentOS
ufw status                 # Ubuntu

# 运行健康检查
bash scripts/health-check.sh
```

**解决方案：**
- 确认阿里云控制台安全组已放通 18789 端口
- 重启服务：`docker compose restart openclaw-gateway`

### 问题 2：模型回复失败

**排查步骤：**
```bash
# 查看日志中的模型调用错误
docker compose logs openclaw-gateway | grep -i "error\|moonshot\|model"

# 测试 API Key 是否有效
curl -H "Authorization: Bearer 你的API_KEY" https://api.moonshot.cn/v1/models
```

**解决方案：**
- 确认 API Key 正确且未过期
- 检查 Moonshot 账户余额
- 重新运行 `bash scripts/configure-model.sh`

### 问题 3：钉钉消息无回复

**排查步骤：**
```bash
# 查看钉钉相关日志
docker compose logs openclaw-gateway | grep -i dingtalk

# 检查插件是否已加载
openclaw plugins list
```

**解决方案：**
- 确认钉钉应用的机器人能力已启用
- 确认消息接收模式为 Stream 模式
- 重新运行 `bash config/channels/dingtalk-setup.sh`

### 问题 4：QQ NapCat 登录失败

**排查步骤：**
```bash
# 查看 NapCat 日志
docker logs -f napcat

# 检查容器状态
docker ps -a | grep napcat
```

**解决方案：**
- 确保 QQ 号已完成实名认证
- 扫码时确保手机和服务器网络通畅
- 如果二维码过期，重启容器：`docker restart napcat`

### 问题 5：服务启动后内存不足

```bash
# 查看内存使用
free -h

# 查看容器资源使用
docker stats --no-stream
```

**解决方案：** 升级服务器至 4GB 内存配置。

---

## 七、运维命令速查表

| 操作 | 命令 |
|------|------|
| 查看容器状态 | `docker compose ps` |
| 查看实时日志 | `docker compose logs -f openclaw-gateway` |
| 重启服务 | `docker compose restart openclaw-gateway` |
| 停止服务 | `docker compose down` |
| 启动服务 | `docker compose up -d` |
| 查看插件列表 | `openclaw plugins list` |
| 修改配置 | `openclaw config set <key> <value>` |
| 健康检查 | `bash scripts/health-check.sh` |
| 查看资源使用 | `docker stats --no-stream` |
| 更新 OpenClaw | `cd ~/openclaw/openclaw && git pull && docker compose up -d --build` |
| 查看 NapCat 日志 | `docker logs -f napcat` |
| 重启 NapCat | `docker restart napcat` |

---

## 八、安全加固

### 基础安全措施

```bash
# 1. 修改 SSH 端口（可选）
# 编辑 /etc/ssh/sshd_config，修改 Port 22 为其他端口

# 2. 禁止 root 密码登录（配置 SSH 密钥后）
# 编辑 /etc/ssh/sshd_config：PasswordAuthentication no

# 3. 安装 fail2ban 防暴力破解
apt install -y fail2ban  # Ubuntu
yum install -y fail2ban  # CentOS

# 4. 启用自动安全更新
apt install -y unattended-upgrades  # Ubuntu
```

### OpenClaw 安全配置

- 部署完成后，在 OpenClaw Web 面板中设置强密码
- 如不需要公网访问 Web 面板，在安全组中移除 18789 端口的公网访问规则
- 定期更新 OpenClaw 到最新版本以获取安全补丁
- 建议升级到 v2026.1.29 以上版本（修复了 CVE-2026-25253）

### 注意事项

> OpenClaw 作为 AI Agent 具有执行 Shell 命令和读写文件的能力。
> 请勿在存有敏感数据的服务器上运行 OpenClaw，建议使用独立的服务器实例。
