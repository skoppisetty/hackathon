#!/usr/bin/env python

import os
import sys
localDir = os.path.dirname(__file__)
absDir = os.path.join(os.getcwd(), localDir)

import cherrypy
import json

import hashlib

class FileDemo(object):

    def index(self):
        return """
        <html><body>
            <h2>Upload a file</h2>
            <form action="images" method="post" enctype="multipart/form-data">
            filename: <input type="file" name="file" /><br />
            <input type="submit" />
            </form>
            <h2>Download a file</h2>
            <a href='download'>This one</a>
        </body></html>
        """
    index.exposed = True

    @cherrypy.tools.json_out()
    def images(self, file, filereference):
        out = """<html>
        <body>
            myFile length: %s<br />
            myFile filename: %s<br />
            myFile mime-type: %s<br />
            myFile md5-sum: %s
        </body>
        </html>"""

        # Although this just counts the file length, it demonstrates
        # how to read large files in chunks instead of all at once.
        # CherryPy reads the uploaded file into a temporary file;
        # myFile.file.read reads from that.
        size = 0

        m = hashlib.md5()
        size = 0
        while True:
            data = file.file.read(8192)
            if not data:
                break
            size += len(data)
            m.update(data)
        file.file.seek(0)
        h = m.hexdigest()
        return { 
            "file_size": size,
            "file_name": unicode(file.filename),            
            "file_md5": h,
            "file_reference": filereference,
            "content_type": unicode(file.content_type),
            "file_url": "127.0.0.1:8080/"+h
        }
    images.exposed = True

    @cherrypy.tools.json_out()
    def datasets(self, file):
        out = """<html>
        <body>
            myFile length: %s<br />
            myFile filename: %s<br />
            myFile mime-type: %s<br />
            myFile md5-sum: %s
        </body>
        </html>"""

        # Although this just counts the file length, it demonstrates
        # how to read large files in chunks instead of all at once.
        # CherryPy reads the uploaded file into a temporary file;
        # myFile.file.read reads from that.
        size = 0
        m = hashlib.md5()
        size = 0
        while True:
            data = file.file.read(8192)
            print data
            if not data:
                break
            size += len(data)
            m.update(data)
        file.file.seek(0)
        h = m.hexdigest()
        return { 
            "file_size": size,
            "file_name": unicode(file.filename),            
            "file_md5": h,
            "content_type": unicode(file.content_type),
            "file_url": "127.0.0.1:8080/"+h
        }
    datasets.exposed = True

    @cherrypy.tools.json_out()
    def shutdown(self):
      sys.exit()
    shutdown.exposed = True


tutconf = os.path.join(os.path.dirname(__file__), 'tutorial.conf')

if __name__ == '__main__':
    # CherryPy always starts with app.root when trying to map request URIs
    # to objects, so we need to mount a request handler root. A request
    # to '/' will be mapped to HelloWorld().index().
    cherrypy.quickstart(FileDemo(), script_name="/upload", config=tutconf)
else:
    # This branch is for the test suite; you can ignore it.
    cherrypy.tree.mount(FileDemo(), config=tutconf)
