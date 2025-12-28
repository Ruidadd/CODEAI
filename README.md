# 🚀 AI选股器

> AI驱动的智能股票分析工具 - 上传截图，立即获得专业分析

基于Claude AI的股票图表分析工具，提供类似OpenAI的现代化界面，支持图片上传、自动分析和智能建议。

![AI选股器](https://img.shields.io/badge/AI-Claude-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Node](https://img.shields.io/badge/node-%3E%3D14-brightgreen)

## ✨ 特性

- 🎨 **现代化UI** - 类似OpenAI的暗色主题设计
- 📊 **智能分析** - Claude AI驱动的专业技术分析
- 🖼️ **图片上传** - 支持拖拽上传、点击上传
- 📈 **多维分析** - 技术指标、趋势判断、风险评估
- 💡 **操作建议** - 基于AI的买卖建议
- 📝 **历史记录** - 自动保存分析历史
- 🚀 **即开即用** - 零配置前端，快速部署

## 📸 截图

```
┌─────────────────────────────────────────────────────┐
│  📊 AI选股器                            [+ 新建分析] │
├─────────────┬───────────────────────────────────────┤
│             │   AI驱动的智能选股分析                │
│  分析历史   │   上传股票图表截图，AI将为您提供专业   │
│             │   的分析建议                          │
│  • 腾讯... │                                       │
│  • 阿里... │   📊 技术分析  📈 趋势判断  💡 投资建议│
│             │                                       │
│             │   [拖拽或点击上传图片]                │
└─────────────┴───────────────────────────────────────┘
```

## 🛠️ 技术栈

- **前端**: HTML5, CSS3, Vanilla JavaScript
- **后端**: Node.js, Express
- **AI**: Claude 3.5 Sonnet (Anthropic)
- **文件处理**: Multer
- **样式**: 自定义CSS (暗色主题)

## 📦 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd CODEAI
```

### 2. 安装依赖

```bash
npm install
```

### 3. 配置API密钥

复制环境变量模板并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，添加您的Anthropic API密钥：

```env
ANTHROPIC_API_KEY=your_api_key_here
PORT=3000
```

> 💡 **获取API密钥**: 访问 [Anthropic Console](https://console.anthropic.com/) 注册并获取API密钥

### 4. 启动服务

```bash
npm start
```

服务启动后，访问: `http://localhost:3000`

## 🎯 使用指南

### 基础使用

1. **上传图片**
   - 点击上传按钮选择股票图表截图
   - 或直接拖拽图片到输入区域

2. **添加要求**（可选）
   - 在文本框中输入额外的分析要求
   - 例如："重点关注短期趋势"

3. **获取分析**
   - 点击发送按钮
   - AI将自动分析图表并给出专业建议

### 分析内容

AI会提供以下维度的分析：

- 📊 **图表概览** - 整体走势描述
- 📈 **技术指标** - 均线、MACD、RSI等
- 🎯 **关键点位** - 支撑位和阻力位
- 💡 **趋势判断** - 上升/下降/震荡
- ⚠️ **风险提示** - 潜在风险警告
- 🎪 **操作建议** - 买入/卖出/观望

## 📁 项目结构

```
CODEAI/
├── public/                 # 前端静态文件
│   ├── index.html         # 主页面
│   ├── style.css          # 样式文件
│   └── app.js             # 前端逻辑
├── server.js              # Express服务器
├── ai-analyzer.js         # AI分析模块
├── package.json           # 项目配置
├── .env.example           # 环境变量模板
├── .gitignore            # Git忽略文件
└── README.md             # 项目文档
```

## 🔧 API接口

### POST /api/analyze

分析股票图片

**请求**:
- Content-Type: `multipart/form-data`
- Body:
  - `image`: 图片文件 (必需)
  - `prompt`: 自定义提示 (可选)

**响应**:
```json
{
  "success": true,
  "analysis": "分析结果文本..."
}
```

### GET /api/health

健康检查

**响应**:
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "apiKeyConfigured": true
}
```

## 🎨 自定义配置

### 修改端口

在 `.env` 文件中修改：

```env
PORT=8080
```

### 自定义分析提示词

编辑 `ai-analyzer.js` 中的 `STOCK_ANALYSIS_SYSTEM_PROMPT` 变量

### 调整主题颜色

修改 `public/style.css` 中的CSS变量：

```css
:root {
    --bg-primary: #0d0d0d;
    --accent-color: #10a37f;
    /* 更多颜色... */
}
```

## 🚀 部署

### 本地部署

```bash
npm start
```

### Docker部署（可选）

创建 `Dockerfile`:

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

构建并运行：

```bash
docker build -t ai-stock-picker .
docker run -p 3000:3000 --env-file .env ai-stock-picker
```

### 云平台部署

支持部署到：
- Heroku
- Railway
- Render
- Vercel (需要适配Serverless)

## ⚠️ 注意事项

1. **API费用**: 使用Anthropic API会产生费用，请注意用量
2. **免责声明**: AI分析仅供参考，不构成投资建议
3. **数据安全**: 上传的图片会临时存储后删除
4. **图片大小**: 单个图片最大10MB
5. **支持格式**: JPG, PNG, GIF, WebP

## 🐛 故障排除

### API密钥错误

```
错误: API密钥无效
解决: 检查.env文件中的ANTHROPIC_API_KEY是否正确
```

### 端口被占用

```
错误: Error: listen EADDRINUSE
解决: 修改.env中的PORT或关闭占用端口的程序
```

### 依赖安装失败

```bash
# 清除缓存重新安装
rm -rf node_modules package-lock.json
npm install
```

## 📝 开发计划

- [ ] 添加更多技术指标支持
- [ ] 支持批量分析
- [ ] 添加用户认证
- [ ] 实时股票数据集成
- [ ] 移动端优化
- [ ] 多语言支持

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- [Anthropic](https://www.anthropic.com/) - 提供Claude AI
- [OpenAI](https://openai.com/) - UI设计灵感
- 所有开源贡献者

---

**⭐ 如果这个项目对你有帮助，请给一个Star！**
