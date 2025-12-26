#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Concurrent Test Suite for Dining Philosophers Simulation
Tests concurrent scenarios with 4, 6, 8, 10, 12 philosophers
Verifies thread safety, deadlock avoidance, and anti-starvation mechanisms
"""

import sys
import os
import time
from datetime import datetime
from pathlib import Path

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


class ConcurrentTestRunner:
    def __init__(self):
        self.results = []
        self.report_path = project_root / "test_reports" / "concurrent_test_report.md"
        
    def check_no_starvation(self, events, num_philosophers, test_duration):
        """Check that no philosopher is starving (all philosophers eat at least once)"""
        eating_events = {}
        for event in events:
            if "EATING" in event.details:
                eating_events[event.phil_id] = eating_events.get(event.phil_id, 0) + 1
        
        starved = []
        for i in range(num_philosophers):
            if i not in eating_events or eating_events[i] == 0:
                starved.append(i)
        
        return len(starved) == 0, starved, eating_events
    
    def check_no_deadlock(self, events):
        """Check for deadlock indicators in events"""
        # Look for sustained HUNGRY state without any eating
        last_states = {}
        for event in events:
            if event.event_type == "STATE":
                last_states[event.phil_id] = event.details
        
        # If all philosophers are stuck in HUNGRY, it's likely a deadlock
        all_hungry = all(state == "HUNGRY" for state in last_states.values())
        return not all_hungry
    
    def check_thread_safety(self, events):
        """Check for data race indicators"""
        # Look for any ERROR events or inconsistencies
        errors = [e for e in events if "ERROR" in e.event_type or "ERROR" in e.details]
        return len(errors) == 0, errors
    
    def test_n_philosophers(self, n_phil, n_forks, test_duration=10):
        """Test with n philosophers and n-1 forks"""
        print(f"\n{'='*60}")
        print(f"Testing {n_phil} philosophers with {n_forks} forks")
        print(f"{'='*60}")
        
        test_result = {
            'philosophers': n_phil,
            'forks': n_forks,
            'duration': test_duration,
            'passed': False,
            'no_starvation': False,
            'no_deadlock': False,
            'thread_safe': False,
            'events_count': 0,
            'eating_distribution': {},
            'issues': []
        }
        
        try:
            # Create and start simulation
            sim = sim_core.Simulation(n_phil, n_forks)
            sim.start()
            print(f"✓ Simulation started")
            
            # Monitor for test_duration seconds
            print(f"  Running for {test_duration} seconds...")
            time.sleep(test_duration)
            
            # Poll events
            events = sim.poll_events()
            test_result['events_count'] = len(events)
            print(f"✓ Collected {len(events)} events")
            
            # Stop simulation
            sim.stop()
            print(f"✓ Simulation stopped")
            
            # Analyze results
            # 1. Check for starvation
            no_starvation, starved, eating_dist = self.check_no_starvation(events, n_phil, test_duration)
            test_result['no_starvation'] = no_starvation
            test_result['eating_distribution'] = eating_dist
            
            if no_starvation:
                print(f"✓ No starvation detected - all philosophers ate")
            else:
                print(f"✗ Starvation detected - philosophers {starved} did not eat")
                test_result['issues'].append(f"Philosophers {starved} starved")
            
            # 2. Check for deadlock
            no_deadlock = self.check_no_deadlock(events)
            test_result['no_deadlock'] = no_deadlock
            
            if no_deadlock:
                print(f"✓ No deadlock detected")
            else:
                print(f"✗ Possible deadlock detected")
                test_result['issues'].append("Possible deadlock")
            
            # 3. Check thread safety
            thread_safe, errors = self.check_thread_safety(events)
            test_result['thread_safe'] = thread_safe
            
            if thread_safe:
                print(f"✓ No thread safety issues")
            else:
                print(f"✗ Thread safety issues detected: {len(errors)} errors")
                test_result['issues'].append(f"{len(errors)} thread safety errors")
            
            # Overall pass/fail
            test_result['passed'] = no_starvation and no_deadlock and thread_safe
            
            if test_result['passed']:
                print(f"\n✅ TEST PASSED")
            else:
                print(f"\n❌ TEST FAILED: {', '.join(test_result['issues'])}")
                
        except Exception as e:
            test_result['issues'].append(f"Exception: {str(e)}")
            print(f"❌ Test failed with exception: {e}")
        
        self.results.append(test_result)
        return test_result
    
    def run_all_tests(self):
        """Run all concurrent tests with different philosopher counts"""
        print(f"\n{'#'*60}")
        print(f"# CONCURRENT TEST SUITE")
        print(f"# Testing 4, 6, 8, 10, 12 philosopher scenarios")
        print(f"{'#'*60}")
        
        start_time = datetime.now()
        
        # Test configurations: (philosophers, forks, duration)
        configs = [
            (4, 3, 10),   # 4 philosophers, 3 forks, 10 seconds
            (6, 5, 10),   # 6 philosophers, 5 forks, 10 seconds
            (8, 7, 10),   # 8 philosophers, 7 forks, 10 seconds
            (10, 9, 10),  # 10 philosophers, 9 forks, 10 seconds
            (12, 11, 10), # 12 philosophers, 11 forks, 10 seconds
        ]
        
        for n_phil, n_forks, duration in configs:
            self.test_n_philosophers(n_phil, n_forks, duration)
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Generate report
        self.generate_report(start_time, end_time, total_duration)
        
        return all(r['passed'] for r in self.results)
    
    def generate_report(self, start_time, end_time, total_duration):
        """Generate Markdown report"""
        print(f"\nGenerating report: {self.report_path}")
        
        # Ensure report directory exists
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.report_path, 'w', encoding='utf-8') as f:
            f.write("# Concurrent Test Report\n\n")
            f.write(f"**Test Date:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Duration:** {total_duration:.2f} seconds\n\n")
            
            # Summary
            passed = sum(1 for r in self.results if r['passed'])
            total = len(self.results)
            f.write(f"## Summary\n\n")
            f.write(f"- **Total Tests:** {total}\n")
            f.write(f"- **Passed:** {passed}\n")
            f.write(f"- **Failed:** {total - passed}\n")
            f.write(f"- **Success Rate:** {passed/total*100:.1f}%\n\n")
            
            # Detailed results
            f.write("## Test Results\n\n")
            f.write("| Philosophers | Forks | Duration | Events | No Starvation | No Deadlock | Thread Safe | Status |\n")
            f.write("|--------------|-------|----------|--------|---------------|-------------|-------------|--------|\n")
            
            for r in self.results:
                status = "✅ PASS" if r['passed'] else "❌ FAIL"
                starvation = "✓" if r['no_starvation'] else "✗"
                deadlock = "✓" if r['no_deadlock'] else "✗"
                thread_safe = "✓" if r['thread_safe'] else "✗"
                
                f.write(f"| {r['philosophers']} | {r['forks']} | {r['duration']}s | {r['events_count']} | "
                       f"{starvation} | {deadlock} | {thread_safe} | {status} |\n")
            
            f.write("\n## Detailed Analysis\n\n")
            
            for i, r in enumerate(self.results, 1):
                f.write(f"### Test {i}: {r['philosophers']} Philosophers, {r['forks']} Forks\n\n")
                
                if r['passed']:
                    f.write("**Status:** ✅ PASSED\n\n")
                else:
                    f.write("**Status:** ❌ FAILED\n\n")
                    f.write(f"**Issues:**\n")
                    for issue in r['issues']:
                        f.write(f"- {issue}\n")
                    f.write("\n")
                
                f.write(f"**Metrics:**\n")
                f.write(f"- Events collected: {r['events_count']}\n")
                f.write(f"- No starvation: {'Yes' if r['no_starvation'] else 'No'}\n")
                f.write(f"- No deadlock: {'Yes' if r['no_deadlock'] else 'No'}\n")
                f.write(f"- Thread safe: {'Yes' if r['thread_safe'] else 'No'}\n\n")
                
                if r['eating_distribution']:
                    f.write("**Eating Distribution:**\n")
                    for phil_id, count in sorted(r['eating_distribution'].items()):
                        f.write(f"- Philosopher {phil_id}: {count} meals\n")
                    f.write("\n")
        
        print(f"✓ Report generated successfully")


def main():
    """Main entry point for concurrent tests"""
    runner = ConcurrentTestRunner()
    success = runner.run_all_tests()
    
    if success:
        print("\n" + "="*60)
        print("✅ ALL CONCURRENT TESTS PASSED")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("❌ SOME TESTS FAILED")
        print("="*60)
        sys.exit(1)


if __name__ == "__main__":
    main()
