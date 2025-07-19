import random
import math
import json
import time
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from pathlib import Path

# 导入自定义模块
from .weather import WeatherSimulator, WeatherState
from .objects import DeviceManager, SensorReading
from .plant import Plant, create_plant, Phenology, PlantStatus


@dataclass
class SoilState:
    """简化的土壤状态数据结构"""
    moisture: float         # 土壤湿度 [0,1]
    nutrients: float        # 养分水平 [0,1]
    pot_id: int            # 花盆编号

@dataclass 
class StepResult:
    """单步模拟结果"""
    step: int
    weather: WeatherState
    soil_states: List[SoilState]
    plant_states: List[PlantStatus]
    sensor_readings: Optional[Dict]
    student_decisions: Dict
    device_actions: Dict
    score: float

class SoilManager:
    """简化的土壤管理器 - 专注于水分和养分平衡"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.soil_config = config["soil"]
        
        # 初始化5个花盆的土壤状态
        self.soil_states = []
        for i in range(5):
            self.soil_states.append(SoilState(
                moisture=0.5,
                nutrients=0.5,
                pot_id=i
            ))
            
        # 简化的物理参数
        self.pot_capacity = self.soil_config["pot_capacity_ml"]
        self.evaporation_rate = self.soil_config["evaporation_base_rate"]
        self.nutrient_consumption_rate = self.soil_config["nutrient_consumption_rate"]
        
        # 使用配置中的浇水和施肥效果
        self.water_per_action = config["devices"]["water_pump"]["water_effect"]
        self.fertilizer_per_action = config["devices"]["fertilizer"]["fertilizer_effect"]
        
    def update_soil(self, weather: WeatherState, device_actions: Dict, plants: List[Plant]):
        """
        更新所有花盆的土壤状态 - 简化逻辑
        
        Args:
            weather: 天气状态
            device_actions: 设备操作记录
            plants: 植物列表
        """
        for i, soil in enumerate(self.soil_states):
            # 水分变化 - 简化计算
            self._update_moisture_simple(soil, weather, device_actions, plants[i] if i < len(plants) else None)
            
            # 养分变化 - 简化计算
            self._update_nutrients_simple(soil, weather, device_actions, plants[i] if i < len(plants) else None)
            
    def _update_moisture_simple(self, soil: SoilState, weather: WeatherState, 
                               device_actions: Dict, plant: Optional[Plant]):
        """简化的土壤湿度更新"""
        
        # 基础水分消耗 - 降低消耗速度，让每天浇水一次足够
        base_consumption = self.evaporation_rate  # 每步消耗2%
        
        # 温度影响消耗速度 - 只影响蒸发，不影响植物健康
        temp_factor = 1.0 + max(0, (weather.temperature - 25) * 0.02)  # 高温增加消耗
        
        # 植物蒸腾 - 大幅简化，去除生长阶段影响
        plant_consumption = 0.0
        if plant and plant.is_alive():
            # 基于植物大小的简单消耗
            plant_consumption = 0.01 * (plant.biomass / 5.0) * (plant.health / 100.0)
            
        # 总消耗
        total_consumption = base_consumption * temp_factor + plant_consumption
        
        # 降雨补充 - 简化为固定补充
        rainfall_input = 0.0
        if weather.is_raining:
            rainfall_input = 0.15  # 降雨时补充15%湿度
            
        # 灌溉补充 - 使用配置中的效果
        irrigation = 0.0
        for action in device_actions.get("water", []):
            if action.get("pot_id") == soil.pot_id and action.get("actual_effect", 0) > 0:
                irrigation += action["actual_effect"]
                
        # 更新湿度
        moisture_change = rainfall_input + irrigation - total_consumption
        soil.moisture += moisture_change
        soil.moisture = max(0.0, min(1.3, soil.moisture))  # 允许轻微过量到130%
        
    def _update_nutrients_simple(self, soil: SoilState, weather: WeatherState, 
                                device_actions: Dict, plant: Optional[Plant]):
        """简化的土壤养分更新"""
        
        # 植物养分消耗 - 简化计算，去除生长阶段影响
        plant_uptake = 0.0
        if plant and plant.is_alive():
            # 统一的养分消耗，不再区分生长阶段
            base_uptake = self.nutrient_consumption_rate
            plant_uptake = base_uptake * (plant.health / 100.0)
            
        # 降雨导致的养分流失 - 简化
        rain_loss = 0.0
        if weather.is_raining:
            rain_loss = 0.05  # 降雨时流失5%养分
            
        # 施肥补充 - 使用配置中的效果
        fertilizer_input = 0.0
        for action in device_actions.get("fertilize", []):
            if action.get("pot_id") == soil.pot_id and action.get("actual_effect", 0) > 0:
                fertilizer_input += action["actual_effect"]
                
        # 更新养分水平
        nutrient_change = fertilizer_input - plant_uptake - rain_loss
        soil.nutrients += nutrient_change
        soil.nutrients = max(0.0, min(1.5, soil.nutrients))  # 允许过量到150%
        
    def get_soil_state(self, pot_id: int) -> SoilState:
        """获取指定花盆的土壤状态"""
        return self.soil_states[pot_id]
        
    def get_all_soil_states(self) -> List[SoilState]:
        """获取所有土壤状态"""
        return self.soil_states.copy()

class StateManager:
    """状态管理器 - 追踪和记录系统状态"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.simulation_history = []
        self.daily_summaries = []
        self.start_time = time.time()
        
        # 历史数据缓存 - 用于提供给学生
        self.sensor_history = {}  # pot_id -> list of readings
        self.action_history = {}  # pot_id -> list of actions
        
    def log_step(self, step_result: StepResult):
        """记录单步结果"""
        self.simulation_history.append(step_result)
        
        # 更新传感器历史数据
        if step_result.sensor_readings:
            for pot_key, reading in step_result.sensor_readings.items():
                if pot_key.startswith("pot_"):
                    pot_id = int(pot_key.split("_")[1])
                    if pot_id not in self.sensor_history:
                        self.sensor_history[pot_id] = []
                    
                    # 添加当前读数
                    self.sensor_history[pot_id].append({
                        "step": step_result.step,
                        "soil_moisture": reading.soil_moisture,
                        "nutrient_level": reading.nutrient_level,
                        "temperature": reading.temperature
                    })
                    
                    # 只保留最近24小时(24步)的历史
                    if len(self.sensor_history[pot_id]) > 24:
                        self.sensor_history[pot_id].pop(0)
        
        # 更新操作历史
        for pot_id in range(5):
            if pot_id not in self.action_history:
                self.action_history[pot_id] = []
                
            # 记录浇水操作
            for action in step_result.student_decisions.get("water", []):
                if action.get("pot_id") == pot_id:
                    self.action_history[pot_id].append({
                        "step": step_result.step,
                        "action": "water"
                    })
                    
            # 记录施肥操作
            for action in step_result.student_decisions.get("fertilize", []):
                if action.get("pot_id") == pot_id:
                    self.action_history[pot_id].append({
                        "step": step_result.step,
                        "action": "fertilize"
                    })
                    
            # 只保留最近48小时(48步)的操作历史
            if len(self.action_history[pot_id]) > 48:
                self.action_history[pot_id] = self.action_history[pot_id][-48:]
        
        # 每日汇总（每8步）
        if step_result.step % 8 == 7:  # 每天结束
            self._create_daily_summary(step_result.step)
            
    def get_sensor_history(self, pot_id: int) -> List[Dict]:
        """获取指定花盆的传感器历史数据"""
        return self.sensor_history.get(pot_id, [])
        
    def get_action_history(self, pot_id: int) -> List[Dict]:
        """获取指定花盆的操作历史数据"""
        return self.action_history.get(pot_id, [])
            
    def _create_daily_summary(self, step: int):
        """创建每日汇总"""
        day = step // 8
        daily_steps = self.simulation_history[-8:]  # 最近8步
        
        # 计算每日统计
        avg_temp = sum(s.weather.temperature for s in daily_steps) / len(daily_steps)
        total_rain = sum(s.weather.rainfall_amount if s.weather.is_raining else 0 for s in daily_steps)
        
        # 植物状态统计
        plant_health = [s.plant_states for s in daily_steps]
        avg_plant_health = sum(p.health for step_plants in plant_health for p in step_plants) / (len(plant_health) * 5)
        
        # 决策统计
        water_actions = sum(len(s.student_decisions.get("water", [])) for s in daily_steps)
        fertilize_actions = sum(len(s.student_decisions.get("fertilize", [])) for s in daily_steps)
        
        daily_summary = {
            "day": day,
            "avg_temperature": avg_temp,
            "total_rainfall": total_rain,
            "avg_plant_health": avg_plant_health,
            "total_water_actions": water_actions,
            "total_fertilize_actions": fertilize_actions
        }
        
        self.daily_summaries.append(daily_summary)
        
    def get_simulation_summary(self) -> Dict:
        """获取模拟汇总"""
        runtime = time.time() - self.start_time
        
        return {
            "runtime_seconds": runtime,
            "total_steps": len(self.simulation_history),
            "daily_summaries": self.daily_summaries,
            "final_scores": [s.score for s in self.simulation_history[-8:]]  # 最后一天的得分
        }

