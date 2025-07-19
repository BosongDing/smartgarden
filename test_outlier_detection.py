#!/usr/bin/env python3
"""
Test script to demonstrate outlier detection capabilities in the optimal strategy.
This shows how the enhanced strategy handles various sensor failures and errors.
"""

import sys
import os
from dataclasses import dataclass
from typing import Optional

# Add current directory to path to import optimal strategy
sys.path.append(os.path.dirname(__file__))

from optimal_strategy import detect_sensor_outliers, get_fallback_sensor_values, optimal_should_water, optimal_should_fertilize

@dataclass
class MockSensorReading:
    """Mock sensor reading for testing"""
    soil_moisture: Optional[float] = None
    nutrient_level: Optional[float] = None
    temperature: Optional[float] = None
    timestamp: int = 0

@dataclass 
class MockPlantStatus:
    """Mock plant status for testing"""
    health: float = 100.0
    biomass: float = 0.2
    phenology = None
    days_alive: int = 5

class MockPhenology:
    value = 'vegetative'

def test_outlier_detection():
    """Test various sensor failure scenarios"""
    
    print("=== Testing Outlier Detection ===\n")
    
    # Normal sensor history (baseline)
    normal_history = [
        {'step': 1, 'soil_moisture': 0.45, 'nutrient_level': 0.40, 'temperature': 18.0},
        {'step': 2, 'soil_moisture': 0.42, 'nutrient_level': 0.38, 'temperature': 19.0},
        {'step': 3, 'soil_moisture': 0.39, 'nutrient_level': 0.36, 'temperature': 18.5},
    ]
    
    # Test cases for different sensor failures
    test_cases = [
        {
            'name': 'Normal Reading',
            'sensor_data': MockSensorReading(soil_moisture=0.35, nutrient_level=0.33),
            'description': 'Sensor readings appear normal and consistent with history'
        },
        {
            'name': 'Step 0 Failure (Extreme Spike)',
            'sensor_data': MockSensorReading(soil_moisture=0.95, nutrient_level=0.05),
            'description': 'Exactly like the failure we saw in step 0 - extreme values'
        },
        {
            'name': 'Missing Data (None)',
            'sensor_data': MockSensorReading(soil_moisture=None, nutrient_level=0.4),
            'description': 'Sensor communication failure - missing moisture data'
        },
        {
            'name': 'Inconsistent Pattern',
            'sensor_data': MockSensorReading(soil_moisture=0.85, nutrient_level=0.08),
            'description': 'Physically inconsistent: very high moisture + very low nutrients'
        },
        {
            'name': 'Stuck Sensor',
            'sensor_data': MockSensorReading(soil_moisture=0.5, nutrient_level=0.5),
            'description': 'Sensor returning same values repeatedly'
        },
        {
            'name': 'Sudden Change',
            'sensor_data': MockSensorReading(soil_moisture=0.02, nutrient_level=0.9),
            'description': 'Large deviation from recent historical average'
        },
        {
            'name': 'Extreme Low Values',
            'sensor_data': MockSensorReading(soil_moisture=0.02, nutrient_level=0.03),
            'description': 'Both values at extreme low end'
        }
    ]
    
    # Create stuck sensor history for stuck sensor test
    stuck_history = [
        {'step': 1, 'soil_moisture': 0.5, 'nutrient_level': 0.5, 'temperature': 18.0},
        {'step': 2, 'soil_moisture': 0.5, 'nutrient_level': 0.5, 'temperature': 19.0},
        {'step': 3, 'soil_moisture': 0.5, 'nutrient_level': 0.5, 'temperature': 18.5},
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"{i+1}. {test_case['name']}")
        print(f"   Description: {test_case['description']}")
        
        # Use stuck history for stuck sensor test, normal history otherwise
        history = stuck_history if 'Stuck' in test_case['name'] else normal_history
        
        # Detect outliers
        outlier_result = detect_sensor_outliers(
            sensor_data=test_case['sensor_data'],
            sensor_history=history,
            pot_id=0,
            step=4
        )
        
        # Display results
        moisture = test_case['sensor_data'].soil_moisture
        nutrients = test_case['sensor_data'].nutrient_level
        print(f"   Sensor Reading: moisture={moisture}, nutrients={nutrients}")
        print(f"   Is Outlier: {outlier_result['is_outlier']}")
        
        if outlier_result['is_outlier']:
            print(f"   Outlier Type: {outlier_result['outlier_type']}")
            print(f"   Confidence: {outlier_result['confidence']:.1f}")
            print(f"   Recommended Action: {outlier_result['recommended_action']}")
        else:
            print(f"   Status: Sensor reading appears reliable")
        
        print()

