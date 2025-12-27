"""
使用 Python 内置 profiling 工具
"""
import cProfile
import pstats
import io
import sys
import os

# 修复：添加正确的路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

# 添加路径
sys.path.insert(0, os.path.join(project_root, 'test_py'))
sys.path.insert(0, os.path.join(project_root, 'build', 'Release'))

print(f"Project root: {project_root}")
print(f"Python paths added:")
print(f"  - {os. path.join(project_root, 'test_py')}")
print(f"  - {os.path.join(project_root, 'build', 'Release')}")
print()

def run_test():
    """运行测试并生成性能报告"""
    print("="*60)
    print("Python Performance Profiling")
    print("="*60)
    print()
    
    # 验证模块可导入
    try:
        import sim_core
        print("✅ sim_core module found")
    except ImportError as e:
        print(f"❌ ERROR: Cannot import sim_core")
        print(f"   Make sure C++ module is compiled:")
        print(f"   cmake --build build --config Release")
        sys.exit(1)
    
    try:
        import concurrent_test
        print("✅ concurrent_test module found")
    except ImportError as e: 
        print(f"❌ ERROR: Cannot import concurrent_test")
        print(f"   {e}")
        sys.exit(1)
    
    print()
    
    # 创建 profiler
    profiler = cProfile.Profile()
    
    # 开始 profiling
    print("Starting profiler...")
    profiler.enable()
    
    # 导入并运行测试
    from concurrent_test import ConcurrentTester
    tester = ConcurrentTester()
    
    # 只运行一个快速测试
    print("Running test (5 philosophers, 30 seconds)...")
    tester.test_n_philosophers(5, 4, duration=30)
    
    # 停止 profiling
    profiler.disable()
    print("Profiler stopped")
    
    # 生成报告
    print("\n" + "="*60)
    print("Performance Report")
    print("="*60)
    print()
    
    # 创建统计对象
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    
    # 按累计时间排序
    ps.sort_stats('cumulative')
    ps.print_stats(20)  # 打印前 20 个
    
    report = s.getvalue()
    print(report)
    
    # 保存到文件
    logs_dir = os.path.join(project_root, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # 保存文本报告
    report_file = os.path.join(logs_dir, 'python_profile_report.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        # 写入完整报告（包括更多统计信息）
        f. write("="*70 + "\n")
        f.write("Python Performance Profiling Report\n")
        f.write("="*70 + "\n\n")
        
        # 基本信息
        ps2 = pstats.Stats(profiler, stream=f)
        
        # 1. 按累计时间
        f.write("\n" + "="*70 + "\n")
        f.write("Top 30 Functions by Cumulative Time\n")
        f.write("="*70 + "\n")
        ps2.sort_stats('cumulative')
        ps2.print_stats(30)
        
        # 2. 按自身时间
        f.write("\n" + "="*70 + "\n")
        f.write("Top 30 Functions by Total Time (excluding subcalls)\n")
        f.write("="*70 + "\n")
        ps2.sort_stats('tottime')
        ps2.print_stats(30)
        
        # 3. 按调用次数
        f.write("\n" + "="*70 + "\n")
        f.write("Top 30 Most Called Functions\n")
        f.write("="*70 + "\n")
        ps2.sort_stats('ncalls')
        ps2.print_stats(30)
    
    # 保存二进制格式（可用于 snakeviz）
    prof_file = os.path.join(logs_dir, 'python_profile.prof')
    profiler.dump_stats(prof_file)
    
    print("\n" + "="*60)
    print("Reports Saved")
    print("="*60)
    print(f"Text report:  {report_file}")
    print(f"Binary profile: {prof_file}")
    print()
    print("View with:")
    print(f"  type {report_file}")
    print(f"  snakeviz {prof_file}  (if snakeviz installed)")

if __name__ == "__main__": 
    run_test()