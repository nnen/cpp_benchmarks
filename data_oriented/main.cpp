#include <benchmark/benchmark.h>

#include <cpp_benchmark_common/cpp_benchmark_common.h>

#include <memory>
#include <random>
#include <algorithm>


struct Vector3
{
   Vector3() = default;
   inline Vector3(float x, float y, float z) : x(x), y(y), z(z) {}

   inline Vector3 operator+(const Vector3& other) const
   {
      return Vector3(x + other.x, y + other.y, z + other.z);
   }

   inline Vector3 operator*(float scalar) const
   {
      return Vector3(x * scalar, y * scalar, z * scalar);
   }
   
   float x;
   float y;
   float z;
};


class OOPEntity : public std::enable_shared_from_this<OOPEntity>
{
public:
    virtual void Update(float dt) = 0;
};


class OOPEntityImpl : public OOPEntity
{
public:
   void Update(float dt) override
   {
      m_position = m_position + m_velocity * dt;
   }

private:
   Vector3 m_position;
   Vector3 m_velocity;
};


template<bool ClearCache = false, bool Shuffle = false, bool ExtraAllocs = false>
void BM_oop_tpl(benchmark::State& state)
{
   volatile size_t numEntities = static_cast<size_t>(state.range(0));
   volatile float dt = 0.016f;

   std::random_device rd;
   std::mt19937 gen(rd());
   std::uniform_int_distribution<> extraAllocDist(1, 3);

   std::vector<std::shared_ptr<OOPEntity>> entities;
   entities.reserve(numEntities);

   std::vector<std::shared_ptr<OOPEntity>> extraAllocsVec;

   for (size_t i = 0; i < numEntities; ++i)
   {
      entities.push_back(std::make_shared<OOPEntityImpl>());

      if constexpr (ExtraAllocs)
      {
         const int numAllocs = extraAllocDist(gen);
         
         for (int i = 0; i < numAllocs; ++i)
         {
            extraAllocsVec.push_back(std::make_shared<OOPEntityImpl>());
         }
      }
   }

   if constexpr (Shuffle)
   {
      std::shuffle(entities.begin(), entities.end(), gen);
   }

   for (auto _ : state)
   {
      if constexpr (ClearCache)
      {
         TryClearingCache(state);
      }

      for (auto& entity : entities)
      {
         entity->Update(dt);
      }
   }
}


void BM_oop(benchmark::State& state)
{
   BM_oop_tpl<>(state);
}


void BM_oop_cc(benchmark::State& state)
{
   BM_oop_tpl<true>(state);
}


void BM_oop_ealloc(benchmark::State& state)
{
   BM_oop_tpl<false, false, true>(state);
}


void BM_oop_ealloc_shfl(benchmark::State& state)
{
   BM_oop_tpl<false, true, true>(state);
}


struct DODEntity
{
   Vector3 m_position;
   Vector3 m_velocity;
};


void BM_dod(benchmark::State& state)
{
   volatile size_t numEntities = static_cast<size_t>(state.range(0));
   volatile float dt = 0.016f;
   
   std::vector<DODEntity> entities;
   entities.resize(numEntities);
   
   for (auto _ : state)
   {
      TryClearingCache(state);

      DODEntity* const start = &entities.front();
      const DODEntity* const end = start + numEntities;
      for (DODEntity* entity = start; entity < end; ++entity)
      {
         entity->m_position = entity->m_position + entity->m_velocity * dt;
      }
   }
}


void BM_dod_soa(benchmark::State& state)
{
   volatile size_t numEntities = static_cast<size_t>(state.range(0));
   volatile float dt = 0.016f;
   
   std::vector<Vector3> positions;
   std::vector<Vector3> velocities;
   positions.resize(numEntities);
   velocities.resize(numEntities);
   
   for (auto _ : state)
   {
      //TryClearingCache(state);

      Vector3* position = &positions.front();
      const Vector3* const positionEnd = position + numEntities;

      const Vector3* velocity = &velocities.front();
      const Vector3* const velocityEnd = velocity + numEntities;

      for (; position < positionEnd; ++position, ++velocity)
      {
         *position = *position + *velocity * dt;
      }
   }
}


constexpr benchmark::IterationCount NumIterations = 5;
constexpr benchmark::IterationCount NumIterationsShort = 200;
constexpr benchmark::TimeUnit BenchmarkTimeUnit = benchmark::kMillisecond;


#define MY_BENCHMARK_BASE(name_) \
   BENCHMARK(name_)->Unit(BenchmarkTimeUnit)
   //->UseRealTime() \
   //->MinTime(0.1) \
   //->Repetitions(10) \
   //->ReportAggregatesOnly(true)

#define MY_BENCHMARK(name_) \
   MY_BENCHMARK_BASE(name_) \
   ->Arg(100) \
   ->Arg(1000) \
   ->Arg(10000) \
   ->Arg(100000) \
   ->Arg(10000000) \
   ->Arg(20000000)

#define MY_BENCHMARK_SHORT(name_) \
   MY_BENCHMARK_BASE(name_) \
   /* ->Arg(100) */ \
   ->Arg(1000) \
   ->Arg(10000) \
   ->Arg(100000) \
   ->Iterations(NumIterationsShort)

#define MY_BENCHMARK_LONG(name_) \
   MY_BENCHMARK_BASE(name_) \
   ->Arg(1000000) \
   ->Arg(10000000) \
   ->Arg(20000000) \
   ->Arg(40000000) \
   ->Iterations(NumIterations)

#define MY_BENCHMARK_BOTH(name_) \
   MY_BENCHMARK_SHORT(name_); \
   MY_BENCHMARK_LONG(name_);


MY_BENCHMARK_BOTH(BM_oop);
MY_BENCHMARK_BOTH(BM_oop_cc);
MY_BENCHMARK_BOTH(BM_oop_ealloc);
MY_BENCHMARK_BOTH(BM_oop_ealloc_shfl);
MY_BENCHMARK_BOTH(BM_dod);
MY_BENCHMARK_BOTH(BM_dod_soa);
//BENCHMARK(BM_dod_soa)->Range(2 << 10, 2 << 21)->Unit(BenchmarkTimeUnit);
//BENCHMARK(BM_dod_soa)->DenseRange(1000, 10000000, 10);


BENCHMARK_MAIN();

