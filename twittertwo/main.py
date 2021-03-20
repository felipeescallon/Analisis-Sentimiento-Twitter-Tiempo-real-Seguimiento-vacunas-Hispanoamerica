from TwStreamListener import *

print("Start process")
myStreamListener = TwStreamListener()
print("myStreamListener.__init__() EXECUTED")
myStreamListener.connect()
print("myStreamListener.connect() EXECUTED")
myStreamListener.run()
print("myStreamListener.run() EXECUTED")
print("Stop process")