"""
分析 cProfile 生成的性能报告
"""
import pstats
import sys

def analyze_profile(profile_file):
    """详细分析 profile 文件"""
    
    print("="*70)
    print(" "*20 + "cProfile Analysis Report")
    print("="*70)
    print()
    
    # 加载统计数据
    stats = pstats.Stats(profile_file)
    
    # ===== 1. 按累计时间排序 (找出整体最耗时的函数) =====
    print("\n" + "="*70)
    print("Top 20 Functions by Cumulative Time (包含子函数)")
    print("="*70)
    stats.sort_stats('cumulative')
    stats.print_stats(20)
    
    # ===== 2. 按自身时间排序 (找出自身最耗时的函数) =====
    print("\n" + "="*70)
    print("Top 20 Functions by Total Time (不含子函数)")
    print("="*70)
    stats.sort_stats('tottime')
    stats.print_stats(20)
    
    # ===== 3. 按调用次数排序 (找出高频调用) =====
    print("\n" + "="*70)
    print("Top 20 Most Called Functions")
    print("="*70)
    stats.sort_stats('ncalls')
    stats.print_stats(20)
    
    # ===== 4. 查看特定函数的调用者 =====
    print("\n" + "="*70)
    print("Callers of poll_events (谁调用了 poll_events)")
    print("="*70)
    stats.print_callers('poll_events')
    
    # ===== 5. 查看特定函数调用了谁 =====
    print("\n" + "="*70)
    print("Callees of test_n_philosophers (test_n_philosophers 调用了谁)")
    print("="*70)
    stats.print_callees('test_n_philosophers')
    
    # ===== 6. 统计摘要 =====
    print("\n" + "="*70)
    print("Statistics Summary")
    print("="*70)
    stats.print_stats()
    
    total_time = stats.total_tt
    print(f"\nTotal execution time: {total_time:.3f} seconds")
    
    # 分析函数占比
    stats.sort_stats('tottime')
    stats_list = stats.stats
    
    print("\nTime Distribution (Top 5):")
    count = 0
    for func, (cc, nc, tt, ct, callers) in sorted(stats_list.items(), 
                                                    key=lambda x: x[1][2], 
                                                    reverse=True):
        if count >= 5:
            break
        percent = (tt / total_time) * 100
        print(f"  {func}: {tt:.3f}s ({percent:.1f}%)")
        count += 1

if __name__ == "__main__":
    if len(sys.argv) > 1:
        profile_file = sys.argv[1]
    else:
        profile_file = '../logs/python_profile.prof'
    
    analyze_profile(profile_file)