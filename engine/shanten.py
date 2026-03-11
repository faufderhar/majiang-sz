"""
向听数（Shanten）计算算法
=========================

"向听数"（日语 Shanten，中文也叫"上听数"或"欠张数"）是麻将中最重要的指标之一。

什么是向听数？
- 向听数 = 你的手牌距离"听牌"（可以胡的状态）还差几步
- 向听数为 0 → 已经听牌（再进一张就胡）
- 向听数为 1 → 差一步就能听牌
- 向听数为 -1 → 已经胡牌（和了）

核心公式：
    向听数 = (需要的面子数 × 2) - 现有面子数 - 搭子数 + 调整值

    其中：
    - 面子（mentsu）：三张组成的完整组合（顺子 123 或刻子 111）
    - 搭子（taatsu）：两张能变成面子的半成品（如 12、13、11）
    - 雀头（jantou）：一对相同的牌

算法思路（递归分解法）：
    1. 将 34 种牌按花色分成 4 组（万/筒/条/字）
    2. 对每组独立计算可能的面子和搭子组合
    3. 遍历所有可能的组合，找到向听数最小的方案

四川麻将特殊处理：
    - 只考虑万/筒/条三种花色，忽略字牌
    - 需要缺一门，缺门的花色不参与计算
"""

from typing import List, Tuple, Optional
from .tiles import (
    Hand, Suit, SUIT_SIZE, ZI_SIZE, ZI_OFFSET,
    SICHUAN_VALID_SUITS, tile_name, tile_index
)


def calculate_shanten(hand: Hand, sichuan_mode: bool = True,
                      missing_suit: Optional[Suit] = None) -> int:
    """
    计算手牌的向听数。
    
    参数：
        hand: 手牌
        sichuan_mode: 是否使用四川麻将规则（默认 True）
        missing_suit: 缺门的花色（四川麻将），如果为 None 则自动选择最优缺门
    
    返回：
        向听数（-1 表示已胡牌，0 表示听牌，>0 表示还差几步）
    
    使用示例：
        hand = Hand.from_string("123m456p789s11p")  # 14 张牌
        shanten = calculate_shanten(hand)
        if shanten == -1:
            print("已经胡牌！")
        elif shanten == 0:
            print("已经听牌！")
        else:
            print(f"还差 {shanten} 步听牌")
    """
    tiles = hand.tiles
    total = sum(tiles)
    
    if sichuan_mode:
        # 四川麻将：移除字牌
        for i in range(ZI_OFFSET, ZI_OFFSET + ZI_SIZE):
            tiles[i] = 0
        
        if missing_suit is not None:
            # 如果指定了缺门，自动尝试所有可能的缺门
            suits_to_use = [s for s in SICHUAN_VALID_SUITS if s != missing_suit]
            return _calc_regular_shanten(tiles, suits_to_use, total)
        else:
            # 自动选择最优缺门：尝试每一种缺门，取最小向听数
            best = 99
            for skip_suit in SICHUAN_VALID_SUITS:
                suits_to_use = [s for s in SICHUAN_VALID_SUITS if s != skip_suit]
                # 检查缺门的花色是否已无牌
                offset = int(skip_suit) * SUIT_SIZE
                temp_tiles = list(tiles)
                for i in range(SUIT_SIZE):
                    temp_tiles[offset + i] = 0
                s = _calc_regular_shanten(temp_tiles, suits_to_use, total)
                if s < best:
                    best = s
            return best
    else:
        # 普通麻将：使用全部花色
        suits = [Suit.WAN, Suit.TONG, Suit.TIAO, Suit.ZI]
        return _calc_regular_shanten(tiles, suits, total)


def _calc_regular_shanten(tiles: List[int], suits: List[Suit], 
                           total_tiles: int) -> int:
    """
    计算常规牌型的向听数（面子+雀头的标准和牌形式）。
    
    标准和牌形式：4 组面子 + 1 雀头 = 14 张牌
    （四川麻将手牌一般也是 13 张 + 1 张摸牌 = 14 张）
    
    算法核心：
    1. 将手牌按花色拆分
    2. 对每种花色递归搜索所有可能的面子/搭子组合
    3. 把各花色的结果合并，找到全局最优
    
    向听数公式：
        shanten = 2 * (4 - mentsu_count) - partial_count - has_pair
        
        mentsu_count: 完整的面子数
        partial_count: 搭子数（半成品）
        has_pair: 是否有雀头（0 或 1）
    """
    # 需要的面子数
    # 对于 14 张牌：需要 4 组面子 + 1 雀头
    # 对于 13 张牌：需要 4 组面子 + 1 雀头 - 1（还差一张胡牌）
    target_mentsu = 4
    
    # 搜索最优的面子/搭子/雀头组合
    best_shanten = 8  # 最坏情况：13 张互不相关的牌
    
    # 递归搜索所有可能的面子组合
    _search_combinations(tiles, suits, 0, 0, 0, False, best_shanten, 
                         target_mentsu, result := [8])
    
    best_shanten = result[0]
    
    # 同时检查特殊牌型：七对子
    seven_pairs = _calc_seven_pairs_shanten(tiles, suits)
    best_shanten = min(best_shanten, seven_pairs)
    
    # 四川麻将没有国士无双（十三幺），跳过
    
    return best_shanten


