// 全局状态
let selectedImage = null;
let analysisHistory = [];

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    adjustTextareaHeight();
});

// 处理图片选择
function handleImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    // 验证文件类型
    if (!file.type.startsWith('image/')) {
        alert('请选择图片文件');
        return;
    }

    // 验证文件大小（最大10MB）
    if (file.size > 10 * 1024 * 1024) {
        alert('图片大小不能超过10MB');
        return;
    }

    selectedImage = file;

    // 预览图片
    const reader = new FileReader();
    reader.onload = (e) => {
        const preview = document.getElementById('imagePreview');
        const img = document.getElementById('previewImg');
        img.src = e.target.result;
        preview.classList.remove('hidden');

        // 启用发送按钮
        document.getElementById('sendBtn').disabled = false;
    };
    reader.readAsDataURL(file);
}

// 移除图片
function removeImage() {
    selectedImage = null;
    const preview = document.getElementById('imagePreview');
    preview.classList.add('hidden');
    document.getElementById('imageInput').value = '';

    // 如果没有图片，禁用发送按钮
    document.getElementById('sendBtn').disabled = true;
}

// 处理键盘事件
function handleKeyDown(event) {
    // Shift + Enter 换行，Enter 发送
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        if (!document.getElementById('sendBtn').disabled) {
            analyzeStock();
        }
    }
}

// 自动调整文本框高度
function adjustTextareaHeight() {
    const textarea = document.getElementById('promptInput');
    textarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 200) + 'px';
    });
}

// 分析股票
async function analyzeStock() {
    if (!selectedImage) {
        alert('请先上传股票图表截图');
        return;
    }

    const promptInput = document.getElementById('promptInput');
    const customPrompt = promptInput.value.trim();

    // 隐藏欢迎界面，显示分析区域
    document.getElementById('welcomeScreen').classList.add('hidden');
    document.getElementById('analysisArea').classList.remove('hidden');

    // 添加用户消息
    addMessage('user', {
        image: URL.createObjectURL(selectedImage),
        text: customPrompt || '请分析这张股票图表'
    });

    // 禁用发送按钮
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;

    // 添加加载消息
    const loadingId = addMessage('assistant', { loading: true });

    try {
        // 创建FormData
        const formData = new FormData();
        formData.append('image', selectedImage);
        if (customPrompt) {
            formData.append('prompt', customPrompt);
        }

        // 发送请求
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`分析失败: ${response.statusText}`);
        }

        const data = await response.json();

        // 移除加载消息
        removeMessage(loadingId);

        // 添加AI响应
        addMessage('assistant', { text: data.analysis });

        // 保存到历史记录
        saveToHistory({
            timestamp: Date.now(),
            preview: data.analysis.substring(0, 50) + '...',
            fullAnalysis: data.analysis
        });

    } catch (error) {
        console.error('分析错误:', error);
        removeMessage(loadingId);
        addMessage('assistant', {
            text: `抱歉，分析过程中出现错误：${error.message}\n\n请确保：\n1. 已在.env文件中配置ANTHROPIC_API_KEY\n2. 后端服务正在运行\n3. 网络连接正常`
        });
    }

    // 清空输入
    promptInput.value = '';
    promptInput.style.height = 'auto';
    removeImage();
}

// 添加消息
function addMessage(role, content) {
    const messagesContainer = document.getElementById('messages');
    const messageId = 'msg_' + Date.now();

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.id = messageId;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '您' : 'AI';

    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';

    if (content.loading) {
        messageContent.innerHTML = `
            <div class="loading">
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
            </div>
        `;
    } else {
        if (content.image) {
            const img = document.createElement('img');
            img.src = content.image;
            messageContent.appendChild(img);
        }

        if (content.text) {
            const textDiv = document.createElement('div');
            textDiv.className = 'message-text';
            textDiv.innerHTML = formatMessage(content.text);
            messageContent.appendChild(textDiv);
        }
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(messageContent);
    messagesContainer.appendChild(messageDiv);

    // 滚动到底部
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    return messageId;
}

// 移除消息
function removeMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.remove();
    }
}

// 格式化消息文本（支持简单的markdown）
function formatMessage(text) {
    // 转义HTML
    text = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');

    // 转换标题
    text = text.replace(/### (.+)$/gm, '<h3>$1</h3>');

    // 转换粗体
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // 转换列表
    text = text.replace(/^\* (.+)$/gm, '<li>$1</li>');
    text = text.replace(/^- (.+)$/gm, '<li>$1</li>');
    text = text.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

    // 转换数字列表
    text = text.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

    // 转换换行
    text = text.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
    text = '<p>' + text + '</p>';

    return text;
}

// 重置分析
function resetAnalysis() {
    document.getElementById('welcomeScreen').classList.remove('hidden');
    document.getElementById('analysisArea').classList.add('hidden');
    document.getElementById('messages').innerHTML = '';
    removeImage();
}

// 保存到历史记录
function saveToHistory(item) {
    analysisHistory.unshift(item);
    if (analysisHistory.length > 10) {
        analysisHistory.pop();
    }
    localStorage.setItem('analysisHistory', JSON.stringify(analysisHistory));
    updateHistoryList();
}

// 加载历史记录
function loadHistory() {
    const saved = localStorage.getItem('analysisHistory');
    if (saved) {
        try {
            analysisHistory = JSON.parse(saved);
            updateHistoryList();
        } catch (e) {
            console.error('加载历史记录失败:', e);
        }
    }
}

// 更新历史记录列表
function updateHistoryList() {
    const historyList = document.getElementById('historyList');
    historyList.innerHTML = '';

    if (analysisHistory.length === 0) {
        historyList.innerHTML = '<div style="padding: 12px; color: var(--text-secondary); font-size: 13px;">暂无历史记录</div>';
        return;
    }

    analysisHistory.forEach((item, index) => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.textContent = item.preview;
        historyItem.title = item.preview;
        historyItem.onclick = () => viewHistory(index);
        historyList.appendChild(historyItem);
    });
}

// 查看历史记录
function viewHistory(index) {
    const item = analysisHistory[index];
    if (!item) return;

    document.getElementById('welcomeScreen').classList.add('hidden');
    document.getElementById('analysisArea').classList.remove('hidden');
    document.getElementById('messages').innerHTML = '';

    addMessage('assistant', { text: item.fullAnalysis });
}

// 添加拖放支持
const inputWrapper = document.querySelector('.input-wrapper');
if (inputWrapper) {
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        inputWrapper.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        inputWrapper.addEventListener(eventName, () => {
            inputWrapper.style.borderColor = 'var(--accent-color)';
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        inputWrapper.addEventListener(eventName, () => {
            inputWrapper.style.borderColor = '';
        });
    });

    inputWrapper.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const imageInput = document.getElementById('imageInput');
            imageInput.files = files;
            handleImageSelect({ target: imageInput });
        }
    });
}
