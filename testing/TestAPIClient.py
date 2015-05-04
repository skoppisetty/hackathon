#!/usr/bin/env python
#
# Copyright (c) 2013 Liu, Yonggang <myidpt@gmail.com>, University of Florida
#
# This software may be used and distribted according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

# This preprocess is to set up the paths to make sure the current module
# referencing in the files to be tested.
import sys, os, unittest, tempfile, datetime, urllib2, subprocess
from threading import Thread
rootdir = os.path.dirname(os.getcwd())
sys.path.append(rootdir)
sys.path.append(os.path.join(rootdir, 'lib'))

from dataingestion.services import api_client
from dataingestion.services.api_client import ClientException

from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
from time import sleep
import threading
import ctypes

     
class TestAPIClient(unittest.TestCase):
  def setUp(self):
    self._endpoint = "http://127.0.0.1:8080"
    api_client.init(self._endpoint)
    # The following uuid/apikey pair is only for testing purpose.
    self._accountuuid = "60f7cb1e-02f5-425c-bc37-cae87550317a"
    self._apikey = "99f3ea05d8229a2f0d3aa1fcadf4a9a3"
    # Make the media file paths.
    self._filepath1 = os.path.join(os.getcwd(), "image1.jpg")
    self._filepath2 = os.path.join(os.getcwd(), "image2.jpg")
    self._invalidfilepath = "Notvalid/path.jpg"
    self._emptysruuid = ""
    self._startServer()
    sleep(0.1)
    subprocess.Popen(["sudo", "iptables", "-D", "OUTPUT", "-p", "tcp",
                      "-j", "DROP"])
    print "Please wait a few seconds ..."

  def tearDown(self):
    # Shut down the server.
    self._stopServer()
    subprocess.Popen(["sudo", "iptables", "-D", "OUTPUT", "-p", "tcp",
                      "-j", "DROP"])

  def _startServer(self):
    self._server_thread = Thread(target=self._serverThread)
    self._server_thread.start()

  def _stopServer(self):
    url = ("http://127.0.0.1:8080/upload/shutdown")
    request = urllib2.Request(url)
    try:
      urllib2.urlopen(request)
    except:
      pass
    self._server_thread.join()

  def _serverThread(arg):
    p = subprocess.Popen('stub_server/file-service.py',
                         shell=False,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    p.communicate()

  def _testAuthenticate(self):
    '''
    Test the authenticate function. It is also prerequisit for following tests.
    '''
    self.assertTrue(api_client.authenticate(self._accountuuid, self._apikey))
    print "Authentication test1 done."

    api_client.auth_string = None # Reset auth_string to remove the state.
    self.assertFalse(
        api_client.authenticate(
            "60f7cb1e-02f5-425c-bc37-thisiswrongid",
            self._apikey))
    print "Authentication test2 done."

    # Bring down the network and test.
    subprocess.Popen(["sudo", "iptables", "-A", "OUTPUT", "-p", "tcp",
                      "-j", "DROP"])
    sleep(2)
    self.assertRaises(ClientException,
                      api_client.authenticate,
                      "60f7cb1e-02f5-425c-bc37-thisiswrongid",
                      self._apikey)
    # Bring up the network again.
    subprocess.Popen(["sudo", "iptables", "-D", "OUTPUT", "-p", "tcp",
                      "-j", "DROP"])
    print "Authentication test3 done."


  def _testPostImage(self):
    '''Test _post_image.'''
    # The file exists.
    api_client._post_image(
        self._filepath1, "http://herbarium.bio.fsu.edu/images/herbarium/jpegs/E:\ImageIngestionAppliance\000000001.jpg")
    print "Post image test1 done."
    # The path does not exist.
    self.assertRaises(
        IOError, api_client._post_image, self._invalidfilepath, "ABC1")
    print "Post image test2 done."
    # The path is a directory.
    self.assertRaises(
        IOError, api_client._post_image, os.getcwd(), "ABC2")
    print "Post image test3 done."

    # Bring down the server and test.
    self._stopServer()
    self.assertRaises(ClientException,
                      api_client._post_image, self._filepath1, "ABC3")
    # Bring up the server again.
    self._startServer()
    sleep(0.2)
    print "Post image test4 done."

    # Bring down the network and test.
    subprocess.Popen(["sudo", "iptables", "-A", "OUTPUT", "-p", "tcp",
                      "-j", "DROP"])
    sleep(2)
    self.assertRaises(ClientException,
                      api_client._post_image, self._filepath1, "ABC4")
    # Bring up the network again.
    subprocess.Popen(["sudo", "iptables", "-D", "OUTPUT", "-p", "tcp",
                      "-j", "DROP"])
    print "Post image test5 done."

  def _testPostCsv(self):
    '''Test _post_csv.'''
    #f = tempfile.NamedTemporaryFile("wb")
    name = os.path.join(tempfile.gettempdir(), "temp.csv")
    f = open(name, "wb")
    f.write("test,test,test,test,test\ntest,test,test,test,test\n")
    f.close()
    api_client._post_csv(name)
    print "Post csv test done."

  def runTest(self):
    self._testAuthenticate()
    self._testPostImage()
    self._testPostCsv()

if __name__ == '__main__':
      unittest.main()
