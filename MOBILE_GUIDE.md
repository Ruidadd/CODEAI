# OpenClaw 手机使用指南

## 简介

OpenClaw 是一个**自托管的个人 AI 助手网关**，它将你常用的消息应用（如微信、WhatsApp、Telegram、Slack 等）与 AI 智能体连接起来。你可以在自己的服务器或手机上运行 OpenClaw 网关，数据完全私有，不经过第三方。

支持的消息平台包括：WhatsApp、Telegram、Slack、Discord、Google Chat、Signal、iMessage（需 BlueBubbles）、Microsoft Teams、Matrix、Zalo 以及内置 WebChat。

---

## Android 使用方式

### 方式一：官方 Android 伴侣 App（推荐）

官方 Android 应用可将你的手机变成一个"AI 节点"，通过 WebSocket 连接到已运行的 OpenClaw 网关，并将摄像头、麦克风、屏幕和传感器接入 AI 系统。

**步骤：**
1. 确保你已在服务器或电脑上部署了 OpenClaw 网关。
2. 在 Android 设备上安装官方 OpenClaw 伴侣 App。
3. 若手机与网关在同一局域网内，App 会通过 mDNS 自动发现网关，无需手动配置 IP。
4. 配对成功后，即可通过手机直接与 AI 交互，支持语音、摄像头、Canvas 等功能。

**参考文档：** https://docs.openclaw.ai/platforms/android

---

### 方式二：Termux 直接安装（进阶）

通过 Termux 在 Android 手机上直接运行 OpenClaw 网关，将手机本身变成服务器。

**步骤：**
1. 在 Android 上安装 [Termux](https://termux.dev/)。
2. 在 Termux 中运行以下命令（安装时间约 3–10 分钟）：

   ```bash
   curl -sL myopenclawhub.com/install | bash
   ```

3. 安装完成后，在 **Termux 内直接启动网关**（不要通过 SSH 连接后再启动，否则断开 SSH 后网关会停止运行）。

**参考教程：** https://gist.github.com/alisolanki/84422f89575970eac848f552af188816

---

### 方式三：消息应用接入（最简单）

如果你已经在服务器上运行了 OpenClaw 网关，只需将 Telegram 或 WhatsApp 等消息应用与网关绑定，即可直接在手机的消息 App 中与 AI 对话，无需额外安装任何 OpenClaw 专属客户端。

**步骤：**
1. 在服务器上部署并启动 OpenClaw 网关。
2. 在网关配置中启用 Telegram 或 WhatsApp 频道，按提示完成绑定。
3. 在手机上打开已有的 Telegram 或 WhatsApp，向绑定的 AI 机器人发消息即可使用。

---

## iOS 使用方式

### 方式一：官方 iOS 伴侣 App

官方 iOS 伴侣 App 可连接到你已部署的 OpenClaw 网关，提供原生 iOS 体验。

**功能：**
- Canvas 交互界面（实时可视化操作）
- 摄像头与语音输入
- 流式 AI 响应

**安装：**
- 在 App Store 搜索 **OpenClaw Messenger**（App ID：6759085147）或直接访问：
  https://apps.apple.com/us/app/openclaw-messenger/id6759085147

**前提条件：** 需要有已在运行的 OpenClaw 网关实例。

---

### 方式二：OpenClaw Mobile（独立 App）

无需自己部署网关，也无需 API 密钥，直接在 iPhone 上使用 AI。

**安装：**
- 在 App Store 搜索 **OpenClaw Mobile** 并安装即可。

适合不想自托管、希望快速体验 AI 功能的用户。

---

## 快速上手建议

| 场景 | 推荐方式 |
|------|----------|
| 想最快速体验，不折腾 | iOS/Android 上使用 OpenClaw Mobile 独立 App，或通过 Telegram/WhatsApp 接入已有网关 |
| 想要完整功能（语音、摄像头、Canvas）| 部署网关 + 安装官方伴侣 App |
| 想把旧安卓手机变成 24/7 AI 服务器 | Termux 方式安装网关 |

---

## 参考资源

- 官方网站：https://openclaw.ai/
- 官方文档：https://docs.openclaw.ai/
- GitHub 仓库：https://github.com/openclaw/openclaw
- Android 平台文档：https://docs.openclaw.ai/platforms/android
- iOS App Store（OpenClaw Messenger）：https://apps.apple.com/us/app/openclaw-messenger/id6759085147
