"""
压力测试 - 高并发长时间运行测试
监控指标：
- CPU使用率
- 内存占用
- 上下文切换
- 吞吐量稳定性
"""

import sys
import os
import time
import psutil
import threading
from datetime import datetime

sys.path. append('./build/Release')
import sim_core

class StressTester:
    def __init__(self):
        self.monitoring = False
        self.metrics = {
            'cpu':  [],
            'memory': [],
            'threads': [],
            'ctx_switches': [],
            'timestamps': []
        }
    
    def monitor_resources(self, process, interval=1):
        """资源监控线程"""
        while self.monitoring:
            self.metrics['cpu'].append(process.cpu_percent())
            self.metrics['memory'].append(process.memory_info().rss / 1024 / 1024)  # MB
            self.metrics['threads'].append(process.num_threads())
            ctx = process.num_ctx_switches()
            self.metrics['ctx_switches'].append(ctx. voluntary + ctx.involuntary)
            self.metrics['timestamps']. append(time.time())
            time.sleep(interval)
    
    def stress_test_high_concurrency(self, n_phil=15, duration=300):
        """高并发压力测试（5分钟）"""
        print(f"\n{'='*60}")
        print(f"压力测试: {n_phil}哲学家 高并发场景")
        print(f"运行时间: {duration}秒 ({duration/60:.1f}分钟)")
        print(f"{'='*60}\n")
        
        process = psutil.Process()
        
        # 启动监控线程
        self.monitoring = True
        monitor_thread = threading.Thread(target=self.monitor_resources, args=(process, 1))
        monitor_thread.start()
        
        # 启动模拟
        sim = sim_core. Simulation(n_phil, n_phil-1)
        sim.start()
        
        print("⏱️  开始监控...")
        start_time = time.time()
        
        # 定期输出状态
        for i in range(duration):
            time.sleep(1)
            if (i+1) % 30 == 0:
                elapsed = i + 1
                print(f"  [{elapsed}s] CPU: {self.metrics['cpu'][-1]:.1f}%, "
                      f"内存: {self.metrics['memory'][-1]:.1f}MB, "
                      f"线程: {self.metrics['threads'][-1]}")
        
        # 停止
        events = sim.poll_events()
        sim.stop()
        
        self.monitoring = False
        monitor_thread.join()
        
        # 分析结果
        eat_events = [e for e in events if e.event_type == "STATE" and e.details == "EATING"]
        
        result = {
            'duration': duration,
            'philosophers': n_phil,
            'total_meals': len(eat_events),
            'throughput':  len(eat_events) / duration,
            'avg_cpu': sum(self.metrics['cpu']) / len(self.metrics['cpu']),
            'max_cpu': max(self.metrics['cpu']),
            'avg_memory': sum(self.metrics['memory']) / len(self.metrics['memory']),
            'max_memory': max(self. metrics['memory']),
            'max_threads': max(self.metrics['threads']),
            'total_ctx_switches': self.metrics['ctx_switches'][-1] - self.metrics['ctx_switches'][0]
        }
        
        # 输出结果
        print(f"\n{'='*60}")
        print("压力测试结果")
        print(f"{'='*60}")
        print(f"✓ 总进餐次数: {result['total_meals']}")
        print(f"✓ 吞吐量: {result['throughput']:. 2f} 次/秒")
        print(f"✓ 平均CPU: {result['avg_cpu']:.1f}%")
        print(f"✓ 峰值CPU: {result['max_cpu']:.1f}%")
        print(f"✓ 平均内存:  {result['avg_memory']:. 1f} MB")
        print(f"✓ 峰值内存: {result['max_memory']:.1f} MB")
        print(f"✓ 最大线程数: {result['max_threads']}")
        print(f"✓ 上下文切换: {result['total_ctx_switches']}")
        
        # 生成报告
        self.generate_report(result)
        
        return result
    
    def generate_report(self, result):
        """生成压力测试报告"""
        os.makedirs('test_reports', exist_ok=True)
        
        report_path = 'test_reports/stress_test_report.md'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 压力测试报告\n\n")
            f.write(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## 测试配置\n\n")
            f.write(f"- **哲学家数量**: {result['philosophers']}\n")
            f.write(f"- **运行时间**: {result['duration']}秒 ({result['duration']/60:. 1f}分钟)\n\n")
            
            f. write("## 性能指标\n\n")
            f.write("| 指标 | 数值 |\n")
            f.write("|------|------|\n")
            f.write(f"| 总进餐次数 | {result['total_meals']} |\n")
            f.write(f"| 吞吐量 | {result['throughput']:.2f} 次/秒 |\n")
            f.write(f"| 平均CPU使用率 | {result['avg_cpu']:.1f}% |\n")
            f.write(f"| 峰值CPU使用率 | {result['max_cpu']:.1f}% |\n")
            f.write(f"| 平均内存占用 | {result['avg_memory']:.1f} MB |\n")
            f.write(f"| 峰值内存占用 | {result['max_memory']:.1f} MB |\n")
            f.write(f"| 最大线程数 | {result['max_threads']} |\n")
            f.write(f"| 上下文切换总数 | {result['total_ctx_switches']} |\n")
            
            f.write("\n## CPU使用率时间序列（文本图表）\n\n```\n")
            # 简单文本图表
            for i in range(0, len(self.metrics['cpu']), 10):
                cpu = self.metrics['cpu'][i]
                bar = '█' * int(cpu / 2)
                f.write(f"{i:4d}s | {bar} {cpu:.1f}%\n")
            f.write("```\n")
            
            f.write("\n## 结论\n\n")
            if result['avg_cpu'] < 80 and result['max_memory'] < 500:
                f.write("✅ **压力测试通过** - 系统在高并发下表现稳定\n")
            else:
                f.write("⚠️ **需要优化** - CPU或内存使用率较高\n")
        
        print(f"\n✅ 报告已保存: {report_path}")

if __name__ == "__main__":
    tester = StressTester()
    tester.stress_test_high_concurrency(n_phil=15, duration=300)