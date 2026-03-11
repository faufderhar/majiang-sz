"""
麻将牌型定义与编码系统
=======================

这是整个引擎的基础模块，定义了麻将牌的数据结构和编码方式。

核心设计思路：
- 使用 int[34] 数组表示一手牌（或场上的牌），每个位置的值表示该牌的数量（0~4）
- 索引 0-8:   万子（1万~9万）
- 索引 9-17:  筒子（1筒~9筒）
- 索引 18-26: 条子（1条~9条）
- 索引 27-33: 字牌（东、南、西、北、中、发、白）

四川麻将特殊规则：
- 没有字牌（风牌和箭牌），但本引擎依然保留完整编码，方便扩展到其他麻将变种
- "缺门"规则：必须选择放弃一门花色（万/筒/条），手牌中不能保留该门
- 血战到底：一家胡牌后，剩余玩家继续打，直到三家都胡或牌墙打完
"""

from enum import IntEnum
from typing import List, Optional, Tuple


# ============================================================
# 花色定义（Suit）
# ============================================================
class Suit(IntEnum):
    """
    花色枚举
    
    麻将一共有三种花色（万、筒、条）和一种特殊类型（字牌）。
    四川麻将通常只使用万、筒、条三种花色，不使用字牌。
    
    每种花色有 9 张牌（1~9），字牌有 7 种。
    """
    WAN = 0     # 万子（又叫"万"或"万字"），图案是汉字数字
    TONG = 1    # 筒子（又叫"饼"），图案是圆形
    TIAO = 2    # 条子（又叫"索"），图案是竹条/竹子
    ZI = 3      # 字牌：东南西北中发白


# ============================================================
# 牌的索引常量
# ============================================================
# 定义每种牌在 34 位数组中的索引位置
# 万子：索引 0-8（对应 1万~9万）
WAN_OFFSET = 0
# 筒子：索引 9-17（对应 1筒~9筒）
TONG_OFFSET = 9
# 条子：索引 18-26（对应 1条~9条）
TIAO_OFFSET = 18
# 字牌：索引 27-33
ZI_OFFSET = 27

# 每种花色包含的牌数
SUIT_SIZE = 9   # 万/筒/条各 9 种
ZI_SIZE = 7     # 字牌 7 种

# 总牌种数
TOTAL_TILE_TYPES = 34  # 9 + 9 + 9 + 7 = 34 种

# 每种牌各有 4 张
TILES_PER_TYPE = 4

# 总牌数
TOTAL_TILES = TOTAL_TILE_TYPES * TILES_PER_TYPE  # 34 * 4 = 136 张


# ============================================================
# 字牌具体定义
# ============================================================
class Wind(IntEnum):
    """风牌枚举"""
    EAST = 27    # 东
    SOUTH = 28   # 南
    WEST = 29    # 西
    NORTH = 30   # 北


class Dragon(IntEnum):
    """箭牌（三元牌）枚举"""
    ZHONG = 31   # 中（红中）
    FA = 32      # 发（发财）
    BAI = 33     # 白（白板）


# ============================================================
# 牌的文字表示（用于显示和解析）
# ============================================================
# 花色后缀：m=万(man), p=筒(pin), s=条(suo/sou)、z=字(zi)
SUIT_CHARS = {
    Suit.WAN: 'm',   # m = man = 万
    Suit.TONG: 'p',  # p = pin = 筒 (有时也用 b = bing)
    Suit.TIAO: 's',  # s = suo = 条 (有时也用 t = tiao)
    Suit.ZI: 'z',    # z = zi = 字
}

# 反向映射：字符 → 花色
CHAR_TO_SUIT = {v: k for k, v in SUIT_CHARS.items()}

# 字牌的名称
ZI_NAMES = ['东', '南', '西', '北', '中', '发', '白']

# 牌的中文名称映射（索引 → 中文名）
TILE_NAMES = {}
for i in range(9):
    TILE_NAMES[WAN_OFFSET + i] = f'{i + 1}万'
    TILE_NAMES[TONG_OFFSET + i] = f'{i + 1}筒'
    TILE_NAMES[TIAO_OFFSET + i] = f'{i + 1}条'
for i, name in enumerate(ZI_NAMES):
    TILE_NAMES[ZI_OFFSET + i] = name


