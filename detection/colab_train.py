# ============================================================
# 🀄 麻将牌识别 — Google Colab 训练脚本
# ============================================================
# 使用方法：
# 1. 在 Google Colab 中新建一个 Notebook
# 2. 将下面的代码逐个单元格粘贴运行
# 3. 确保选择了 GPU 运行时（菜单 → 运行时 → 更改运行时类型 → GPU）

# ---- 单元格 1: 安装依赖 ----
!pip install ultralytics roboflow -q

# ---- 单元格 2: 下载数据集 ----
# 方式一：从 Roboflow 下载（需要 API Key）
# from roboflow import Roboflow
# rf = Roboflow(api_key="YOUR_API_KEY_HERE")
# project = rf.workspace("mahjong-uko7s").project("sg-mahjong")
# dataset = project.version(1).download("yolov11")

# 方式二：上传自己的数据集
# 将数据集压缩包上传到 Colab，然后解压
# !unzip mahjong-dataset.zip -d datasets/mahjong

# ---- 单元格 3: 创建数据集配置 ----
%%writefile mahjong.yaml
path: ./datasets/mahjong
train: images/train
val: images/val
nc: 27
names:
  0: 1m
  1: 2m
  2: 3m
  3: 4m
  4: 5m
  5: 6m
  6: 7m
  7: 8m
  8: 9m
  9: 1p
  10: 2p
  11: 3p
  12: 4p
  13: 5p
  14: 6p
  15: 7p
  16: 8p
  17: 9p
  18: 1s
  19: 2s
  20: 3s
  21: 4s
  22: 5s
  23: 6s
  24: 7s
  25: 8s
  26: 9s

# ---- 单元格 4: 开始训练 ----
from ultralytics import YOLO

model = YOLO('yolo11n.pt')  # nano 版本，快速训练
results = model.train(
    data='mahjong.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    patience=20,
    project='runs/detect',
    name='mahjong',
    fliplr=0.0,   # 麻将牌不翻转
    flipud=0.0,
)

# ---- 单元格 5: 查看训练结果 ----
from IPython.display import Image
Image(filename='runs/detect/mahjong/results.png', width=800)

# ---- 单元格 6: 导出 ONNX 模型 ----
best_model = YOLO('runs/detect/mahjong/weights/best.pt')
best_model.export(format='onnx', imgsz=640, simplify=True)

# ---- 单元格 7: 下载模型 ----
from google.colab import files
files.download('runs/detect/mahjong/weights/best.pt')
files.download('runs/detect/mahjong/weights/best.onnx')
