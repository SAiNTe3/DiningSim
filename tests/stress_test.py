#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stress Test Suite for Dining Philosophers Simulation
Tests high concurrency scenarios (15+ threads) for 5 minutes
Monitors CPU usage, memory consumption, and system resources
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


class StressTestRunner:
    def __init__(self):
        self.report_path = project_root / "test_reports" / "stress_test_report.md"
        self.results = {}
        
    def stress_test_high_concurrency(self, n_phil=15, n_forks=14, duration_minutes=5):
        """Run high concurrency stress test"""
        print(f"\n{'='*60}")
        print(f"Stress Test: {n_phil} Philosophers, {n_forks} Forks")
        print(f"Duration: {duration_minutes} minutes")
        print(f"{'='*60}")
        
        duration_seconds = duration_minutes * 60
        sample_interval = 1  # Sample every second
        
        result = {
            'philosophers': n_phil,
            'forks': n_forks,
            'duration_minutes': duration_minutes,
            'start_time': datetime.now(),
            'cpu_samples': [],
            'memory_samples': [],
            'context_switches_start': 0,
            'context_switches_end': 0,
            'events_count': 0,
            'passed': False,
            'issues': []
        }
        
        try:
            # Get process handle
            process = psutil.Process()
            
            # Record initial context switches
            ctx_switches_start = process.num_ctx_switches()
            result['context_switches_start'] = ctx_switches_start.voluntary + ctx_switches_start.involuntary
            
            # Create and start simulation
            print(f"Creating simulation...")
            sim = sim_core.Simulation(n_phil, n_forks)
            sim.start()
            print(f"✓ Simulation started")
            
            # Monitor for specified duration
            print(f"\nMonitoring resources (sampling every {sample_interval}s)...")
            samples = 0
            max_samples = duration_seconds // sample_interval
            
            start_time = time.time()
            
            for i in range(max_samples):
                elapsed = time.time() - start_time
                
                # Get CPU percentage (interval-based)
                cpu_percent = process.cpu_percent(interval=0.1)
                
                # Get memory info
                mem_info = process.memory_info()
                memory_mb = mem_info.rss / 1024 / 1024
                
                result['cpu_samples'].append(cpu_percent)
                result['memory_samples'].append(memory_mb)
                
                samples += 1
                
                # Progress indicator every 30 seconds
                if (i + 1) % 30 == 0:
                    print(f"  [{int(elapsed)}s/{duration_seconds}s] "
                          f"CPU: {cpu_percent:.1f}% | Memory: {memory_mb:.1f} MB | "
                          f"Samples: {samples}")
                
                # Sleep until next sample
                time.sleep(sample_interval)
            
            print(f"\n✓ Monitoring complete - collected {samples} samples")
            
            # Get final context switches
            ctx_switches_end = process.num_ctx_switches()
            result['context_switches_end'] = ctx_switches_end.voluntary + ctx_switches_end.involuntary
            
            # Poll events
            print(f"Collecting events...")
            events = sim.poll_events()
            result['events_count'] = len(events)
            print(f"✓ Collected {len(events)} events")
            
            # Stop simulation
            sim.stop()
            print(f"✓ Simulation stopped")
            
            # Calculate statistics
            result['end_time'] = datetime.now()
            result['cpu_avg'] = sum(result['cpu_samples']) / len(result['cpu_samples']) if result['cpu_samples'] else 0
            result['cpu_max'] = max(result['cpu_samples']) if result['cpu_samples'] else 0
            result['cpu_min'] = min(result['cpu_samples']) if result['cpu_samples'] else 0
            
            result['memory_avg'] = sum(result['memory_samples']) / len(result['memory_samples']) if result['memory_samples'] else 0
            result['memory_max'] = max(result['memory_samples']) if result['memory_samples'] else 0
            result['memory_min'] = min(result['memory_samples']) if result['memory_samples'] else 0
            
            # Check for memory leak (memory should be relatively stable)
            if len(result['memory_samples']) > 10:
                first_half_avg = sum(result['memory_samples'][:len(result['memory_samples'])//2]) / (len(result['memory_samples'])//2)
                second_half_avg = sum(result['memory_samples'][len(result['memory_samples'])//2:]) / (len(result['memory_samples'])//2)
                memory_growth = ((second_half_avg - first_half_avg) / first_half_avg) * 100
                result['memory_growth_percent'] = memory_growth
                
                if memory_growth > 50:  # More than 50% growth
                    result['issues'].append(f"Possible memory leak: {memory_growth:.1f}% growth")
                    print(f"⚠ Warning: Memory grew by {memory_growth:.1f}%")
                else:
                    print(f"✓ Memory stable (growth: {memory_growth:.1f}%)")
            
            # Calculate throughput (events per second)
            result['throughput'] = result['events_count'] / duration_seconds
            
            # Calculate context switches per second
            ctx_switches_total = result['context_switches_end'] - result['context_switches_start']
            result['context_switches_total'] = ctx_switches_total
            result['context_switches_per_sec'] = ctx_switches_total / duration_seconds
            
            # Determine pass/fail
            result['passed'] = len(result['issues']) == 0 and result['events_count'] > 0
            
            print(f"\n{'='*60}")
            print(f"Stress Test Results:")
            print(f"  CPU: avg={result['cpu_avg']:.1f}%, max={result['cpu_max']:.1f}%, min={result['cpu_min']:.1f}%")
            print(f"  Memory: avg={result['memory_avg']:.1f}MB, max={result['memory_max']:.1f}MB")
            print(f"  Events: {result['events_count']} ({result['throughput']:.1f} events/sec)")
            print(f"  Context Switches: {ctx_switches_total} ({result['context_switches_per_sec']:.1f}/sec)")
            
            if result['passed']:
                print(f"\n✅ STRESS TEST PASSED")
            else:
                print(f"\n❌ STRESS TEST FAILED: {', '.join(result['issues'])}")
            print(f"{'='*60}")
            
        except Exception as e:
            result['issues'].append(f"Exception: {str(e)}")
            result['passed'] = False
            print(f"❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
        
        self.results = result
        return result
    
    def generate_report(self):
        """Generate Markdown report"""
        print(f"\nGenerating report: {self.report_path}")
        
        # Ensure report directory exists
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        
        r = self.results
        
        with open(self.report_path, 'w', encoding='utf-8') as f:
            f.write("# Stress Test Report\n\n")
            f.write(f"**Test Date:** {r['start_time'].strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Configuration:**\n")
            f.write(f"- Philosophers: {r['philosophers']}\n")
            f.write(f"- Forks: {r['forks']}\n")
            f.write(f"- Duration: {r['duration_minutes']} minutes\n\n")
            
            # Status
            f.write(f"## Test Status\n\n")
            if r['passed']:
                f.write("**Result:** ✅ PASSED\n\n")
            else:
                f.write("**Result:** ❌ FAILED\n\n")
                f.write("**Issues:**\n")
                for issue in r['issues']:
                    f.write(f"- {issue}\n")
                f.write("\n")
            
            # Performance Metrics
            f.write("## Performance Metrics\n\n")
            
            f.write("### CPU Usage\n\n")
            f.write(f"- **Average:** {r['cpu_avg']:.2f}%\n")
            f.write(f"- **Maximum:** {r['cpu_max']:.2f}%\n")
            f.write(f"- **Minimum:** {r['cpu_min']:.2f}%\n\n")
            
            f.write("### Memory Usage\n\n")
            f.write(f"- **Average:** {r['memory_avg']:.2f} MB\n")
            f.write(f"- **Maximum:** {r['memory_max']:.2f} MB\n")
            f.write(f"- **Minimum:** {r['memory_min']:.2f} MB\n")
            if 'memory_growth_percent' in r:
                f.write(f"- **Growth:** {r['memory_growth_percent']:.2f}%\n")
            f.write("\n")
            
            f.write("### Throughput\n\n")
            f.write(f"- **Total Events:** {r['events_count']}\n")
            f.write(f"- **Events/Second:** {r['throughput']:.2f}\n\n")
            
            f.write("### Context Switching\n\n")
            f.write(f"- **Total Context Switches:** {r['context_switches_total']}\n")
            f.write(f"- **Context Switches/Second:** {r['context_switches_per_sec']:.2f}\n\n")
            
            # Text-based charts
            f.write("## Resource Usage Over Time\n\n")
            
            # CPU chart
            f.write("### CPU Usage Chart (Text)\n\n")
            f.write("```\n")
            self._write_text_chart(f, r['cpu_samples'], "CPU %", 0, 100)
            f.write("```\n\n")
            
            # Memory chart
            f.write("### Memory Usage Chart (Text)\n\n")
            f.write("```\n")
            self._write_text_chart(f, r['memory_samples'], "Memory MB", 
                                  int(r['memory_min']), int(r['memory_max'] + 1))
            f.write("```\n\n")
            
            # Summary
            f.write("## Summary\n\n")
            f.write(f"The stress test ran for {r['duration_minutes']} minutes with {r['philosophers']} philosophers ")
            f.write(f"competing for {r['forks']} forks. ")
            f.write(f"The system generated {r['events_count']} events with an average throughput of {r['throughput']:.2f} events/sec. ")
            f.write(f"CPU usage averaged {r['cpu_avg']:.1f}% and memory usage averaged {r['memory_avg']:.1f} MB.\n\n")
            
            if r['passed']:
                f.write("The simulation performed stably under stress with no significant issues detected.\n")
            else:
                f.write("Issues were detected during the stress test. See details above.\n")
        
        print(f"✓ Report generated successfully")
    
    def _write_text_chart(self, f, samples, ylabel, min_val, max_val):
        """Write a simple text-based chart"""
        # Sample down to ~50 points for readability
        step = max(1, len(samples) // 50)
        sampled = samples[::step]
        
        chart_height = 10
        chart_width = len(sampled)
        
        if max_val == min_val:
            max_val = min_val + 1
        
        f.write(f"{ylabel}\n")
        
        # Draw chart
        for row in range(chart_height, 0, -1):
            threshold = min_val + (max_val - min_val) * row / chart_height
            line = f"{threshold:6.1f} |"
            for val in sampled:
                if val >= threshold:
                    line += "█"
                else:
                    line += " "
            f.write(line + "\n")
        
        f.write(f"{'       +' + '-' * chart_width}\n")
        f.write(f"        0{'':>{chart_width-10}}Time (samples)\n")


def main():
    """Main entry point for stress tests"""
    runner = StressTestRunner()
    
    # Run 5-minute stress test with 15 philosophers
    result = runner.stress_test_high_concurrency(n_phil=15, n_forks=14, duration_minutes=5)
    
    # Generate report
    runner.generate_report()
    
    if result['passed']:
        print("\n" + "="*60)
        print("✅ STRESS TEST PASSED")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("❌ STRESS TEST FAILED")
        print("="*60)
        sys.exit(1)


if __name__ == "__main__":
    main()