class EvaluationEngine:
    """简化的评估引擎 - 只专注于生物量和健康度"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.eval_config = config["evaluation"]
        self.weights = self.eval_config["scoring_weights"]
        self.penalties = self.eval_config["penalties"]
        
        # 评估历史
        self.score_history = []
        self.penalty_log = []
        
    def calculate_score(self, step: int, plants: List[Plant], 
                       decisions: Dict, device_actions: Dict) -> float:
        """
        计算当前步骤的得分 - 简化为只包含生物量和健康度
        
        Args:
            step: 当前步数
            plants: 植物列表
            decisions: 学生决策
            device_actions: 设备操作记录
            
        Returns:
            当前得分
        """
        # 只保留两个基础得分组件
        biomass_score = self._calculate_biomass_score(plants)
        health_score = self._calculate_health_score(plants)
        
        # 加权总分 - 只用生物量和健康度
        base_score = (
            biomass_score * self.weights["total_biomass"] +
            health_score * self.weights["plant_health"]
        )
        
        # 计算惩罚 - 加强过量惩罚
        penalty = self._calculate_penalties_enhanced(plants, decisions, device_actions)
        
        # 最终得分
        final_score = max(0, base_score + penalty)
        
        # 记录得分
        score_record = {
            "step": step,
            "base_score": base_score,
            "penalty": penalty,
            "final_score": final_score,
            "water_actions": len(device_actions.get("water", [])),
            "fertilize_actions": len(device_actions.get("fertilize", [])),
            "components": {
                "biomass": biomass_score,
                "health": health_score
            }
        }
        
        self.score_history.append(score_record)
        
        return final_score
        
    def _calculate_biomass_score(self, plants: List[Plant]) -> float:
        """计算生物量得分"""
        total_biomass = sum(p.biomass for p in plants if p.is_alive())
        # 理论最大生物量约为50g (5植物 × 10g)
        return min(100.0, (total_biomass / 50.0) * 100.0)
        
    def _calculate_health_score(self, plants: List[Plant]) -> float:
        """计算健康度得分"""
        if not plants:
            return 0.0
        alive_plants = [p for p in plants if p.is_alive()]
        if not alive_plants:
            return 0.0
        avg_health = sum(p.health for p in alive_plants) / len(alive_plants)
        return avg_health
        
    def _calculate_penalties_enhanced(self, plants: List[Plant], decisions: Dict, 
                                    device_actions: Dict) -> float:
        """计算惩罚分数 - 加强过量操作惩罚"""
        penalty = 0
        
        # 植物死亡惩罚
        dead_plants = sum(1 for p in plants if not p.is_alive())
        penalty += dead_plants * self.penalties["plant_death"]
        
        # 过度浇水惩罚 - 加强惩罚
        water_actions = len(device_actions.get("water", []))
        if water_actions > 10:  # 每天最多1-2次浇水，8步×30天=240步，合理为30-60次
            penalty += (water_actions - 10) * self.penalties["overwatering"]
            
        # 过度施肥惩罚 - 加强惩罚
        fertilize_actions = len(device_actions.get("fertilize", []))
        if fertilize_actions > 15:  # 每2-3天施肥一次，合理为10-20次
            penalty += (fertilize_actions - 15) * self.penalties["overfertilizing"]
            
        # 过量浇水导致的直接植物损害
        for plant in plants:
            if hasattr(plant, 'soil_moisture') and plant.soil_moisture > 1.0:
                excess = plant.soil_moisture - 1.0
                penalty += excess * 50  # 过量部分×50的惩罚
                
        return penalty
        
    def get_evaluation_summary(self) -> Dict:
        """获取评估汇总"""
        if not self.score_history:
            return {}
            
        final_score = self.score_history[-1]
        
        return {
                "final_score": final_score["final_score"],
                "score_trend": [s["final_score"] for s in self.score_history[-20:]],
                "component_breakdown": final_score["components"],
                "total_penalties": sum(s["penalty"] for s in self.score_history),
                "best_score": max(s["final_score"] for s in self.score_history)
            }

class GardenSimulator:
    """简化的花园模拟器 - 专注于核心教学目标"""
    
    def __init__(self, config_path: str = "garden_env/config.json"):
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
            
        # # 设置随机种子
        # random.seed(self.config["simulation"]["random_seed"])
        
        # 初始化组件
        self.weather_sim = WeatherSimulator(config_path)
        self.device_manager = DeviceManager(config_path)
        self.soil_manager = SoilManager(self.config)
        self.state_manager = StateManager(self.config)
        self.evaluator = EvaluationEngine(self.config)
        
        # 初始化植物（5种植物各一株）
        self.plants = [
            create_plant("lettuce", 0),
            create_plant("spinach", 1),
            create_plant("radish", 2),
            create_plant("swiss_chard", 3),
            create_plant("nasturtium", 4)
        ]
        
        # 学生决策函数
        self.student_functions = {
            "should_water": lambda state: False,
            "should_fertilize": lambda state: False
        }
        
        # 模拟状态
        self.current_step = 0
        self.is_running = False
        self.step_results = []
        
    def register_student_functions(self, should_water: Callable, should_fertilize: Callable):
        """注册学生决策函数"""
        self.student_functions["should_water"] = should_water
        self.student_functions["should_fertilize"] = should_fertilize
        
    def run_simulation(self, total_steps: Optional[int] = None) -> Dict:
        """
        运行完整模拟
        
        Args:
            total_steps: 模拟总步数，默认使用配置文件中的值
            
        Returns:
            模拟结果摘要
        """
        if total_steps is None:
            total_steps = self.config["simulation"]["total_steps"]
            
        self.is_running = True
        self.step_results = []
        
        print(f"🌱 开始模拟：{total_steps}步 ({total_steps//8}天)")
        
        try:
            for step in range(total_steps):
                step_result = self.step_simulation(step)
                self.step_results.append(step_result)
                
                # # Debug output - formatted for readability
                # print(f"\n{'='*60}")
                # print(f"STEP {step_result.step} DEBUG")
                # print(f"{'='*60}")
                # print(f"Weather: T={step_result.weather.temperature:.1f}°C, Rain={step_result.weather.is_raining}")
                # print(f"Score: {step_result.score:.2f}")
                
                # print(f"\nSoil States:")
                # for i, soil in enumerate(step_result.soil_states):
                #     print(f"  Pot {i}: moisture={soil.moisture:.3f}, nutrients={soil.nutrients:.3f}")
                
                # print(f"\nPlant States:")
                # for i, plant in enumerate(step_result.plant_states):
                #     print(f"  Pot {i}: health={plant.health:.1f}, biomass={plant.biomass:.3f}, phenology={plant.phenology.value}")
                
                # print(f"\nSensor Readings:")
                # for pot_key, reading in step_result.sensor_readings.items():
                #     if pot_key.startswith('pot_'):
                #         moisture = reading.soil_moisture if reading.soil_moisture is not None else "None"
                #         nutrients = reading.nutrient_level if reading.nutrient_level is not None else "None"
                #         print(f"  {pot_key}: moisture={moisture}, nutrients={nutrients}")
                
                # print(f"\nStudent Decisions:")
                # print(f"  Water: {step_result.student_decisions.get('water', [])}")
                # print(f"  Fertilize: {step_result.student_decisions.get('fertilize', [])}")
                
                # print(f"\nDevice Actions:")
                # print(f"  Water: {step_result.device_actions.get('water', [])}")
                # print(f"  Fertilize: {step_result.device_actions.get('fertilize', [])}")
                
                # input("Press Enter to continue...")
                
                # 每天显示进度
                if step % 8 == 7:
                    day = step // 8 + 1
                    score = step_result.score
                    alive_plants = sum(1 for p in step_result.plant_states if p.health > 0)
                    print(f"第{day:2d}天 | 得分: {score:6.2f} | 存活植物: {alive_plants}/5| 温度: {step_result.weather.temperature:.1f}℃")
                    
        except KeyboardInterrupt:
            print("⚠️  模拟被用户中断")
            
        finally:
            self.is_running = False
            
        return self._generate_final_report()
        
    def step_simulation(self, step: int) -> StepResult:
        """
        执行单步模拟 - 简化流程
        
        Args:
            step: 当前步数
            
        Returns:
            单步模拟结果
        """
        self.current_step = step
        
        # ① 更新天气
        weather = self.weather_sim.step_weather(step)
        
        # ② 获取传感器读数（基于当前植物状态）
        sensor_readings = self.device_manager.get_sensor_readings(self.plants, asdict(weather), step)
        
        # ③ 学生决策 - 提供历史数据
        student_decisions = self._make_student_decisions_with_history(sensor_readings,weather)
        
        # ④ 执行设备操作 - 考虑设备故障
        device_actions_dict = self._execute_device_actions(student_decisions, step)
        
        # ⑤ 更新土壤状态（使用实际操作效果）
        self.soil_manager.update_soil(weather, device_actions_dict, self.plants)
        
        # ⑥ 更新植物状态 - 去除温度影响，加强过量惩罚
        plant_states = []
        for i, plant in enumerate(self.plants):
            soil_state = self.soil_manager.get_soil_state(i)
            # 更新植物的土壤状态
            plant.soil_moisture = soil_state.moisture
            plant.nutrient_level = soil_state.nutrients
            
            # 过量浇水/施肥的直接健康损害
            if soil_state.moisture > 1.0:
                excess_water = soil_state.moisture - 1.0
                plant.health -= excess_water * 20  # 过量水分直接损害健康
                
            if soil_state.nutrients > 1.2:
                excess_nutrients = soil_state.nutrients - 1.2
                plant.health -= excess_nutrients * 30  # 过量养分导致中毒
            
            plant_status = plant.update(
                weather_state=asdict(weather),
                soil_state={"moisture": soil_state.moisture, "nutrients": soil_state.nutrients},
                step=step
            )
            plant_states.append(plant_status)
            
        # ⑦ 计算得分 - 简化评分
        score = self.evaluator.calculate_score(step, self.plants, student_decisions, device_actions_dict)
        
        # ⑧ 记录状态
        step_result = StepResult(
            step=step,
            weather=weather,
            soil_states=self.soil_manager.get_all_soil_states(),
            plant_states=plant_states,
            sensor_readings=sensor_readings,
            student_decisions=student_decisions,
            device_actions=device_actions_dict,
            score=score
        )
        
        self.state_manager.log_step(step_result)
        
        return step_result
        
    def _make_student_decisions_with_history(self, sensor_readings: Optional[Dict],weather: WeatherState) -> Dict:
        """执行学生决策函数 - 提供历史数据"""
        decisions = {"water": [], "fertilize": []}
        
        if sensor_readings is None:
            return decisions
            
        # 为每个花盆调用决策函数
        for pot_id in range(5):
            pot_key = f"pot_{pot_id}"
            if pot_key in sensor_readings:
                # 构建包含历史数据的状态字典
                state = {
                    "pot_id": pot_id,
                    "step": self.current_step,
                    "day": self.current_step // 8,
                    "time_of_day": (self.current_step * 3) % 24,
                    "sensor_data": sensor_readings[pot_key],
                    "environment": sensor_readings.get("environment", {}),
                    "Rain": weather.is_raining,
                    "plant_type": self.plants[pot_id].__class__.__name__.lower(),
                    "plant_status": self.plants[pot_id].get_status(),
                    # 历史数据
                    "sensor_history": self.state_manager.get_sensor_history(pot_id),
                    "action_history": self.state_manager.get_action_history(pot_id)
                }
                
                # 调用学生函数
                try:
                    should_water = self.student_functions["should_water"](state)
                    should_fertilize = self.student_functions["should_fertilize"](state)
                    
                    if should_water:
                        decisions["water"].append({"pot_id": pot_id, "duration": 0.5})
                    if should_fertilize:
                        decisions["fertilize"].append({"pot_id": pot_id, "amount": 1.0})
                        
                except Exception as e:
                    print(f"⚠️  学生决策函数出错 (pot {pot_id}): {e}")
                    
        return decisions
        
    def _execute_device_actions(self, student_decisions: Dict, step: int) -> Dict:
        """执行设备操作 - 考虑设备故障"""
        device_actions = {"water": [], "fertilize": []}
        
        # 执行浇水操作
        for decision in student_decisions.get("water", []):
            pot_id = decision["pot_id"]
            duration = decision.get("duration", 0.5)
            
            # 通过设备管理器执行，可能因故障失败
            actual_effect = self.device_manager.execute_watering(pot_id, duration, step)
            
            device_actions["water"].append({
                "pot_id": pot_id,
                "step": step,
                "requested_duration": duration,
                "actual_effect": actual_effect,
                "success": actual_effect > 0
            })
            
        # 执行施肥操作
        for decision in student_decisions.get("fertilize", []):
            pot_id = decision["pot_id"]
            amount = decision.get("amount", 1.0)
            
            # 通过设备管理器执行，可能因故障失败
            actual_effect = self.device_manager.execute_fertilizing(pot_id, amount, step)
            
            device_actions["fertilize"].append({
                "pot_id": pot_id,
                "step": step,
                "requested_amount": amount,
                "actual_effect": actual_effect,
                "success": actual_effect > 0
            })
            
        return device_actions
        
    def _generate_final_report(self) -> Dict:
        """生成最终报告"""
        if not self.step_results:
            return {"error": "没有模拟数据"}
            
        final_step = self.step_results[-1]
        
        # 植物最终状态
        plant_summary = {}
        for i, plant_state in enumerate(final_step.plant_states):
            plant_types = ["lettuce", "spinach", "radish", "swiss_chard", "nasturtium"]
            plant_type = plant_types[i]
            
            plant_summary[plant_type] = {
                "health": plant_state.health,
                "biomass": plant_state.biomass,
                "phenology": plant_state.phenology.value,
                "days_alive": plant_state.days_alive,
                "is_alive": plant_state.health > 0,
                "soil_moisture": plant_state.soil_moisture,
                "nutrient_level": plant_state.nutrient_level,
                "stress_level": plant_state.stress_level
            }
            
        # 总体统计
        alive_count = sum(1 for p in final_step.plant_states if p.health > 0)
        total_biomass = sum(p.biomass for p in final_step.plant_states if p.health > 0)
        avg_health = sum(p.health for p in final_step.plant_states if p.health > 0) / max(1, alive_count)
        
        # 操作统计
        total_water_actions = sum(len(s.student_decisions.get("water", [])) for s in self.step_results)
        total_fertilize_actions = sum(len(s.student_decisions.get("fertilize", [])) for s in self.step_results)
        
        # 设备故障统计
        successful_water_actions = sum(len([a for a in s.device_actions.get("water", []) if a.get("success", False)]) for s in self.step_results)
        successful_fertilize_actions = sum(len([a for a in s.device_actions.get("fertilize", []) if a.get("success", False)]) for s in self.step_results)
        
        # 得分趋势
        scores = [s.score for s in self.step_results]
        
        return {
            "simulation_summary": {
                "total_steps": len(self.step_results),
                "total_days": len(self.step_results) // 8,
                "final_score": final_step.score,
                "max_score": max(scores) if scores else 0,
                "avg_score": sum(scores) / len(scores) if scores else 0
            },
            "plant_results": {
                "survival_rate": alive_count / 5,
                "total_biomass": total_biomass,
                "average_health": avg_health,
                "individual_plants": plant_summary
            },
            "student_performance": {
                "total_water_actions": total_water_actions,
                "total_fertilize_actions": total_fertilize_actions,
                "successful_water_actions": successful_water_actions,
                "successful_fertilize_actions": successful_fertilize_actions,
                "water_success_rate": successful_water_actions / max(1, total_water_actions),
                "fertilize_success_rate": successful_fertilize_actions / max(1, total_fertilize_actions),
                "water_frequency": total_water_actions / (len(self.step_results) / 8),  # 每天平均次数
                "fertilize_frequency": total_fertilize_actions / (len(self.step_results) / 8),
                "score_trend": scores[-40:] if len(scores) > 40 else scores  # 最后5天的得分
            },
            "evaluation_summary": self.evaluator.get_evaluation_summary(),
            "state_summary": self.state_manager.get_simulation_summary()
        }

    # 为了兼容性，保留一些接口方法
    def get_sensor_readings(self):
        """获取当前传感器读数"""
        if not self.is_running:
            return None
        weather_dict = asdict(self.weather_sim.get_current_weather()) if self.weather_sim.get_current_weather() else {}
        return self.device_manager.get_sensor_readings(self.plants, weather_dict, self.current_step)
    
    def get_weather_state(self):
        """获取当前天气状态"""
        return self.weather_sim.get_current_weather()
    
    def get_plant_states(self):
        """获取当前植物状态"""
        return [plant.get_status() for plant in self.plants]

# 兼容旧接口
class Simulator:
    """兼容类 - 保持与旧代码的兼容性"""
    
    def __init__(self, register_fn_dict: Dict[str, Callable]):
        self.garden_sim = GardenSimulator()
        self.garden_sim.register_student_functions(
            register_fn_dict["should_water"],
            register_fn_dict["should_fertilize"]
        )
        
    def run(self, steps: int = 240, render: bool = True):
        """运行模拟"""
        return self.garden_sim.run_simulation(steps)