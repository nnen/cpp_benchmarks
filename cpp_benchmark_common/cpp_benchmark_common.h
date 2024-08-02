#include <benchmark/benchmark.h>

#include <cstdint>


inline void TryClearingCache(benchmark::State& state)
{
   state.PauseTiming();

   const auto& cpuInfo = benchmark::CPUInfo::Get();

   size_t cacheSize = 0;
   for (const auto& cacheInfo : cpuInfo.caches)
   {
      if (cacheInfo.size > cacheSize)
      {
         cacheSize = cacheInfo.size;
      }
   }

   const size_t biggerThanCacheSize = cacheSize * 2;
   auto* bigArray = new uint8_t[biggerThanCacheSize];

   memset(bigArray, 0, biggerThanCacheSize * sizeof(uint8_t));

   delete[] bigArray;

   state.ResumeTiming();
}

