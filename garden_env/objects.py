import random
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SensorReading:
    """简化的传感器读数数据结构"""
    soil_moisture: Optional[float] = None
    nutrient_level: Optional[float] = None
    temperature: Optional[float] = None
    timestamp: int = 0

class WaterPump:
    """简化的水泵系统 - 基于配置的百分比效果"""
    
    def __init__(self, config: Dict):
        self.water_effect = config["devices"]["water_pump"]["water_effect"]
        
        # 运行统计
        self.total_water_used = 0.0
        self.operation_count = 0
        
        # 设备故障状态
        self.is_failed = False
        self.failure_end_step = 0
        self.failure_probability = config["devices"]["sensors"]["failure_probability"]
        
    def irrigate(self, pot_id: int, duration_hours: float, current_step: int) -> float:
        """
        执行灌溉操作 - 简化版本
        
        Args:
            pot_id: 花盆编号 (0-4)
            duration_hours: 灌溉持续时间（小时）- 忽略，使用固定效果
            current_step: 当前步数
            
        Returns:
            实际灌溉效果（百分比）
        """
        # 检查设备故障恢复
        if self.is_failed and current_step >= self.failure_end_step:
            self.is_failed = False
            
        # 随机触发设备故障
        if not self.is_failed and random.random() < self.failure_probability:
            self.is_failed = True
            self.failure_end_step = 1  # 故障持续3-8步
            
        # 如果设备故障，无法操作
        if self.is_failed:
            return 0.0
        
        # 正常操作
        water_effect = self.water_effect
        
        # 更新统计
        self.total_water_used += water_effect
        self.operation_count += 1
        
        return water_effect
    
    def get_status(self) -> Dict:
        """获取水泵状态"""
        return {
            "total_water_used": self.total_water_used,
            "operation_count": self.operation_count,
            "water_effect": self.water_effect,
            "is_failed": self.is_failed
        }

class Fertilizer:
    """简化的施肥器系统 - 基于配置的百分比效果"""
    
    def __init__(self, config: Dict):
        self.fertilizer_effect = config["devices"]["fertilizer"]["fertilizer_effect"]
        
        # 运行统计
        self.total_fertilizer_used = 0.0
        self.application_count = 0
        
        # 设备故障状态
        self.is_failed = False
        self.failure_end_step = 0
        self.failure_probability = config["devices"]["sensors"]["failure_probability"]
        
    def apply_fertilizer(self, pot_id: int, amount: float, current_step: int) -> float:
        """
        施肥操作 - 简化版本
        
        Args:
            pot_id: 花盆编号
            amount: 施肥量基数 - 忽略，使用固定效果
            current_step: 当前步数
            
        Returns:
            实际养分增加量（百分比）
        """
        # 检查设备故障恢复
        if self.is_failed and current_step >= self.failure_end_step:
            self.is_failed = False
            
        # 随机触发设备故障
        if not self.is_failed and random.random() < self.failure_probability:
            self.is_failed = True
            self.failure_end_step = current_step + random.randint(3, 8)  # 故障持续3-8步
            
        # 如果设备故障，无法操作
        if self.is_failed:
            return 0.0
        
        # 正常操作
        nutrient_increase = self.fertilizer_effect
        
        # 更新统计
        self.total_fertilizer_used += nutrient_increase
        self.application_count += 1
        
        return nutrient_increase
        
    def get_status(self) -> Dict:
        """获取施肥器状态"""
        return {
            "total_fertilizer_used": self.total_fertilizer_used,
            "application_count": self.application_count,
            "fertilizer_effect": self.fertilizer_effect,
            "is_failed": self.is_failed
        }