def _search_combinations(tiles: List[int], suits: List[Suit],
                          suit_idx: int, mentsu: int, partial: int,
                          has_pair: bool, best: int, target: int,
                          result: List[int]) -> None:
    """
    递归搜索所有面子/搭子/雀头组合。
    
    参数：
        tiles: 34 位牌数组
        suits: 参与计算的花色列表
        suit_idx: 当前处理的花色索引
        mentsu: 已找到的面子数
        partial: 已找到的搭子数
        has_pair: 是否已有雀头
        best: 当前最优向听数（用于剪枝）
        target: 需要的面子数（通常为 4）
        result: 存储结果的列表（用列表模拟引用传递）
    """
    if suit_idx >= len(suits):
        # 所有花色处理完毕，计算向听数
        # 公式：向听数 = 2 × (需要面子数 - 已有面子数) - 搭子数 - 有雀头
        # 其中面子+搭子总数不能超过需要面子数（4）再加上搭子/雀头的位置
        
        # 限制面子+搭子的总数不超过目标
        actual_mentsu = min(mentsu, target)
        remaining_slots = target - actual_mentsu
        actual_partial = min(partial + (1 if has_pair else 0), remaining_slots + 1)
        
        shanten = 2 * (target - actual_mentsu) - actual_partial
        if has_pair and actual_partial > 0:
            # 已经在 actual_partial 中扣除了
            pass
        
        # 更简洁的计算方式
        total_sets = mentsu
        total_partial = partial + (1 if has_pair else 0)
        
        # 面子和搭子加起来不能超过 target + 1 (4面子+1雀头=5)
        if total_sets + total_partial > target + 1:
            total_partial = target + 1 - total_sets
        if total_sets > target:
            total_sets = target
        
        shanten = 2 * (target - total_sets) - total_partial
        
        if shanten < result[0]:
            result[0] = shanten
        return
    
    suit = suits[suit_idx]
    offset = int(suit) * SUIT_SIZE
    size = ZI_SIZE if suit == Suit.ZI else SUIT_SIZE
    
    # 提取当前花色的牌
    suit_tiles = tiles[offset:offset + size]
    
    # 对这个花色，搜索所有可能的面子/搭子/雀头组合
    _search_suit(suit_tiles, size, suit == Suit.ZI, 0,
                 tiles, suits, suit_idx, mentsu, partial, has_pair,
                 best, target, result)


