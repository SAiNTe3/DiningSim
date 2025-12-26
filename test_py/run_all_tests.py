"""
测试套件主入口 - 运行所有测试并生成综合报告
"""

import sys
import os
import time
from datetime import datetime

# 确保可以导入测试模块
sys.path. insert(0, os.path.dirname(__file__))

def run_all_tests():
    print("\n" + "="*70)
    print(" " * 15 + "哲学家就餐问题 - 完整测试套件")
    print("="*70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    test_results = []
    
    # 1. 并发测试
    print("\n[1/4] 运行并发测试...")
    try:
        from concurrent_test import ConcurrentTester
        tester1 = ConcurrentTester()
        tester1.run_all_tests()
        test_results.append(("并发测试", "✅ 通过", len(tester1.results)))
    except Exception as e:
        print(f"❌ 并发测试失败: {e}")
        test_results.append(("并发测试", "❌ 失败", 0))
    
    # 2. 压力测试
    import traceback
    print("\n[2/4] 运行压力测试（这将需要5分钟）...")
    try:
        from stress_test import StressTester
        tester2 = StressTester()
        tester2.stress_test_high_concurrency(n_phil=15, duration=300)
        test_results. append(("压力测试", "✅ 通过", 1))
    except Exception as e:
        print(f"❌ 压力测试失败: {e}")
        print("\n详细错误信息：")
        traceback.print_exc()
        test_results.append(("压力测试", "❌ 失败", 0))
    
    # 3. 边界测试
    print("\n[3/4] 运行边界测试...")
    try:
        from boundary_test import BoundaryTester
        tester3 = BoundaryTester()
        tester3.run_all_tests()
        test_results.append(("边界测试", "✅ 通过", len(tester3.results)))
    except Exception as e:
        print(f"❌ 边界测试失败: {e}")
        test_results. append(("边界测试", "❌ 失败", 0))
    
    # 4. 生成综合报告
    print("\n[4/4] 生成综合报告...")
    generate_summary_report(test_results)
    
    print("\n" + "="*70)
    print("所有测试完成！")
    print("="*70)
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n查看报告:  test_reports/summary_report.md\n")

def generate_summary_report(test_results):
    """生成综合测试报告"""
    os.makedirs('test_reports', exist_ok=True)
    
    report_path = 'test_reports/summary_report.md'
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 测试套件综合报告\n\n")
        f.write(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 测试执行概况\n\n")
        f.write("| 测试类型 | 状态 | 测试用例数 |\n")
        f.write("|----------|------|------------|\n")
        
        for name, status, count in test_results:
            f.write(f"| {name} | {status} | {count} |\n")
        
        f. write("\n## 详细报告链接\n\n")
        f.write("- [并发测试报告](concurrent_test_report.md)\n")
        f.write("- [压力测试报告](stress_test_report.md)\n")
        f.write("- [边界测试报告](boundary_test_report.md)\n")
        
        f.write("\n## 总结\n\n")
        passed = sum(1 for _, status, _ in test_results if "✅" in status)
        total = len(test_results)
        
        f.write(f"- **测试套件通过率**: {passed}/{total} ({passed/total*100:.1f}%)\n")
        
        if passed == total: 
            f.write("\n✅ **所有测试通过！** 系统满足所有并发、压力和边界测试要求。\n")
        else:
            f.write("\n⚠️ **部分测试失败** 请检查详细报告。\n")
    
    print(f"✅ 综合报告已保存: {report_path}")

if __name__ == "__main__":
    run_all_tests()