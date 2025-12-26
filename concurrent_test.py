"""
并发测试 - 验证多线程场景下的正确性
测试场景：
- 4个哲学家（最小并发）
- 6个哲学家（标准场景）  
- 8个哲学家（中等并发）
- 10个哲学家（高并发）
- 12个哲学家（压力边缘）
"""

import sys
import os
import time
import json
from datetime import datetime

sys.path.append('./build/Release')
import sim_core

class ConcurrentTester:
    def __init__(self):
        self.results = []
        
    def test_n_philosophers(self, n_phil, n_fork, duration=30):
        """测试N个哲学家并发场景"""
        print(f"\n{'='*60}")
        print(f"测试: {n_phil}哲学家 + {n_fork}叉子")
        print(f"{'='*60}")
        
        sim = sim_core.Simulation(n_phil, n_fork)
        sim.start()
        
        start_time = time.time()
        time.sleep(duration)
        
        events = sim.poll_events()
        has_deadlock = sim.detect_deadlock()
        states = sim.get_states()
        
        sim.stop()
        
        # 分析结果
        eat_events = [e for e in events if e.event_type == "STATE" and e.details == "EATING"]
        eat_counts = {}
        for e in eat_events:
            eat_counts[e.phil_id] = eat_counts. get(e.phil_id, 0) + 1
        
        # 饥饿检测
        starved = [pid for pid, count in eat_counts.items() if count == 0]
        
        result = {
            "config": f"{n_phil}P+{n_fork}F",
            "duration": duration,
            "total_meals": len(eat_events),
            "throughput": len(eat_events) / duration,
            "deadlock":  has_deadlock,
            "starved_philosophers": starved,
            "passed": not has_deadlock and len(starved) == 0
        }
        
        self.results.append(result)
        
        # 输出结果
        print(f"✓ 总进餐次数: {result['total_meals']}")
        print(f"✓ 吞吐量: {result['throughput']:.2f} 次/秒")
        print(f"✓ 死锁检测: {'❌ 有死锁' if has_deadlock else '✅ 无死锁'}")
        print(f"✓ 饥饿检测: {'❌ 有饥饿' if starved else '✅ 无饥饿'}")
        print(f"✓ 测试结果: {'✅ PASS' if result['passed'] else '❌ FAIL'}")
        
        return result
    
    def run_all_tests(self):
        """运行所有并发测试"""
        test_configs = [
            (4, 3),   # 最小并发
            (5, 4),   # 标准场景
            (6, 5),   
            (8, 7),   # 中等并发
            (10, 9),  # 高并发
            (12, 11), # 压力边缘
        ]
        
        print("\n" + "="*60)
        print("并发测试套件 - 开始")
        print("="*60)
        
        for n_phil, n_fork in test_configs:
            self.test_n_philosophers(n_phil, n_fork, duration=30)
        
        # 生成报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        os.makedirs('test_reports', exist_ok=True)
        
        report_path = 'test_reports/concurrent_test_report.md'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 并发测试报告\n\n")
            f.write(f"**测试时间**:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## 测试结果汇总\n\n")
            f.write("| 配置 | 总进餐 | 吞吐量(次/秒) | 死锁 | 饥饿 | 结果 |\n")
            f.write("|------|--------|--------------|------|------|------|\n")
            
            for r in self.results:
                deadlock_mark = "❌" if r['deadlock'] else "✅"
                starved_mark = "❌" if r['starved_philosophers'] else "✅"
                result_mark = "✅ PASS" if r['passed'] else "❌ FAIL"
                
                f.write(f"| {r['config']} | {r['total_meals']} | {r['throughput']:.2f} | "
                       f"{deadlock_mark} | {starved_mark} | {result_mark} |\n")
            
            f.write("\n## 详细分析\n\n")
            passed = sum(1 for r in self. results if r['passed'])
            f.write(f"- **通过率**: {passed}/{len(self. results)} ({passed/len(self.results)*100:.1f}%)\n")
            f.write(f"- **平均吞吐量**: {sum(r['throughput'] for r in self.results)/len(self.results):.2f} 次/秒\n")
            
        print(f"\n✅ 报告已保存:  {report_path}")

if __name__ == "__main__": 
    tester = ConcurrentTester()
    tester.run_all_tests()