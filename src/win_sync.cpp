#include "win_sync.h"
#include <stdexcept>

// WinMutex 实现
WinMutex::WinMutex() {
    InitializeCriticalSection(&cs);
}

WinMutex::~WinMutex() {
    DeleteCriticalSection(&cs);
}

void WinMutex::lock() {
    EnterCriticalSection(&cs);
}

bool WinMutex::try_lock() {
    return TryEnterCriticalSection(&cs) != 0;
}

void WinMutex::unlock() {
    LeaveCriticalSection(&cs);
}

// WinSemaphore 实现
WinSemaphore::WinSemaphore(long initial_count, long max_count) {
    handle = CreateSemaphoreW(NULL, initial_count, max_count, NULL);
    if (handle == NULL) {
        throw std::runtime_error("CreateSemaphore failed");
    }
}

WinSemaphore::~WinSemaphore() {
    if (handle != NULL) {
        CloseHandle(handle);
    }
}

void WinSemaphore::wait() {
    WaitForSingleObject(handle, INFINITE);
}

bool WinSemaphore::try_wait(DWORD timeout_ms) {
    return WaitForSingleObject(handle, timeout_ms) == WAIT_OBJECT_0;
}

void WinSemaphore::post() {
    ReleaseSemaphore(handle, 1, NULL);
}

// WinThread 实现
WinThread::~WinThread() {
    if (handle != NULL) {
        CloseHandle(handle);
    }
}

void WinThread::join() {
    if (handle != NULL) {
        WaitForSingleObject(handle, INFINITE);
        CloseHandle(handle);
        handle = NULL;
    }
}
