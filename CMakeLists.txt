cmake_minimum_required(VERSION 3.16)
project(DiningPhilosophers)

# 设置 C++ 标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 1. 自动寻找 Python 解释器和开发库
find_package(Python COMPONENTS Interpreter Development REQUIRED)

# 2. 寻找 pybind11
# 如果是通过 pip 安装的，通常需要以下方式定位
execute_process(
    COMMAND "${Python_EXECUTABLE}" -m pybind11 --cmakedir
    OUTPUT_VARIABLE pybind11_CMake_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)
list(APPEND CMAKE_PREFIX_PATH "${pybind11_CMake_DIR}")
find_package(pybind11 REQUIRED)

# 3. 定义 C++ 模块 (源文件放在 src 目录下)
# 模块名称为 sim_core，Python 中将通过 import sim_core 使用
pybind11_add_module(sim_core 
    src/main.cpp 
    src/simulation.cpp
)

# 4. 指定头文件目录
target_include_directories(sim_core PRIVATE src)

# 5. Windows 平台特殊处理 (确保生成 .pyd 文件)
if(WIN32)
    set_target_properties(sim_core PROPERTIES SUFFIX ".pyd")
endif()