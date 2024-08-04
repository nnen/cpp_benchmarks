cmake_minimum_required (VERSION 3.8)

file(GLOB_RECURSE data_oriented2_SRC
    "*.h"
    "*.inl"
    "*.cpp")

add_executable(data_oriented2 ${data_oriented2_SRC})

target_include_directories (data_oriented2 PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/..)

target_link_libraries(
    data_oriented2 
    cpp_benchmark_common
    benchmark::benchmark
)

