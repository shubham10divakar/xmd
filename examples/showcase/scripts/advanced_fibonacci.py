"""Advanced Python script — Fibonacci with memoization + prime sieve."""
from functools import lru_cache
import time

# ── Fibonacci with memoization ───────────────────────────────────────────────

@lru_cache(maxsize=None)
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

start = time.perf_counter()
targets = [10, 20, 30, 40, 50]
results = [(n, fib(n)) for n in targets]
elapsed = (time.perf_counter() - start) * 1000

print("=== Fibonacci with Memoization ===")
for n, value in results:
    print(f"  fib({n:>2}) = {value:>12,}")
print(f"\n  Computed in {elapsed:.3f} ms")
print(f"  Cache hits : {fib.cache_info().hits}")

# ── Sieve of Eratosthenes ────────────────────────────────────────────────────

def sieve(limit):
    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False
    for i in range(2, int(limit**0.5) + 1):
        if is_prime[i]:
            for j in range(i * i, limit + 1, i):
                is_prime[j] = False
    return [i for i, p in enumerate(is_prime) if p]

primes = sieve(100)
print(f"\n=== Primes up to 100 ({len(primes)} found) ===")
print(f"  {primes}")
print(f"  Sum of primes: {sum(primes)}")