def _search_suit(suit_tiles: List[int], size: int, is_zi: bool, pos: int,
                  tiles: List[int], suits: List[Suit], suit_idx: int,
                  mentsu: int, partial: int, has_pair: bool,
                  best: int, target: int, result: List[int]) -> None:
    """
    在单个花色中搜索面子/搭子/雀头组合。
    
    面子（完整组合）包括：
    - 顺子（shuntsu）: 三张连续的牌，如 1-2-3（字牌不能组顺子）
    - 刻子（koutsu）: 三张相同的牌，如 1-1-1
    
    搭子（半成品）包括：
    - 对子（toitsu）: 两张相同的牌，如 1-1（也可以做雀头）
    - 两面搭（ryanmen）: 两张连续的牌，如 2-3（等 1 或 4）
    - 嵌张搭（kanchan）: 两张间隔一位的牌，如 1-3（等 2）
    """
    # 跳过空位
    while pos < size and suit_tiles[pos] == 0:
        pos += 1
    
    if pos >= size:
        # 当前花色处理完毕，进入下一个花色
        _search_combinations(tiles, suits, suit_idx + 1,
                            mentsu, partial, has_pair,
                            best, target, result)
        return
    
    # 剪枝：如果当前方案不可能更好，就跳过
    current_shanten = 2 * (target - mentsu) - partial - (1 if has_pair else 0)
    if current_shanten < result[0]:
        # 可能还有更好的，但当前已经够好了（实际上这个剪枝条件需要更精确）
        pass
    
    # =====================
    # 尝试提取刻子 (三张相同: AAA)
    # =====================
    if suit_tiles[pos] >= 3:
        suit_tiles[pos] -= 3
        _search_suit(suit_tiles, size, is_zi, pos,
                     tiles, suits, suit_idx,
                     mentsu + 1, partial, has_pair,
                     best, target, result)
        suit_tiles[pos] += 3
    
    # =====================
    # 尝试提取顺子 (三张连续: ABC)
    # =====================
    if not is_zi and pos + 2 < size:
        if suit_tiles[pos] >= 1 and suit_tiles[pos+1] >= 1 and suit_tiles[pos+2] >= 1:
            suit_tiles[pos] -= 1
            suit_tiles[pos+1] -= 1
            suit_tiles[pos+2] -= 1
            _search_suit(suit_tiles, size, is_zi, pos,
                         tiles, suits, suit_idx,
                         mentsu + 1, partial, has_pair,
                         best, target, result)
            suit_tiles[pos] += 1
            suit_tiles[pos+1] += 1
            suit_tiles[pos+2] += 1
    
    # =====================
    # 尝试提取对子 (两张相同: AA) — 作为雀头或搭子
    # =====================
    if suit_tiles[pos] >= 2:
        # 情况1：作为雀头（如果还没有雀头）
        if not has_pair:
            suit_tiles[pos] -= 2
            _search_suit(suit_tiles, size, is_zi, pos,
                         tiles, suits, suit_idx,
                         mentsu, partial, True,  # has_pair = True
                         best, target, result)
            suit_tiles[pos] += 2
        
        # 情况2：作为搭子（对子搭）
        suit_tiles[pos] -= 2
        _search_suit(suit_tiles, size, is_zi, pos,
                     tiles, suits, suit_idx,
                     mentsu, partial + 1, has_pair,
                     best, target, result)
        suit_tiles[pos] += 2
    
    # =====================
    # 尝试提取两面搭 (两张连续: AB)
    # =====================
    if not is_zi and pos + 1 < size:
        if suit_tiles[pos] >= 1 and suit_tiles[pos+1] >= 1:
            suit_tiles[pos] -= 1
            suit_tiles[pos+1] -= 1
            _search_suit(suit_tiles, size, is_zi, pos,
                         tiles, suits, suit_idx,
                         mentsu, partial + 1, has_pair,
                         best, target, result)
            suit_tiles[pos] += 1
            suit_tiles[pos+1] += 1
    
    # =====================
    # 尝试提取嵌张搭 (间隔一位: AC)
    # =====================
    if not is_zi and pos + 2 < size:
        if suit_tiles[pos] >= 1 and suit_tiles[pos+2] >= 1:
            suit_tiles[pos] -= 1
            suit_tiles[pos+2] -= 1
            _search_suit(suit_tiles, size, is_zi, pos,
                         tiles, suits, suit_idx,
                         mentsu, partial + 1, has_pair,
                         best, target, result)
            suit_tiles[pos] += 1
            suit_tiles[pos+2] += 1
    
    # =====================
    # 不提取任何组合，跳过当前位置
    # =====================
    # 这对应"剩余的牌是孤张"的情况
    _search_suit(suit_tiles, size, is_zi, pos + 1,
                 tiles, suits, suit_idx,
                 mentsu, partial, has_pair,
                 best, target, result)


def _calc_seven_pairs_shanten(tiles: List[int], suits: List[Suit]) -> int:
    """
    计算七对子牌型的向听数。
    
    七对子：7 组对子（2+2+2+2+2+2+2 = 14 张）
    
    向听数 = 6 - 对子数
    
    注意：四川麻将中通常支持七对子（"龙七对"更厉害！）
    """
    pairs = 0
    has_tiles = 0
    
    for suit in suits:
        offset = int(suit) * SUIT_SIZE
        size = ZI_SIZE if suit == Suit.ZI else SUIT_SIZE
        for i in range(size):
            if tiles[offset + i] >= 2:
                pairs += 1
            if tiles[offset + i] >= 1:
                has_tiles += 1
    
    # 七对子需要 7 对，向听数 = 6 - 对子数
    # 但同时需要 7 种不同的牌（四川麻将允许用 4 张凑 2 对）
    if has_tiles < 7:
        # 不够 7 种牌，不可能凑七对子
        return 99
    
    return 6 - pairs


