const express = require('express');
const cors = require('cors');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// 中间件
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// 配置文件上传
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        const uploadDir = './uploads';
        if (!fs.existsSync(uploadDir)) {
            fs.mkdirSync(uploadDir, { recursive: true });
        }
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
        cb(null, uniqueSuffix + path.extname(file.originalname));
    }
});

const upload = multer({
    storage: storage,
    limits: {
        fileSize: 10 * 1024 * 1024 // 10MB限制
    },
    fileFilter: (req, file, cb) => {
        const allowedTypes = /jpeg|jpg|png|gif|webp/;
        const extname = allowedTypes.test(path.extname(file.originalname).toLowerCase());
        const mimetype = allowedTypes.test(file.mimetype);

        if (mimetype && extname) {
            return cb(null, true);
        } else {
            cb(new Error('只允许上传图片文件!'));
        }
    }
});

// 导入AI分析模块
const { analyzeStockImage } = require('./ai-analyzer');

// API路由
app.post('/api/analyze', upload.single('image'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: '未上传图片文件' });
        }

        console.log(`正在分析图片: ${req.file.filename}`);

        const customPrompt = req.body.prompt || '';
        const imagePath = req.file.path;

        // 调用AI分析
        const analysis = await analyzeStockImage(imagePath, customPrompt);

        // 分析完成后删除临时文件
        fs.unlink(imagePath, (err) => {
            if (err) console.error('删除临时文件失败:', err);
        });

        res.json({
            success: true,
            analysis: analysis
        });

    } catch (error) {
        console.error('分析错误:', error);

        // 清理上传的文件
        if (req.file) {
            fs.unlink(req.file.path, (err) => {
                if (err) console.error('删除临时文件失败:', err);
            });
        }

        res.status(500).json({
            error: '分析失败',
            message: error.message
        });
    }
});

// 健康检查
app.get('/api/health', (req, res) => {
    res.json({
        status: 'ok',
        timestamp: new Date().toISOString(),
        apiKeyConfigured: !!process.env.ANTHROPIC_API_KEY
    });
});

// 启动服务器
app.listen(PORT, () => {
    console.log(`
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║            🚀 AI选股器服务已启动                      ║
║                                                       ║
║   服务地址: http://localhost:${PORT}                ║
║   状态检查: http://localhost:${PORT}/api/health     ║
║                                                       ║
║   请在浏览器中访问以使用应用                          ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
    `);

    // 检查API密钥
    if (!process.env.ANTHROPIC_API_KEY) {
        console.warn(`
⚠️  警告: 未检测到 ANTHROPIC_API_KEY

   请按照以下步骤配置:
   1. 复制 .env.example 为 .env
   2. 在 .env 中设置您的 Anthropic API Key
   3. 重启服务器
        `);
    } else {
        console.log('✅ Anthropic API Key 已配置');
    }
});

// 错误处理
process.on('uncaughtException', (error) => {
    console.error('未捕获的异常:', error);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('未处理的Promise拒绝:', reason);
});
