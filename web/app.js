/**
 * 麻将辅助分析 — 前端交互逻辑
 * ================================
 * 
 * 功能：
 * 1. 点击选牌 — 点击牌面按钮添加到手牌，右键或再次点击移除
 * 2. 缺门选择 — 选择一门花色禁用
 * 3. 发送分析请求 — 调用后端 API 获取分析结果
 * 4. 展示结果 — 向听数、有效进牌、出牌推荐
 */

// ============================================================
// 全局状态
// ============================================================

// 手牌状态：记录每种牌被选了几张
// 键名格式：'1m', '2m', ...  值：选择数量 (0-4)
const handState = {};

// 当前缺门花色
let missingSuit = 'tiao';  // 默认缺条

// API 基础 URL
const API_BASE = '';  // 同源，不需要设置

// 花色到牌组 ID 的映射
const suitToGroupId = {
    'wan': 'group-wan',
    'tong': 'group-tong',
    'tiao': 'group-tiao'
};

// 花色后缀到中文名的映射
const suitSuffix = { 'm': '万', 'p': '筒', 's': '条' };
const suitClass = { 'm': '', 'p': 'tong', 's': 'tiao' };

// 汉字数字
const cnNumbers = ['一', '二', '三', '四', '五', '六', '七', '八', '九'];


// ============================================================
// 初始化
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    // 初始化手牌状态
    for (let i = 1; i <= 9; i++) {
        handState[`${i}m`] = 0;
        handState[`${i}p`] = 0;
        handState[`${i}s`] = 0;
    }
    
    // 应用默认缺门
    applyMissingSuit();
    
    // 为牌面按钮添加右键事件（右键=减少）
    document.querySelectorAll('.tile-btn').forEach(btn => {
        btn.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            removeTile(btn);
        });
    });
    
    // 注册 Service Worker（PWA 离线缓存）
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js')
            .then(() => console.log('✅ Service Worker 注册成功'))
            .catch(err => console.log('SW 注册失败:', err));
    }
});


// ============================================================
// 缺门选择
// ============================================================

/**
 * 选择缺门花色
 * @param {string} suit - 缺门花色：'wan', 'tong', 'tiao'
 */
function selectMissingSuit(suit) {
    missingSuit = suit;
    
    // 更新按钮样式
    document.querySelectorAll('.suit-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.suit === suit);
    });
    
    // 清空缺门花色已选的牌
    const suffixMap = { 'wan': 'm', 'tong': 'p', 'tiao': 's' };
    const suffix = suffixMap[suit];
    for (let i = 1; i <= 9; i++) {
        const key = `${i}${suffix}`;
        handState[key] = 0;
        updateTileButton(key);
    }
    
    // 应用缺门视觉效果
    applyMissingSuit();
    
    // 更新手牌展示
    updateSelectedDisplay();
    
    showToast(`已选择缺${suitSuffix[suffix]}`);
}

/**
 * 应用缺门花色的视觉效果
 */
function applyMissingSuit() {
    // 移除所有 missing 类
    document.querySelectorAll('.tile-group').forEach(g => {
        g.classList.remove('missing');
    });
    
    // 为缺门花色添加 missing 类
    const groupId = suitToGroupId[missingSuit];
    if (groupId) {
        document.getElementById(groupId).classList.add('missing');
    }
}


// ============================================================
// 牌的添加和移除
// ============================================================

/**
 * 点击牌面按钮 — 添加一张牌到手牌
 * @param {HTMLElement} btn - 被点击的按钮
 */
function toggleTile(btn) {
    const tile = btn.dataset.tile;
    const currentCount = handState[tile] || 0;
    
    // 检查总数是否已达上限
    const totalCount = getTotalCount();
    
    if (currentCount >= 4) {
        showToast('每种牌最多 4 张！');
        return;
    }
    
    if (totalCount >= 14) {
        showToast('手牌最多 14 张！');
        return;
    }
    
    // 增加计数
    handState[tile] = currentCount + 1;
    
    // 更新 UI
    updateTileButton(tile);
    updateSelectedDisplay();
    
    // 加一点触觉反馈（微震动效果）
    btn.style.transform = 'scale(0.92)';
    setTimeout(() => { btn.style.transform = ''; }, 100);
}

/**
 * 从手牌移除一张牌（右键触发）
 * @param {HTMLElement} btn - 被右键点击的按钮
 */
function removeTile(btn) {
    const tile = btn.dataset.tile;
    const currentCount = handState[tile] || 0;
    
    if (currentCount <= 0) return;
    
    handState[tile] = currentCount - 1;
    updateTileButton(tile);
    updateSelectedDisplay();
}

/**
 * 从已选手牌展示区移除一张牌（点击已选牌）
 * @param {string} tile - 牌的标识符，如 '1m'
 */
