#include <benchmark/benchmark.h>

#include <cstdint>
#include <algorithm>
#include <memory>


template<typename T>
void InitSequence(T begin, T end)
{
   std::uint32_t i = 0;
   while (begin != end)
   {
      *begin = i++;
      ++begin;
   }
}


void TryClearingCache()
{
   constexpr size_t biggerThanCacheSize = 10 * 1024 * 1024;
   long* bigArray = new long[biggerThanCacheSize];

   for (size_t i = 0; i < biggerThanCacheSize; ++i)
   {
      //bigArray[i] = rand();
      bigArray[i] = 0;
   }

   delete[] bigArray;
}


void BM_sort_array(benchmark::State& state)
{
   constexpr std::size_t size = 1024;
   std::uint32_t array[size];

   InitSequence(array, array + size);

   for (auto _ : state)
   {
      state.PauseTiming();
      TryClearingCache();
      state.ResumeTiming();

      std::sort(array, array + size);
   }
}


void BM_sort_vector(benchmark::State& state)
{
   constexpr std::size_t size = 1024;

   std::vector<uint32_t> vector;
   vector.resize(size);
   InitSequence(vector.begin(), vector.end());

   for (auto _ : state)
   {
      state.PauseTiming();
      TryClearingCache();
      state.ResumeTiming();

      std::sort(vector.begin(), vector.end());
   }
}


struct ValueOnHeap : public std::enable_shared_from_this<ValueOnHeap>
{
   std::uint32_t m_value;

   struct LessThan
   {
      bool operator()(const std::shared_ptr<ValueOnHeap>& lhs, const std::shared_ptr<ValueOnHeap>& rhs) const
      {
         return lhs->m_value < rhs->m_value;
      }
   };
};


void BM_sort_values_on_heap(benchmark::State& state)
{
   constexpr std::size_t size = 1024;

   using Ptr = std::shared_ptr<ValueOnHeap>;
   Ptr array[size];

   for (size_t i = 0; i < size; ++i)
   {
      array[i] = std::make_shared<ValueOnHeap>();
      array[i]->m_value = static_cast<uint32_t>(i);
   }

   for (auto _ : state)
   {
      state.PauseTiming();
      TryClearingCache();
      state.ResumeTiming();

      std::sort(array, array + size, ValueOnHeap::LessThan());
   }
}


BENCHMARK(BM_sort_array)->Iterations(100);
BENCHMARK(BM_sort_vector)->Iterations(100);
BENCHMARK(BM_sort_values_on_heap)->Iterations(100);


BENCHMARK_MAIN();
