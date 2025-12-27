import cProfile
import pstats
import io
import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'test_py'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build', 'Release'))

def run_test():
    """运行测试并生成性能报告"""
    print("="*60)
    print("Python Performance Profiling")
    print("="*60)
    print()
    
    # 创建 profiler
    profiler = cProfile.Profile()
    
    # 开始 profiling
    profiler.enable()
    
    # 导入并运行测试
    from concurrent_test import ConcurrentTester
    tester = ConcurrentTester()
    
    # 只运行一个快速测试
    tester. test_n_philosophers(5, 4, duration=30)
    
    # 停止 profiling
    profiler.disable()
    
    # 生成报告
    print("\n" + "="*60)
    print("Performance Report")
    print("="*60)
    
    # 创建统计对象
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    
    # 按累计时间排序
    ps.sort_stats('cumulative')
    ps.print_stats(20)  # 打印前 20 个
    
    report = s.getvalue()
    print(report)
    
    # 保存到文件
    os.makedirs('../logs', exist_ok=True)
    with open('../logs/python_profile_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\nReport saved to: logs/python_profile_report.txt")

if __name__ == "__main__":
    run_test()