function removeSelectedTile(tile) {
    const currentCount = handState[tile] || 0;
    if (currentCount <= 0) return;
    
    handState[tile] = currentCount - 1;
    updateTileButton(tile);
    updateSelectedDisplay();
}

/**
 * 清空所有手牌
 */
function clearHand() {
    for (const key in handState) {
        handState[key] = 0;
        updateTileButton(key);
    }
    updateSelectedDisplay();
    
    // 隐藏分析结果
    document.getElementById('resultSection').style.display = 'none';
}


// ============================================================
// UI 更新函数
// ============================================================

/**
 * 更新牌面按钮的显示状态
 * @param {string} tile - 牌标识符
 */
function updateTileButton(tile) {
    const btn = document.querySelector(`.tile-btn[data-tile="${tile}"]`);
    if (!btn) return;
    
    const count = handState[tile] || 0;
    const badge = document.getElementById(`count-${tile}`);
    
    if (count > 0) {
        btn.classList.add('selected');
        if (badge) {
            badge.textContent = count;
            badge.style.display = 'flex';
        }
    } else {
        btn.classList.remove('selected');
        if (badge) {
            badge.style.display = 'none';
        }
    }
    
    // 如果达到 4 张，禁用按钮
    if (count >= 4) {
        btn.classList.add('maxed');
    } else {
        btn.classList.remove('maxed');
    }
}

/**
 * 更新已选手牌展示区
 */
function updateSelectedDisplay() {
    const container = document.getElementById('selectedTiles');
    const totalCount = getTotalCount();
    
    // 更新计数文字
    document.getElementById('tileCount').textContent = `${totalCount} / 14 张`;
    
    if (totalCount === 0) {
        container.innerHTML = '<div class="empty-hint">👆 点击上方的牌来添加到手牌</div>';
        return;
    }
    
    // 按照万、筒、条的顺序生成已选牌
    let html = '';
    const order = ['m', 'p', 's'];
    
    for (const suffix of order) {
        for (let i = 1; i <= 9; i++) {
            const tile = `${i}${suffix}`;
            const count = handState[tile] || 0;
            
            for (let j = 0; j < count; j++) {
                const suitCls = suitClass[suffix];
                html += `
                    <div class="selected-tile" onclick="removeSelectedTile('${tile}')" 
                         title="点击移除">
                        <span class="tile-face">${cnNumbers[i-1]}</span>
                        <span class="tile-suit ${suitCls}">${suitSuffix[suffix]}</span>
                    </div>
                `;
            }
        }
    }
    
    container.innerHTML = html;
}


// ============================================================
// 分析功能
// ============================================================

/**
 * 发送分析请求到后端 API
 */
async function analyze() {
    const totalCount = getTotalCount();
    
    if (totalCount === 0) {
        showToast('请先选择手牌！');
        return;
    }
    
    if (totalCount < 4) {
        showToast('手牌太少，至少需要 4 张');
        return;
    }
    
    // 构建手牌字符串
    const handString = buildHandString();
    
    // 显示加载状态
    const btn = document.getElementById('analyzeBtn');
    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> 分析中...';
    btn.classList.add('loading');
    
    try {
        // 缺门花色映射
        const missingSuitMap = { 'wan': 'wan', 'tong': 'tong', 'tiao': 'tiao' };
        
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                hand: handString,
                missing_suit: missingSuitMap[missingSuit],
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayResults(data.data);
        } else {
            showToast(`分析失败：${data.error}`);
        }
    } catch (err) {
        showToast(`网络错误：${err.message}`);
        console.error('Analysis error:', err);
    } finally {
        btn.innerHTML = originalHTML;
        btn.classList.remove('loading');
    }
}

/**
 * 构建手牌字符串（如 "123m456p789s"）
 */
function buildHandString() {
    let result = '';
    const suffixes = ['m', 'p', 's'];
    
    for (const suffix of suffixes) {
        let numbers = '';
        for (let i = 1; i <= 9; i++) {
            const tile = `${i}${suffix}`;
            const count = handState[tile] || 0;
            for (let j = 0; j < count; j++) {
                numbers += i;
            }
        }
        if (numbers) {
            result += numbers + suffix;
        }
    }
    
    return result;
}


// ============================================================
// 结果展示
// ============================================================

/**
 * 展示分析结果
 * @param {Object} data - API 返回的分析数据
 */
