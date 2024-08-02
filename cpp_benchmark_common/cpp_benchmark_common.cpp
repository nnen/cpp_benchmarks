#include "cpp_benchmark_common.h"


void TryClearingCache(benchmark::State &state)
{
    state.PauseTiming();

    constexpr size_t biggerThanCacheSize = 10 * 1024 * 1024;
    long *bigArray = new long[biggerThanCacheSize];

    memset(bigArray, 0, biggerThanCacheSize * sizeof(long));
    // for (size_t i = 0; i < biggerThanCacheSize; ++i)
    //{
    //    bigArray[i] = 0;
    // }

    delete[] bigArray;

    state.ResumeTiming();
}
