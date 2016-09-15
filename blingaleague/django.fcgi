#!/usr/bin/env python
import sys, os
from os import path
import site

this_dir = path.realpath(path.dirname(path.dirname(__file__)))
print this_dir

# Add a custom Python path.
sys.path.insert(0, this_dir)

# Switch to the directory of your project. (Optional.)
os.chdir(path.join(this_dir, '..'))

# Set the DJANGO_SETTINGS_MODULE environment variable.
os.environ['DJANGO_SETTINGS_MODULE'] = "settings"

site.addsitedir(path.join(this_dir,"..","environ","lib","python2.7","site-packages"))

from django.core.servers.fastcgi import runfastcgi
runfastcgi(
# These options are not needed for non-daemonized processes
#    socket=path.join(this_dir, 'django.sock'),
#    pidfile=path.join(this_dir, 'django.pid'),
    method='prefork',
    maxspare=4,
    minspare=1,
    maxchildren=16,
    maxrequests='30',
    workdir=this_dir,
    daemonize="no",
    umask='002',
)