function displayResults(data) {
    const section = document.getElementById('resultSection');
    section.style.display = 'block';
    
    // 滚动到结果区域
    setTimeout(() => {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
    
    // —— 向听数 ——
    const shantenCard = document.getElementById('shantenCard');
    const shantenValue = document.getElementById('shantenValue');
    const shantenText = document.getElementById('shantenText');
    
    shantenCard.className = 'result-card shanten-card';
    
    if (data.shanten === -1) {
        shantenValue.textContent = '胡牌！';
        shantenCard.classList.add('win');
    } else if (data.shanten === 0) {
        shantenValue.textContent = '听牌';
        shantenCard.classList.add('tenpai');
    } else {
        shantenValue.textContent = `${data.shanten} 向听`;
        shantenCard.classList.add('away');
    }
    shantenText.textContent = data.shanten_text;
    
    // —— 有效进牌 ——
    const effectiveCard = document.getElementById('effectiveCard');
    const effectiveTiles = document.getElementById('effectiveTiles');
    const effectiveTotal = document.getElementById('effectiveTotal');
    
    if (data.effective_tiles && Object.keys(data.effective_tiles).length > 0) {
        effectiveCard.style.display = 'block';
        effectiveTotal.textContent = `共 ${data.effective_total} 张可进牌`;
        
        let etHtml = '';
        for (const [name, count] of Object.entries(data.effective_tiles)) {
            etHtml += `
                <div class="effective-tile">
                    <span>${name}</span>
                    <span class="remaining">×${count}</span>
                </div>
            `;
        }
        effectiveTiles.innerHTML = etHtml;
    } else {
        effectiveCard.style.display = 'none';
    }
    
    // —— 出牌推荐 ——
    const recommendCard = document.getElementById('recommendCard');
    const recommendList = document.getElementById('recommendList');
    
    if (data.discard_recommendations && data.discard_recommendations.length > 0) {
        recommendCard.style.display = 'block';
        
        let recHtml = '';
        data.discard_recommendations.forEach((rec, index) => {
            // 危险度样式
            let dangerClass = 'danger-safe';
            const dl = rec.danger_level || '';
            if (dl.includes('极危')) dangerClass = 'danger-very-high';
            else if (dl.includes('高危')) dangerClass = 'danger-high';
            else if (dl.includes('中危')) dangerClass = 'danger-medium';
            else if (dl.includes('低危')) dangerClass = 'danger-low';
            else dangerClass = 'danger-safe';
            
            recHtml += `
                <div class="recommend-item">
                    <div style="display:flex;align-items:center;gap:10px;">
                        <div class="recommend-rank">${index + 1}</div>
                        <div>
                            <div class="recommend-name">打 ${rec.name}</div>
                            <div class="recommend-info">
                                ${rec.shanten}向听 · 进${rec.effective_count}种${rec.effective_tiles_remaining}张
                            </div>
                        </div>
                    </div>
                    <div class="recommend-danger ${dangerClass}">
                        ${dl || '安全'}
                    </div>
                </div>
            `;
        });
        recommendList.innerHTML = recHtml;
    } else {
        recommendCard.style.display = 'none';
    }
}


// ============================================================
// 工具函数
// ============================================================

/**
 * 获取当前手牌总数
 */
function getTotalCount() {
    let total = 0;
    for (const key in handState) {
        total += handState[key] || 0;
    }
    return total;
}

/**
 * 显示 Toast 提示
 * @param {string} message - 提示消息
 */
function showToast(message) {
    // 移除已有的 toast
    document.querySelectorAll('.toast').forEach(t => t.remove());
    
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => toast.remove(), 2500);
}


// ============================================================
// 摄像头功能
// ============================================================
// 摄像头使用 WebRTC 的 getUserMedia API
// 拍照后将图像发送到后端 /api/detect 进行 YOLO 识别

let cameraStream = null;  // 当前摄像头流

/**
 * 开启摄像头
 * 使用 navigator.mediaDevices.getUserMedia 获取视频流
 */
async function startCamera() {
    try {
        // 先检查模型是否可用
        const statusRes = await fetch('/api/model_status');
        const statusData = await statusRes.json();
        
        if (!statusData.model_exists) {
            document.getElementById('modelNotice').style.display = 'block';
            showToast('⚠️ YOLO 模型未加载，拍照识别功能暂不可用');
            // 仍然打开摄像头（可以预览但识别会失败）
        }
        
        // 请求摄像头权限
        // facingMode: 'environment' 优先使用后置摄像头（手机端）
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'environment',
                width: { ideal: 1280 },
                height: { ideal: 960 },
            }
        });
        
        // 显示视频预览
        const video = document.getElementById('cameraVideo');
        video.srcObject = cameraStream;
        video.style.display = 'block';
        
        // 隐藏占位符，显示控制按钮
        document.getElementById('cameraPlaceholder').style.display = 'none';
        document.getElementById('startCameraBtn').style.display = 'none';
        document.getElementById('captureBtn').style.display = 'flex';
        document.getElementById('stopCameraBtn').style.display = 'flex';
        
        // 更新状态
        const status = document.getElementById('cameraStatus');
        status.textContent = '已开启';
        status.classList.add('active');
        
        showToast('📷 摄像头已开启');
        
    } catch (err) {
        console.error('Camera error:', err);
        if (err.name === 'NotAllowedError') {
            showToast('❌ 请允许摄像头权限');
        } else if (err.name === 'NotFoundError') {
            showToast('❌ 未找到摄像头设备');
        } else {
            showToast(`❌ 摄像头错误: ${err.message}`);
        }
    }
}

