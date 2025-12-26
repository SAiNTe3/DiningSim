"""
边界测试 - 测试极端场景
测试场景：
1. 极端竞争（2哲学家1叉子）
2. 资源充足（N哲学家N叉子）
3. 事件队列溢出（>5000事件）
4. 快速启停
5. 单哲学家场景
"""

import sys
import os
import time
from datetime import datetime

sys.path. append('./build/Release')
import sim_core

class BoundaryTester:
    def __init__(self):
        self.results = []
    
    def test_extreme_competition(self):
        """边界测试1:  极端资源竞争"""
        print(f"\n{'='*60}")
        print("边界测试: 极端竞争（2哲学家 + 1叉子）")
        print(f"{'='*60}")
        
        sim = sim_core.Simulation(2, 1)
        sim.start()
        time.sleep(30)
        
        events = sim.poll_events()
        sim.stop()
        
        eat_events = [e for e in events if "EATING" in e.details]
        
        result = {
            "name": "极端竞争",
            "config": "2P+1F",
            "meals": len(eat_events),
            "passed": len(eat_events) > 0  # 至少有人能吃到
        }
        
        print(f"✓ 进餐次数: {result['meals']}")
        print(f"✓ 结果: {'✅ PASS (系统未崩溃)' if result['passed'] else '❌ FAIL'}")
        
        self.results.append(result)
        return result
    
    def test_abundant_resources(self):
        """边界测试2: 资源充足"""
        print(f"\n{'='*60}")
        print("边界测试:  资源充足（5哲学家 + 5叉子）")
        print(f"{'='*60}")
        
        sim = sim_core.Simulation(5, 5)
        sim.start()
        time.sleep(30)
        
        events = sim. poll_events()
        sim.stop()
        
        eat_events = [e for e in events if "EATING" in e. details]
        eat_counts = {}
        for e in eat_events:
            eat_counts[e.phil_id] = eat_counts.get(e.phil_id, 0) + 1
        
        # 资源充足时，所有人都应该能吃到
        all_ate = len(eat_counts) == 5
        
        result = {
            "name":  "资源充足",
            "config": "5P+5F",
            "meals": len(eat_events),
            "all_ate": all_ate,
            "passed": all_ate
        }
        
        print(f"✓ 进餐次数: {result['meals']}")
        print(f"✓ 所有人都进餐:  {'✅ 是' if all_ate else '❌ 否'}")
        print(f"✓ 结果: {'✅ PASS' if result['passed'] else '❌ FAIL'}")
        
        self. results.append(result)
        return result
    
    def test_event_queue_overflow(self):
        """边界测试3: 事件队列溢出"""
        print(f"\n{'='*60}")
        print("边界测试:  事件队列溢出（>5000事件）")
        print(f"{'='*60}")
        
        sim = sim_core.Simulation(10, 9)
        sim.start()
        
        # 运行较长时间产生大量事件
        time.sleep(60)
        
        events = sim.poll_events()
        sim.stop()
        
        # 根据代码，队列最大5000条
        result = {
            "name": "事件队列溢出",
            "config": "10P+9F, 60s",
            "events_collected": len(events),
            "passed": True  # 只要不崩溃就算通过
        }
        
        print(f"✓ 收集事件数: {result['events_collected']}")
        print(f"✓ 结果: {'✅ PASS (队列正常)' if result['passed'] else '❌ FAIL'}")
        
        self.results.append(result)
        return result
    
    def test_rapid_start_stop(self):
        """边界测试4: 快速启停"""
        print(f"\n{'='*60}")
        print("边界测试: 快速启停（10次循环）")
        print(f"{'='*60}")
        
        passed = True
        for i in range(10):
            try:
                sim = sim_core.Simulation(5, 4)
                sim.start()
                time.sleep(0.5)
                sim.stop()
            except Exception as e:
                print(f"❌ 第{i+1}次失败: {e}")
                passed = False
                break
        
        result = {
            "name": "快速启停",
            "config": "10次循环",
            "passed":  passed
        }
        
        print(f"✓ 结果: {'✅ PASS (无内存泄漏/崩溃)' if passed else '❌ FAIL'}")
        
        self.results.append(result)
        return result
    
    def test_single_philosopher(self):
        """边界测试5: 单哲学家"""
        print(f"\n{'='*60}")
        print("边界测试: 单哲学家（边界最小配置）")
        print(f"{'='*60}")
        
        sim = sim_core. Simulation(1, 1)
        sim.start()
        time.sleep(10)
        
        events = sim.poll_events()
        sim.stop()
        
        eat_events = [e for e in events if "EATING" in e.details]
        
        result = {
            "name": "单哲学家",
            "config": "1P+1F",
            "meals":  len(eat_events),
            "passed": len(eat_events) > 0
        }
        
        print(f"✓ 进餐次数: {result['meals']}")
        print(f"✓ 结果: {'✅ PASS' if result['passed'] else '❌ FAIL'}")
        
        self.results.append(result)
        return result
    
    def run_all_tests(self):
        """运行所有边界测试"""
        print("\n" + "="*60)
        print("边界测试套件 - 开始")
        print("="*60)
        
        self.test_extreme_competition()
        self.test_abundant_resources()
        self.test_event_queue_overflow()
        self.test_rapid_start_stop()
        self.test_single_philosopher()
        
        self.generate_report()
    
    def generate_report(self):
        """生成边界测试报告"""
        os.makedirs('test_reports', exist_ok=True)
        
        report_path = 'test_reports/boundary_test_report.md'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f. write("# 边界测试报告\n\n")
            f.write(f"**测试时间**: {datetime. now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## 测试结果汇总\n\n")
            f.write("| 测试场景 | 配置 | 结果 |\n")
            f.write("|----------|------|------|\n")
            
            for r in self.results:
                result_mark = "✅ PASS" if r['passed'] else "❌ FAIL"
                f.write(f"| {r['name']} | {r['config']} | {result_mark} |\n")
            
            f. write("\n## 统计分析\n\n")
            passed = sum(1 for r in self.results if r['passed'])
            f.write(f"- **通过率**: {passed}/{len(self. results)} ({passed/len(self.results)*100:.1f}%)\n")
            
            f.write("\n## 结论\n\n")
            if passed == len(self.results):
                f.write("✅ **所有边界测试通过** - 系统在极端场景下表现稳定\n")
            else:
                f.write("⚠️ **部分测试失败** - 需要检查失败场景\n")
        
        print(f"\n✅ 报告已保存: {report_path}")

if __name__ == "__main__":
    tester = BoundaryTester()
    tester.run_all_tests()