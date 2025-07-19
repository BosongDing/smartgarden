import random
import math
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

class Phenology(Enum):
    """植物生长阶段"""
    SEEDLING = "seedling"       # 幼苗期
    VEGETATIVE = "vegetative"   # 营养生长期
    FLOWERING = "flowering"     # 开花期
    HARVESTABLE = "harvestable" # 可收获期
    DORMANT = "dormant"         # 休眠期
    DEAD = "dead"               # 死亡

@dataclass
class PlantStatus:
    """植物状态快照"""
    soil_moisture: float
    nutrient_level: float
    health: float
    biomass: float
    phenology: Phenology
    days_alive: int
    stress_level: float

class Plant:
    """简化的植物基类 - 基于阈值的响应机制"""
    
    def __init__(self, plant_config: Dict, pot_id: int = 0):
        # 基础配置
        self.config = plant_config
        self.pot_id = pot_id
        self.species_name = plant_config.get("scientific_name", "Unknown")
        self.category = plant_config.get("category", "unknown")
        
        # 生理状态
        self.soil_moisture = 0.5      # 土壤湿度 [0,1]
        self.nutrient_level = 0.5     # 养分水平 [0,1]
        self.health = 100.0           # 健康度 [0,100]
        self.biomass = 0.1            # 生物量 (g)
        self.phenology = Phenology.SEEDLING  # 生长阶段
        
        # 阈值参数
        self.soil_threshold = plant_config["soil_threshold"]
        self.nutrient_threshold = plant_config["nutrient_threshold"]
        self.critical_soil = plant_config["critical_soil"]
        self.critical_nutrient = plant_config["critical_nutrient"]
        
        # 生长参数
        self.growth_rate_max = plant_config["growth_rate_max"]
        self.harvest_day = plant_config["harvest_day"]
        
        # 状态跟踪
        self.days_alive = 0
        self.step_count = 0
        self.stress_level = 0.0
        
    def update(self, weather_state: Dict, soil_state: Dict, step: int) -> PlantStatus:
        """
        更新植物状态 - 简化的生理过程
        
        Args:
            weather_state: 天气状态
            soil_state: 土壤状态
            step: 当前步数
            
        Returns:
            更新后的植物状态
        """
        self.step_count = step
        self.days_alive = step // 8  # 每8步为一天
        
        # 更新土壤状态
        self.soil_moisture = soil_state.get("moisture", self.soil_moisture)
        self.nutrient_level = soil_state.get("nutrients", self.nutrient_level)
        
        # 简化的生理过程
        self._update_phenology()
        self._update_health_simple()
        self._update_growth_simple()
        self._update_stress_simple()
        
        return self.get_status()
    
    def _update_phenology(self):
        """更新生长阶段 - 基于天数"""
        if self.health <= 0:
            self.phenology = Phenology.DEAD
            return
            
        # 基于天数的简单阶段转换
        if self.days_alive < 7:
            self.phenology = Phenology.SEEDLING
        elif self.days_alive < self.harvest_day * 0.7:
            self.phenology = Phenology.VEGETATIVE
        elif self.days_alive < self.harvest_day * 0.9:
            self.phenology = Phenology.FLOWERING
        elif self.days_alive < self.harvest_day * 1.2:
            self.phenology = Phenology.HARVESTABLE
        else:
            self.phenology = Phenology.DORMANT
    
    def _update_health_simple(self):
        """简化的健康更新 - 只基于水分和养分"""
        health_change = 0.0
            
        # 水分压力
        if self.soil_moisture < self.critical_soil:
            health_change -= 5.0  # 严重缺水
        elif self.soil_moisture < self.soil_threshold:
            health_change -= 1.0  # 轻度缺水
            
        # 养分压力
        if self.nutrient_level < self.critical_nutrient:
            health_change -= 5.0  # 严重缺肥
        elif self.nutrient_level < self.nutrient_threshold:
            health_change -= 1.0  # 轻度缺肥
            
        # 过量问题
        if self.nutrient_level > 1.2:
            health_change -= 10.0  # 肥料中毒
        if self.soil_moisture > 1.0:
            health_change -= 8.0   # 过量浇水
            
        # 健康恢复 - 简化条件
        if (self.soil_moisture >= self.soil_threshold and 
            self.nutrient_level >= self.nutrient_threshold):
            health_change += 3.0  # 条件良好时恢复
        elif health_change == 0:  # 无压力时基础恢复
            health_change += 1.0
            
        # 应用健康变化
        self.health += health_change
        self.health = max(0.0, min(100.0, self.health))
        
        # 死亡检查
        if self.health <= 0:
            self.phenology = Phenology.DEAD
    
    def _update_growth_simple(self):
        """简化的生长更新 - 基于健康度和条件"""
        if self.health <= 20.0:  # 健康度过低停止生长
            return
            
        # 基础生长率
        base_growth = self.growth_rate_max
        
        # 生长阶段系数 - 简化为统一
        stage_factor = 1.0
        if self.phenology == Phenology.SEEDLING:
            stage_factor = 0.6
        elif self.phenology == Phenology.HARVESTABLE:
            stage_factor = 0.3
        elif self.phenology == Phenology.DORMANT:
            stage_factor = 0.0
            
        # 条件因子 - 简化判断
        condition_factor = 1.0
        if (self.soil_moisture < self.soil_threshold or 
            self.nutrient_level < self.nutrient_threshold):
            condition_factor = 0.5  # 条件不足减半生长
            
        if (self.soil_moisture < self.critical_soil or 
            self.nutrient_level < self.critical_nutrient):
            condition_factor = 0.1  # 严重不足几乎停止生长
            
        # 健康因子
        health_factor = self.health / 100.0
        
        # 计算生长
        growth = base_growth * stage_factor * condition_factor * health_factor
        self.biomass += growth
        
    def _update_stress_simple(self):
        """简化的压力计算"""
        stress_factors = []
        
        # 水分压力
        if self.soil_moisture < self.critical_soil:
            stress_factors.append(0.9)
        elif self.soil_moisture < self.soil_threshold:
            stress_factors.append(0.4)
        else:
            stress_factors.append(0.0)
            
        # 养分压力
        if self.nutrient_level < self.critical_nutrient:
            stress_factors.append(0.9)
        elif self.nutrient_level < self.nutrient_threshold:
            stress_factors.append(0.4)
        else:
            stress_factors.append(0.0)
            
        # 计算平均压力
        self.stress_level = sum(stress_factors) / len(stress_factors) if stress_factors else 0.0
    
    def get_status(self) -> PlantStatus:
        """获取植物状态快照"""
        return PlantStatus(
            soil_moisture=self.soil_moisture,
            nutrient_level=self.nutrient_level,
            health=self.health,
            biomass=self.biomass,
            phenology=self.phenology,
            days_alive=self.days_alive,
            stress_level=self.stress_level
        )
    
    def get_harvest_yield(self) -> float:
        """计算收获产量"""
        if self.phenology != Phenology.HARVESTABLE:
            return 0.0
            
        # 基于生物量和健康度计算产量
        yield_factor = (self.health / 100.0) * min(1.0, self.biomass / 5.0)
        return self.biomass * yield_factor
    
    def is_alive(self) -> bool:
        """检查植物是否存活"""
        return self.phenology != Phenology.DEAD and self.health > 0

