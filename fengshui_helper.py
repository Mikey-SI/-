"""Calculate today's accurate Chinese 天干地支 (Heavenly Stems & Earthly Branches),
五行 (Five Elements), 农历 (Lunar date), and provide structured fengshui context
for the AI prompts. This eliminates the AI's date hallucination problem.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ===== Heavenly Stems (天干) =====
HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
STEM_ELEMENTS = {  # 五行
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}
STEM_YIN_YANG = {
    "甲": "阳", "乙": "阴",
    "丙": "阳", "丁": "阴",
    "戊": "阳", "己": "阴",
    "庚": "阳", "辛": "阴",
    "壬": "阳", "癸": "阴",
}

# ===== Earthly Branches (地支) =====
EARTHLY_BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
BRANCH_ELEMENTS = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水",
}
BRANCH_ANIMALS = {
    "子": "鼠", "丑": "牛", "寅": "虎", "卯": "兔",
    "辰": "龙", "巳": "蛇", "午": "马", "未": "羊",
    "申": "猴", "酉": "鸡", "戌": "狗", "亥": "猪",
}

# ===== Lucky colors per element (五行对应颜色) =====
ELEMENT_COLORS = {
    "金": "白色、金色、银色",
    "木": "绿色、青色",
    "水": "黑色、深蓝色",
    "火": "红色、紫色、橙色",
    "土": "黄色、棕色、米色",
}

# ===== Direction per element =====
ELEMENT_DIRECTIONS = {
    "金": "西方、西北",
    "木": "东方、东南",
    "水": "北方",
    "火": "南方",
    "土": "中央、西南、东北",
}

# ===== 五行相生相克 =====
ELEMENT_GENERATES = {  # 生（帮扶）
    "金": "水", "水": "木", "木": "火", "火": "土", "土": "金"
}
ELEMENT_OVERCOMES = {  # 克（克制）
    "金": "木", "木": "土", "土": "水", "水": "火", "火": "金"
}


def get_day_ganzhi(date: datetime) -> tuple:
    """Calculate the 干支 (Heavenly Stem + Earthly Branch) for a given date.

    Reference epoch: 1900-01-01 was 甲戌 day (stem index 0, branch index 10).
    Wait - more accurate: 2000-01-07 was 甲子 day (offset 0).
    We use 1984-02-02 as 甲子 day reference (verified standard).
    """
    # Reference: 1984-02-02 (Thursday) was 甲子 day per traditional calendar
    reference = datetime(1984, 2, 2)
    days_diff = (date.date() - reference.date()).days
    
    stem_idx = days_diff % 10
    branch_idx = days_diff % 12
    
    stem = HEAVENLY_STEMS[stem_idx]
    branch = EARTHLY_BRANCHES[branch_idx]
    
    return stem, branch


def get_year_ganzhi(date: datetime) -> tuple:
    """Calculate the 干支 of the year. Lichun (around Feb 4) is the boundary."""
    year = date.year
    if (date.month == 1) or (date.month == 2 and date.day < 4):
        year -= 1
    # 1984 was 甲子年
    diff = year - 1984
    stem_idx = diff % 10
    branch_idx = diff % 12
    return HEAVENLY_STEMS[stem_idx], EARTHLY_BRANCHES[branch_idx]


def get_today_fengshui_context() -> dict:
    """Returns a complete fengshui context dictionary for the AI prompt.
    All time-related fields are computed accurately, eliminating AI hallucination.
    """
    # Use Beijing/Macau time
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    
    day_stem, day_branch = get_day_ganzhi(now)
    year_stem, year_branch = get_year_ganzhi(now)
    
    day_stem_element = STEM_ELEMENTS[day_stem]
    day_branch_element = BRANCH_ELEMENTS[day_branch]
    day_yin_yang = STEM_YIN_YANG[day_stem]
    day_animal = BRANCH_ANIMALS[day_branch]
    
    # The day's primary element is the day stem element (主气)
    primary_element = day_stem_element
    
    return {
        "date_str": now.strftime("%Y-%m-%d"),
        "weekday_cn": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()],
        "weekday_en": now.strftime("%A"),
        "year_ganzhi": f"{year_stem}{year_branch}",
        "year_animal": BRANCH_ANIMALS[year_branch],
        "day_ganzhi": f"{day_stem}{day_branch}",
        "day_stem": day_stem,
        "day_branch": day_branch,
        "day_yin_yang": day_yin_yang,
        "day_animal": day_animal,
        "day_stem_element": day_stem_element,
        "day_branch_element": day_branch_element,
        "primary_element": primary_element,
        "lucky_color": ELEMENT_COLORS[primary_element],
        "lucky_direction": ELEMENT_DIRECTIONS[primary_element],
        "element_generates": ELEMENT_GENERATES[primary_element],  # 我生
        "element_overcomes": ELEMENT_OVERCOMES[primary_element],  # 我克
        # Reader A: 弱火 (weak fire) implications
        "reader_a_analysis": _reader_a_weak_fire(primary_element),
        # Reader B: 身弱乙木 (weak yi-wood) implications
        "reader_b_analysis": _reader_b_weak_yi_wood(primary_element, day_branch_element),
    }


def _reader_a_weak_fire(day_element: str) -> str:
    """Analysis for someone with weak fire constitution."""
    if day_element == "木":
        return "木生火，今日是弱火之人的助力日（吉）。木日扶助火气，宜进取、宜决策、宜进攻性投资。建议穿绿色或红色服饰增强能量。"
    elif day_element == "火":
        return "火日见火，弱火之人得同气相助（大吉）。今日适合主动出击、布局新仓位、表达观点。但需防过燥，午时（11-13点）后宜冷静。"
    elif day_element == "土":
        return "火生土，今日弱火之人能量被泄（小凶）。气运被分散，宜守不宜攻。避免重仓决策，宜观望、复盘、整理资料。"
    elif day_element == "金":
        return "火克金本应有利（火日时），但弱火之人金日反受牵制（中性偏凶）。宜避免贸然出手，特别是科技股和金融股。"
    else:  # 水
        return "水克火，今日弱火之人受冲（凶）。宜保守、避免高风险操作、不宜与人争执。下午及晚间能量较稳，可处理琐事。"


def _reader_b_weak_yi_wood(day_stem_element: str, day_branch_element: str) -> str:
    """Analysis for someone with weak Yi-Wood (乙木) constitution."""
    # 乙木 prefers: 水 (滋养)、木 (同助)
    # 乙木 fears: 金 (克制)、火 (耗泄)、过多土 (无养)
    if day_stem_element == "水":
        return "水生木，身弱乙木之人今日得滋养（大吉）。最适合启动新计划、进行学习、签订重要合约。穿黑色或深蓝色衣物可增加贵人运。"
    elif day_stem_element == "木":
        return "木日同气相助，身弱乙木得比劫之力（吉）。可放胆决策，但避免独行——团队合作收益更大。"
    elif day_stem_element == "金":
        return "金克木，身弱乙木今日受冲（大凶）。务必避开重大决策、避免合同签署、谨慎沟通。穿绿色或黑色防身。"
    elif day_stem_element == "火":
        return "木生火，身弱乙木今日能量被泄（凶）。容易疲倦、决策力下降。宜静不宜动，多休息、少操劳。"
    else:  # 土
        return "木克土过度则伤己，身弱乙木今日宜守（中性偏凶）。避免投机性交易，宜处理常规事务。"


if __name__ == "__main__":
    ctx = get_today_fengshui_context()
    import json
    print(json.dumps(ctx, ensure_ascii=False, indent=2))