/**
 * 关闭摄像头
 */
function stopCamera() {
    if (cameraStream) {
        // 停止所有轨道
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
    
    const video = document.getElementById('cameraVideo');
    video.srcObject = null;
    video.style.display = 'none';
    
    // 隐藏截图
    document.getElementById('capturedImage').style.display = 'none';
    
    // 恢复占位符和按钮
    document.getElementById('cameraPlaceholder').style.display = 'flex';
    document.getElementById('startCameraBtn').style.display = 'flex';
    document.getElementById('captureBtn').style.display = 'none';
    document.getElementById('stopCameraBtn').style.display = 'none';
    
    // 更新状态
    const status = document.getElementById('cameraStatus');
    status.textContent = '未启用';
    status.classList.remove('active');
}

/**
 * 拍照并发送到后端进行识别
 * 
 * 流程：
 * 1. 从视频流截取当前帧到 canvas
 * 2. 将 canvas 内容转为 base64
 * 3. 发送到 /api/detect API
 * 4. 用识别结果自动填充手牌
 */
async function captureAndDetect() {
    const video = document.getElementById('cameraVideo');
    const canvas = document.getElementById('cameraCanvas');
    const capturedImg = document.getElementById('capturedImage');
    
    if (!video.srcObject) {
        showToast('请先开启摄像头');
        return;
    }
    
    // 1. 截取当前帧
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    
    // 显示截图预览
    const imageDataUrl = canvas.toDataURL('image/jpeg', 0.9);
    capturedImg.src = imageDataUrl;
    capturedImg.style.display = 'block';
    video.style.display = 'none';
    
    // 显示加载状态
    const captureBtn = document.getElementById('captureBtn');
    const origText = captureBtn.innerHTML;
    captureBtn.innerHTML = '<span class="spinner"></span> 识别中...';
    captureBtn.disabled = true;
    
    try {
        // 2. 发送到后端
        const response = await fetch('/api/detect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image_base64: imageDataUrl,
                missing_suit: missingSuit,
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 3. 用识别结果填充手牌
            applyDetectionResults(data.data);
            showToast(`✅ 识别到 ${data.data.total_tiles} 张手牌`);
        } else {
            if (data.model_missing) {
                showToast('⚠️ 模型未加载，请先训练 YOLO 模型');
                document.getElementById('modelNotice').style.display = 'block';
            } else {
                showToast(`识别失败: ${data.error}`);
            }
        }
    } catch (err) {
        showToast(`网络错误: ${err.message}`);
        console.error('Detection error:', err);
    } finally {
        captureBtn.innerHTML = origText;
        captureBtn.disabled = false;
        
        // 2 秒后恢复视频预览
        setTimeout(() => {
            if (cameraStream) {
                capturedImg.style.display = 'none';
                video.style.display = 'block';
            }
        }, 2000);
    }
}

/**
 * 将检测结果应用到手牌选择状态
 * @param {Object} data - 检测 API 返回的数据
 */
function applyDetectionResults(data) {
    // 先清空当前手牌
    clearHand();
    
    // 解析 hand_string（如 "123m456p"）
    if (data.hand_string) {
        const handStr = data.hand_string;
        const suffixMap = { 'm': 'm', 'p': 'p', 's': 's' };
        let numbers = '';
        
        for (const ch of handStr) {
            if (suffixMap[ch]) {
                // 遇到花色后缀，将之前积累的数字转为牌
                for (const num of numbers) {
                    const tile = num + ch;
                    if (handState.hasOwnProperty(tile)) {
                        handState[tile] = Math.min((handState[tile] || 0) + 1, 4);
                    }
                }
                numbers = '';
            } else {
                numbers += ch;
            }
        }
        
        // 更新所有按钮状态
        for (const key in handState) {
            updateTileButton(key);
        }
        updateSelectedDisplay();
    }
    
    // 显示分析结果
    displayResults(data);
}

/**
 * 页面加载时检查模型状态
 */
async function checkModelStatus() {
    try {
        const res = await fetch('/api/model_status');
        const data = await res.json();
        if (!data.model_exists) {
            document.getElementById('modelNotice').style.display = 'block';
        }
    } catch (err) {
        // 静默失败
    }
}

// 页面加载后检查模型
document.addEventListener('DOMContentLoaded', checkModelStatus);
