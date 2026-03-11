"""
出牌推荐与三家危险分析
=====================

这个模块把向听数计算和防守分析结合起来，提供最终的出牌建议。

核心功能：
1. **进攻推荐**：基于向听数和有效进牌数，推荐最有效率的出牌
2. **防守分析**：基于可见牌和三家的出牌模式，评估每张牌的危险度
3. **攻守平衡**：综合进攻效率和防守安全性，给出最终推荐

危险度评估原理：
- 如果某张牌在场上已经出现 3 张或以上 → 非常安全（别人不太可能听这张牌）
- 如果某张牌是"生张"（场上一张都没出现） → 较危险
- 如果某张牌是某家刚打的牌旁边的牌 → 较安全（"筋牌"理论）
- 如果某家明显在做某一门花色 → 打该门的牌更危险
"""

from typing import List, Dict, Optional, Tuple
from .tiles import (
    Hand, VisibleTiles, Suit, SUIT_SIZE, ZI_SIZE, ZI_OFFSET,
    SICHUAN_VALID_SUITS, SICHUAN_TILE_TYPES, TOTAL_TILE_TYPES,
    TILES_PER_TYPE, tile_name, tile_index, is_sichuan_tile
)
from .shanten import calculate_shanten, get_effective_tiles, get_discard_analysis


# ============================================================
# 危险度等级
# ============================================================
class DangerLevel:
    """
    危险度等级常量。
    
    数值越高越危险。
    """
    SAFE = 0          # 安全：已出 3-4 张，或者与对手打出的牌形成筋牌
    LOW = 1           # 低危：场上出现过 2 张，或者字牌已出
    MEDIUM = 2        # 中危：场上出现 1 张，或者数牌中间张
    HIGH = 3          # 高危：生张（一张没出过），特别是 3-7 的数牌
    VERY_HIGH = 4     # 极危：生张 + 某家明显在做该门


