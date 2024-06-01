import sys

from easyprocess import EasyProcess

python = sys.executable

prog = """
import time
for i in range(3):
    print(i, flush=True)
    time.sleep(1)
"""

print("-- no timeout")
stdout = EasyProcess([python, "-c", prog]).call().stdout
print(stdout)

print("-- timeout=1.5s")
stdout = EasyProcess([python, "-c", prog]).call(timeout=1.5).stdout
print(stdout)

print("-- timeout=50s")
stdout = EasyProcess([python, "-c", prog]).call(timeout=50).stdout
print(stdout)
