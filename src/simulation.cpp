#include "simulation.h"
#include <chrono>
#include <random>
#include <algorithm>
#include <map>
#include <iostream>

#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
// Cross-platform sleep function
inline void Sleep(unsigned int milliseconds) {
    usleep(milliseconds * 1000);
}
#endif

// Simulation 类实现了一个哲学家就餐问题的仿真。
// 主要包含：线程并发控制（WinThread / WinMutex）、资源分配策略（Banker's Algorithm 的简化形式）、
// 死锁检测、以及反饥饿（starvation）处理等操作系统相关概念。

Simulation::Simulation(int n_phil, int n_forks)
    : num_philosophers(n_phil), num_forks(n_forks), 
      running(false),  // 显式初始化为 false
      current_strategy(Strategy::NONE),  // 显式初始化策略
      states(n_phil, State::THINKING), 
      wait_counts(n_phil, 0),
      eat_counts(n_phil, 0),
      max_wait_counts(n_phil, 0) {
    // 初始化叉子列表，每把叉子用一个互斥量保护（Fork 包含 mtx 和 holder 字段）
    for (int i = 0; i < n_forks; ++i) {
        forks.push_back(std::make_unique<Fork>());
    }

    // 计算竞争者：任何共享同一把叉子的哲学家都视为竞争者。
    // 这用于反饥饿策略：当某些竞争者等待过久时，优先让它们获得资源。
    competitors.resize(n_phil);
    auto get_forks = [&](int id) {
        // 将哲学家映射到叉子的策略：使用比例映射使得哲学家数和叉子数不一定相等时也合理分配
        int l = (static_cast<long long>(id) * n_forks) / n_phil;
        int r = (l + 1) % n_forks;
        return std::pair<int, int>{l, r};
    };

    for (int i = 0; i < n_phil; ++i) {
        auto [l1, r1] = get_forks(i);
        for (int j = 0; j < n_phil; ++j) {
            if (i == j) continue;
            auto [l2, r2] = get_forks(j);
            if (l1 == l2 || l1 == r2 || r1 == l2 || r1 == r2) {
                competitors[i].push_back(j);
            }
        }
    }
}

Simulation::~Simulation() { 
    // 析构时确保干净退出：停止所有线程并收集统计信息
    stop();
}

void Simulation::start() {
    // 启动仿真：为每个哲学家创建一个线程
    if (running) return;
    running = true;
    for (int i = 0; i < num_philosophers; ++i) {
        // 每个线程运行 philosopher_thread，代表一个并发执行的进程/线程
        auto t = std::make_unique<WinThread>();
        t->start([this, i]() { this->philosopher_thread(i); });
        threads.push_back(std::move(t));
    }
    log_event(-1, "SYSTEM", "Simulation started");
}

void Simulation::stop() {
    // 停止仿真：先通知线程停止（running = false），然后 join 等待线程退出，避免悬挂线程。
    running = false;
    for (auto& t : threads) {
        if (t->joinable()) t->join();
    }
    threads.clear();

    // 收集并记录统计信息
    for (int i = 0; i < num_philosophers; ++i) {
        if (states[i] == State::HUNGRY && wait_counts[i] > max_wait_counts[i]) {
             max_wait_counts[i] = wait_counts[i];
        }
        std::string details = "Eaten: " + std::to_string(eat_counts[i]) + 
                              ", MaxWait: " + std::to_string(max_wait_counts[i]);
        log_event(i, "STATS", details);
        std::cout << "Phil " << i << " " << details << std::endl;
    }

    log_event(-1, "SYSTEM", "Simulation stopped");
}

void Simulation::set_strategy(int strategy_code) {
    // 修改资源分配策略需要对共享状态上锁，避免竞态条件
    WinLockGuard lock(state_mutex);
    if (strategy_code == 1) current_strategy = Strategy::BANKER;
    else current_strategy = Strategy::NONE;
    log_event(-1, "SYSTEM", "Strategy changed to " + std::to_string(strategy_code));
}

void Simulation::log_event(int phil_id, const std::string& type, const std::string& details) {
    // 事件记录受 event_mutex 保护，避免多线程并发写入导致数据不一致
    WinLockGuard lock(event_mutex);
    auto now = std::chrono::system_clock::now().time_since_epoch();
    double ts = std::chrono::duration<double>(now).count();
    event_queue.push_back({ts, phil_id, type, details});
    // 限制事件队列长度，防止无限增长导致内存问题
    if (event_queue.size() > 5000) event_queue.pop_front();
}

std::vector<SimEvent> Simulation::poll_events() {
    // 从事件队列中取出所有事件并清空队列，使用锁来保证一致性
    WinLockGuard lock(event_mutex);
    std::vector<SimEvent> events(event_queue.begin(), event_queue.end());
    event_queue.clear();
    return events;
}

