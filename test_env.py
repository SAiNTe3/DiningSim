import sys
import os
import time
# 将编译产物的路径加入 Python 搜索路径
# 请根据实际编译生成的路径修改下面的 'build/Release'
sys.path.append('./build/Release') 

try:
    import sim_core

except ImportError as e:
    print(f"Error: Could not find the module. {e}")
    


sim = sim_core.Simulation(5)
print("Starting simulation...")
sim.start()

try:
    for _ in range(10):
        states = sim.get_states()
        # 0: Thinking, 1: Hungry, 2: Eating
        print(f"Current States: {states}")
        time.sleep(0.5)
finally:
    print("Stopping...")
    sim.stop()
