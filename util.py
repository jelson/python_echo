import datetime
import sys

from config import LOGFILE_NAME

logfile = open(LOGFILE_NAME, "a")

def say(s):
    print(s)
    sys.stdout.flush()
    logfile.write(f"{datetime.datetime.now()}: {s}\n")
    logfile.flush()

