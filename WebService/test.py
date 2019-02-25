import os

cmd = """python test.py"""

originaldir = os.getcwd()
os.chdir('C:\\Users\\lenovo\\Desktop\\test')
a = os.system(cmd)

os.chdir(originaldir)
print(os.getcwd())