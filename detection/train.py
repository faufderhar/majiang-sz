"""
麻将牌识别模型训练脚本
========================

支持两种使用方式：
    1. 本地训练（需要 NVIDIA GPU）
    2. Google Colab 训练（推荐，免费 GPU）

使用方法：
    # 下载数据集
    python detection/train.py --download-dataset
    
    # 本地训练（需 GPU）
    python detection/train.py --train --epochs 100
    
    # 评估模型
    python detection/train.py --eval --model runs/detect/train/weights/best.pt
    
    # 导出 ONNX（用于移动端部署）
    python detection/train.py --export --model runs/detect/train/weights/best.pt
"""

import argparse
import os
import sys


def download_dataset():
    """
    从 Roboflow 下载麻将牌标注数据集。
    
    Roboflow 是一个图像标注平台，社区中有几个现成的麻将牌数据集：
    - roman-nguyen/mahjong-vtacs
    - mahjong-uko7s/sg-mahjong
    - calvin-hsu/mahjong-t25l9
    
    这里我们使用 Roboflow 的 Python SDK 来下载。
    """
    print("=" * 50)
    print("  📦 下载麻将牌数据集")
    print("=" * 50)
    
    try:
        from roboflow import Roboflow
    except ImportError:
        print("\n⚠️ 需要先安装 roboflow:")
        print("   pip install roboflow")
        print("\n🔑 然后需要在 https://roboflow.com 注册并获取 API Key")
        print("\n📋 手动下载步骤：")
        print("   1. 访问 https://universe.roboflow.com 搜索 'mahjong'")
        print("   2. 选择一个数据集（推荐：sg-mahjong 或 mahjong-vtacs）")
        print("   3. 导出为 YOLOv11 格式")
        print("   4. 解压到 datasets/mahjong/ 目录")
        print("\n📂 期望的数据集结构：")
        print("   datasets/mahjong/")
        print("   ├── images/")
        print("   │   ├── train/  (训练图片)")
        print("   │   └── val/    (验证图片)")
        print("   └── labels/")
        print("       ├── train/  (训练标注 .txt)")
        print("       └── val/    (验证标注 .txt)")
        return
    
    # 如果安装了 roboflow，尝试下载
    print("\n请输入你的 Roboflow API Key:")
    print("（在 https://app.roboflow.com/settings/api-key 查看）")
    api_key = input("API Key: ").strip()
    
    if not api_key:
        print("未提供 API Key，跳过下载")
        return
    
    rf = Roboflow(api_key=api_key)
    
    # 下载社区数据集（以 sg-mahjong 为例）
    project = rf.workspace("mahjong-uko7s").project("sg-mahjong")
    dataset = project.version(1).download("yolov11", location="datasets/mahjong")
    
    print(f"\n✅ 数据集已下载到: datasets/mahjong/")
    print(f"   训练图片数: {len(os.listdir('datasets/mahjong/images/train'))}")


def train_model(epochs: int = 100, batch_size: int = 16,
                img_size: int = 640, model_size: str = 'n'):
    """
    训练 YOLOv11 麻将牌检测模型。
    
    参数说明：
        epochs: 训练轮数（推荐 100~300，数据集大用 100 就够）
        batch_size: 批大小（GPU 显存不够就减小，如 8 或 4）
        img_size: 输入图像大小（640 是标准尺寸）
        model_size: 模型大小变体
            - 'n' (nano): 最小最快，适合手机端（推荐起步）
            - 's' (small): 速度和精度平衡
            - 'm' (medium): 更高精度
            - 'l' (large): 高精度但慢
            - 'x' (extra): 最高精度
    """
    from ultralytics import YOLO
    
    print("=" * 50)
    print("  🏋️ 开始训练 YOLOv11 麻将识别模型")
    print("=" * 50)
    print(f"  模型大小: yolo11{model_size}")
    print(f"  训练轮数: {epochs}")
    print(f"  批大小: {batch_size}")
    print(f"  图像大小: {img_size}")
    print("=" * 50)
    
    # 数据集配置文件路径
    data_yaml = os.path.join(os.path.dirname(__file__), 'mahjong.yaml')
    
    # 加载预训练的 YOLOv11 模型（从 COCO 数据集预训练的权重开始微调）
    # 'yolo11n.pt' 表示 YOLOv11 nano 版本的预训练权重
    model = YOLO(f'yolo11{model_size}.pt')
    
    # 开始训练
    # 关键参数解释：
    # - data: 数据集配置文件路径
    # - epochs: 训练多少轮（每轮遍历一次所有训练数据）
    # - imgsz: 输入图像会被缩放到这个尺寸
    # - batch: 每次训练多少张图片（越大需要越多显存）
    # - patience: 如果验证精度连续多少轮不提升就提前停止
    # - project: 训练结果存储的根目录
    # - name: 实验名称
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=img_size,
        batch=batch_size,
        patience=20,          # 20 轮不提升就停止
        project='runs/detect',
        name='mahjong',
        exist_ok=True,        # 覆盖已有的同名实验
        verbose=True,
        
        # 数据增强参数（增加训练鲁棒性）
        hsv_h=0.015,          # 色调扰动
        hsv_s=0.7,            # 饱和度扰动
        hsv_v=0.4,            # 亮度扰动
        degrees=10,           # 随机旋转角度
        translate=0.1,        # 随机平移比例
        scale=0.5,            # 随机缩放比例
        fliplr=0.0,           # 水平翻转（麻将牌不适合翻转！）
        flipud=0.0,           # 垂直翻转（同上）
        mosaic=1.0,           # Mosaic 增强（拼接 4 张图片）
    )
    
    print("\n" + "=" * 50)
    print("  ✅ 训练完成！")
    print(f"  最佳模型: runs/detect/mahjong/weights/best.pt")
    print(f"  最后模型: runs/detect/mahjong/weights/last.pt")
    print("=" * 50)
    
    return results


