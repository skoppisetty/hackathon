#!/usr/bin/env python
#
# Copyright (c) 2011 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php 
import os
from cherrypy.lib.static import serve_file

class DataIngestionUI(object):
    exposed = True
    
    def __init__(self):
        pass
    
    def GET(self):
        return serve_file(os.path.join(os.getcwd(), 'www', 'index.html'))