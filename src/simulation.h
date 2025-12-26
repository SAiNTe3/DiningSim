#pragma once
#include <vector>
#include <string>
#include <memory>
#include <deque>
#include "win_sync.h" // 使用 Windows 同步原语封装

enum class State { THINKING, HUNGRY, EATING };
enum class Strategy { NONE, BANKER }; 

struct Fork {
    WinMutex mtx; // 使用 WinMutex
    int holder; 
    
    Fork() : holder(-1) {}
    
    // 禁止拷贝
    Fork(const Fork&) = delete;
    Fork& operator=(const Fork&) = delete;
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
    volatile bool running; 
    Strategy current_strategy;

    std::vector<State> states;
    std::vector<std::unique_ptr<Fork>> forks;
    std::vector<std::unique_ptr<WinThread>> threads; // 使用 WinThread
    
    // 饥饿计数器，用于防止饥饿
    std::vector<int> wait_counts;
    std::vector<int> eat_counts;
    std::vector<int> max_wait_counts;
    std::vector<std::vector<int>> competitors;
    const int STARVATION_THRESHOLD = 10;

    WinMutex event_mutex; // 使用 WinMutex
    std::deque<SimEvent> event_queue;
    void log_event(int phil_id, const std::string& type, const std::string& details);

    WinMutex state_mutex; // 使用 WinMutex

    void philosopher_thread(int id);
    bool request_permission(int phil_id, int fork_id);
    
    bool is_safe_state(int phil_id, int fork_id);
};