# 具体植物类型 - 简化版本，移除特殊机制

class Lettuce(Plant):
    """生菜 - 标准植物"""
    
    def __init__(self, pot_id: int = 0):
        with open("garden_env/config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        plant_config = config["plants"]["lettuce"]
        super().__init__(plant_config, pot_id)

class Spinach(Plant):
    """菠菜 - 标准植物"""
    
    def __init__(self, pot_id: int = 0):
        with open("garden_env/config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        plant_config = config["plants"]["spinach"]
        super().__init__(plant_config, pot_id)

class Radish(Plant):
    """萝卜 - 耐旱植物"""
    
    def __init__(self, pot_id: int = 0):
        with open("garden_env/config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        plant_config = config["plants"]["radish"]
        super().__init__(plant_config, pot_id)
    
    def _update_health_simple(self):
        """萝卜特殊的健康更新 - 耐旱性"""
        health_change = 0.0
            
        # 萝卜的耐旱特性 - 减少水分压力惩罚
        if self.soil_moisture < self.critical_soil:
            health_change -= 3.0  # 比其他植物少2.0的惩罚
        elif self.soil_moisture < self.soil_threshold:
            health_change -= 0.5  # 比其他植物少0.5的惩罚
            
        # 养分压力正常
        if self.nutrient_level < self.critical_nutrient:
            health_change -= 5.0
        elif self.nutrient_level < self.nutrient_threshold:
            health_change -= 1.0
            
        # 过量问题
        if self.nutrient_level > 1.2:
            health_change -= 10.0
        if self.soil_moisture > 1.0:
            health_change -= 8.0
            
        # 健康恢复
        if (self.soil_moisture >= self.soil_threshold and 
            self.nutrient_level >= self.nutrient_threshold):
            health_change += 3.0
        elif health_change == 0:
            health_change += 1.0
            
        self.health += health_change
        self.health = max(0.0, min(100.0, self.health))
        
        if self.health <= 0:
            self.phenology = Phenology.DEAD

class SwissChard(Plant):
    """瑞士甜菜 - 多次采收"""
    
    def __init__(self, pot_id: int = 0):
        with open("garden_env/config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        plant_config = config["plants"]["swiss_chard"]
        super().__init__(plant_config, pot_id)
    
    def _update_phenology(self):
        """瑞士甜菜特殊的阶段更新 - 长期可采收"""
        if self.health <= 0:
            self.phenology = Phenology.DEAD
            return
            
        if self.days_alive < 10:
            self.phenology = Phenology.SEEDLING
        elif self.days_alive < 20:
            self.phenology = Phenology.VEGETATIVE
        else:
            self.phenology = Phenology.HARVESTABLE  # 长期可采收

class Nasturtium(Plant):
    """旱金莲 - 观赏植物，2阶段水分需求"""
    
    def __init__(self, pot_id: int = 0):
        with open("garden_env/config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        plant_config = config["plants"]["nasturtium"]
        super().__init__(plant_config, pot_id)
        
        # 旱金莲特殊配置
        self.flower_stage_soil_threshold = plant_config["flower_stage_soil_threshold"]
        self.flower_stage_day = plant_config["flower_stage_day"]
        self.is_flowering_stage = False
    
    def _update_phenology(self):
        """旱金莲特殊的阶段更新 - 开花导向"""
        if self.health <= 0:
            self.phenology = Phenology.DEAD
            return
            
        if self.days_alive < 10:
            self.phenology = Phenology.SEEDLING
            self.is_flowering_stage = False
        elif self.days_alive < 18:
            self.phenology = Phenology.VEGETATIVE
            self.is_flowering_stage = False
        elif self.days_alive < self.flower_stage_day:
            self.phenology = Phenology.FLOWERING
            self.is_flowering_stage = False
        else:
            self.phenology = Phenology.HARVESTABLE  # 花期可观赏
            self.is_flowering_stage = True
            # 更新水分需求阈值
            self.soil_threshold = self.flower_stage_soil_threshold

def create_plant(plant_type: str, pot_id: int = 0) -> Plant:
    """创建植物实例"""
    plant_classes = {
        "lettuce": Lettuce,
        "spinach": Spinach,
        "radish": Radish,
        "swiss_chard": SwissChard,
        "nasturtium": Nasturtium
    }
    
    if plant_type not in plant_classes:
        raise ValueError(f"Unknown plant type: {plant_type}")
        
    return plant_classes[plant_type](pot_id)