def get_effective_tiles(hand: Hand, sichuan_mode: bool = True,
                        missing_suit: Optional[Suit] = None,
                        visible: Optional[List[int]] = None) -> dict:
    """
    计算有效进牌（Uke-ire）。
    
    "有效进牌"指的是：摸到哪些牌可以降低向听数（让你离听牌更近一步）。
    
    参数：
        hand: 当前手牌（应为 13 张）
        sichuan_mode: 是否使用四川麻将规则
        missing_suit: 缺门花色
        visible: 已可见的牌数量数组（用于计算剩余可进牌的实际数量）
    
    返回：
        字典 {牌索引: 剩余数量}，表示能降低向听数的牌及其剩余数量
    
    使用示例：
        hand = Hand.from_string("123m456p789s11p")
        effective = get_effective_tiles(hand)
        for tile_idx, count in effective.items():
            print(f"进 {tile_name(tile_idx)}（剩余 {count} 张）")
    """
    from .tiles import TOTAL_TILE_TYPES, TILES_PER_TYPE, SICHUAN_TILE_TYPES
    
    current_shanten = calculate_shanten(hand, sichuan_mode, missing_suit)
    tiles = hand.tiles
    
    effective = {}
    max_tile = SICHUAN_TILE_TYPES if sichuan_mode else TOTAL_TILE_TYPES
    
    for i in range(max_tile):
        # 跳过已持有 4 张的牌（不可能再摸到）
        if tiles[i] >= TILES_PER_TYPE:
            continue
        
        # 跳过缺门花色的牌
        if sichuan_mode and missing_suit is not None:
            offset = int(missing_suit) * SUIT_SIZE
            if offset <= i < offset + SUIT_SIZE:
                continue
        
        # 模拟摸入这张牌
        test_hand = hand.copy()
        test_hand.add_tile(i)
        new_shanten = calculate_shanten(test_hand, sichuan_mode, missing_suit)
        
        if new_shanten < current_shanten:
            # 这张牌能降低向听数，是有效进牌
            remaining = TILES_PER_TYPE - tiles[i]
            if visible is not None:
                remaining -= visible[i]
            if remaining > 0:
                effective[i] = remaining
    
    return effective


def get_discard_analysis(hand: Hand, sichuan_mode: bool = True,
                          missing_suit: Optional[Suit] = None,
                          visible: Optional[List[int]] = None) -> List[dict]:
    """
    分析每张手牌的出牌价值 — 核心出牌推荐函数。
    
    对于手中每张可以打出的牌，计算：
    1. 打出后的向听数
    2. 打出后的有效进牌数（能降低向听数的牌的总数量）
    3. 综合评分
    
    参数：
        hand: 当前手牌（应为 14 张，即摸牌后的状态）
        sichuan_mode: 是否使用四川麻将规则
        missing_suit: 缺门花色
        visible: 已可见的牌数量数组
    
    返回：
        按推荐优先级排序的出牌分析列表，每项包含：
        - 'tile': 牌索引
        - 'name': 牌名称
        - 'shanten': 打出后的向听数
        - 'effective_count': 打出后的有效进牌种类数
        - 'effective_tiles_remaining': 打出后的有效进牌总张数
        - 'score': 综合评分（越高越推荐此出牌）
    """
    from .tiles import TOTAL_TILE_TYPES, SICHUAN_TILE_TYPES
    
    tiles = hand.tiles
    results = []
    max_tile = SICHUAN_TILE_TYPES if sichuan_mode else TOTAL_TILE_TYPES
    
    # 记录已处理的牌（避免重复计算同一种牌）
    processed = set()
    
    for i in range(max_tile):
        if tiles[i] <= 0 or i in processed:
            continue
        processed.add(i)
        
        # 模拟打出这张牌
        test_hand = hand.copy()
        test_hand.remove_tile(i)
        
        # 计算打出后的向听数
        new_shanten = calculate_shanten(test_hand, sichuan_mode, missing_suit)
        
        # 计算打出后的有效进牌
        effective = get_effective_tiles(test_hand, sichuan_mode, missing_suit, visible)
        effective_count = len(effective)
        effective_remaining = sum(effective.values())
        
        # 综合评分：
        # - 向听数越低越好（权重最高）
        # - 有效进牌的总张数越多越好
        # - 有效进牌的种类越多越好
        score = -new_shanten * 1000 + effective_remaining * 10 + effective_count
        
        results.append({
            'tile': i,
            'name': tile_name(i),
            'shanten': new_shanten,
            'effective_count': effective_count,
            'effective_tiles_remaining': effective_remaining,
            'score': score,
        })
    
    # 按分数降序排序（分数高的排前面，即推荐优先出的牌）
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results
