
import random
import sys
import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from importlib import import_module
import traceback

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from garden_env.simulator import GardenSimulator, Simulator

# 全局变量 - 用于notebook集成
_registered_functions = {
    "should_water": None,
    "should_fertilize": None
}

def register_student_functions(should_water: Callable, should_fertilize: Callable):
    """
    注册学生决策函数（供notebook使用）
    
    Args:
        should_water: 浇水决策函数
        should_fertilize: 施肥决策函数
    
    Example:
        def should_water(state):
            return state["sensor_data"].soil_moisture < 0.3
            
        def should_fertilize(state):
            return state["sensor_data"].nutrient_level < 0.2
            
        register_student_functions(should_water, should_fertilize)
    """
    global _registered_functions
    _registered_functions["should_water"] = should_water
    _registered_functions["should_fertilize"] = should_fertilize
    print("✅ 学生决策函数已注册")
    print(f"   - 浇水函数: {should_water.__name__}")
    print(f"   - 施肥函数: {should_fertilize.__name__}")

def load_student_functions_from_file(file_path: str) -> Dict[str, Callable]:
    """
    从文件加载学生决策函数
    
    Args:
        file_path: 学生代码文件路径
        
    Returns:
        包含决策函数的字典
    """
    try:
        # 动态导入学生代码
        spec = import_module(file_path.replace('.py', '').replace('/', '.'))
        
        functions = {}
        if hasattr(spec, 'should_water'):
            functions["should_water"] = spec.should_water
        if hasattr(spec, 'should_fertilize'):
            functions["should_fertilize"] = spec.should_fertilize
            
        return functions
        
    except Exception as e:
        print(f"❌ 无法加载学生代码文件 {file_path}: {e}")
        return {}

def load_optimal_strategy() -> Dict[str, Callable]:
    """
    加载优化策略函数
    
    Returns:
        优化策略函数字典
    """
    try:
        import optimal_strategy
        return {
            "should_water": optimal_strategy.should_water,
            "should_fertilize": optimal_strategy.should_fertilize
        }
    except Exception as e:
        print(f"❌ 无法加载优化策略: {e}")
        return {}

def display_simulation_header(args: argparse.Namespace):
    """显示模拟开始信息"""
    print("\n" + "="*60)
    print("🌱 智慧花园模拟器 v1.0")
    print("="*60)
    print(f"📊 模拟配置：")
    print(f"   • 总步数: {args.steps} 步 ({args.steps//8} 天)")
    print(f"   • 随机种子: {args.seed}")
    print(f"   • 配置文件: {args.config}")
    print(f"   • 快速模式: {'是' if args.fast else '否'}")
    if args.output:
        print(f"   • 结果输出: {args.output}")
    print("\n🌿 植物配置：")
    print("   • 生菜 (Lettuce) - 花盆 0")
    print("   • 菠菜 (Spinach) - 花盆 1") 
    print("   • 萝卜 (Radish) - 花盆 2")
    print("   • 甜菜 (Swiss Chard) - 花盆 3")
    print("   • 旱金莲 (Nasturtium) - 花盆 4")
    print("-"*60)

def display_progress(step: int, total_steps: int, plants_status: List[Any], score: float):
    """显示进度信息"""
    day = step // 8 + 1
    progress = (step + 1) / total_steps * 100
    
    # 植物状态统计
    alive_count = sum(1 for p in plants_status if p.health > 0)
    avg_health = sum(p.health for p in plants_status) / len(plants_status)
    avg_biomass = sum(p.biomass for p in plants_status) / len(plants_status)
    
    # 进度条
    bar_length = 30
    filled_length = int(bar_length * progress / 100)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    
    print(f"\r📅 第{day:2d}天 [{bar}] {progress:5.1f}% | "
          f"存活: {alive_count}/5 | 健康: {avg_health:4.1f} | "
          f"生物量: {avg_biomass:4.1f}g | 得分: {score:5.1f}", end="")

