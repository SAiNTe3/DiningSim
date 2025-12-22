#include "simulation.h"
#include <chrono>
#include <random>
Simulation::Simulation(int n_phil, int n_forks)
    : num_philosophers(n_phil), num_forks(n_forks), states(n_phil, State::THINKING) {
    for (int i = 0; i < n_forks; ++i) {
        forks.push_back(std::make_unique<Fork>());
    }
}

Simulation::~Simulation() { 
    running = false; // 先设置标志位
    for (auto& t : threads) {
        if (t.joinable()) t.join(); // 阻塞等待直到线程退出
    }
    threads.clear();
    // 只有在所有线程退出后，才能清理 states 和 forks
}

void Simulation::start() {
    running = true;
    for (int i = 0; i < num_philosophers; ++i) {
        threads.emplace_back(&Simulation::philosopher_thread, this, i);
    }
}

void Simulation::stop() {
    running = false;
    for (auto& t : threads) {
        if (t.joinable()) t.join();
    }
    threads.clear();
}
// ... 前面 Simulation::Simulation 和 start/stop 逻辑保持 ...

void Simulation::philosopher_thread(int id) {
    int left = (id * (num_forks / num_philosophers)) % num_forks;
    int right = (id + 1) % num_forks;

    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(500, 1000);

    while (running) {
        // --- 思考阶段 ---
        {
            std::lock_guard<std::mutex> lock(state_mutex);
            states[id] = State::THINKING;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(dis(gen)));

        // --- 饥饿阶段 ---
        {
            std::lock_guard<std::mutex> lock(state_mutex);
            states[id] = State::HUNGRY;
        }

        bool has_eaten = false;
        while (running && !has_eaten) {
            // 1. 询问仲裁者（银行家算法或 AI）是否允许拿第一个叉子
            // 如果不满足安全序列，则不尝试 lock，直接跳过并等待
            if (request_permission(id, left)) {

                // 2. 尝试非阻塞式锁定左手叉子 (std::unique_lock 配合 try_lock)
                std::unique_lock<std::mutex> lock_l(forks[left]->mtx, std::defer_lock);

                if (lock_l.try_lock()) {
                    forks[left]->holder = id; // 标记占用

                    // 故意延迟，模拟现实中拿起一个叉子到拿起第二个之间的间隔
                    std::this_thread::sleep_for(std::chrono::milliseconds(100));

                    // 3. 尝试拿第二个叉子
                    std::unique_lock<std::mutex> lock_r(forks[right]->mtx, std::defer_lock);
                    if (lock_r.try_lock()) {
                        forks[right]->holder = id;

                        // --- 进食阶段 ---
                        {
                            std::lock_guard<std::mutex> lock(state_mutex);
                            states[id] = State::EATING;
                        }
                        std::this_thread::sleep_for(std::chrono::milliseconds(dis(gen)));

                        // 释放记录
                        forks[right]->holder = -1;
                        has_eaten = true; // 成功进食，跳出尝试循环
                        // lock_r 会在作用域结束时自动析构并释放 mutex
                    }
                    else {
                        // 拿不到右手，必须放下左手（回退策略），防止占有并等待
                        forks[left]->holder = -1;
                    }
                }
            }

            // 如果没吃上，休息一下再重试，避免高频空转消耗 CPU
            if (!has_eaten) {
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
            }
            else {
                forks[left]->holder = -1; // 彻底进食完后释放左手标记
            }
        }
    }
}

std::vector<std::vector<int>> Simulation::get_resource_graph() {
    std::lock_guard<std::mutex> lock(state_mutex);
    std::vector<std::vector<int>> edges;

    for (int i = 0; i < num_philosophers; ++i) {
        int left = i % num_forks;
        int right = (i + 1) % num_forks;

        // 1. 如果哲学家正在进食，说明他占有了两个叉子 (Resource -> Process)
        if (states[i] == State::EATING) {
            edges.push_back({ i, left, 1 });  // 1 代表占用
            edges.push_back({ i, right, 1 });
        }
        // 2. 如果哲学家饥饿，检查他是否正持有左手叉子并等待右手叉子
        else if (states[i] == State::HUNGRY) {
            if (forks[left]->holder == i) {
                edges.push_back({ i, left, 1 });   // 占用左手
                edges.push_back({ i, right, 0 });  // 请求右手 (0 代表请求)
            }
            else {
                edges.push_back({ i, left, 0 });   // 连左手都没拿到，请求左手
            }
        }
    }
    return edges;
}
std::vector<int> Simulation::get_states() {
    std::lock_guard<std::mutex> lock(state_mutex);
    std::vector<int> result;
    for (auto s : states) result.push_back(static_cast<int>(s));
    return result;
}

bool Simulation::request_permission(int phil_id, int fork_id) {
    std::lock_guard<std::mutex> lock(state_mutex);

    int holding_count = 0;
    for (int i = 0; i < num_forks; ++i) { // 遍历叉子
        if (forks[i]->holder != -1) holding_count++;
    }

    // 预防策略：如果资源极度短缺，确保至少留出一个叉子
    if (holding_count >= num_forks - 1 && forks[fork_id]->holder == -1) {
        return false;
    }
    return true;
}