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
    running = false; 
    for (auto& t : threads) {
        if (t.joinable()) t.join(); 
    }
    threads.clear();
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

void Simulation::philosopher_thread(int id) {
    // 1. 均匀映射左手叉子
    int left = (static_cast<long long>(id) * num_forks) / num_philosophers;
    
    // 2. 修正：右手叉子必须是左手叉子的逻辑邻居
    // 这样保证了叉子的连续使用，不会出现中间有空闲叉子却没人能拿的情况
    int right = (left + 1) % num_forks;

    // 特殊情况处理：如果总叉子数少于2，无法进食（物理死锁），或者计算重叠
    if (left == right && num_forks > 1) {
        // 理论上 (x + 1) % N == x 只有在 N=1 时成立
        // 但为了代码健壮性，保留此检查
    }

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
            // 1. 询问仲裁者
            if (request_permission(id, left)) {

                // 2. 尝试锁定左手叉子
                std::unique_lock<std::mutex> lock_l(forks[left]->mtx, std::defer_lock);

                if (lock_l.try_lock()) {
                    forks[left]->holder = id; 

                    std::this_thread::sleep_for(std::chrono::milliseconds(100));

                    // 3. 尝试锁定右手叉子
                    std::unique_lock<std::mutex> lock_r(forks[right]->mtx, std::defer_lock);
                    if (lock_r.try_lock()) {
                        forks[right]->holder = id;

                        // --- 进食阶段 ---
                        {
                            std::lock_guard<std::mutex> lock(state_mutex);
                            states[id] = State::EATING;
                        }
                        std::this_thread::sleep_for(std::chrono::milliseconds(dis(gen)));

                        forks[right]->holder = -1;
                        has_eaten = true; 
                    }
                    else {
                        forks[left]->holder = -1;
                    }
                }
            }

            if (!has_eaten) {
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
            }
            else {
                forks[left]->holder = -1; 
            }
        }
    }
}

std::vector<std::vector<int>> Simulation::get_resource_graph() {
    std::lock_guard<std::mutex> lock(state_mutex);
    std::vector<std::vector<int>> edges;

    for (int i = 0; i < num_philosophers; ++i) {
        // 必须与线程逻辑完全一致
        int left = (static_cast<long long>(i) * num_forks) / num_philosophers;
        int right = (left + 1) % num_forks;

        if (states[i] == State::EATING) {
            edges.push_back({ i, left, 1 });  
            edges.push_back({ i, right, 1 });
        }
        else if (states[i] == State::HUNGRY) {
            if (forks[left]->holder == i) {
                edges.push_back({ i, left, 1 });   
                edges.push_back({ i, right, 0 });  
            }
            else {
                edges.push_back({ i, left, 0 });   
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
    for (int i = 0; i < num_forks; ++i) { 
        if (forks[i]->holder != -1) holding_count++;
    }

    if (holding_count >= num_forks - 1 && forks[fork_id]->holder == -1) {
        return false;
    }
    return true;
}