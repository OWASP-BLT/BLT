import logging
import sys

from easyprocess import EasyProcess

python = sys.executable

# turn on logging
logging.basicConfig(level=logging.DEBUG)

EasyProcess([python, "--version"]).call()
EasyProcess(["ping", "localhost"]).start().sleep(1).stop()
