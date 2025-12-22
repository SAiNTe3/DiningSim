#pragma once
#include <vector>
#include <thread>
#include <mutex>
#include <atomic>
#include <string>
#include <memory>

enum class State { THINKING, HUNGRY, EATING };

struct Fork {
    std::mutex mtx;
    std::atomic<int> holder{ -1 };
};

class Simulation {
public:
    Simulation(int n_phil, int n_forks);
    ~Simulation();

    void start();
    void stop();

    // 基础状态获取
    std::vector<int> get_states();

    // 关键：获取完整资源分配数据
    // 返回格式：[P0_state, P1_state..., F0_holder, F1_holder...]
    std::vector<int> get_full_state();

    // 资源分配图接口：返回 [哲学家ID, 叉子ID, 类型(0:请求, 1:占用)]
    std::vector<std::vector<int>> get_resource_graph();
    bool request_permission(int phil_id, int fork_id);
private:
    int num_philosophers;
    int num_forks; // 新增：叉子数量
    std::atomic<bool> running{ false };

    std::vector<State> states;
    std::vector<std::unique_ptr<Fork>> forks; // 修改这里，使用显式 Fork 结构
    std::vector<std::thread> threads;
    std::mutex state_mutex;

    void philosopher_thread(int id);
};