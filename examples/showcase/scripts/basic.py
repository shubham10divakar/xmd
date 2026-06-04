"""Basic script — plain arithmetic and list operations. No imports needed."""
import sys

print("=== Basic Script ===")
if len(sys.argv) > 1:
    print(f"Args: {sys.argv[1:]}")
print()

nums = list(range(1, 11))
print(f"Numbers : {nums}")
print(f"Sum     : {sum(nums)}")
print(f"Min/Max : {min(nums)} / {max(nums)}")
print(f"Evens   : {[n for n in nums if n % 2 == 0]}")
print(f"Squares : {[n**2 for n in nums]}")
print()

words = ["runxmd", "makes", "markdown", "executable"]
print(f"Words   : {words}")
print(f"Joined  : {' '.join(words)}")
print(f"Upper   : {' '.join(w.upper() for w in words)}")
print(f"Lengths : {[len(w) for w in words]}")
