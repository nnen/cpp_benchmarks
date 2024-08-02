cmake_minimum_required (VERSION 3.8)

file(GLOB_RECURSE cpp_benchmark_common_SRC
    "*.h"
    "*.inl"
    "*.cpp")

add_library(cpp_benchmark_common ${cpp_benchmark_common_SRC})

target_include_directories (cpp_benchmark_common PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/..)

target_link_libraries(
    cpp_benchmark_common 
    benchmark::benchmark
)
