cmake_minimum_required (VERSION 3.8)

file(GLOB_RECURSE modulo_vs_addif_SRC
    "*.h"
    "*.inl"
    "*.cpp")

add_executable(modulo_vs_addif ${modulo_vs_addif_SRC})

target_include_directories (modulo_vs_addif PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/..)

target_link_libraries(
    modulo_vs_addif 
    benchmark::benchmark
)