# ============================================================
# 核心工具函数
# ============================================================
def tile_index(number: int, suit: Suit) -> int:
    """
    根据牌面数字和花色，计算在 34 位数组中的索引。
    
    参数：
        number: 牌面数字（1~9 对应万/筒/条，1~7 对应字牌）
        suit: 花色（WAN/TONG/TIAO/ZI）
    
    返回：
        0~33 的整数索引
    
    示例：
        tile_index(1, Suit.WAN)  → 0   （一万）
        tile_index(9, Suit.WAN)  → 8   （九万）
        tile_index(1, Suit.TONG) → 9   （一筒）
        tile_index(1, Suit.ZI)   → 27  （东风）
    """
    # 计算偏移量：万=0, 筒=9, 条=18, 字=27
    offset = int(suit) * SUIT_SIZE
    # number 是 1 开始的，索引是 0 开始的，所以减 1
    return offset + (number - 1)


def index_to_tile(index: int) -> Tuple[int, Suit]:
    """
    将 34 位数组的索引转换回牌面数字和花色。
    
    参数：
        index: 0~33 的整数索引
    
    返回：
        (number, suit) 元组
    
    示例：
        index_to_tile(0)  → (1, Suit.WAN)   （一万）
        index_to_tile(9)  → (1, Suit.TONG)  （一筒）
        index_to_tile(27) → (1, Suit.ZI)    （东风）
    """
    if index < 0 or index >= TOTAL_TILE_TYPES:
        raise ValueError(f"索引 {index} 超出范围，有效范围为 0~{TOTAL_TILE_TYPES - 1}")
    
    # 除以 9 得到花色，取余得到牌面数字
    suit = Suit(index // SUIT_SIZE)
    number = (index % SUIT_SIZE) + 1  # +1 因为牌面从 1 开始
    return number, suit


def tile_name(index: int) -> str:
    """
    获取牌的中文名称。
    
    示例：
        tile_name(0)  → '1万'
        tile_name(27) → '东'
    """
    return TILE_NAMES.get(index, f'未知牌({index})')


def tile_to_emoji(index: int) -> str:
    """
    将牌索引转为 Unicode 麻将 emoji（如果终端支持的话）。
    
    注意：不是所有终端都支持这些字符，仅作为辅助显示使用。
    标准 Unicode 麻将字符从 U+1F000 开始。
    """
    # Unicode 麻将牌: 🀇🀈🀉🀊🀋🀌🀍🀎🀏 (1-9万)
    #                🀙🀚🀛🀜🀝🀞🀟🀠🀡 (1-9筒) 
    #                🀐🀑🀒🀓🀔🀕🀖🀗🀘 (1-9条)
    #                🀀🀁🀂🀃🀄🀅🀆 (东南西北中发白)
    number, suit = index_to_tile(index)
    if suit == Suit.WAN:
        return chr(0x1F007 + number - 1)  # 🀇 = 1万
    elif suit == Suit.TONG:
        return chr(0x1F019 + number - 1)  # 🀙 = 1筒
    elif suit == Suit.TIAO:
        return chr(0x1F010 + number - 1)  # 🀐 = 1条
    else:  # 字牌
        return chr(0x1F000 + number - 1)  # 🀀 = 东


# ============================================================
# 手牌类（Hand）
# ============================================================
class Hand:
    """
    手牌类 — 表示一个玩家的手牌状态。
    
    内部使用 int[34] 数组表示，每个位置的值表示持有该牌的数量。
    
    为什么用数组而不是列表？
    - 数组下标直接对应牌的种类，查找 O(1)
    - 方便做加减运算（摸牌/出牌）
    - 方便做花色分离计算（向听数算法需要）
    
    使用示例：
        hand = Hand()
        hand.add_tile(0)        # 添加一张一万
        hand.add_tiles("1m2m3m4p5p6p7s8s9s1z1z1z2z")  # 从字符串添加
        print(hand)             # 打印手牌
    """
    
    def __init__(self, tiles: Optional[List[int]] = None):
        """
        初始化手牌。
        
        参数：
            tiles: 可选的 34 位整数数组，表示初始手牌
        """
        if tiles is not None:
            # 验证输入
            if len(tiles) != TOTAL_TILE_TYPES:
                raise ValueError(f"牌数组长度必须为 {TOTAL_TILE_TYPES}，实际为 {len(tiles)}")
            self._tiles = list(tiles)  # 复制一份，避免外部修改
        else:
            # 默认空手牌
            self._tiles = [0] * TOTAL_TILE_TYPES
    
    @property
    def tiles(self) -> List[int]:
        """返回牌数组的副本（避免外部直接修改内部状态）"""
        return list(self._tiles)
    
    @property
    def total_count(self) -> int:
        """手牌总数"""
        return sum(self._tiles)
    
    def count(self, index: int) -> int:
        """获取某种牌的数量"""
        return self._tiles[index]
    
    def add_tile(self, index: int, count: int = 1) -> None:
        """
        添加牌到手牌。
        
        参数：
            index: 牌的索引 (0~33)
            count: 添加数量，默认 1
        
        异常：
            ValueError: 如果添加后数量超过 4（每种牌最多 4 张）
        """
        if self._tiles[index] + count > TILES_PER_TYPE:
            raise ValueError(
                f"无法添加 {count} 张 {tile_name(index)}，"
                f"当前已有 {self._tiles[index]} 张，最多 {TILES_PER_TYPE} 张"
            )
        self._tiles[index] += count
    
    def remove_tile(self, index: int, count: int = 1) -> None:
        """
        从手牌移除牌。
        
        参数：
            index: 牌的索引 (0~33)
            count: 移除数量，默认 1
        
        异常：
            ValueError: 如果移除后数量为负
        """
        if self._tiles[index] - count < 0:
            raise ValueError(
                f"无法移除 {count} 张 {tile_name(index)}，"
                f"当前只有 {self._tiles[index]} 张"
            )
        self._tiles[index] -= count
    
    def has_tile(self, index: int) -> bool:
        """检查是否持有某种牌"""
        return self._tiles[index] > 0
    
    # --------------------------------------------------------
    # 花色相关方法（四川麻将的"缺门"规则需要）
    # --------------------------------------------------------
    def suit_tiles(self, suit: Suit) -> List[int]:
        """
        获取某一花色的牌数组（长度 9 或 7）。
        
        参数：
            suit: 花色
        
        返回：
            该花色的牌数量数组
        
        示例：
            hand.suit_tiles(Suit.WAN)  → [1, 0, 1, 0, ...] （表示有一万和三万各 1 张）
        """
        offset = int(suit) * SUIT_SIZE
        size = ZI_SIZE if suit == Suit.ZI else SUIT_SIZE
        return self._tiles[offset:offset + size]
    
    def suit_count(self, suit: Suit) -> int:
        """获取某一花色的总牌数"""
        return sum(self.suit_tiles(suit))
    
    def missing_suit(self) -> Optional[Suit]:
        """
        检测"缺门"的花色（四川麻将规则）。
        
        四川麻将要求选择一门花色完全不持有（缺门），
        如果手牌中某门花色数量为 0，返回该花色。
        
        返回：
            缺门的花色，如果没有则返回 None
        """
        for suit in [Suit.WAN, Suit.TONG, Suit.TIAO]:
            if self.suit_count(suit) == 0:
                return suit
        return None
    
    # --------------------------------------------------------
    # 字符串解析和显示
    # --------------------------------------------------------
    @classmethod
    def from_string(cls, s: str) -> 'Hand':
        """
        从简写字符串创建手牌。
        
        格式说明：
        - 数字 + 花色字母的组合
        - m=万, p=筒, s=条, z=字
        - 同花色的多张牌可以连续写数字，花色字母放最后
        
        示例：
            "123m456p789s11z"   → 一二三万 + 四五六筒 + 七八九条 + 东东
            "1m2m3m"           → 一万 二万 三万
            "19m19p19s1234567z" → 十三幺需要的牌
        
        参数：
            s: 牌的简写字符串
        
        返回：
            Hand 实例
        """
        hand = cls()
        
        # 从字符串中解析牌
        # 收集当前花色字母之前的所有数字
        numbers = []
        for char in s:
            if char.isdigit():
                # 收集数字
                numbers.append(int(char))
            elif char in CHAR_TO_SUIT:
                # 遇到花色字母，将之前收集的数字全部添加为该花色的牌
                suit = CHAR_TO_SUIT[char]
                for num in numbers:
                    idx = tile_index(num, suit)
                    hand.add_tile(idx)
                numbers = []  # 清空，准备下一组
            else:
                raise ValueError(f"无法识别的字符 '{char}'，有效字符为: 1-9, m, p, s, z")
        
        if numbers:
            raise ValueError(f"字符串末尾有未处理的数字 {numbers}，请确保每组数字后跟花色字母")
        
        return hand
    
    def to_string(self) -> str:
        """
        将手牌转换为简写字符串。
        
        示例：
            Hand([1,1,1,0,...]) → "123m"
        """
        parts = []
        
        for suit in [Suit.WAN, Suit.TONG, Suit.TIAO, Suit.ZI]:
            offset = int(suit) * SUIT_SIZE
            size = ZI_SIZE if suit == Suit.ZI else SUIT_SIZE
            
            suit_nums = []
            for i in range(size):
                count = self._tiles[offset + i]
                # 对于每张持有的牌，添加对应数量的数字
                for _ in range(count):
                    suit_nums.append(str(i + 1))
            
            if suit_nums:
                parts.append(''.join(suit_nums) + SUIT_CHARS[suit])
        
        return ''.join(parts)
    
    def to_display(self) -> str:
        """
        将手牌转换为带中文名称的可读字符串。
        
        示例：
            "一万 二万 三万 四筒 五筒 六筒 七条 八条 九条 东 东 东 南"
        """
        names = []
        for i in range(TOTAL_TILE_TYPES):
            for _ in range(self._tiles[i]):
                names.append(tile_name(i))
        return ' '.join(names)
    
    def to_emoji(self) -> str:
        """将手牌转换为 emoji 字符串显示"""
        emojis = []
        for i in range(TOTAL_TILE_TYPES):
            for _ in range(self._tiles[i]):
                emojis.append(tile_to_emoji(i))
        return ''.join(emojis)
    
    def __str__(self) -> str:
        return f"{self.to_string()} ({self.to_display()})"
    
    def __repr__(self) -> str:
        return f"Hand('{self.to_string()}')"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Hand):
            return NotImplemented
        return self._tiles == other._tiles
    
    def copy(self) -> 'Hand':
        """创建手牌的深拷贝"""
        return Hand(list(self._tiles))


