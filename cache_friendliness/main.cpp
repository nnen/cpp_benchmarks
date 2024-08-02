#include <benchmark/benchmark.h>

#include <cpp_benchmark_common/cpp_benchmark_common.h>

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


void BM_sort_array(benchmark::State& state)
{
   volatile std::size_t size = state.range(0);

   uint32_t* array = new uint32_t[size];

   InitSequence(array, array + size);

   for (auto _ : state)
   {
      TryClearingCache(state);

      std::sort(array, array + size);
   }
   
   delete[] array;
}


void BM_sort_vector(benchmark::State& state)
{
   volatile std::size_t size = state.range(0);

   std::vector<uint32_t> vector;
   vector.resize(size);
   InitSequence(vector.begin(), vector.end());

   for (auto _ : state)
   {
      TryClearingCache(state);

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
   volatile std::size_t size = state.range(0);

   using Ptr = std::shared_ptr<ValueOnHeap>;
   Ptr* array = new Ptr[size];

   for (size_t i = 0; i < size; ++i)
   {
      array[i] = std::make_shared<ValueOnHeap>();
      array[i]->m_value = static_cast<uint32_t>(i);
   }

   for (auto _ : state)
   {
      TryClearingCache(state);

      std::sort(array, array + size, ValueOnHeap::LessThan());
   }

   delete[] array;
}


#define MY_BENCHMARK(name_) \
   BENCHMARK(name_)->Unit(benchmark::kMillisecond)->Iterations(100)->Range(1024, 1024 << 12);


MY_BENCHMARK(BM_sort_array);
MY_BENCHMARK(BM_sort_vector);
MY_BENCHMARK(BM_sort_values_on_heap);


BENCHMARK_MAIN();
