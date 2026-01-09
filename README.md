# 📇 名片识别助手 | Business Card Scanner

使用 Google Gemini AI 自动识别名片信息，支持批量处理和多格式导出。

## ✨ 功能特点

- 🤖 **AI 智能识别** - 使用 Google Gemini Vision API 精准提取名片信息
- 📷 **多格式支持** - 支持 JPG、PNG、WebP、GIF、BMP 等常见图片格式
- 🌍 **多语言识别** - 支持中英文及其他语言名片
- 📊 **批量处理** - 一次上传多张名片，批量识别
- 📁 **多格式导出** - 支持导出为 CSV、Excel、JSON、vCard 格式

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey) 获取 Gemini API Key
2. 复制 `.env.example` 为 `.env` 并填入你的 API Key：
   ```bash
   cp .env.example .env
   ```
3. 或者直接在应用界面中输入 API Key

### 3. 运行应用

```bash
streamlit run app.py
```

应用将在浏览器中打开，默认地址：`http://localhost:8501`

## 📖 使用说明

### 上传名片

1. 在侧边栏输入你的 Gemini API Key
2. 点击「验证 API」确认连接成功
3. 在主页面上传名片图片（支持多选）
4. 点击「开始识别」按钮

### 查看结果

- 识别完成后，切换到「结果管理」标签页
- 查看表格形式的汇总数据
- 展开每张名片查看详细信息
- 可以删除不需要的名片记录

### 导出数据

支持以下导出格式：

| 格式 | 说明 | 适用场景 |
|------|------|----------|
| CSV | 逗号分隔值文件 | Excel、Google Sheets 等 |
| Excel | .xlsx 格式 | Microsoft Excel |
| JSON | 结构化数据 | 程序处理、API 集成 |
| vCard | .vcf 联系人格式 | 导入手机通讯录、Outlook 等 |

## 📋 识别字段

| 字段 | 说明 |
|------|------|
| 姓名 | 联系人姓名 |
| 公司 | 公司/组织名称 |
| 职位 | 职位/头衔 |
| 邮箱 | 电子邮件地址 |
| 电话 | 办公电话 |
| 手机 | 移动电话 |
| 传真 | 传真号码 |
| 地址 | 办公地址 |
| 网站 | 公司网站 |
| LinkedIn | LinkedIn 账号 |
| 微信 | 微信号 |
| 备注 | 其他信息 |

## 🛠️ 技术栈

- **前端**: Streamlit
- **AI 模型**: Google Gemini 2.0 Flash
- **数据处理**: Pandas
- **图像处理**: Pillow

## 📁 项目结构

```
├── app.py              # Streamlit 主应用
├── card_recognizer.py  # Gemini 名片识别服务
├── export_utils.py     # 导出工具函数
├── requirements.txt    # Python 依赖
├── .env.example        # 环境变量示例
├── .gitignore          # Git 忽略文件
└── README.md           # 项目说明
```

## ⚠️ 注意事项

- 请确保名片图片清晰，避免模糊或遮挡
- API 调用会消耗 Gemini API 配额
- 敏感信息请妥善保管，不要上传到公共平台

## 📄 License

MIT License