bool Simulation::is_safe_state(int phil_id, int fork_id) {
    // 基于银行家算法（Banker's Algorithm）的安全性检查的简化实现：
    // available[] 表示每个资源（叉子）当前是否可用（1 = 可用, 0 = 不可用）
    // need[] 表示每个哲学家还需要多少个资源才能完成（这里最大需要 2 把叉子）
    // 该函数用于在允许某哲学家占用某把叉子之前，判断系统是否仍然处于安全状态，
    // 以避免引入可能导致死锁的分配。
    std::vector<int> available(num_forks, 1);
    std::vector<int> need(num_philosophers, 2); 

    for (int i = 0; i < num_forks; ++i) {
        int holder = forks[i]->holder;
        if (holder != -1) {
            // 如果叉子被占用，则该资源不可用，并且占用该叉子的哲学家需要的资源数减一
            available[i] = 0;
            need[holder]--;
        }
    }

    // 如果要请求的叉子当前不可用，则肯定不能分配
    if (available[fork_id] == 0) return false; 

    // 试假设将 fork_id 分配给 phil_id，然后检查系统是否可以顺利完成所有人的需求
    available[fork_id] = 0;
    need[phil_id]--;

    std::vector<bool> finish(num_philosophers, false);
    int finished_count = 0;

    // 尝试找到一个顺序，使得每个哲学家都能获得所需资源并完成（类似银行家算法的安全性检测循环）
    while (finished_count < num_philosophers) {
        bool found = false;
        for (int i = 0; i < num_philosophers; ++i) {
            if (!finish[i]) {
                if (need[i] <= 0) { 
                    // 此哲学家当前已满足需求，标记为完成
                    finish[i] = true;
                    finished_count++;
                    found = true;
                } else {
                    int left = (static_cast<long long>(i) * num_forks) / num_philosophers;
                    int right = (left + 1) % num_forks;
                    
                    // 检查左右叉子是否都能被该哲学家获取（要么已由其持有，要么为可用）
                    bool left_ok = (forks[left]->holder == i) || (available[left] == 1);
                    if (i == phil_id && left == fork_id) left_ok = true; // 模拟我们刚刚给了 phil_id 该叉子

                    bool right_ok = (forks[right]->holder == i) || (available[right] == 1);
                    if (i == phil_id && right == fork_id) right_ok = true;
                    
                    if (left_ok && right_ok) {
                        // 若该哲学家能够获得足够资源，则认为他可以完成，释放其占用的资源（模拟释放）
                        finish[i] = true;
                        finished_count++;
                        found = true;
                        if (forks[left]->holder == i) available[left] = 1;
                        if (forks[right]->holder == i) available[right] = 1;
                        if (i == phil_id && left == fork_id) available[left] = 1;
                        if (i == phil_id && right == fork_id) available[right] = 1;
                    }
                }
            }
        }
        // 如果遍历一轮没有找到可完成的哲学家，则系统不安全（存在潜在死锁风险）
        if (!found) return false; 
    }
    return true;
}

bool Simulation::request_permission(int phil_id, int fork_id) {
    // 该函数在修改共享状态前加锁以保证原子性，避免竞态条件
    WinLockGuard lock(state_mutex);

    // 1. 基础检查：叉子是否被占用
    if (forks[fork_id]->holder != -1) return false;

    // 2. 反饥饿机制 (Anti-Starvation)
    // 检查所有竞争者是否处于饥饿状态且等待时间超过阈值，如果是则优先礼让，以避免长期饥饿（starvation）。
    for (int comp_id : competitors[phil_id]) {
        if (states[comp_id] == State::HUNGRY && 
            wait_counts[comp_id] > STARVATION_THRESHOLD && 
            wait_counts[comp_id] > wait_counts[phil_id]) {
            return false; // 礼让竞争者
        }
    }

    // 3. 策略分发：若启用了银行家算法策略，则进行安全性检查；否则直接允许分配（乐观分配）
    if (current_strategy == Strategy::BANKER) {
        return is_safe_state(phil_id, fork_id);
    }
    else {
        return true; 
    }
}