def evaluate_model(model_path: str):
    """
    评估模型在验证集上的性能。
    
    主要指标：
    - mAP@0.5: 在 IoU=0.5 时的平均精度（>0.9 算很好）
    - mAP@0.5:0.95: 在多种 IoU 下的平均精度
    - Precision: 检测出的牌中正确的比例
    - Recall: 实际存在的牌中被检测到的比例
    """
    from ultralytics import YOLO
    
    print("=" * 50)
    print("  📊 模型评估")
    print("=" * 50)
    
    model = YOLO(model_path)
    data_yaml = os.path.join(os.path.dirname(__file__), 'mahjong.yaml')
    
    results = model.val(data=data_yaml, verbose=True)
    
    print(f"\n📈 评估结果：")
    print(f"   mAP@0.5:      {results.box.map50:.4f}")
    print(f"   mAP@0.5:0.95: {results.box.map:.4f}")
    print(f"   Precision:     {results.box.mp:.4f}")
    print(f"   Recall:        {results.box.mr:.4f}")
    
    return results


def export_model(model_path: str, format: str = 'onnx'):
    """
    导出模型为其他格式（用于移动端部署）。
    
    支持的格式：
    - 'onnx':    通用神经网络格式（推荐，WebAssembly 可用）
    - 'tflite':  TensorFlow Lite（Android 原生）
    - 'coreml':  Core ML（iOS 原生）
    - 'ncnn':    NCNN（腾讯开源，适合移动端 C++）
    """
    from ultralytics import YOLO
    
    print(f"📦 导出模型: {model_path} → {format}")
    
    model = YOLO(model_path)
    
    exported_path = model.export(
        format=format,
        imgsz=640,
        simplify=True,  # ONNX 图简化
    )
    
    print(f"✅ 导出完成: {exported_path}")
    return exported_path


def generate_colab_notebook():
    """
    生成 Google Colab 训练笔记本。
    
    如果本地没有 GPU，可以用 Google Colab 的免费 GPU 训练。
    该函数生成一个 .py 脚本，可以直接粘贴到 Colab 中运行。
    """
    notebook_content = '''# ============================================================
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
'''
    
    output_path = os.path.join(os.path.dirname(__file__), 'colab_train.py')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(notebook_content)
    
    print(f"✅ Colab 训练脚本已生成: {output_path}")
    print("\n📋 使用步骤：")
    print("   1. 打开 https://colab.research.google.com")
    print("   2. 新建 Notebook → 运行时 → 更改运行时类型 → GPU")
    print("   3. 将脚本内容逐段粘贴到单元格中运行")
    print("   4. 训练完成后下载 best.pt 和 best.onnx")
    print("   5. 将模型放到 models/ 目录中使用")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='麻将牌识别模型训练工具')
    
    parser.add_argument('--download-dataset', action='store_true',
                        help='下载训练数据集')
    parser.add_argument('--train', action='store_true',
                        help='开始训练模型')
    parser.add_argument('--eval', action='store_true',
                        help='评估模型性能')
    parser.add_argument('--export', action='store_true',
                        help='导出模型（如 ONNX）')
    parser.add_argument('--colab', action='store_true',
                        help='生成 Google Colab 训练脚本')
    
    parser.add_argument('--model', type=str, default='',
                        help='模型文件路径')
    parser.add_argument('--epochs', type=int, default=100,
                        help='训练轮数')
    parser.add_argument('--batch', type=int, default=16,
                        help='批大小')
    parser.add_argument('--size', type=str, default='n',
                        choices=['n', 's', 'm', 'l', 'x'],
                        help='模型大小: n(nano)/s(small)/m(medium)/l(large)/x(extra)')
    parser.add_argument('--format', type=str, default='onnx',
                        choices=['onnx', 'tflite', 'coreml', 'ncnn'],
                        help='导出格式')
    
    args = parser.parse_args()
    
    if args.download_dataset:
        download_dataset()
    elif args.train:
        train_model(
            epochs=args.epochs,
            batch_size=args.batch,
            model_size=args.size,
        )
    elif args.eval:
        if not args.model:
            print("请指定模型路径: --model runs/detect/mahjong/weights/best.pt")
        else:
            evaluate_model(args.model)
    elif args.export:
        if not args.model:
            print("请指定模型路径: --model runs/detect/mahjong/weights/best.pt")
        else:
            export_model(args.model, format=args.format)
    elif args.colab:
        generate_colab_notebook()
    else:
        parser.print_help()
        print("\n💡 快速开始：")
        print("   # 生成 Colab 训练脚本（推荐，免费 GPU）")
        print("   python detection/train.py --colab")
        print()
        print("   # 或本地训练（需要 NVIDIA GPU）")
        print("   python detection/train.py --train --epochs 100")
