#include "simulation.h"
#include <chrono>
#include <random>
#include <algorithm>
#include <map>
#include <iostream>

Simulation::Simulation(int n_phil, int n_forks)
    : num_philosophers(n_phil), num_forks(n_forks), 
      states(n_phil, State::THINKING), 
      wait_counts(n_phil, 0),
      eat_counts(n_phil, 0),
      max_wait_counts(n_phil, 0) {
    for (int i = 0; i < n_forks; ++i) {
        forks.push_back(std::make_unique<Fork>());
    }

    // Calculate competitors (anyone who shares a fork)
    competitors.resize(n_phil);
    auto get_forks = [&](int id) {
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
    stop();
}

void Simulation::start() {
    if (running) return;
    running = true;
    for (int i = 0; i < num_philosophers; ++i) {
        threads.emplace_back(&Simulation::philosopher_thread, this, i);
    }
    log_event(-1, "SYSTEM", "Simulation started");
}

void Simulation::stop() {
    running = false;
    for (auto& t : threads) {
        if (t.joinable()) t.join();
    }
    threads.clear();

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
    std::lock_guard<std::mutex> lock(state_mutex);
    if (strategy_code == 1) current_strategy = Strategy::BANKER;
    else current_strategy = Strategy::NONE;
    log_event(-1, "SYSTEM", "Strategy changed to " + std::to_string(strategy_code));
}

void Simulation::log_event(int phil_id, const std::string& type, const std::string& details) {
    std::lock_guard<std::mutex> lock(event_mutex);
    auto now = std::chrono::system_clock::now().time_since_epoch();
    double ts = std::chrono::duration<double>(now).count();
    event_queue.push_back({ts, phil_id, type, details});
    if (event_queue.size() > 5000) event_queue.pop_front();
}

std::vector<SimEvent> Simulation::poll_events() {
    std::lock_guard<std::mutex> lock(event_mutex);
    std::vector<SimEvent> events(event_queue.begin(), event_queue.end());
    event_queue.clear();
    return events;
}

bool Simulation::is_safe_state(int phil_id, int fork_id) {
    std::vector<int> available(num_forks, 1);
    std::vector<int> need(num_philosophers, 2); 

    for (int i = 0; i < num_forks; ++i) {
        int holder = forks[i]->holder;
        if (holder != -1) {
            available[i] = 0;
            need[holder]--;
        }
    }

    if (available[fork_id] == 0) return false; 

    available[fork_id] = 0;
    need[phil_id]--;

    std::vector<bool> finish(num_philosophers, false);
    int finished_count = 0;

    while (finished_count < num_philosophers) {
        bool found = false;
        for (int i = 0; i < num_philosophers; ++i) {
            if (!finish[i]) {
                if (need[i] <= 0) { 
                    finish[i] = true;
                    finished_count++;
                    found = true;
                } else {
                    int left = (static_cast<long long>(i) * num_forks) / num_philosophers;
                    int right = (left + 1) % num_forks;
                    
                    bool left_ok = (forks[left]->holder == i) || (available[left] == 1);
                    if (i == phil_id && left == fork_id) left_ok = true;

                    bool right_ok = (forks[right]->holder == i) || (available[right] == 1);
                    if (i == phil_id && right == fork_id) right_ok = true;
                    
                    if (left_ok && right_ok) {
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
        if (!found) return false; 
    }
    return true;
}

bool Simulation::request_permission(int phil_id, int fork_id) {
    std::lock_guard<std::mutex> lock(state_mutex);

    // 1. 基础检查：叉子是否被占用
    if (forks[fork_id]->holder != -1) return false;

    // 2. 反饥饿机制 (Anti-Starvation)
    // 检查所有竞争者是否处于饥饿状态且等待时间过长
    for (int comp_id : competitors[phil_id]) {
        if (states[comp_id] == State::HUNGRY && 
            wait_counts[comp_id] > STARVATION_THRESHOLD && 
            wait_counts[comp_id] > wait_counts[phil_id]) {
            return false; // 礼让竞争者
        }
    }

    // 3. 策略分发
    if (current_strategy == Strategy::BANKER) {
        return is_safe_state(phil_id, fork_id);
    }
    else {
        return true; 
    }
}

void Simulation::philosopher_thread(int id) {
    int left = (static_cast<long long>(id) * num_forks) / num_philosophers;
    int right = (left + 1) % num_forks;

    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(500, 1000);

    while (running) {
        // THINKING
        {
            std::lock_guard<std::mutex> lock(state_mutex);
            states[id] = State::THINKING;
        }
        log_event(id, "STATE", "THINKING");
        std::this_thread::sleep_for(std::chrono::milliseconds(dis(gen)));

        // HUNGRY
        {
            std::lock_guard<std::mutex> lock(state_mutex);
            states[id] = State::HUNGRY;
            wait_counts[id] = 0; // 开始新一轮饥饿，计数归零
        }
        log_event(id, "STATE", "HUNGRY");

        bool has_eaten = false;
        while (running && !has_eaten) {
            if (request_permission(id, left)) {
                std::unique_lock<std::mutex> lock_l(forks[left]->mtx, std::defer_lock);
                if (lock_l.try_lock()) {
                    forks[left]->holder = id;
                    log_event(id, "ACQUIRE", "Left Fork " + std::to_string(left));

                    std::this_thread::sleep_for(std::chrono::milliseconds(10));

                    if (request_permission(id, right)) { 
                        std::unique_lock<std::mutex> lock_r(forks[right]->mtx, std::defer_lock);
                        if (lock_r.try_lock()) {
                            forks[right]->holder = id;
                            log_event(id, "ACQUIRE", "Right Fork " + std::to_string(right));

                            // EATING
                            {
                                std::lock_guard<std::mutex> lock(state_mutex);
                                states[id] = State::EATING;
                                
                                eat_counts[id]++;
                                if (wait_counts[id] > max_wait_counts[id]) {
                                    max_wait_counts[id] = wait_counts[id];
                                }
                                wait_counts[id] = 0; // 成功进食，重置计数
                            }
                            log_event(id, "STATE", "EATING");
                            std::this_thread::sleep_for(std::chrono::milliseconds(dis(gen)));

                            // 释放右手
                            forks[right]->holder = -1;
                            log_event(id, "RELEASE", "Right Fork " + std::to_string(right));
                            
                            // 释放左手
                            forks[left]->holder = -1;
                            log_event(id, "RELEASE", "Left Fork " + std::to_string(left));
                            
                            has_eaten = true;
                        } else {
                            forks[left]->holder = -1;
                            log_event(id, "RELEASE", "Left Fork " + std::to_string(left) + " (Backoff)");
                            std::this_thread::sleep_for(std::chrono::milliseconds(dis(gen) / 10));
                        }
                    } else {
                         forks[left]->holder = -1;
                         log_event(id, "RELEASE", "Left Fork " + std::to_string(left) + " (Permission Denied)");
                         std::this_thread::sleep_for(std::chrono::milliseconds(dis(gen) / 10));
                    }
                }
            }
            
            if (!has_eaten) {
                // 增加等待计数
                {
                    std::lock_guard<std::mutex> lock(state_mutex);
                    wait_counts[id]++;
                }
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
            }
        }
    }
}

bool Simulation::detect_deadlock() {
    std::lock_guard<std::mutex> lock(state_mutex);
    std::map<int, int> waiting_for; 
    for (int i = 0; i < num_philosophers; ++i) {
        if (states[i] == State::HUNGRY) {
            int left = (static_cast<long long>(i) * num_forks) / num_philosophers;
            int right = (left + 1) % num_forks;
            if (forks[left]->holder != i && forks[left]->holder != -1) {
                waiting_for[i] = forks[left]->holder;
            }
            else if (forks[left]->holder == i && forks[right]->holder != -1 && forks[right]->holder != i) {
                waiting_for[i] = forks[right]->holder;
            }
        }
    }
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
    std::lock_guard<std::mutex> lock(state_mutex);
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
    std::lock_guard<std::mutex> lock(state_mutex);
    std::vector<int> result;
    for (auto s : states) result.push_back(static_cast<int>(s));
    return result;
}