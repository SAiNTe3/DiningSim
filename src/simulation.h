#pragma once
#include <vector>
#include <thread>
#include <mutex>
#include <atomic>
#include <string>
#include <memory>
#include <deque>

enum class State { THINKING, HUNGRY, EATING };
enum class Strategy { NONE, BANKER }; 

struct Fork {
    std::mutex mtx;
    std::atomic<int> holder{ -1 };
};

struct SimEvent {
    double timestamp;
    int phil_id;
    std::string event_type; 
    std::string details;
};

class Simulation {
public:
    Simulation(int n_phil, int n_forks);
    ~Simulation();

    void start();
    void stop();
    
    void set_strategy(int strategy_code);

    std::vector<int> get_states();
    std::vector<std::vector<int>> get_resource_graph();
    
    std::vector<SimEvent> poll_events();

    bool detect_deadlock();

private:
    int num_philosophers;
    int num_forks;
    std::atomic<bool> running{ false };
    Strategy current_strategy{ Strategy::NONE };

    std::vector<State> states;
    std::vector<std::unique_ptr<Fork>> forks;
    std::vector<std::thread> threads;
    
    // 新增：饥饿计数器，用于防止饥饿
    std::vector<int> wait_counts;
    std::vector<int> eat_counts;
    std::vector<int> max_wait_counts;
    std::vector<std::vector<int>> competitors;
    const int STARVATION_THRESHOLD = 10; // 饥饿阈值：失败10次后被视为"饥饿"

    std::mutex event_mutex;
    std::deque<SimEvent> event_queue;
    void log_event(int phil_id, const std::string& type, const std::string& details);

    std::mutex state_mutex;

    void philosopher_thread(int id);
    bool request_permission(int phil_id, int fork_id);
    
    bool is_safe_state(int phil_id, int fork_id);
};