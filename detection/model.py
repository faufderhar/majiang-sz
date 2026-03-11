"""
麻将牌面识别 — 推理管道
========================

将 YOLO 检测结果转换为引擎可用的牌面编码。

流程：
    图像输入 → YOLO 检测 → 后处理（NMS + 过滤） → 牌面编码 → 传给分析引擎

支持的模型格式：
    - PyTorch (.pt)    — 训练和本地推理
    - ONNX (.onnx)     — 跨平台推理（推荐用于移动端）
"""

import os
import sys
from typing import List, Dict, Optional, Tuple

# 将项目根目录加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.tiles import Hand, tile_index, Suit, tile_name


# ============================================================
# 类别映射（YOLO class_id → 引擎 tile_index）
# ============================================================
# YOLO 的 27 类直接对应引擎的索引 0~26
# class_id 0 = 1万 = tile_index 0
# class_id 9 = 1筒 = tile_index 9
# ...以此类推

# 类别标签名称
CLASS_NAMES = [
    '1m', '2m', '3m', '4m', '5m', '6m', '7m', '8m', '9m',  # 万子
    '1p', '2p', '3p', '4p', '5p', '6p', '7p', '8p', '9p',  # 筒子
    '1s', '2s', '3s', '4s', '5s', '6s', '7s', '8s', '9s',  # 条子
]

# 类别名称的中文映射
CLASS_NAMES_CN = [
    '一万', '二万', '三万', '四万', '五万', '六万', '七万', '八万', '九万',
    '一筒', '二筒', '三筒', '四筒', '五筒', '六筒', '七筒', '八筒', '九筒',
    '一条', '二条', '三条', '四条', '五条', '六条', '七条', '八条', '九条',
]


class DetectionResult:
    """
    单个检测结果 — 表示图像中检测到的一张麻将牌。
    
    属性：
        class_id: YOLO 的类别 ID（0~26）
        tile_index: 引擎中的牌索引（0~26，与 class_id 相同）
        class_name: 类别标签名（如 '1m'）
        class_name_cn: 中文名（如 '一万'）
        confidence: 检测置信度（0.0~1.0）
        bbox: 边界框 [x1, y1, x2, y2]（像素坐标）
        center: 边界框中心点 (cx, cy)
    """
    
    def __init__(self, class_id: int, confidence: float,
                 bbox: Tuple[float, float, float, float]):
        self.class_id = class_id
        self.tile_index = class_id  # 四川麻将中两者相同
        self.class_name = CLASS_NAMES[class_id] if class_id < len(CLASS_NAMES) else '?'
        self.class_name_cn = CLASS_NAMES_CN[class_id] if class_id < len(CLASS_NAMES_CN) else '?'
        self.confidence = confidence
        self.bbox = bbox
        
        # 计算中心点
        x1, y1, x2, y2 = bbox
        self.center = ((x1 + x2) / 2, (y1 + y2) / 2)
        self.width = x2 - x1
        self.height = y2 - y1
    
    def __str__(self):
        return (f"{self.class_name_cn} "
                f"(置信度:{self.confidence:.2f}, "
                f"位置:[{self.bbox[0]:.0f},{self.bbox[1]:.0f},"
                f"{self.bbox[2]:.0f},{self.bbox[3]:.0f}])")
    
    def __repr__(self):
        return f"DetectionResult({self.class_name}, {self.confidence:.2f})"


