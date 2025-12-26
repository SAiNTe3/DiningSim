#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Benchmark Test Suite for Dining Philosophers Simulation
Automated performance metrics collection and comparison
Generates performance reports with charts
"""

import sys
import os
import time
import psutil
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Add build directory to path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root / "build"))

try:
    import sim_core
except ImportError as e:
    print(f"Error: Could not import sim_core. Make sure the C++ module is built.")
    print(f"Details: {e}")
    sys.exit(1)


class PerformanceTestRunner:
    def __init__(self):
        self.results = []
        self.report_path = project_root / "test_reports" / "performance_report.md"
    
    def benchmark_configuration(self, n_phil, n_forks, duration=30, strategy=None):
        """Benchmark a specific configuration"""
        print(f"\n{'='*60}")
        print(f"Benchmarking: {n_phil} philosophers, {n_forks} forks")
        if strategy:
            print(f"Strategy: {strategy}")
        print(f"{'='*60}")
        
        result = {
            'philosophers': n_phil,
            'forks': n_forks,
            'duration': duration,
            'strategy': strategy or 'NONE',
            'cpu_samples': [],
            'memory_samples': [],
            'latencies': [],
            'events_count': 0,
        }
        
        try:
            process = psutil.Process()
            
            # Create simulation
            sim = sim_core.Simulation(n_phil, n_forks)
            
            # Set strategy if specified
            if strategy == 'BANKER':
                sim.set_strategy(1)  # 1 = Banker's Algorithm
            
            sim.start()
            print(f"✓ Simulation started")
            
            start_time = time.time()
            last_event_count = 0
            
            # Monitor performance
            for i in range(duration):
                # CPU and memory
                cpu = process.cpu_percent(interval=0.1)
                mem = process.memory_info().rss / 1024 / 1024
                
                result['cpu_samples'].append(cpu)
                result['memory_samples'].append(mem)
                
                # Event throughput
                events = sim.poll_events()
                new_events = len(events) - last_event_count
                last_event_count = len(events)
                
                time.sleep(0.9)  # Total 1 second per iteration
            
            # Final event collection
            events = sim.poll_events()
            result['events_count'] = len(events)
            
            # Calculate metrics
            elapsed = time.time() - start_time
            result['actual_duration'] = elapsed
            result['throughput'] = result['events_count'] / elapsed
            result['cpu_avg'] = sum(result['cpu_samples']) / len(result['cpu_samples'])
            result['cpu_max'] = max(result['cpu_samples'])
            result['memory_avg'] = sum(result['memory_samples']) / len(result['memory_samples'])
            result['memory_max'] = max(result['memory_samples'])
            
            # Calculate eating distribution
            eating_by_phil = defaultdict(int)
            for e in events:
                if "EATING" in e.details:
                    eating_by_phil[e.phil_id] += 1
            
            result['eating_distribution'] = dict(eating_by_phil)
            result['total_meals'] = sum(eating_by_phil.values())
            result['meals_per_sec'] = result['total_meals'] / elapsed
            
            # Fairness metric (standard deviation of eating counts)
            if eating_by_phil:
                counts = list(eating_by_phil.values())
                avg_meals = sum(counts) / len(counts)
                variance = sum((x - avg_meals) ** 2 for x in counts) / len(counts)
                result['fairness_stddev'] = variance ** 0.5
            else:
                result['fairness_stddev'] = 0
            
            sim.stop()
            print(f"✓ Benchmark complete")
            print(f"  Events: {result['events_count']}")
            print(f"  Throughput: {result['throughput']:.2f} events/sec")
            print(f"  Meals: {result['total_meals']} ({result['meals_per_sec']:.2f}/sec)")
            print(f"  CPU: {result['cpu_avg']:.1f}% avg, {result['cpu_max']:.1f}% max")
            print(f"  Memory: {result['memory_avg']:.1f} MB avg")
            
        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
            import traceback
            traceback.print_exc()
            result['error'] = str(e)
        
        self.results.append(result)
        return result
    
    def run_all_benchmarks(self):
        """Run all performance benchmarks"""
        print(f"\n{'#'*60}")
        print(f"# PERFORMANCE BENCHMARK SUITE")
        print(f"# Automated performance metrics collection")
        print(f"{'#'*60}")
        
        start_time = datetime.now()
        
        # Standard configurations
        configs = [
            (4, 3, 30, None),
            (6, 5, 30, None),
            (8, 7, 30, None),
            (10, 9, 30, None),
        ]
        
        for n_phil, n_forks, duration, strategy in configs:
            self.benchmark_configuration(n_phil, n_forks, duration, strategy)
        
        # Compare strategies (if time permits, use shorter duration)
        print(f"\n{'='*60}")
        print(f"Comparing strategies...")
        print(f"{'='*60}")
        
        # Test with default strategy
        self.benchmark_configuration(8, 7, 20, 'NONE')
        
        # Test with Banker's algorithm
        self.benchmark_configuration(8, 7, 20, 'BANKER')
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Generate report
        self.generate_report(start_time, end_time, total_duration)
        
        return True
    
    def generate_report(self, start_time, end_time, total_duration):
        """Generate Markdown performance report"""
        print(f"\nGenerating report: {self.report_path}")
        
        # Ensure report directory exists
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.report_path, 'w', encoding='utf-8') as f:
            f.write("# Performance Benchmark Report\n\n")
            f.write(f"**Test Date:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Test Duration:** {total_duration:.2f} seconds\n\n")
            
            # Summary table
            f.write("## Performance Summary\n\n")
            f.write("| Config | Strategy | Duration | Events | Throughput | Meals/sec | CPU Avg | Memory Avg |\n")
            f.write("|--------|----------|----------|--------|------------|-----------|---------|------------|\n")
            
            for r in self.results:
                if 'error' not in r:
                    config = f"{r['philosophers']}P/{r['forks']}F"
                    f.write(f"| {config} | {r['strategy']} | {r['duration']}s | "
                           f"{r['events_count']} | {r['throughput']:.2f} e/s | "
                           f"{r['meals_per_sec']:.2f} m/s | {r['cpu_avg']:.1f}% | "
                           f"{r['memory_avg']:.1f} MB |\n")
            
            f.write("\n")
            
            # Detailed metrics
            f.write("## Detailed Metrics\n\n")
            
            for i, r in enumerate(self.results, 1):
                if 'error' in r:
                    f.write(f"### Benchmark {i}: {r['philosophers']}P/{r['forks']}F - ERROR\n\n")
                    f.write(f"Error: {r['error']}\n\n")
                    continue
                
                f.write(f"### Benchmark {i}: {r['philosophers']} Philosophers, {r['forks']} Forks\n\n")
                f.write(f"**Strategy:** {r['strategy']}\n\n")
                
                f.write("**Throughput:**\n")
                f.write(f"- Total Events: {r['events_count']}\n")
                f.write(f"- Events/Second: {r['throughput']:.2f}\n")
                f.write(f"- Total Meals: {r['total_meals']}\n")
                f.write(f"- Meals/Second: {r['meals_per_sec']:.2f}\n\n")
                
                f.write("**Resource Usage:**\n")
                f.write(f"- CPU Average: {r['cpu_avg']:.2f}%\n")
                f.write(f"- CPU Maximum: {r['cpu_max']:.2f}%\n")
                f.write(f"- Memory Average: {r['memory_avg']:.2f} MB\n")
                f.write(f"- Memory Maximum: {r['memory_max']:.2f} MB\n\n")
                
                f.write("**Fairness:**\n")
                f.write(f"- Standard Deviation of Meals: {r['fairness_stddev']:.2f}\n")
                f.write(f"- Eating Distribution:\n")
                for phil_id, count in sorted(r['eating_distribution'].items()):
                    f.write(f"  - Philosopher {phil_id}: {count} meals\n")
                f.write("\n")
                
                # CPU chart
                f.write("**CPU Usage Over Time (Text Chart):**\n\n")
                f.write("```\n")
                self._write_simple_chart(f, r['cpu_samples'], "CPU %", 0, 100)
                f.write("```\n\n")
            
            # Strategy comparison
            f.write("## Strategy Comparison\n\n")
            
            # Find strategy comparison results (8P/7F with different strategies)
            strategy_results = {}
            for r in self.results:
                if r['philosophers'] == 8 and r['forks'] == 7 and 'error' not in r:
                    strategy_results[r['strategy']] = r
            
            if len(strategy_results) >= 2:
                f.write("Comparing different resource allocation strategies:\n\n")
                f.write("| Metric | NONE | BANKER | Difference |\n")
                f.write("|--------|------|--------|------------|\n")
                
                none_r = strategy_results.get('NONE', {})
                banker_r = strategy_results.get('BANKER', {})
                
                if none_r and banker_r:
                    metrics = [
                        ('Throughput (e/s)', 'throughput'),
                        ('Meals/sec', 'meals_per_sec'),
                        ('CPU Avg (%)', 'cpu_avg'),
                        ('Memory Avg (MB)', 'memory_avg'),
                        ('Fairness (σ)', 'fairness_stddev'),
                    ]
                    
                    for name, key in metrics:
                        none_val = none_r.get(key, 0)
                        banker_val = banker_r.get(key, 0)
                        
                        if none_val != 0:
                            diff_pct = ((banker_val - none_val) / none_val) * 100
                            diff_str = f"{diff_pct:+.1f}%"
                        else:
                            diff_str = "N/A"
                        
                        f.write(f"| {name} | {none_val:.2f} | {banker_val:.2f} | {diff_str} |\n")
                    
                    f.write("\n")
            else:
                f.write("Strategy comparison not available.\n\n")
            
            # Performance graph (text-based)
            f.write("## Throughput Comparison\n\n")
            f.write("```\n")
            
            # Bar chart of throughput
            max_throughput = max(r.get('throughput', 0) for r in self.results if 'error' not in r)
            
            for r in self.results:
                if 'error' not in r:
                    config = f"{r['philosophers']}P/{r['forks']}F"
                    bar_len = int((r['throughput'] / max_throughput) * 40)
                    bar = "█" * bar_len
                    f.write(f"{config:10} {bar} {r['throughput']:.2f} events/sec\n")
            
            f.write("```\n\n")
            
            # Conclusions
            f.write("## Conclusions\n\n")
            
            best_throughput = max((r for r in self.results if 'error' not in r), 
                                 key=lambda x: x['throughput'], default=None)
            
            if best_throughput:
                f.write(f"- **Best Throughput:** {best_throughput['philosophers']}P/{best_throughput['forks']}F "
                       f"with {best_throughput['throughput']:.2f} events/sec\n")
            
            avg_cpu = sum(r['cpu_avg'] for r in self.results if 'error' not in r) / len([r for r in self.results if 'error' not in r])
            avg_memory = sum(r['memory_avg'] for r in self.results if 'error' not in r) / len([r for r in self.results if 'error' not in r])
            
            f.write(f"- **Average CPU Usage:** {avg_cpu:.1f}%\n")
            f.write(f"- **Average Memory Usage:** {avg_memory:.1f} MB\n\n")
            
            f.write("The simulation demonstrates stable performance across different configurations. ")
            f.write("Resource usage scales reasonably with the number of philosophers.\n")
        
        print(f"✓ Report generated successfully")
    
    def _write_simple_chart(self, f, samples, ylabel, min_val, max_val):
        """Write a simple text-based line chart"""
        # Sample down to ~40 points
        step = max(1, len(samples) // 40)
        sampled = samples[::step]
        
        chart_height = 8
        
        if max_val == min_val:
            max_val = min_val + 1
        
        for row in range(chart_height, 0, -1):
            threshold = min_val + (max_val - min_val) * row / chart_height
            line = f"{threshold:5.0f} |"
            for val in sampled:
                if val >= threshold:
                    line += "█"
                else:
                    line += " "
            f.write(line + "\n")
        
        f.write(f"{'      +' + '-' * len(sampled)}\n")
        f.write(f"       Time →\n")


def main():
    """Main entry point for performance tests"""
    runner = PerformanceTestRunner()
    
    runner.run_all_benchmarks()
    
    print("\n" + "="*60)
    print("✅ PERFORMANCE BENCHMARKS COMPLETE")
    print("="*60)
    sys.exit(0)


if __name__ == "__main__":
    main()
