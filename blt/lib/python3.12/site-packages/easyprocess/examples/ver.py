import sys

from easyprocess import EasyProcess

python = sys.executable
v = EasyProcess([python, "--version"]).call().stderr
print("your python version:%s" % v)