class MahjongDetector:
    """
    麻将牌面检测器 — 基于 YOLO 的检测和识别。
    
    使用步骤：
    1. 创建检测器，加载模型
    2. 传入图像进行检测
    3. 获取检测结果（排好序的牌列表）
    
    使用示例：
        detector = MahjongDetector('models/mahjong-yolo.pt')
        results = detector.detect('photo.jpg')
        for tile in results:
            print(f"检测到: {tile.class_name_cn} 置信度: {tile.confidence:.2f}")
    """
    
    def __init__(self, model_path: str, confidence_threshold: float = 0.5):
        """
        初始化检测器。
        
        参数：
            model_path: YOLO 模型文件路径（.pt 或 .onnx）
            confidence_threshold: 置信度阈值，低于此值的检测结果会被过滤
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        
        # 延迟导入 ultralytics（可能未安装）
        self._load_model()
    
    def _load_model(self):
        """加载 YOLO 模型"""
        try:
            from ultralytics import YOLO
            
            if not os.path.exists(self.model_path):
                print(f"⚠️ 模型文件不存在: {self.model_path}")
                print("请先训练模型或下载预训练模型。")
                print("可以运行: python detection/train.py --download-pretrained")
                return
            
            self.model = YOLO(self.model_path)
            print(f"✅ 模型加载成功: {self.model_path}")
            
        except ImportError:
            print("⚠️ ultralytics 未安装，请运行: pip install ultralytics")
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
    
    def detect(self, image_source, return_image: bool = False) -> List[DetectionResult]:
        """
        对图像进行麻将牌检测。
        
        参数：
            image_source: 图像来源，可以是：
                - 文件路径字符串（如 'photo.jpg'）
                - numpy 数组（OpenCV 格式的 BGR 图像）
                - PIL Image 对象
            return_image: 是否返回标注后的图像
        
        返回：
            DetectionResult 列表，按置信度从高到低排序
        """
        if self.model is None:
            print("❌ 模型未加载，无法执行检测")
            return []
        
        try:
            # 执行 YOLO 推理
            results = self.model(
                image_source,
                conf=self.confidence_threshold,
                verbose=False  # 不打印推理日志
            )
            
            # 解析检测结果
            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                
                for i in range(len(boxes)):
                    class_id = int(boxes.cls[i].item())
                    confidence = float(boxes.conf[i].item())
                    bbox = boxes.xyxy[i].tolist()  # [x1, y1, x2, y2]
                    
                    if class_id < len(CLASS_NAMES):
                        det = DetectionResult(class_id, confidence, tuple(bbox))
                        detections.append(det)
            
            # 按置信度降序排序
            detections.sort(key=lambda d: d.confidence, reverse=True)
            
            return detections
            
        except Exception as e:
            print(f"❌ 检测失败: {e}")
            return []
    
    def detect_to_hand(self, image_source,
                        region: str = 'all') -> Tuple[Hand, List[DetectionResult]]:
        """
        检测图像中的牌并转换为 Hand 对象。
        
        这是连接"视觉识别层"和"分析引擎层"的关键方法。
        
        参数：
            image_source: 图像来源
            region: 区域过滤（'all'=所有, 'hand'=手牌区, 'table'=桌面区）
                    后续版本将支持基于 y 坐标区分手牌和桌面牌
        
        返回：
            (hand, detections) 元组
        """
        detections = self.detect(image_source)
        
        # 将检测结果转为手牌
        hand = Hand()
        used_detections = []
        
        for det in detections:
            tile_idx = det.tile_index
            # 检查是否超过 4 张（可能检测到重复的）
            if hand.count(tile_idx) < 4:
                try:
                    hand.add_tile(tile_idx)
                    used_detections.append(det)
                except ValueError:
                    pass  # 超过上限，跳过
        
        return hand, used_detections
    
    def detect_and_split(self, image_source,
                          split_y_ratio: float = 0.6
                          ) -> Dict[str, Tuple[Hand, List[DetectionResult]]]:
        """
        检测并按区域分割为手牌和桌面牌。
        
        原理：一般拍照时，手牌在画面下方，桌面牌在上方。
        通过 y 坐标的阈值来区分。
        
        参数：
            image_source: 图像来源
            split_y_ratio: 分割线的 y 坐标比例（默认 0.6，即画面 60% 以下为手牌区）
        
        返回：
            {'hand': (Hand, detections), 'table': (Hand, detections)}
        """
        detections = self.detect(image_source)
        
        if not detections:
            empty = Hand()
            return {'hand': (empty, []), 'table': (empty, [])}
        
        # 获取图像高度（从检测结果的 bbox 推断）
        max_y = max(d.bbox[3] for d in detections)
        split_y = max_y * split_y_ratio
        
        # 分割
        hand_dets = [d for d in detections if d.center[1] >= split_y]
        table_dets = [d for d in detections if d.center[1] < split_y]
        
        # 转换为 Hand
        hand_tiles = Hand()
        for d in hand_dets:
            if hand_tiles.count(d.tile_index) < 4:
                try:
                    hand_tiles.add_tile(d.tile_index)
                except ValueError:
                    pass
        
        table_tiles = Hand()
        for d in table_dets:
            if table_tiles.count(d.tile_index) < 4:
                try:
                    table_tiles.add_tile(d.tile_index)
                except ValueError:
                    pass
        
        return {
            'hand': (hand_tiles, hand_dets),
            'table': (table_tiles, table_dets),
        }


# ============================================================
# 便捷函数
# ============================================================
def detections_to_summary(detections: List[DetectionResult]) -> str:
    """
    将检测结果生成可读摘要。
    
    示例输出:
        "检测到 13 张牌: 一万×2 二万 三万 四筒 五筒 六筒 七条 八条 九条 东 东 东"
    """
    if not detections:
        return "未检测到任何牌"
    
    # 统计每种牌的数量
    counts = {}
    for d in detections:
        name = d.class_name_cn
        counts[name] = counts.get(name, 0) + 1
    
    parts = []
    for name, count in counts.items():
        if count > 1:
            parts.append(f"{name}×{count}")
        else:
            parts.append(name)
    
    return f"检测到 {len(detections)} 张牌: {' '.join(parts)}"
