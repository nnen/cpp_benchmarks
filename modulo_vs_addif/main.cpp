#include <benchmark/benchmark.h>

#include <cstdint>


template<typename T>
struct Traits
{
   using Value = T;
   constexpr static Value MaxModulo = 32;
   constexpr static Value MaxLoop = 100;
};


template<typename Traits>
void BM_modulo(benchmark::State& state)
{
   using Value = typename Traits::Value;

   volatile Value maxModulo = Traits::MaxModulo;
   volatile Value maxLoop = Traits::MaxLoop;
   volatile Value result;

   for (auto _ : state)
   {
      for (volatile Value m = 1; m < maxModulo; ++m)
      {
         for (volatile Value i = 0; i < maxLoop; ++i)
         {
            benchmark::DoNotOptimize(result = ((i + 1) % m));
         }
      }
   }
}


template<typename Traits>
void BM_modulo_const(benchmark::State& state)
{
   using Value = typename Traits::Value;

   constexpr Value modulo = static_cast<Value>(0x10);
   volatile Value maxLoop = Traits::MaxLoop;
   volatile Value result;

   for (auto _ : state)
   {
      for (volatile Value j = 1; j < Traits::MaxModulo; ++j)
      {
         for (volatile Value i = 0; i < maxLoop; ++i)
         {
            benchmark::DoNotOptimize(result = ((i + 1) % modulo));
         }
      }
   }
}


template<typename Traits>
void BM_bitmask(benchmark::State& state)
{
   using Value = typename Traits::Value;

   constexpr Value mask = static_cast<Value>(0x0f);
   volatile Value maxLoop = Traits::MaxLoop;
   volatile Value result;

   for (auto _ : state)
   {
      for (volatile Value j = 1; j < Traits::MaxModulo; ++j)
      {
         for (volatile Value i = 0; i < maxLoop; ++i)
         {
            benchmark::DoNotOptimize(result = ((i + 1) & mask));
         }
      }
   }
}


template<typename Traits>
void BM_addif(benchmark::State& state)
{
   using Value = typename Traits::Value;

   volatile Value maxModulo = Traits::MaxModulo;
   volatile Value maxLoop = Traits::MaxLoop;
   volatile Value result;

   for (auto _ : state)
   {
      for (volatile Value m = 1; m < maxModulo; ++m)
      {
         for (volatile Value i = 0; i < maxLoop; ++i)
         {
            benchmark::DoNotOptimize(result = i + 1);
            if (result >= maxModulo)
            {
               result -= maxModulo;
            }
         }
      }
   }
}


template<typename Traits>
void BM_addwhile(benchmark::State& state)
{
   using Value = typename Traits::Value;

   volatile Value maxModulo = Traits::MaxModulo;
   volatile Value maxLoop = Traits::MaxLoop;
   volatile Value result;

   for (auto _ : state)
   {
      for (volatile Value m = 1; m < maxModulo; ++m)
      {
         for (volatile Value i = 0; i < maxLoop; ++i)
         {
            result = i + 1;
            while (result >= maxModulo)
            {
               result -= maxModulo;
            }
         }
      }
   }
}


//BENCHMARK_TEMPLATE(BM_modulo2, Traits<int64_t>)->Ranges({ {1, 32}, {0, 100} });

#define MY_BENCHMARK(name_) \
   BENCHMARK_TEMPLATE(name_, Traits<int32_t>)->Name(#name_ "/i32"); \
   BENCHMARK_TEMPLATE(name_, Traits<uint32_t>)->Name(#name_ "/u32"); \
   BENCHMARK_TEMPLATE(name_, Traits<int64_t>)->Name(#name_ "/i64"); \
   BENCHMARK_TEMPLATE(name_, Traits<uint64_t>)->Name(#name_ "/u64");


MY_BENCHMARK(BM_modulo)
MY_BENCHMARK(BM_modulo_const)
MY_BENCHMARK(BM_bitmask)
MY_BENCHMARK(BM_addwhile)
MY_BENCHMARK(BM_addif)


//BENCHMARK_TEMPLATE(BM_modulo, Traits<int32_t>);
//BENCHMARK_TEMPLATE(BM_modulo, Traits<uint32_t>);
//BENCHMARK_TEMPLATE(BM_modulo, Traits<int64_t>);
//BENCHMARK_TEMPLATE(BM_modulo, Traits<uint64_t>);

//BENCHMARK_TEMPLATE(BM_modulo_const, Traits<int32_t>);
//BENCHMARK_TEMPLATE(BM_modulo_const, Traits<uint32_t>);
//BENCHMARK_TEMPLATE(BM_modulo_const, Traits<int64_t>);
//BENCHMARK_TEMPLATE(BM_modulo_const, Traits<uint64_t>);

//BENCHMARK_TEMPLATE(BM_bitmask, Traits<int32_t>);
//BENCHMARK_TEMPLATE(BM_bitmask, Traits<uint32_t>);
//BENCHMARK_TEMPLATE(BM_bitmask, Traits<int64_t>);
//BENCHMARK_TEMPLATE(BM_bitmask, Traits<uint64_t>);

//BENCHMARK_TEMPLATE(BM_addwhile, Traits<int32_t>);
//BENCHMARK_TEMPLATE(BM_addwhile, Traits<uint32_t>);
//BENCHMARK_TEMPLATE(BM_addwhile, Traits<int64_t>);
//BENCHMARK_TEMPLATE(BM_addwhile, Traits<uint64_t>);

//BENCHMARK_TEMPLATE(BM_addif, Traits<int32_t>);
//BENCHMARK_TEMPLATE(BM_addif, Traits<uint32_t>);
//BENCHMARK_TEMPLATE(BM_addif, Traits<int64_t>);
//BENCHMARK_TEMPLATE(BM_addif, Traits<uint64_t>);


BENCHMARK_MAIN();

