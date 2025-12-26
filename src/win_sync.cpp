#include "win_sync.h"
#include <stdexcept>

// WinMutex implementation
WinMutex::WinMutex() {
#ifdef _WIN32
    InitializeCriticalSection(&cs);
#else
    pthread_mutex_init(&mutex, NULL);
#endif
}

WinMutex::~WinMutex() {
#ifdef _WIN32
    DeleteCriticalSection(&cs);
#else
    pthread_mutex_destroy(&mutex);
#endif
}

void WinMutex::lock() {
#ifdef _WIN32
    EnterCriticalSection(&cs);
#else
    pthread_mutex_lock(&mutex);
#endif
}

bool WinMutex::try_lock() {
#ifdef _WIN32
    return TryEnterCriticalSection(&cs) != 0;
#else
    return pthread_mutex_trylock(&mutex) == 0;
#endif
}

void WinMutex::unlock() {
#ifdef _WIN32
    LeaveCriticalSection(&cs);
#else
    pthread_mutex_unlock(&mutex);
#endif
}

// WinSemaphore implementation
WinSemaphore::WinSemaphore(long initial_count, long max_count) {
#ifdef _WIN32
    handle = CreateSemaphoreW(NULL, initial_count, max_count, NULL);
    if (handle == NULL) {
        throw std::runtime_error("CreateSemaphore failed");
    }
#else
    if (sem_init(&sem, 0, initial_count) != 0) {
        throw std::runtime_error("sem_init failed");
    }
#endif
}

WinSemaphore::~WinSemaphore() {
#ifdef _WIN32
    if (handle != NULL) {
        CloseHandle(handle);
    }
#else
    sem_destroy(&sem);
#endif
}

void WinSemaphore::wait() {
#ifdef _WIN32
    WaitForSingleObject(handle, INFINITE);
#else
    sem_wait(&sem);
#endif
}

#ifdef _WIN32
bool WinSemaphore::try_wait(DWORD timeout_ms) {
    return WaitForSingleObject(handle, timeout_ms) == WAIT_OBJECT_0;
}
#else
bool WinSemaphore::try_wait(unsigned int timeout_ms) {
    if (timeout_ms == 0) {
        return sem_trywait(&sem) == 0;
    } else {
        struct timespec ts;
        clock_gettime(CLOCK_REALTIME, &ts);
        ts.tv_sec += timeout_ms / 1000;
        ts.tv_nsec += (timeout_ms % 1000) * 1000000;
        if (ts.tv_nsec >= 1000000000) {
            ts.tv_sec += 1;
            ts.tv_nsec -= 1000000000;
        }
        return sem_timedwait(&sem, &ts) == 0;
    }
}
#endif

void WinSemaphore::post() {
#ifdef _WIN32
    ReleaseSemaphore(handle, 1, NULL);
#else
    sem_post(&sem);
#endif
}

// WinThread implementation
WinThread::~WinThread() {
#ifdef _WIN32
    if (handle != NULL) {
        CloseHandle(handle);
    }
#else
    if (started) {
        pthread_detach(thread_id);
    }
#endif
}

void WinThread::join() {
#ifdef _WIN32
    if (handle != NULL) {
        WaitForSingleObject(handle, INFINITE);
        CloseHandle(handle);
        handle = NULL;
    }
#else
    if (started) {
        pthread_join(thread_id, NULL);
        started = false;
    }
#endif
}
