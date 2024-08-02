cmake_minimum_required (VERSION 3.8)

file(GLOB_RECURSE cache_friendliness_SRC
    "*.h"
    "*.inl"
    "*.cpp")

add_executable(cache_friendliness ${cache_friendliness_SRC})

target_include_directories (cache_friendliness PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/..)

target_link_libraries(
    cache_friendliness 
    cpp_benchmark_common
    benchmark::benchmark
)

