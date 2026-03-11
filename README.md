# 🀄 麻将辅助分析工具

四川麻将（血战到底）辅助分析工具，支持 **手动选牌 + 摄像头拍照识别**，实时计算向听数、有效进牌和出牌推荐。

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 📊 向听数计算 | 精确计算当前手牌距离听牌的步数 |
| 🎯 有效进牌分析 | 列出所有能减少向听数的牌及剩余张数 |
| 💡 出牌推荐 | 综合进攻效率和防守安全，推荐最优出牌 |
| 🔍 三家分析 | 根据出牌推测对手缺门和危险牌 |
| 📷 摄像头识别 | YOLO 模型识别牌面（需训练模型） |
| 📱 PWA 支持 | 可安装到手机主屏幕使用 |

## 🚀 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/your-username/majiang-sz.git
cd majiang-sz

# 2. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动服务
python app.py

# 5. 打开浏览器访问
# http://localhost:5001
```

## 📁 项目结构

```
majiang-sz/
├── engine/                  # 核心分析引擎
│   ├── tiles.py             # 牌型编码（34 位数组）
│   ├── shanten.py           # 向听数计算 + 有效进牌
│   └── analyzer.py          # 综合分析器（攻守平衡）
├── detection/               # YOLO 牌面识别模块
│   ├── model.py             # 推理管道 + 手牌/桌面分割
│   ├── train.py             # 训练/评估/导出工具
│   ├── download_model.py    # 预训练模型适配工具
│   ├── mahjong.yaml         # 数据集配置（27 类）
│   └── colab_train.py       # Google Colab 训练脚本
├── web/                     # 前端界面
│   ├── index.html           # 选牌 + 摄像头 + 结果展示
│   ├── style.css            # 深色主题样式
│   ├── app.js               # 交互逻辑
│   ├── manifest.json        # PWA 配置
│   └── sw.js                # Service Worker 离线缓存
├── models/                  # 模型存放目录
├── tests/                   # 单元测试
│   └── test_engine.py       # 35 个测试用例
├── app.py                   # Flask API 服务器
├── requirements.txt         # Python 依赖
└── README.md                # 本文件
```

## 🧪 运行测试

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

## 📷 摄像头识别（可选）

摄像头识别需要 YOLO 模型。可以通过以下方式获取：

### 方式 A：使用预训练模型

```bash
# 从开源仓库获取
git clone https://github.com/friklogff/YOLOv11ForMahjong.git /tmp/yolo-mj
cp /tmp/yolo-mj/model/one/best-mj-300.pt models/external-34class.pt
python detection/download_model.py --adapt
```

### 方式 B：自己训练（Google Colab 免费 GPU）

```bash
python detection/train.py --colab
# 将生成的脚本粘贴到 Colab Notebook 运行
# 训练完成后下载 best.pt 到 models/mahjong-best.pt
```

## 📱 手机使用

1. 手机和电脑连接同一 WiFi
2. 电脑终端运行 `python app.py`
3. 手机浏览器访问 `http://电脑IP:5001`
4. 点击浏览器菜单"添加到主屏幕"

## 🛠 技术栈

- **后端**: Python + Flask
- **前端**: HTML + CSS + JavaScript（原生，无框架）
- **分析引擎**: 递归分解法向听数算法
- **牌面识别**: YOLOv11（ultralytics）
- **移动端**: PWA（Progressive Web App）

## 📄 许可证

MIT License
