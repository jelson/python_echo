import datetime
import sys

LOGFILE_NAME = "/mnt/storage/logs/echo/echolog"
logfile = open(LOGFILE_NAME, "a")

def say(s):
    print(s)
    sys.stdout.flush()
    logfile.write(f"{datetime.datetime.now()}: {s}\n")
    logfile.flush()