# ============================================================
# 三家出牌记录
# ============================================================
class PlayerDiscards:
    """
    记录某一家的出牌历史（牌河）。
    
    通过分析一家的出牌，可以推断：
    - 这家可能在做什么牌型
    - 这家缺什么门（四川麻将）
    - 这家可能听什么牌
    """
    
    def __init__(self, player_name: str = ""):
        self.player_name = player_name
        # 按顺序记录打出的牌
        self.discards: List[int] = []
        # 明牌（吃碰杠）
        self.melds: List[List[int]] = []
    
    def add_discard(self, tile_index: int) -> None:
        """记录打出一张牌"""
        self.discards.append(tile_index)
    
    def add_meld(self, tiles: List[int]) -> None:
        """记录一组明牌（碰/杠/吃）"""
        self.melds.append(tiles)
    
    def get_discarded_suits(self) -> Dict[Suit, int]:
        """统计打出的各门花色数量"""
        suit_counts = {s: 0 for s in SICHUAN_VALID_SUITS}
        for tile in self.discards:
            suit = Suit(tile // SUIT_SIZE)
            if suit in suit_counts:
                suit_counts[suit] += 1
        return suit_counts
    
    def guess_missing_suit(self) -> Optional[Suit]:
        """
        推测该家的缺门花色。
        
        原理：如果一家早期大量打出某门花色的牌，
               很可能就是缺那门的。
        
        返回：
            推测的缺门花色，不确定时返回 None
        """
        if len(self.discards) < 3:
            return None  # 出牌太少，无法判断
        
        suit_counts = self.get_discarded_suits()
        
        # 看前 5 手出的牌，如果大量集中在某门
        early_suits = {s: 0 for s in SICHUAN_VALID_SUITS}
        for tile in self.discards[:min(5, len(self.discards))]:
            suit = Suit(tile // SUIT_SIZE)
            if suit in early_suits:
                early_suits[suit] += 1
        
        # 如果前几手出了 3 张以上某门的牌，很可能缺该门
        for suit, count in early_suits.items():
            if count >= 3:
                return suit
        
        return None
    
    def get_safe_tiles(self) -> List[int]:
        """
        获取相对安全的牌（对这家来说）。
        
        安全牌包括：
        1. 这家自己刚打出的牌（不太可能回头听这张牌）
        2. 该家打出的牌的筋牌（"筋"= 间隔 3 的数牌组合）
        """
        safe = set()
        
        # 最近打出的牌是安全的
        for tile in self.discards:
            safe.add(tile)
        
        # 筋牌理论：如果打了 4，则 1 和 7 相对安全（筋牌关系）
        for tile in self.discards:
            suit = tile // SUIT_SIZE
            num = tile % SUIT_SIZE  # 0-based
            
            if suit < 3:  # 只对数牌有筋牌关系，字牌没有
                # 筋牌关系：间隔 3
                if num >= 3:
                    safe.add(suit * SUIT_SIZE + num - 3)
                if num + 3 < SUIT_SIZE:
                    safe.add(suit * SUIT_SIZE + num + 3)
        
        return list(safe)


# ============================================================
# 综合分析器（Analyzer）
# ============================================================
class MahjongAnalyzer:
    """
    麻将综合分析器 — 将所有分析模块整合在一起。
    
    使用步骤：
    1. 创建分析器实例
    2. 设置自己的手牌
    3. 记录场上可见的牌和三家的出牌
    4. 调用分析方法获取推荐
    
    使用示例：
        analyzer = MahjongAnalyzer()
        analyzer.set_hand("123m456p789s11p")         # 设置手牌
        analyzer.set_missing_suit(Suit.TIAO)          # 我缺条
        analyzer.add_visible_tile(0, 2)               # 场上已见 2 张一万
        result = analyzer.analyze()                    # 获取分析结果
    """
    
    def __init__(self, sichuan_mode: bool = True):
        """
        初始化分析器。
        
        参数：
            sichuan_mode: 是否使用四川麻将规则（默认 True）
        """
        self.sichuan_mode = sichuan_mode
        self.hand: Optional[Hand] = None
        self.missing_suit: Optional[Suit] = None
        self.visible = VisibleTiles()
        
        # 三家的出牌记录（下家、对家、上家）
        self.players = [
            PlayerDiscards("下家"),
            PlayerDiscards("对家"),
            PlayerDiscards("上家"),
        ]
    
    def set_hand(self, hand_str: str) -> None:
        """
        设置自己的手牌（从字符串解析）。
        
        参数：
            hand_str: 手牌字符串，如 "123m456p789s11p"
        """
        self.hand = Hand.from_string(hand_str)
        
        # 将手牌加入可见牌统计
        for i in range(TOTAL_TILE_TYPES):
            count = self.hand.count(i)
            if count > 0:
                self.visible.add(i, count)
    
    def set_missing_suit(self, suit: Suit) -> None:
        """设置缺门花色（四川麻将）"""
        self.missing_suit = suit
    
    def add_discard(self, player_index: int, tile_str: str) -> None:
        """
        记录某家打出一张牌。
        
        参数：
            player_index: 玩家索引（0=下家, 1=对家, 2=上家）
            tile_str: 牌字符串，如 "1m"
        """
        temp_hand = Hand.from_string(tile_str)
        for i in range(TOTAL_TILE_TYPES):
            if temp_hand.count(i) > 0:
                self.players[player_index].add_discard(i)
                self.visible.add(i)
                break
    
    def add_visible_tile(self, tile_index: int, count: int = 1) -> None:
        """直接添加可见牌"""
        self.visible.add(tile_index, count)
    
    def analyze(self) -> dict:
        """
        执行综合分析，返回完整的分析结果。
        
        返回：
            包含以下信息的字典：
            - 'shanten': 当前向听数
            - 'effective_tiles': 有效进牌列表
            - 'discard_recommendations': 出牌推荐列表（已按优先级排序）
            - 'danger_analysis': 每张手牌的危险度分析
            - 'opponent_analysis': 三家的出牌分析
        """
        if self.hand is None:
            raise ValueError("请先调用 set_hand() 设置手牌")
        
        # 1. 计算当前向听数
        current_shanten = calculate_shanten(
            self.hand, self.sichuan_mode, self.missing_suit
        )
        
        # 2. 计算有效进牌（如果是 13 张手牌）
        visible_array = [self.visible.visible_count(i) for i in range(TOTAL_TILE_TYPES)]
        
        effective_tiles = {}
        if self.hand.total_count == 13:
            effective_tiles = get_effective_tiles(
                self.hand, self.sichuan_mode, self.missing_suit, visible_array
            )
        
        # 3. 出牌推荐（如果是 14 张手牌）
        discard_recs = []
        if self.hand.total_count == 14:
            discard_recs = get_discard_analysis(
                self.hand, self.sichuan_mode, self.missing_suit, visible_array
            )
        
        # 4. 危险度分析
        danger = self._analyze_danger()
        
        # 5. 三家分析
        opponent_info = self._analyze_opponents()
        
        # 6. 将危险度信息合并到出牌推荐中
        final_recs = self._merge_recommendations(discard_recs, danger)
        
        return {
            'shanten': current_shanten,
            'effective_tiles': {
                tile_name(k): v for k, v in effective_tiles.items()
            },
            'effective_total': sum(effective_tiles.values()),
            'discard_recommendations': final_recs,
            'danger_analysis': danger,
            'opponent_analysis': opponent_info,
        }
    
    def _analyze_danger(self) -> Dict[int, dict]:
        """
        分析每种牌的危险度。
        
        返回：
            {牌索引: {'level': 危险等级, 'reason': 原因说明}} 
        """
        danger = {}
        max_tile = SICHUAN_TILE_TYPES if self.sichuan_mode else TOTAL_TILE_TYPES
        
        for i in range(max_tile):
            if self.hand is None or not self.hand.has_tile(i):
                continue
            
            visible_count = self.visible.visible_count(i)
            name = tile_name(i)
            
            # 基础危险度判断
            if visible_count >= 3:
                # 已经见了 3 张以上，非常安全
                level = DangerLevel.SAFE
                reason = f"{name} 已见 {visible_count} 张，场上几乎没有了"
            elif visible_count == 2:
                level = DangerLevel.LOW
                reason = f"{name} 已见 2 张，剩余不多"
            elif visible_count == 1:
                level = DangerLevel.MEDIUM
                reason = f"{name} 仅见 1 张，注意安全"
            else:
                # 生张（0 张可见）
                level = DangerLevel.HIGH
                reason = f"{name} 是生张（场上未出现），危险！"
            
            # 检查是否在三家的安全牌列表中
            for player in self.players:
                safe_tiles = player.get_safe_tiles()
                if i in safe_tiles:
                    level = max(level - 1, DangerLevel.SAFE)
                    reason += f" （{player.player_name}的筋牌，较安全）"
            
            # 检查三家是否可能在做该门
            suit = Suit(i // SUIT_SIZE) if i < SICHUAN_TILE_TYPES else None
            if suit is not None:
                for player in self.players:
                    guessed_missing = player.guess_missing_suit()
                    if guessed_missing is not None and guessed_missing != suit:
                        # 对方不缺该门，说明可能在做该门 → 该门牌更危险
                        if visible_count == 0:
                            level = DangerLevel.VERY_HIGH
                            reason += f" （{player.player_name}可能做{self._suit_name(suit)}，极危！）"
            
            danger[i] = {
                'level': level,
                'level_text': self._danger_text(level),
                'reason': reason,
            }
        
        return danger
    
    def _analyze_opponents(self) -> List[dict]:
        """分析三家的出牌模式"""
        results = []
        
        for player in self.players:
            info = {
                'name': player.player_name,
                'discard_count': len(player.discards),
                'discards': [tile_name(d) for d in player.discards],
                'guessed_missing': None,
                'possible_needs': [],
            }
            
            # 推测缺门
            missing = player.guess_missing_suit()
            if missing is not None:
                info['guessed_missing'] = self._suit_name(missing)
            
            # 推测可能需要的牌（根据不缺的花色）
            if missing is not None:
                needs = [s for s in SICHUAN_VALID_SUITS if s != missing]
                info['possible_needs'] = [self._suit_name(s) for s in needs]
            
            results.append(info)
        
        return results
    
    def _merge_recommendations(self, discard_recs: List[dict],
                                danger: Dict[int, dict]) -> List[dict]:
        """
        将进攻推荐和防守分析合并。
        
        最终评分 = 效率分数 - 危险度惩罚
        """
        for rec in discard_recs:
            tile_idx = rec['tile']
            if tile_idx in danger:
                danger_level = danger[tile_idx]['level']
                # 危险度惩罚：越危险的牌扣分越多（但如果打出它效率很高也值得考虑）
                danger_penalty = danger_level * 50
                rec['danger_level'] = danger[tile_idx]['level_text']
                rec['danger_reason'] = danger[tile_idx]['reason']
                rec['final_score'] = rec['score'] - danger_penalty
            else:
                rec['danger_level'] = '安全'
                rec['danger_reason'] = '不在手中'
                rec['final_score'] = rec['score']
        
        # 按 final_score 重新排序
        discard_recs.sort(key=lambda x: x['final_score'], reverse=True)
        
        return discard_recs
    
    @staticmethod
    def _suit_name(suit: Suit) -> str:
        """花色中文名"""
        names = {Suit.WAN: '万', Suit.TONG: '筒', Suit.TIAO: '条', Suit.ZI: '字'}
        return names.get(suit, '未知')
    
    @staticmethod
    def _danger_text(level: int) -> str:
        """危险等级文字"""
        texts = {
            DangerLevel.SAFE: '🟢 安全',
            DangerLevel.LOW: '🔵 低危',
            DangerLevel.MEDIUM: '🟡 中危',
            DangerLevel.HIGH: '🔴 高危',
            DangerLevel.VERY_HIGH: '⛔ 极危',
        }
        return texts.get(level, '未知')
    
    def print_analysis(self) -> None:
        """将分析结果格式化打印到控制台（方便调试）"""
        result = self.analyze()
        
        print("=" * 60)
        print("  🀄 麻将辅助分析结果")
        print("=" * 60)
        
        print(f"\n📋 手牌: {self.hand}")
        print(f"📊 向听数: {result['shanten']}")
        
        if result['shanten'] == -1:
            print("🎉 恭喜！已经胡牌！")
            return
        elif result['shanten'] == 0:
            print("✨ 听牌中！")
        
        # 有效进牌
        if result['effective_tiles']:
            print(f"\n🎯 有效进牌 ({result['effective_total']} 张):")
            for name, count in result['effective_tiles'].items():
                print(f"   {name} × {count}")
        
        # 出牌推荐
        if result['discard_recommendations']:
            print(f"\n💡 出牌推荐 (按优先级排序):")
            print(f"   {'牌名':<6} {'向听数':<6} {'进牌种类':<8} {'进牌张数':<8} {'危险度':<10} {'评分'}")
            print("   " + "-" * 54)
            for rec in result['discard_recommendations'][:5]:  # 显示前 5 个
                print(f"   {rec['name']:<6} {rec['shanten']:<6} "
                      f"{rec['effective_count']:<8} "
                      f"{rec['effective_tiles_remaining']:<8} "
                      f"{rec.get('danger_level', 'N/A'):<10} "
                      f"{rec.get('final_score', rec['score'])}")
        
        # 三家分析
        print(f"\n🔍 三家分析:")
        for opp in result['opponent_analysis']:
            missing = opp['guessed_missing'] or '未知'
            print(f"   {opp['name']}: 已出 {opp['discard_count']} 张, "
                  f"推测缺{missing}")
        
        print("\n" + "=" * 60)