def display_final_results(results: Dict):
    """显示最终结果"""
    print("\n\n" + "="*60)
    print("📊 模拟完成 - 最终结果")
    print("="*60)
    
    # 基本统计
    sim_summary = results.get("simulation_summary", {})
    eval_summary = results.get("evaluation_summary", {})
    plant_results = results.get("plant_results", {})
    plant_summary = plant_results.get("individual_plants", {})
    
    print(f"🎯 最终得分: {eval_summary.get('final_score', 0):.2f}")
    print(f"⏱️  模拟时间: {sim_summary.get('simulation_time', 0):.2f} 秒")
    print(f"🌱 植物存活: {int(plant_results.get('survival_rate', 0) * 5)}/5")
    
    # 植物详情
    print("\n🌿 植物状态详情:")
    plant_names = {
        "lettuce": "生菜",
        "spinach": "菠菜", 
        "radish": "萝卜",
        "swiss_chard": "甜菜",
        "nasturtium": "旱金莲"
    }
    
    for plant_type, plant_data in plant_summary.items():
        name = plant_names.get(plant_type, plant_type)
        status = "✅ 存活" if plant_data.get("is_alive", False) else "❌ 死亡"
        health = plant_data.get("health", 0)
        biomass = plant_data.get("biomass", 0)
        phenology = plant_data.get("phenology", "unknown")
        
        print(f"   • {name:8s} | {status} | 健康: {health:5.1f} | "
              f"生物量: {biomass:5.1f}g | 阶段: {phenology}")

    # 学生表现统计
    student_perf = results.get("student_performance", {})
    if student_perf:
        print("\n📈 操作统计:")
        print(f"   • 浇水次数: {student_perf.get('total_water_actions', 0)}")
        print(f"   • 施肥次数: {student_perf.get('total_fertilize_actions', 0)}")
        print(f"   • 浇水成功率: {student_perf.get('water_success_rate', 0)*100:.1f}%")
        print(f"   • 施肥成功率: {student_perf.get('fertilize_success_rate', 0)*100:.1f}%")
    
    # 评估详情
    if eval_summary:
        print("\n🏆 评估详情:")
        components = eval_summary.get("component_breakdown", {})
        print(f"   • 生物量得分: {components.get('biomass', 0):.1f}")
        print(f"   • 健康得分: {components.get('health', 0):.1f}")
        print(f"   • 存活得分: {components.get('survival', 0):.1f}")
        print(f"   • 效率得分: {components.get('efficiency', 0):.1f}")
        print(f"   • 总惩罚: {eval_summary.get('total_penalties', 0):.1f}")
        print(f"   • 最高得分: {eval_summary.get('best_score', 0):.1f}")

def save_results(results: Dict, output_path: str):
    """保存结果到文件"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n💾 结果已保存到: {output_path}")
    except Exception as e:
        print(f"\n❌ 保存结果失败: {e}")

def run_simulation_with_functions(functions: Dict[str, Callable], args: argparse.Namespace) -> Dict:
    """
    使用指定的决策函数运行模拟
    
    Args:
        functions: 决策函数字典
        args: 命令行参数
        
    Returns:
        模拟结果字典
    """
    try:
        # 创建模拟器
        simulator = GardenSimulator(args.config)
        
        # 注册学生函数
        simulator.register_student_functions(
            functions["should_water"],
            functions["should_fertilize"]
        )
        
        # 运行模拟
        results = simulator.run_simulation(
            total_steps=args.steps
        )
        
        return results
        
    except Exception as e:
        print(f"\n❌ 模拟运行失败: {e}")
        if args.debug:
            traceback.print_exc()
        return {}

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="智慧花园模拟器 - 测试你的植物管理策略",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  python run_simulation.py                          # 使用优化策略
  python run_simulation.py --steps 120 --seed 123  # 自定义参数
  python run_simulation.py --fast --output results.json  # 快速模式并保存结果
  python run_simulation.py --student-code student_code/decision_stub.py     # 加载学生代码
        """
    )
    
    parser.add_argument("--steps", type=int, default=240,
                       help="模拟步数 (默认: 240, 即30天)")
    parser.add_argument("--seed", type=int, default=42,
                       help="随机种子 (默认: 42)")
    parser.add_argument("--config", type=str, default="garden_env/config.json",
                       help="配置文件路径 (默认: garden_env/config.json)")
    parser.add_argument("--fast", action="store_true",
                       help="快速模式 - 不显示详细进度")
    parser.add_argument("--output", type=str,
                       help="结果输出文件路径 (JSON格式)")
    parser.add_argument("--student-code", type=str,
                       help="学生代码文件路径")
    parser.add_argument("--debug", action="store_true",
                       help="调试模式 - 显示详细错误信息")
    
    args = parser.parse_args()
    
    # 检查配置文件
    if not Path(args.config).exists():
        print(f"❌ 配置文件不存在: {args.config}")
        return 1
    
    # 显示模拟信息
    display_simulation_header(args)
    
    # 确定使用的决策函数 - 新的优先级：学生代码 > 全局注册 > 优化策略
    functions = {}
    
    if args.student_code:
        print(f"📝 加载学生代码: {args.student_code}")
        functions = load_student_functions_from_file(args.student_code)
    elif _registered_functions["should_water"] is not None:
        print("📝 使用已注册的学生函数")
        functions = _registered_functions.copy()
    else:
        print("📝 使用优化策略")
        functions = load_optimal_strategy()
    
    # 验证函数
    if not functions.get("should_water") or not functions.get("should_fertilize"):
        print("❌ 决策函数不完整，回退到优化策略")
        functions = load_optimal_strategy()
        
        if not functions.get("should_water") or not functions.get("should_fertilize"):
            print("❌ 无法加载任何有效的决策函数")
            return 1
    
    print(f"   • 浇水函数: {functions['should_water'].__name__}")
    print(f"   • 施肥函数: {functions['should_fertilize'].__name__}")
    
    # 运行模拟
    print("\n🚀 开始模拟...")
    start_time = time.time()
    
    results = run_simulation_with_functions(functions, args)
    
    end_time = time.time()
    
    if results:
        # 显示结果
        display_final_results(results)
        
        # 保存结果
        if args.output:
            save_results(results, args.output)
            
        print(f"\n⏱️  总运行时间: {end_time - start_time:.2f} 秒")
        print("🎉 模拟完成！")
        
        return 0
    else:
        print("\n❌ 模拟失败")
        return 1

# 保持向后兼容
if __name__ == "__main__":
    sys.exit(main())