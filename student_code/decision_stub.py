"""
学生决策函数模板
===============

学生需要实现两个核心函数：
1. should_water(state) -> bool  : 决定是否浇水
2. should_fertilize(state) -> bool : 决定是否施肥

状态字典包含以下信息：
- pot_id: 花盆编号 (0-4)
- step: 当前步数
- day: 当前天数
- sensor_data: 传感器读数 (包含 soil_moisture, nutrient_level, temperature)
- plant_type: 植物类型
- plant_status: 植物状态 (包含 health, biomass, phenology)
"""

def should_water(state):
    """
    决定是否浇水
    
    Args:
        state: 包含传感器数据和植物状态的字典
        
    Returns:
        bool: True表示需要浇水，False表示不需要
    """
    # TODO: 学生在这里实现浇水策略
    return False

def should_fertilize(state):
    """
    决定是否施肥
    
    Args:
        state: 包含传感器数据和植物状态的字典
        
    Returns:
        bool: True表示需要施肥，False表示不需要
    """
    # TODO: 学生在这里实现施肥策略
    return False 