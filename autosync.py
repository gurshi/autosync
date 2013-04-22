#!/usr/bin/env python
from fsevents import Observer
import threading
import subprocess
import logging, logging.handlers

observer = Observer()
observer.start()

#### EDIT HERE ####
LOCALSRC      = "~"
REMOTEDST     = "ssh://user@machine/path-to-code"
UNISONOPTIONS = ["-auto","-batch", "-ignorecase", "false", "-terse",
                 "-ignore", "Name {GPATH,GRTAGS,GTAGS}",
                 "-ignore", "Name {cscope.files,cscope.out,ID}"]
UNISONCMD     = "/opt/local/bin/unison"
LOGFILE       = "/tmp/autosync.log"

###################
INTERVAL = 0.1 # sec
MAX_INTERVAL = 60 
interval = INTERVAL
pending = False
syncing  = False
LOCALPATH     = tuple(LOCALSRC.split("/"))

#FSEvent Callback
def fsevent(subpath, mask):
    logger.info("fsevent: %s", subpath)
    schedule(INTERVAL)

def schedule(timeout):
    global timer
    logger.debug("schedule: begin")
    with lock:
        if timer:
            timer.cancel()
        timer = threading.Timer(timeout, sync)
        timer.start()
    logger.debug("schedule: end")

#Timer Callback
def sync():
    global interval, syncing

    logger.debug("sync: begin %s" % str(syncing) )

    cmd = [UNISONCMD, LOCALSRC, REMOTEDST] + UNISONOPTIONS

    with lock:
        if syncing:
            schedule(INTERVAL)
            logger.debug("sync: return %s" % str(syncing) )
            return
        syncing = True

    f = file('/tmp/unison.out', 'w') 
    proc = subprocess.Popen( cmd, stdout=f, 
                             stderr=subprocess.STDOUT)
    logger.info("sync: start")
    ret = proc.wait()
    f.close()
    for out in file('/tmp/unison.out'):
        logger.info(out.strip())

    if ret != 0:
        logger.error("sync: failed.")
        interval = MAX_INTERVAL if interval >= MAX_INTERVAL else interval * 2
        logger.info("sync: wait %s secounds" % (interval)) 
        schedule(interval)
    else:
        interval = INTERVAL
        logger.info("sync: done")

    syncing = False
    logger.debug("sync: end %s" % str(syncing)) 

#Setup Callbacks
from fsevents import Stream

logger = logging.getLogger()
logger.setLevel(logging.INFO)
fh = logging.handlers.RotatingFileHandler(LOGFILE, maxBytes=10*1024*1024,
                                          backupCount=1)
formatter = logging.Formatter("%(asctime)s - %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)


lock = threading.RLock()
timer = None
schedule(INTERVAL)

stream = Stream(fsevent, LOCALSRC)
observer.schedule(stream)
