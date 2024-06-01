import os
import sys
import urllib.request
from os.path import abspath, dirname
from time import sleep

from easyprocess import EasyProcess

webserver_code = """
from http.server import HTTPServer, CGIHTTPRequestHandler
srv = HTTPServer(server_address=("", 8080), RequestHandlerClass=CGIHTTPRequestHandler)
srv.serve_forever()
"""
os.chdir(dirname(abspath(__file__)))
with EasyProcess([sys.executable, "-c", webserver_code]):
    sleep(2)  # wait for server
    html = urllib.request.urlopen("http://localhost:8080").read().decode("utf-8")
print(html)
