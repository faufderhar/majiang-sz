"""
麻将辅助工具 — Web API 服务器
==============================

提供 RESTful API 接口，供前端 Web 界面调用。
使用 Flask 框架，轻量、简单、适合 Demo 阶段。

API 接口：
- POST /api/analyze    — 分析手牌，返回向听数、有效进牌、出牌推荐
- GET  /               — 返回前端页面
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys

# 确保能导入 engine 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.tiles import Hand, Suit, TOTAL_TILE_TYPES, tile_name
from engine.shanten import calculate_shanten, get_effective_tiles, get_discard_analysis
from engine.analyzer import MahjongAnalyzer

app = Flask(__name__, static_folder='web', static_url_path='')
CORS(app)  # 允许跨域请求（开发阶段方便调试）


@app.route('/')
def index():
    """返回前端首页"""
    return send_from_directory('web', 'index.html')


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    分析手牌 API
    
    请求 JSON 格式：
    {
        "hand": "123m456p789s11p",          // 手牌字符串（必填）
        "missing_suit": "tiao",             // 缺门花色：wan/tong/tiao（可选）
        "discards": {                        // 三家出牌（可选）
            "0": ["1s", "3s"],              // 下家出牌
            "1": ["2m"],                    // 对家出牌
            "2": ["9p"]                     // 上家出牌
        }
    }
    
    返回 JSON 格式：
    {
        "success": true,
        "data": {
            "hand_display": "...",
            "shanten": 0,
            "effective_tiles": {...},
            "discard_recommendations": [...],
            ...
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'hand' not in data:
            return jsonify({
                'success': False,
                'error': '请提供手牌字符串，如 {"hand": "123m456p789s11p"}'
            }), 400
        
        hand_str = data['hand'].strip()
        
        # 解析缺门花色
        suit_map = {
            'wan': Suit.WAN, 'tong': Suit.TONG, 'tiao': Suit.TIAO,
            'm': Suit.WAN, 'p': Suit.TONG, 's': Suit.TIAO,
            '万': Suit.WAN, '筒': Suit.TONG, '条': Suit.TIAO,
        }
        missing_suit = None
        if 'missing_suit' in data and data['missing_suit']:
            ms = data['missing_suit'].lower().strip()
            missing_suit = suit_map.get(ms)
        
        # 创建分析器
        analyzer = MahjongAnalyzer(sichuan_mode=True)
        analyzer.set_hand(hand_str)
        
        if missing_suit is not None:
            analyzer.set_missing_suit(missing_suit)
        
        # 记录三家出牌
        discards = data.get('discards', {})
        for player_idx_str, tiles in discards.items():
            player_idx = int(player_idx_str)
            if 0 <= player_idx <= 2:
                for tile_str in tiles:
                    try:
                        analyzer.add_discard(player_idx, tile_str)
                    except Exception:
                        pass  # 跳过无效输入
        
        # 执行分析
        result = analyzer.analyze()
        
        # 构建响应
        response = {
            'success': True,
            'data': {
                'hand_string': analyzer.hand.to_string(),
                'hand_display': analyzer.hand.to_display(),
                'hand_emoji': analyzer.hand.to_emoji(),
                'total_tiles': analyzer.hand.total_count,
                'shanten': result['shanten'],
                'shanten_text': _shanten_text(result['shanten']),
                'effective_tiles': result['effective_tiles'],
                'effective_total': result['effective_total'],
                'discard_recommendations': result['discard_recommendations'][:8],
                'opponent_analysis': result['opponent_analysis'],
            }
        }
        
        return jsonify(response)
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'输入错误：{str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器错误：{str(e)}'
        }), 500


@app.route('/api/quick_shanten', methods=['GET'])
def quick_shanten():
    """
    快速向听数查询（GET 方式，方便测试）
    
    参数：
        hand: 手牌字符串
        missing: 缺门花色（可选）
    
    示例：
        /api/quick_shanten?hand=123m456p789s11p&missing=tiao
    """
    hand_str = request.args.get('hand', '')
    missing = request.args.get('missing', '')
    
    if not hand_str:
        return jsonify({'error': '请提供 hand 参数'}), 400
    
    try:
        hand = Hand.from_string(hand_str)
        
        suit_map = {'wan': Suit.WAN, 'tong': Suit.TONG, 'tiao': Suit.TIAO,
                     'm': Suit.WAN, 'p': Suit.TONG, 's': Suit.TIAO}
        missing_suit = suit_map.get(missing.lower()) if missing else None
        
        shanten = calculate_shanten(hand, sichuan_mode=True, missing_suit=missing_suit)
        
        return jsonify({
            'hand': hand.to_string(),
            'display': hand.to_display(),
            'shanten': shanten,
            'shanten_text': _shanten_text(shanten),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


def _shanten_text(shanten: int) -> str:
    """将向听数转为可读文字"""
    if shanten == -1:
        return '🎉 已经胡牌！'
    elif shanten == 0:
        return '✨ 听牌中！'
    else:
        return f'📊 {shanten} 向听（还差 {shanten} 步听牌）'


# ============================================================
# 图像检测 API（摄像头拍照识别）
# ============================================================
# 全局检测器实例（懒加载）
_detector = None

def _get_detector():
    """获取或初始化检测器（单例模式）"""
    global _detector
    if _detector is None:
        model_path = os.path.join(
            os.path.dirname(__file__), 'models', 'mahjong-best.pt'
        )
        if os.path.exists(model_path):
            from detection.model import MahjongDetector
            _detector = MahjongDetector(model_path)
        else:
            print(f"⚠️ 模型文件未找到: {model_path}")
            print("  请先训练模型或下载预训练模型到 models/ 目录")
    return _detector


@app.route('/api/detect', methods=['POST'])
def detect_tiles():
    """
    图像检测 API — 识别摄像头拍摄的图片中的麻将牌。
    
    请求：
        multipart/form-data 表单，包含：
        - image: 图像文件
        - missing_suit: 缺门花色（可选）
    
    或 JSON 格式：
        {"image_base64": "...", "missing_suit": "tiao"}
    
    返回与 /api/analyze 相同格式的分析结果。
    """
    import base64
    import io
    
    try:
        detector = _get_detector()
        
        if detector is None:
            return jsonify({
                'success': False,
                'error': '模型未加载。请将训练好的模型放到 models/mahjong-best.pt',
                'model_missing': True,
            }), 503
        
        # 获取图像数据
        image_data = None
        
        if request.content_type and 'multipart/form-data' in request.content_type:
            # 表单上传
            file = request.files.get('image')
            if file:
                image_data = file.read()
        else:
            # JSON base64
            data = request.get_json()
            if data and 'image_base64' in data:
                # 去掉 data:image/xxx;base64, 前缀
                b64 = data['image_base64']
                if ',' in b64:
                    b64 = b64.split(',')[1]
                image_data = base64.b64decode(b64)
        
        if image_data is None:
            return jsonify({
                'success': False,
                'error': '请提供图像（form-data 的 image 字段，或 JSON 的 image_base64 字段）'
            }), 400
        
        # 将图像数据转为 numpy 数组
        import numpy as np
        try:
            from PIL import Image as PILImage
            img = PILImage.open(io.BytesIO(image_data))
            img_array = np.array(img)
        except ImportError:
            # 没有 PIL，尝试 OpenCV
            img_array = np.frombuffer(image_data, np.uint8)
            import cv2
            img_array = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        # 执行检测并分割手牌/桌面牌
        split_result = detector.detect_and_split(img_array)
        hand_tiles, hand_dets = split_result['hand']
        table_tiles, table_dets = split_result['table']
        
        # 解析缺门
        missing_suit = None
        ms_str = (request.form.get('missing_suit') or 
                  (request.get_json() or {}).get('missing_suit', ''))
        suit_map = {'wan': Suit.WAN, 'tong': Suit.TONG, 'tiao': Suit.TIAO}
        if ms_str:
            missing_suit = suit_map.get(ms_str.lower())
        
        # 用分析引擎处理
        analyzer = MahjongAnalyzer(sichuan_mode=True)
        # 直接设置 hand 对象（不通过字符串）
        analyzer.hand = hand_tiles
        if missing_suit:
            analyzer.set_missing_suit(missing_suit)
        
        # 添加桌面牌到可见牌
        for i in range(TOTAL_TILE_TYPES):
            count = table_tiles.count(i)
            if count > 0:
                analyzer.visible.add(i, count)
        
        result = analyzer.analyze()
        
        # 构建针对检测的额外信息
        detection_info = {
            'hand_detections': [
                {'name': d.class_name_cn, 'confidence': round(d.confidence, 2),
                 'bbox': [round(v) for v in d.bbox]}
                for d in hand_dets
            ],
            'table_detections': [
                {'name': d.class_name_cn, 'confidence': round(d.confidence, 2),
                 'bbox': [round(v) for v in d.bbox]}
                for d in table_dets
            ],
        }
        
        response = {
            'success': True,
            'data': {
                'hand_string': hand_tiles.to_string(),
                'hand_display': hand_tiles.to_display(),
                'total_tiles': hand_tiles.total_count,
                'table_display': table_tiles.to_display(),
                'table_count': table_tiles.total_count,
                'shanten': result['shanten'],
                'shanten_text': _shanten_text(result['shanten']),
                'effective_tiles': result['effective_tiles'],
                'effective_total': result['effective_total'],
                'discard_recommendations': result['discard_recommendations'][:8],
                'detection': detection_info,
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'检测错误：{str(e)}'
        }), 500


@app.route('/api/model_status', methods=['GET'])
def model_status():
    """检查模型是否可用"""
    model_path = os.path.join(os.path.dirname(__file__), 'models', 'mahjong-best.pt')
    return jsonify({
        'model_exists': os.path.exists(model_path),
        'model_path': model_path,
    })


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("  🀄 麻将辅助工具 — Web Demo")
    print("  打开浏览器访问: http://localhost:5001")
    print("=" * 50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5001)