class SensorArray:
    """简化的传感器阵列 - 增强故障和错误机制"""
    
    def __init__(self, config: Dict):
        self.config = config["devices"]["sensors"]
        
        # 传感器故障状态 - 用于异常值教学
        self.sensor_failures = {}  # pot_id -> failure_end_step
        self.failure_probability = self.config["failure_probability"]  # 10%
        self.sensor_error_probability = self.config["sensor_error_probability"]  # 5%
        
        # 读数计数
        self.reading_count = 0
        
    def get_readings(self, plants: List, weather_state: Dict, current_step: int) -> Optional[Dict]:
        """
        获取传感器读数 - 增强故障和错误机制
        
        Args:
            plants: 植物列表
            weather_state: 天气状态
            current_step: 当前步数
            
        Returns:
            传感器读数字典
        """
        # 检查并恢复传感器故障
        recovered_sensors = []
        for pot_id, failure_end_step in list(self.sensor_failures.items()):
            if current_step >= failure_end_step:
                recovered_sensors.append(pot_id)
                
        for pot_id in recovered_sensors:
            del self.sensor_failures[pot_id]
        
        # 随机触发新的传感器故障 - 增加到10%
        for pot_id in range(len(plants)):
            if pot_id not in self.sensor_failures and random.random() < self.failure_probability:
                # 故障持续6-12步
                failure_duration = 1
                self.sensor_failures[pot_id] = current_step + failure_duration
        
        # 生成每个花盆的读数
        readings = {}
        for i, plant in enumerate(plants):
            # 检查是否故障
            if i in self.sensor_failures:
                # 传感器故障 - 生成异常值作为教学内容
                readings[f"pot_{i}"] = self._generate_faulty_reading(plant, weather_state, current_step)
            else:
                # 检查是否有传感器错误 - 新增5%错误率
                if random.random() < self.sensor_error_probability:
                    readings[f"pot_{i}"] = self._generate_error_reading(plant, weather_state, current_step)
                else:
                    # 正常读数 - 无噪声
                    readings[f"pot_{i}"] = SensorReading(
                        soil_moisture=plant.soil_moisture,
                        nutrient_level=plant.nutrient_level,
                        temperature=weather_state["temperature"],
                        timestamp=current_step
                    )
            
        # 环境传感器读数
        readings["environment"] = SensorReading(
            temperature=weather_state["temperature"],
            timestamp=current_step
        )
        
        self.reading_count += 1
        return readings
    
    def _generate_faulty_reading(self, plant, weather_state: Dict, current_step: int) -> SensorReading:
        """生成故障传感器的异常读数"""
        # 生成明显异常的读数，让学生能够识别
        fault_types = ["stuck", "drift", "spike"]
        fault_type = random.choice(fault_types)
        
        if fault_type == "stuck":
            # 传感器卡住，返回固定值
            return SensorReading(
                soil_moisture=0.5,  # 卡在中间值
                nutrient_level=0.5,
                temperature=weather_state["temperature"],
                timestamp=current_step
            )
        elif fault_type == "drift":
            # 传感器漂移，逐渐偏离真实值
            drift_factor = 0.3 + 0.4 * random.random()  # 0.3-0.7的漂移
            return SensorReading(
                soil_moisture=max(0, min(1, plant.soil_moisture * drift_factor)),
                nutrient_level=max(0, min(1, plant.nutrient_level * drift_factor)),
                temperature=weather_state["temperature"],
                timestamp=current_step
            )
        else:  # spike
            # 传感器尖峰，返回极端值
            return SensorReading(
                soil_moisture=random.choice([0.95, 0.05]),  # 极高或极低
                nutrient_level=random.choice([0.95, 0.05]),
                temperature=weather_state["temperature"],
                timestamp=current_step
            )
    
    def _generate_error_reading(self, plant, weather_state: Dict, current_step: int) -> SensorReading:
        """生成传感器错误读数 - 新增功能"""
        # 50%概率返回极值，50%概率返回None
        if random.random() < 0.5:
            # 极值错误
            return SensorReading(
                soil_moisture=random.choice([0.95, 0.05]),  # 超高或超低
                nutrient_level=random.choice([0.95, 0.05]),
                temperature=weather_state["temperature"],
                timestamp=current_step
            )
        else:
            # None读数错误
            return SensorReading(
                soil_moisture=None,
                nutrient_level=None,
                temperature=weather_state["temperature"],
                timestamp=current_step
            )
    
    def get_status(self) -> Dict:
        """获取传感器状态"""
        return {
            "reading_count": self.reading_count,
            "active_failures": len(self.sensor_failures),
            "failed_sensors": list(self.sensor_failures.keys()),
            "failure_probability": self.failure_probability,
            "sensor_error_probability": self.sensor_error_probability
        }

class DeviceManager:
    """简化的设备管理器 - 处理设备故障"""
    
    def __init__(self, config_path: str = "garden_env/config.json"):
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
            
        # 初始化设备
        self.water_pump = WaterPump(self.config)
        self.fertilizer = Fertilizer(self.config)
        self.sensors = SensorArray(self.config)
        
        # 设备运行日志
        self.operation_log = []
        
    def execute_watering(self, pot_id: int, duration: float, current_step: int) -> float:
        """执行浇水操作 - 可能因设备故障失败"""
        water_effect = self.water_pump.irrigate(pot_id, duration, current_step)
        
        # 记录操作（包括失败的操作）
        self.operation_log.append({
            "step": current_step,
            "action": "water",
            "pot_id": pot_id,
            "requested_duration": duration,
            "actual_effect": water_effect,
            "success": water_effect > 0
        })
        
        return water_effect
    
    def execute_fertilizing(self, pot_id: int, amount: float, current_step: int) -> float:
        """执行施肥操作 - 可能因设备故障失败"""
        nutrient_effect = self.fertilizer.apply_fertilizer(pot_id, amount, current_step)
        
        # 记录操作（包括失败的操作）
        self.operation_log.append({
            "step": current_step,
            "action": "fertilize",
            "pot_id": pot_id,
            "requested_amount": amount,
            "actual_effect": nutrient_effect,
            "success": nutrient_effect > 0
        })
        
        return nutrient_effect
    
    def get_sensor_readings(self, plants: List, weather_state: Dict, current_step: int) -> Optional[Dict]:
        """获取传感器读数"""
        return self.sensors.get_readings(plants, weather_state, current_step)
        
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        return {
            "water_pump": self.water_pump.get_status(),
            "fertilizer": self.fertilizer.get_status(),
            "sensors": self.sensors.get_status(),
            "total_operations": len(self.operation_log),
            "successful_operations": sum(1 for op in self.operation_log if op["success"])
        }