# ============================================================
# 可见牌追踪器（VisibleTiles）
# ============================================================
class VisibleTiles:
    """
    可见牌追踪器 — 记录场上所有可见的牌。
    
    "可见牌"包括：
    1. 自己的手牌
    2. 所有玩家打出去的牌（河牌/牌河）
    3. 所有玩家的明牌（吃/碰/杠的牌）
    
    用途：
    - 计算某种牌的剩余数量，用于判断进牌概率
    - 分析三家可能的手牌组成
    - 评估打出某张牌的危险度
    """
    
    def __init__(self):
        # 记录已可见的牌数量
        self._visible = [0] * TOTAL_TILE_TYPES
    
    def add(self, index: int, count: int = 1) -> None:
        """记录一张可见牌"""
        self._visible[index] += count
        if self._visible[index] > TILES_PER_TYPE:
            raise ValueError(
                f"{tile_name(index)} 可见数量 {self._visible[index]} "
                f"超过最大值 {TILES_PER_TYPE}"
            )
    
    def remaining(self, index: int) -> int:
        """计算某种牌的剩余数量（尚未可见的）"""
        return TILES_PER_TYPE - self._visible[index]
    
    def total_remaining(self) -> int:
        """牌墙中剩余的总牌数（估算）"""
        return TOTAL_TILES - sum(self._visible)
    
    def is_exhausted(self, index: int) -> bool:
        """某种牌是否已经全部可见（打完了/都出现了）"""
        return self._visible[index] >= TILES_PER_TYPE
    
    def visible_count(self, index: int) -> int:
        """获取某种牌的已见数量"""
        return self._visible[index]
    
    def __str__(self) -> str:
        visible = []
        for i in range(TOTAL_TILE_TYPES):
            if self._visible[i] > 0:
                visible.append(f"{tile_name(i)}×{self._visible[i]}")
        return f"已见牌: {', '.join(visible) if visible else '(无)'}"


# ============================================================
# 四川麻将特殊常量
# ============================================================
# 四川麻将只使用万、筒、条，不使用字牌
SICHUAN_VALID_SUITS = [Suit.WAN, Suit.TONG, Suit.TIAO]

# 四川麻将的牌种数：9 × 3 = 27 种
SICHUAN_TILE_TYPES = 27

# 四川麻将的总牌数：27 × 4 = 108 张
SICHUAN_TOTAL_TILES = SICHUAN_TILE_TYPES * TILES_PER_TYPE


def is_sichuan_tile(index: int) -> bool:
    """判断一张牌是否是四川麻将中的有效牌（万/筒/条）"""
    return 0 <= index < SICHUAN_TILE_TYPES


def validate_sichuan_hand(hand: Hand) -> bool:
    """
    验证手牌是否符合四川麻将规则：
    1. 不能包含字牌
    2. 必须缺一门花色
    
    返回：
        True 表示合法，False 表示不合法
    """
    # 检查是否包含字牌
    for i in range(ZI_OFFSET, ZI_OFFSET + ZI_SIZE):
        if hand.count(i) > 0:
            return False
    
    # 四川麻将必须缺一门（注意：这是在出牌阶段才需要检查，起手牌可能三门都有）
    return True
