"""
预训练模型下载和适配工具
========================

从开源仓库下载预训练的麻将识别 YOLO 模型，
并将其类别映射适配到本项目的四川麻将 27 类体系。

已知的开源模型：
- friklogff/YOLOv11ForMahjong (34类，含字牌)
  类别顺序: 饼(筒)→条→万→字

本项目的类别：
- 27类，无字牌
  顺序: 万→筒→条

因此需要做类别映射转换。
"""

import os
import sys
import json

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(ROOT_DIR, 'models')

# 外部仓库的类别定义（friklogff/YOLOv11ForMahjong 的 34 类）
EXTERNAL_34_CLASSES = [
    '一饼', '二饼', '三饼', '四饼', '五饼', '六饼', '七饼', '八饼', '九饼',  # 0-8  (筒子)
    '一条', '二条', '三条', '四条', '五条', '六条', '七条', '八条', '九条',  # 9-17 (条子)
    '一万', '二万', '三万', '四万', '五万', '六万', '七万', '八万', '九万',  # 18-26(万子)
    '东风', '南风', '西风', '北风', '红中', '发财', '白板',                  # 27-33(字牌)
]

# 本项目的 27 类定义（万→筒→条）
OUR_27_CLASSES = [
    '1m', '2m', '3m', '4m', '5m', '6m', '7m', '8m', '9m',  # 0-8  (万子)
    '1p', '2p', '3p', '4p', '5p', '6p', '7p', '8p', '9p',  # 9-17 (筒子)
    '1s', '2s', '3s', '4s', '5s', '6s', '7s', '8s', '9s',  # 18-26(条子)
]

# 外部 34 类 → 本项目 27 类的映射表
# external class_id → our class_id (-1 表示四川麻将不用的字牌)
MAPPING_34_TO_27 = {
    # 饼(筒) → 筒(p)
    0: 9, 1: 10, 2: 11, 3: 12, 4: 13, 5: 14, 6: 15, 7: 16, 8: 17,
    # 条(s) → 条(s)
    9: 18, 10: 19, 11: 20, 12: 21, 13: 22, 14: 23, 15: 24, 16: 25, 17: 26,
    # 万(m) → 万(m)
    18: 0, 19: 1, 20: 2, 21: 3, 22: 4, 23: 5, 24: 6, 25: 7, 26: 8,
    # 字牌 → 忽略 (-1)
    27: -1, 28: -1, 29: -1, 30: -1, 31: -1, 32: -1, 33: -1,
}


def download_pretrained_model():
    """
    下载预训练的 YOLOv11 麻将识别模型。
    
    注意：GitHub 仓库中的模型文件可能需要通过 Git LFS 下载。
    如果直接下载失败，需要手动从仓库 clone。
    """
    print("=" * 50)
    print("  📦 下载预训练麻将 YOLO 模型")
    print("=" * 50)
    
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    print("\n📋 可选方案：")
    print()
    print("方案 A（推荐）：从 GitHub 克隆含模型的仓库")
    print("  git clone https://github.com/friklogff/YOLOv11ForMahjong.git /tmp/yolo-mj")
    print("  cp /tmp/yolo-mj/model/yolo11.pt models/external-34class.pt")
    print("  python detection/download_model.py --adapt")
    print()
    print("方案 B：自己训练")
    print("  python detection/train.py --colab")
    print("  # 训练完成后将 best.pt 复制到 models/mahjong-best.pt")
    print()
    print("方案 C：从 Roboflow 下载数据集训练")
    print("  python detection/train.py --download-dataset")
    print("  python detection/train.py --train")


def adapt_model_classes(external_model_path: str, output_path: str = None):
    """
    适配外部模型的类别映射到本项目体系。
    
    原理：不修改模型本身，而是创建一个包装器，
    在推理时将外部类别 ID 转换为本项目的类别 ID。
    
    参数：
        external_model_path: 外部模型文件路径
        output_path: 保存适配配置的路径
    """
    if not os.path.exists(external_model_path):
        print(f"❌ 模型文件不存在: {external_model_path}")
        return
    
    if output_path is None:
        output_path = os.path.join(MODELS_DIR, 'model_config.json')
    
    # 保存适配配置
    config = {
        'model_path': external_model_path,
        'source': 'friklogff/YOLOv11ForMahjong',
        'source_classes': 34,
        'target_classes': 27,
        'mapping': MAPPING_34_TO_27,
        'skip_classes': [27, 28, 29, 30, 31, 32, 33],  # 字牌类别
        'notes': '外部模型使用 34 类（含字牌），本项目使用 27 类（四川麻将无字牌）',
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 适配配置已保存到: {output_path}")
    print(f"   外部模型: {external_model_path}")
    print(f"   类别映射: 34 类 → 27 类（过滤字牌）")
    
    # 创建一个符号链接或复制作为主模型
    best_path = os.path.join(MODELS_DIR, 'mahjong-best.pt')
    if not os.path.exists(best_path):
        import shutil
        shutil.copy2(external_model_path, best_path)
        print(f"   已复制为主模型: {best_path}")
    
    return config


def create_adapted_detector():
    """
    工厂函数：创建一个适配后的检测器。
    
    如果存在外部模型配置，自动应用类别映射。
    """
    config_path = os.path.join(MODELS_DIR, 'model_config.json')
    model_path = os.path.join(MODELS_DIR, 'mahjong-best.pt')
    
    if not os.path.exists(model_path):
        print("❌ 模型文件不存在，请先下载或训练模型")
        print("   运行: python detection/download_model.py")
        return None
    
    sys.path.insert(0, ROOT_DIR)
    from detection.model import MahjongDetector
    
    # 检查是否需要类别适配
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        mapping = {int(k): v for k, v in config['mapping'].items()}
        
        # 创建适配检测器（重写 detect 方法中的类别转换）
        detector = MahjongDetector(model_path)
        original_detect = detector.detect
        
        def adapted_detect(image_source, return_image=False):
            """检测后自动转换类别 ID"""
            from detection.model import DetectionResult
            
            raw_results = original_detect(image_source, return_image)
            adapted = []
            
            for det in raw_results:
                new_class = mapping.get(det.class_id, -1)
                if new_class >= 0:  # 过滤掉字牌
                    adapted_det = DetectionResult(
                        new_class, det.confidence, det.bbox
                    )
                    adapted.append(adapted_det)
            
            adapted.sort(key=lambda d: d.confidence, reverse=True)
            return adapted
        
        detector.detect = adapted_detect
        print("✅ 已创建适配检测器（34→27 类映射）")
        return detector
    else:
        return MahjongDetector(model_path)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='预训练模型管理工具')
    parser.add_argument('--download', action='store_true',
                        help='显示模型下载指南')
    parser.add_argument('--adapt', action='store_true',
                        help='适配外部模型到本项目类别体系')
    parser.add_argument('--model', type=str,
                        default=os.path.join(MODELS_DIR, 'external-34class.pt'),
                        help='外部模型文件路径')
    
    args = parser.parse_args()
    
    if args.download:
        download_pretrained_model()
    elif args.adapt:
        adapt_model_classes(args.model)
    else:
        parser.print_help()
        print("\n💡 快速开始：")
        print("   1. 下载模型：python detection/download_model.py --download")
        print("   2. 适配类别：python detection/download_model.py --adapt")
