import sys

from easyprocess import EasyProcess

python = sys.executable

print("-- Run program, wait for it to complete, get stdout:")
s = EasyProcess([python, "-c", "print(3)"]).call().stdout
print(s)

print("-- Run program, wait for it to complete, get stderr:")
s = EasyProcess([python, "-c", "import sys;sys.stderr.write('4\\n')"]).call().stderr
print(s)

print("-- Run program, wait for it to complete, get return code:")
s = EasyProcess([python, "--version"]).call().return_code
print(s)

print("-- Run program, wait 1.5 second, stop it, get stdout:")
prog = """
import time
for i in range(10):
    print(i, flush=True)
    time.sleep(1)
"""
s = EasyProcess([python, "-c", prog]).start().sleep(1.5).stop().stdout
print(s)
