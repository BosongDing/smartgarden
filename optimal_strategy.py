#!/usr/bin/env python3
"""
Optimal Strategy - Uses theoretical thresholds from config.json
This function should theoretically achieve maximum harvest under normal conditions
"""

import json
import os

# Load config data
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'garden_env', 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

# Global config (loaded once)
CONFIG = load_config()

def optimal_should_water(state):
    """
    Optimal watering decision using theoretical thresholds from config.json
    
    Args:
        state: 状态字典，包含传感器数据和植物状态
        
    Returns:
        bool: 是否应该浇水
    """
    # print(state)
    # input()
    pot_id = state['pot_id']
    sensor_data = state['sensor_data']
    plant_status = state['plant_status']
    
    # Handle sensor failures/errors
    if sensor_data.soil_moisture is None:
        return False  # Can't make decision without moisture reading
    
    # Get plant type and its optimal threshold
    plant_type = state['plant_type']  # This is already lowercase class name
    
    # Map plant names to config keys
    plant_config_map = {
        'lettuce': 'lettuce',
        'spinach': 'spinach', 
        'radish': 'radish',
        'swisschard': 'swiss_chard',  # Note: class name is 'swisschard' but config key is 'swiss_chard'
        'nasturtium': 'nasturtium'
    }
    
    config_key = plant_config_map.get(plant_type)
    if not config_key:
        # Fallback for unknown plants
        return sensor_data.soil_moisture < 0.35
    
    # Get the optimal threshold from config
    optimal_threshold = CONFIG['plants'][config_key]['soil_threshold']
    
    # Special case for Nasturtium - check if it's in flowering stage with higher water needs
    if plant_type == 'nasturtium' and plant_status:
        if hasattr(plant_status, 'days_alive') and plant_status.days_alive >= CONFIG['plants']['nasturtium']['flower_stage_day']:
            optimal_threshold = CONFIG['plants']['nasturtium']['flower_stage_soil_threshold']
    
    # Only water if plant is alive and below optimal threshold
    if plant_status and plant_status.health <= 0:
        return False
    # find the last water action
    # last_water_action = [action for action in state["action_history"] if action["water"] > 0][-1]
    if state['Rain'] and abs(state["sensor_data"].soil_moisture - state["sensor_history"][-1]["soil_moisture"]) > 0.05:
        return False
    # Use the exact optimal threshold from config
    return sensor_data.soil_moisture < optimal_threshold

def optimal_should_fertilize(state):
    """
    Optimal fertilization decision using theoretical thresholds from config.json
    
    Args:
        state: 状态字典，包含传感器数据和植物状态
        
    Returns:
        bool: 是否应该施肥
    """
    pot_id = state['pot_id']
    sensor_data = state['sensor_data']
    plant_status = state['plant_status']
    
    # Handle sensor failures/errors
    if sensor_data.nutrient_level is None:
        return False  # Can't make decision without nutrient reading
    
    # Get plant type and its optimal threshold
    plant_type = state['plant_type']  # This is already lowercase class name
    
    # Map plant names to config keys
    plant_config_map = {
        'lettuce': 'lettuce',
        'spinach': 'spinach',
        'radish': 'radish', 
        'swisschard': 'swiss_chard',  # Note: class name is 'swisschard' but config key is 'swiss_chard'
        'nasturtium': 'nasturtium'
    }
    
    config_key = plant_config_map.get(plant_type)
    if not config_key:
        # Fallback for unknown plants
        return sensor_data.nutrient_level < 0.30
    
    # Get the optimal threshold from config
    optimal_threshold = CONFIG['plants'][config_key]['nutrient_threshold']
    
    # Only fertilize if plant is alive and below optimal threshold
    if plant_status and plant_status.health <= 0:
        return False
    # last_fertilize_action = [action for action in state["action_history"] if action["fertilize"] > 0][-1]
    if state['Rain'] and abs(state["sensor_data"].nutrient_level - state["sensor_history"][-1]["nutrient_level"]) > 0.05 :
        return False
    
    # Use the exact optimal threshold from config
    return sensor_data.nutrient_level < optimal_threshold

# Export functions with the expected names for the loader
should_water = optimal_should_water
should_fertilize = optimal_should_fertilize

# For testing purposes
if __name__ == "__main__":
    print("=== Optimal Strategy Configuration ===")
    print("Plant optimal thresholds:")
    for plant_name, plant_config in CONFIG['plants'].items():
        soil_thresh = plant_config['soil_threshold']
        nutrient_thresh = plant_config['nutrient_threshold']
        print(f"  {plant_name}: soil={soil_thresh}, nutrient={nutrient_thresh}")
        if plant_name == 'nasturtium':
            flower_thresh = plant_config.get('flower_stage_soil_threshold', soil_thresh)
            flower_day = plant_config.get('flower_stage_day', 20)
            print(f"    (flower stage: soil={flower_thresh} after day {flower_day})")
    print("\nThis strategy uses the exact theoretical optimal thresholds from config.json") 