import random
import math
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

@dataclass
class WeatherState:
    """简化的天气状态数据结构 - 只保留核心要素"""
    temperature: float      # 温度 (°C)
    is_raining: bool       # 是否降雨
    rainfall_amount: float # 降雨量 (mm/3h) - 仅在降雨时有效
    step: int             # 当前步数

class WeatherGenerator:
    """简化的天气生成器 - 只生成温度和降雨"""
    
    def __init__(self, config: Dict, random_seed: int = 42):
        # random.seed(random_seed)
        self.config = config
        
        # 温度参数
        self.temp_mean = self.config["temp_mean"]
        self.temp_amplitude = self.config["temp_amplitude"] 
        self.temp_noise_std = self.config["temp_noise_std"]
        
        # 降雨参数 - 简化为概率+固定量
        self.rain_probability = self.config["rain_probability_per_day"]
        self.rain_amount = 8.0  # 固定降雨量，简化伽马分布
        
        # 状态跟踪
        self.current_step = 0
        self.weather_history = []
        
    def generate_weather(self, step: int) -> WeatherState:
        """
        生成指定步数的简化天气状态
        
        Args:
            step: 当前步数 (0-239)
            
        Returns:
            WeatherState对象
        """
        self.current_step = step
        
        # 计算时间
        time_of_day = (step * 3) % 24  # 每步3小时
        
        # 生成温度
        temperature = self._generate_temperature(step, time_of_day)
        
        # 生成降雨 - 简化逻辑
        is_raining, rainfall_amount = self._generate_rainfall()
        
        weather_state = WeatherState(
            temperature=temperature,
            is_raining=is_raining,
            rainfall_amount=rainfall_amount,
            step=step
        )
        
        self.weather_history.append(weather_state)
        return weather_state
    
    def _generate_temperature(self, step: int, time_of_day: float) -> float:
        """
        生成温度 - 基于日周期和随机噪声
        
        Formula: T = T_mean + amp * sin(2π * t/24) + ε
        """
        # 日周期温度变化
        daily_cycle = self.temp_amplitude * math.sin(2 * math.pi * time_of_day / 24)
        
        # 季节性缓慢变化（模拟30天内的微小变化）
        seasonal_drift = 0.5 * math.sin(2 * math.pi * step / 240)
        
        # 随机噪声
        noise = random.gauss(0, self.temp_noise_std)
        
        temperature = self.temp_mean + daily_cycle + seasonal_drift + noise
        
        # 限制在合理范围内
        return max(5.0, min(40.0, temperature))
    
    def _generate_rainfall(self) -> Tuple[bool, float]:
        """
        生成降雨 - 简化为概率判断
        """
        # 每3小时的降雨概率
        rain_prob_per_step = self.rain_probability / 8  # 每日8步
        
        if random.random() < rain_prob_per_step:
            return True, self.rain_amount  # 固定降雨量
        else:
            return False, 0.0
    
    def get_weather_summary(self) -> Dict:
        """获取天气汇总"""
        if not self.weather_history:
            return {}
            
        recent_weather = self.weather_history[-24:]  # 最近24步
        
        return {
            "average_temperature": sum(w.temperature for w in recent_weather) / len(recent_weather),
            "total_rainfall": sum(w.rainfall_amount for w in recent_weather),
            "rain_days": sum(1 for w in recent_weather if w.is_raining)
        }

class WeatherSimulator:
    """简化的天气模拟器"""
    
    def __init__(self, config_path: str = "garden_env/config.json"):
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        # 使用荷兰7月配置
        weather_config = config["weather"]["netherlands_july"]
        
        # 初始化生成器
        self.weather_generator = WeatherGenerator(weather_config, config["simulation"]["random_seed"])
        
        # 状态
        self.current_weather = None
        
    def step_weather(self, step: int) -> WeatherState:
        """执行天气步骤更新"""
        self.current_weather = self.weather_generator.generate_weather(step)
        return self.current_weather
        
    def get_current_weather(self) -> Optional[WeatherState]:
        """获取当前天气状态"""
        return self.current_weather
        
    def get_simulation_summary(self) -> Dict:
        """获取模拟汇总"""
        return {
            "weather_summary": self.weather_generator.get_weather_summary(),
            "current_weather": self.current_weather
        }
