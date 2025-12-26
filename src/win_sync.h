#pragma once
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <process.h>
#else
#error "This file is only for Windows platform"
#endif

#include <atomic>
#include <functional>

// 封装 Windows CRITICAL_SECTION，提供 RAII 管理
class WinMutex {
public:
    WinMutex();
    ~WinMutex();

    void lock();
    bool try_lock();
    void unlock();

    WinMutex(const WinMutex&) = delete;
    WinMutex& operator=(const WinMutex&) = delete;

private:
    CRITICAL_SECTION cs;
};

// 封装 RAII 风格的锁守卫
class WinLockGuard {
public:
    explicit WinLockGuard(WinMutex& m) : mutex(m) {
        mutex.lock();
    }
    ~WinLockGuard() {
        mutex.unlock();
    }

    WinLockGuard(const WinLockGuard&) = delete;
    WinLockGuard& operator=(const WinLockGuard&) = delete;

private:
    WinMutex& mutex;
};

// 封装 Windows 信号量（可选，用于优化资源分配）
class WinSemaphore {
public:
    explicit WinSemaphore(long initial_count = 0, long max_count = 1);
    ~WinSemaphore();

    void wait();
    bool try_wait(DWORD timeout_ms = 0);
    void post();

    WinSemaphore(const WinSemaphore&) = delete;
    WinSemaphore& operator=(const WinSemaphore&) = delete;

private:
    HANDLE handle;
};

// 封装 Windows 线程
class WinThread {
public:
    WinThread() : handle(NULL) {}
    ~WinThread();

    // 启动线程（传入函数对象）
    template<typename Func>
    void start(Func&& func) {
        auto* wrapper = new std::function<void()>(std::forward<Func>(func));
        handle = (HANDLE)_beginthreadex(
            NULL, 0, thread_proc, wrapper, 0, NULL
        );
    }

    void join();
    bool joinable() const { return handle != NULL; }

    WinThread(const WinThread&) = delete;
    WinThread& operator=(const WinThread&) = delete;

private:
    HANDLE handle;

    static unsigned int __stdcall thread_proc(void* arg) {
        auto* func = static_cast<std::function<void()>*>(arg);
        (*func)();
        delete func;
        return 0;
    }
};