def test_decision_making():
    """Test how decisions are made with various sensor scenarios"""
    
    print("=== Testing Decision Making with Outliers ===\n")
    
    plant_status = MockPlantStatus()
    plant_status.phenology = MockPhenology()
    
    # Normal history
    normal_history = [
        {'step': 1, 'soil_moisture': 0.45, 'nutrient_level': 0.40, 'temperature': 18.0},
        {'step': 2, 'soil_moisture': 0.42, 'nutrient_level': 0.38, 'temperature': 19.0},
        {'step': 3, 'soil_moisture': 0.39, 'nutrient_level': 0.36, 'temperature': 18.5},
    ]
    
    decision_tests = [
        {
            'name': 'Normal Lettuce (should water)',
            'sensor_data': MockSensorReading(soil_moisture=0.30, nutrient_level=0.40),
            'plant_type': 'lettuce',
            'expected': 'Should water (below 0.38 threshold)'
        },
        {
            'name': 'Extreme Spike (Step 0 scenario)',
            'sensor_data': MockSensorReading(soil_moisture=0.95, nutrient_level=0.05),
            'plant_type': 'lettuce',
            'expected': 'Should use fallback/historical data'
        },
        {
            'name': 'Missing moisture data',
            'sensor_data': MockSensorReading(soil_moisture=None, nutrient_level=0.30),
            'plant_type': 'spinach',
            'expected': 'Should use historical average'
        },
        {
            'name': 'Inconsistent readings',
            'sensor_data': MockSensorReading(soil_moisture=0.85, nutrient_level=0.08),
            'plant_type': 'radish',
            'expected': 'Should use fallback values'
        }
    ]
    
    for i, test in enumerate(decision_tests):
        print(f"{i+1}. {test['name']}")
        
        # Create state object for decision functions
        state = {
            'pot_id': 0,
            'step': 4,
            'sensor_data': test['sensor_data'],
            'plant_type': test['plant_type'],
            'plant_status': plant_status,
            'sensor_history': normal_history
        }
        
        # Test watering decision
        should_water = optimal_should_water(state)
        should_fertilize = optimal_should_fertilize(state)
        
        moisture = test['sensor_data'].soil_moisture
        nutrients = test['sensor_data'].nutrient_level
        
        print(f"   Sensor: moisture={moisture}, nutrients={nutrients}")
        print(f"   Plant: {test['plant_type']}")
        print(f"   Decision: Water={should_water}, Fertilize={should_fertilize}")
        print(f"   Expected: {test['expected']}")
        
        # Show what fallback values would be used
        if moisture is None or nutrients is None or moisture >= 0.95 or moisture <= 0.05:
            fallback = get_fallback_sensor_values(
                test['plant_type'], plant_status, 4, normal_history
            )
            print(f"   Fallback values: moisture={fallback['soil_moisture']:.2f}, nutrients={fallback['nutrient_level']:.2f}")
        
        print()

def demonstrate_step0_scenario():
    """Specifically demonstrate how the enhanced strategy handles the Step 0 scenario"""
    
    print("=== Step 0 Scenario Analysis ===\n")
    
    print("Original Step 0 Problem:")
    print("  Actual soil state: moisture=0.480, nutrients=0.485")
    print("  Sensor reading:    moisture=0.95, nutrients=0.05")
    print("  Issue: Extreme sensor spike making decisions impossible\n")
    
    # Simulate the step 0 scenario
    step0_sensor = MockSensorReading(soil_moisture=0.95, nutrient_level=0.05)
    plant_status = MockPlantStatus()
    plant_status.phenology = MockPhenology()
    
    # Since it's step 0, there's no history yet
    empty_history = []
    
    state = {
        'pot_id': 4,  # pot_4 had the failure
        'step': 0,
        'sensor_data': step0_sensor,
        'plant_type': 'nasturtium',  # Assume pot 4 is nasturtium
        'plant_status': plant_status,
        'sensor_history': empty_history
    }
    
    print("Enhanced Strategy Response:")
    
    # Analyze the outlier
    outlier_result = detect_sensor_outliers(step0_sensor, empty_history, 4, 0)
    print(f"  Outlier Detection: {outlier_result['outlier_type']} (confidence: {outlier_result['confidence']:.1f})")
    print(f"  Recommended Action: {outlier_result['recommended_action']}")
    
    # Make decisions
    should_water = optimal_should_water(state)
    should_fertilize = optimal_should_fertilize(state)
    print(f"  Decisions: Water={should_water}, Fertilize={should_fertilize}")
    
    # Show fallback values
    fallback = get_fallback_sensor_values('nasturtium', plant_status, 0, empty_history)
    print(f"  Fallback values used: moisture={fallback['soil_moisture']:.2f}, nutrients={fallback['nutrient_level']:.2f}")
    
    print("\nResult: The enhanced strategy detects the extreme readings as outliers")
    print("        and uses conservative fallback values instead of trusting the")
    print("        obviously faulty sensor data. This prevents wrong decisions!")

if __name__ == "__main__":
    test_outlier_detection()
    test_decision_making()
    demonstrate_step0_scenario() 