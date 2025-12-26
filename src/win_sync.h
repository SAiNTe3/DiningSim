#pragma once
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <process.h>
#else
// POSIX/Linux support
#include <pthread.h>
#include <semaphore.h>
#include <unistd.h>
#include <time.h>
#endif

#include <atomic>
#include <functional>

// Cross-platform Mutex wrapper
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
#ifdef _WIN32
    CRITICAL_SECTION cs;
#else
    pthread_mutex_t mutex;
#endif
};

// RAII lock guard
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

// Cross-platform Semaphore wrapper
class WinSemaphore {
public:
    explicit WinSemaphore(long initial_count = 0, long max_count = 1);
    ~WinSemaphore();

    void wait();
#ifdef _WIN32
    bool try_wait(DWORD timeout_ms = 0);
#else
    bool try_wait(unsigned int timeout_ms = 0);
#endif
    void post();

    WinSemaphore(const WinSemaphore&) = delete;
    WinSemaphore& operator=(const WinSemaphore&) = delete;

private:
#ifdef _WIN32
    HANDLE handle;
#else
    sem_t sem;
#endif
};

// Cross-platform Thread wrapper
class WinThread {
public:
#ifdef _WIN32
    WinThread() : handle(NULL) {}
#else
    WinThread() : thread_id(0), started(false) {}
#endif
    ~WinThread();

    // Start thread with function
    template<typename Func>
    void start(Func&& func) {
        auto* wrapper = new std::function<void()>(std::forward<Func>(func));
#ifdef _WIN32
        handle = (HANDLE)_beginthreadex(
            NULL, 0, thread_proc, wrapper, 0, NULL
        );
#else
        started = true;
        pthread_create(&thread_id, NULL, thread_proc, wrapper);
#endif
    }

    void join();
#ifdef _WIN32
    bool joinable() const { return handle != NULL; }
#else
    bool joinable() const { return started; }
#endif

    WinThread(const WinThread&) = delete;
    WinThread& operator=(const WinThread&) = delete;

private:
#ifdef _WIN32
    HANDLE handle;

    static unsigned int __stdcall thread_proc(void* arg) {
        auto* func = static_cast<std::function<void()>*>(arg);
        (*func)();
        delete func;
        return 0;
    }
#else
    pthread_t thread_id;
    bool started;

    static void* thread_proc(void* arg) {
        auto* func = static_cast<std::function<void()>*>(arg);
        (*func)();
        delete func;
        return nullptr;
    }
#endif
};