void Simulation::philosopher_thread(int id) {
    // 计算该哲学家的左右叉子索引（比例映射），注意 num_philosophers 与 num_forks 不一定相等
    int left = (static_cast<long long>(id) * num_forks) / num_philosophers;
    int right = (left + 1) % num_forks;

    // 使用随机数模拟思考和吃饭的时间间隔（模拟真实系统中任务的非确定性）
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(500, 1000);

    while (running) {
        // THINKING：占用状态锁来安全更新状态数组
        {
            WinLockGuard lock(state_mutex);
            states[id] = State::THINKING;
        }
        log_event(id, "STATE", "THINKING");
        Sleep(dis(gen)); // 使用 Windows API Sleep 替代 std::this_thread::sleep_for

        // HUNGRY：想要吃饭，开始尝试获取资源，并重置本轮等待计数
        {
            WinLockGuard lock(state_mutex);
            states[id] = State::HUNGRY;
            wait_counts[id] = 0; // 开始新一轮饥饿，计数归零
        }
        log_event(id, "STATE", "HUNGRY");

        bool has_eaten = false;
        while (running && !has_eaten) {
            // 先向系统请求是否允许获取左叉子（高层策略判断）
            if (request_permission(id, left)) {
                // 使用 WinMutex 的 try_lock 做非阻塞尝试拿锁
                if (forks[left]->mtx.try_lock()) {
                    // 成功获得左叉子互斥量后，设置 holder 标志以供其他逻辑读取
                    forks[left]->holder = id;
                    log_event(id, "ACQUIRE", "Left Fork " + std::to_string(left));

                    // 小暂停模拟获取第二把叉子的延时（也能暴露出并发竞争）
                    Sleep(10); // 使用 Windows API Sleep

                    // 请求是否允许获取右叉子
                    if (request_permission(id, right)) { 
                        if (forks[right]->mtx.try_lock()) {
                            // 成功获取右叉子
                            forks[right]->holder = id;
                            log_event(id, "ACQUIRE", "Right Fork " + std::to_string(right));

                            // EATING：更新状态并统计，此处对共享状态上锁
                            {
                                WinLockGuard lock(state_mutex);
                                states[id] = State::EATING;
                                
                                eat_counts[id]++;
                                if (wait_counts[id] > max_wait_counts[id]) {
                                    max_wait_counts[id] = wait_counts[id];
                                }
                                wait_counts[id] = 0; // 成功进食，重置计数
                            }
                            log_event(id, "STATE", "EATING");
                            Sleep(dis(gen)); // 使用 Windows API Sleep

                            // 释放资源：先释放右手再释放左手。
                            forks[right]->holder = -1;
                            forks[right]->mtx.unlock();
                            log_event(id, "RELEASE", "Right Fork " + std::to_string(right));
                            
                            forks[left]->holder = -1;
                            forks[left]->mtx.unlock();
                            log_event(id, "RELEASE", "Left Fork " + std::to_string(left));
                            
                            has_eaten = true;
                        } else {
                            // 未能拿到右叉子：回退（把左叉子放下），并进行短暂退避以减少活锁竞争
                            forks[left]->holder = -1;
                            forks[left]->mtx.unlock();
                            log_event(id, "RELEASE", "Left Fork " + std::to_string(left) + " (Backoff)");
                            Sleep(dis(gen) / 10); // 使用 Windows API Sleep
                        }
                    } else {
                         // 策略层拒绝分配右叉子，回退左叉子
                         forks[left]->holder = -1;
                         forks[left]->mtx.unlock();
                         log_event(id, "RELEASE", "Left Fork " + std::to_string(left) + " (Permission Denied)");
                         Sleep(dis(gen) / 10); // 使用 Windows API Sleep
                    }
                }
            }
            
            if (!has_eaten) {
                // 增加等待计数：用于反饥饿策略判断（注意使用锁同步）
                {
                    WinLockGuard lock(state_mutex);
                    wait_counts[id]++;
                }
                // 等待一小段时间后重试，避免 busy-wait
                Sleep(50); // 使用 Windows API Sleep
            }
        }
    }
}

bool Simulation::detect_deadlock() {
    // 基于当前状态构建等待图（部分资源分配图）并检测环路，如果存在环路则判定为死锁
    WinLockGuard lock(state_mutex);
    std::map<int, int> waiting_for; 
    for (int i = 0; i < num_philosophers; ++i) {
        if (states[i] == State::HUNGRY) {
            int left = (static_cast<long long>(i) * num_forks) / num_philosophers;
            int right = (left + 1) % num_forks;
            // 如果哲学家 i 等待某把叉子（且该叉子由另一哲学家持有），就在等待图中记录边 i -> holder
            if (forks[left]->holder != i && forks[left]->holder != -1) {
                waiting_for[i] = forks[left]->holder;
            }
            else if (forks[left]->holder == i && forks[right]->holder != -1 && forks[right]->holder != i) {
                waiting_for[i] = forks[right]->holder;
            }
        }
    }
    // 遍历等待图检测环路（使用简单的访问记录），若发现环路说明存在死锁
    for (auto const& [start_node, _] : waiting_for) {
        int curr = start_node;
        std::vector<int> visited;
        while (waiting_for.count(curr)) {
            visited.push_back(curr);
            curr = waiting_for[curr];
            if (std::find(visited.begin(), visited.end(), curr) != visited.end()) {
                log_event(-1, "DEADLOCK", "Cycle detected involving Phil " + std::to_string(curr));
                return true;
            }
        }
    }
    return false;
}

std::vector<std::vector<int>> Simulation::get_resource_graph() {
    // 返回资源图的一个表示：每个 edge 三元组含义为 {philosopher, resource, holding_flag}
    // holding_flag = 1 表示哲学家占有该资源，0 表示在请求但未占有
    WinLockGuard lock(state_mutex);
    std::vector<std::vector<int>> edges;
    for (int i = 0; i < num_philosophers; ++i) {
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
    // 获取所有哲学家的状态（用于 UI 或外部监控），对共享状态上锁以保证一致性
    WinLockGuard lock(state_mutex);
    std::vector<int> result;
    for (auto s : states) result.push_back(static_cast<int>(s));
    return result;
}