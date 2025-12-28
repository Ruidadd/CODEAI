const Anthropic = require('@anthropic-ai/sdk');
const fs = require('fs');
const path = require('path');

// 初始化Anthropic客户端
const anthropic = new Anthropic({
    apiKey: process.env.ANTHROPIC_API_KEY,
});

// 股票分析系统提示词
const STOCK_ANALYSIS_SYSTEM_PROMPT = `你是一位专业的股票技术分析师，擅长通过图表分析股票走势。你的任务是:

1. **技术分析**: 识别并分析图表中的技术指标，如均线、成交量、MACD、RSI等
2. **形态识别**: 识别K线形态、趋势形态（头肩顶、双底等）
3. **支撑阻力**: 标识关键的支撑位和阻力位
4. **趋势判断**: 判断当前趋势（上升、下降、震荡）
5. **风险评估**: 评估当前价位的风险和机会
6. **操作建议**: 给出具体的买入、卖出或观望建议

请以清晰、专业的方式呈现你的分析，使用以下结构:

### 📊 图表概览
[简要描述图表展示的内容]

### 📈 技术指标分析
[分析各项技术指标]

### 🎯 关键点位
- **支撑位**: [列出支撑位]
- **阻力位**: [列出阻力位]

### 💡 趋势判断
[分析当前趋势和未来可能走向]

### ⚠️ 风险提示
[指出潜在风险]

### 🎪 操作建议
[给出具体建议]

注意:
- 保持客观和专业
- 基于图表事实进行分析
- 明确指出分析的局限性
- 风险提示要明确
- 所有建议仅供参考，不构成投资建议`;

/**
 * 分析股票图片
 * @param {string} imagePath - 图片文件路径
 * @param {string} customPrompt - 用户自定义提示（可选）
 * @returns {Promise<string>} - 分析结果
 */
async function analyzeStockImage(imagePath, customPrompt = '') {
    try {
        // 读取图片文件
        const imageData = fs.readFileSync(imagePath);
        const base64Image = imageData.toString('base64');

        // 检测图片类型
        const ext = path.extname(imagePath).toLowerCase();
        const mediaTypeMap = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        };
        const mediaType = mediaTypeMap[ext] || 'image/jpeg';

        // 构建用户提示
        let userPrompt = '请分析这张股票图表，并提供详细的技术分析和投资建议。';
        if (customPrompt) {
            userPrompt += `\n\n用户补充要求: ${customPrompt}`;
        }

        console.log('正在调用Claude API进行分析...');

        // 调用Claude API
        const message = await anthropic.messages.create({
            model: 'claude-3-5-sonnet-20241022',
            max_tokens: 2048,
            system: STOCK_ANALYSIS_SYSTEM_PROMPT,
            messages: [
                {
                    role: 'user',
                    content: [
                        {
                            type: 'image',
                            source: {
                                type: 'base64',
                                media_type: mediaType,
                                data: base64Image,
                            },
                        },
                        {
                            type: 'text',
                            text: userPrompt
                        }
                    ],
                },
            ],
        });

        // 提取分析结果
        const analysis = message.content[0].text;
        console.log('分析完成');

        return analysis;

    } catch (error) {
        console.error('AI分析错误:', error);

        // 处理不同类型的错误
        if (error.status === 401) {
            throw new Error('API密钥无效，请检查.env文件中的ANTHROPIC_API_KEY配置');
        } else if (error.status === 429) {
            throw new Error('API调用频率超限，请稍后再试');
        } else if (error.status === 529) {
            throw new Error('API服务暂时过载，请稍后再试');
        } else if (error.message && error.message.includes('ENOENT')) {
            throw new Error('图片文件未找到');
        } else {
            throw new Error(`分析失败: ${error.message || '未知错误'}`);
        }
    }
}

/**
 * 测试API连接
 * @returns {Promise<boolean>} - 连接是否成功
 */
async function testApiConnection() {
    try {
        if (!process.env.ANTHROPIC_API_KEY) {
            console.error('未配置ANTHROPIC_API_KEY');
            return false;
        }

        const message = await anthropic.messages.create({
            model: 'claude-3-5-sonnet-20241022',
            max_tokens: 100,
            messages: [
                {
                    role: 'user',
                    content: 'Hello, this is a connection test.'
                }
            ],
        });

        console.log('✅ API连接测试成功');
        return true;
    } catch (error) {
        console.error('❌ API连接测试失败:', error.message);
        return false;
    }
}

module.exports = {
    analyzeStockImage,
    testApiConnection
};
