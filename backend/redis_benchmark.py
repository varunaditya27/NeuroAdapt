import asyncio
import statistics
import time

from backend.db import redis_client


async def benchmark(iterations: int = 1000) -> None:
    key = "bench:key"
    payload = "[0.1,0.2,0.3,0.4,0.5]"

    try:
        await redis_client.set(key, payload, ex=60)

        samples_ms = []
        for _ in range(iterations):
            start = time.perf_counter()
            await redis_client.get(key)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            samples_ms.append(elapsed_ms)

        p50 = statistics.median(samples_ms)
        p99_index = max(0, int(iterations * 0.99) - 1)
        p99 = sorted(samples_ms)[p99_index]

        print(f"Iterations: {iterations}")
        print(f"p50 latency: {p50:.3f} ms")
        print(f"p99 latency: {p99:.3f} ms")
    finally:
        close_method = getattr(redis_client, "aclose", None)
        if close_method is not None:
            await close_method()


if __name__ == "__main__":
    asyncio.run(benchmark())
