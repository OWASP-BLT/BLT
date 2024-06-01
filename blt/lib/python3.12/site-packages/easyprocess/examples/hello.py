from easyprocess import EasyProcess

cmd = ["echo", "hello"]
s = EasyProcess(cmd).call().stdout
print(s)
