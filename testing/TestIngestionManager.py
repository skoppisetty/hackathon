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

from dataingestion.services import (api_client, model, user_config,
                                    ingestion_manager)
from time import sleep

class TestIngestionManager(unittest.TestCase):
  def setUp(self):
    api_client.init("http://beta-api.idigbio.org/v1")
    self._testDB = os.path.join(os.getcwd(), "idigbio.ingest.db")
    if os.path.exists(self._testDB):
      os.remove(self._testDB) # Make sure the database is clean.
    model.setup(os.path.join(os.getcwd(), "idigbio.ingest.db"))
    user_config.setup(os.path.join(os.getcwd(), "user.config"))
    self.assertTrue(
        api_client.authenticate("60f7cb1e-02f5-425c-bc37-cae87550317a",
                                "99f3ea05d8229a2f0d3aa1fcadf4a9a3"))
    self._csvfile1 = "file1.csv"
    self._csvfile2 = "file2.csv"
    header =  "\"idigbio:OriginalFileName\", \"idigbio:MediaGUID\""
    content1 = ("\"" + os.path.join(os.getcwd(), "image1.jpg") + "\", \""
                + "abc" + "\"")
    content2 = ("\"" + os.path.join(os.getcwd(), "wrongimage2.jpg") + "\", \""
                + "efg" + "\"")
    with open(self._csvfile1, "wb") as f:
      f.write(header + "\n")
      f.write(content1)
    with open(self._csvfile2, "wb") as f:
      f.write(header + "\n")
      f.write(content1 + "\n")
      f.write(content2)
    self._startServer()
    sleep(0.1)

  def tearDown(self):
    '''Clean up the tmp db file.'''
    model.close()
    os.remove(self._testDB)
    os.remove(self._csvfile1)
    os.remove(self._csvfile2)
    self._stopServer()

  def _startServer(self):
    self._server_thread = Thread(target=self._serverThread)
    self._server_thread.start()

  def _stopServer(self):
    url = ("http://127.0.0.1:8080/shutdown")
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

 
  def _testUploadTask(self):
    '''Test 1, successful.'''
    values = {
      user_config.CSV_PATH: os.path.join(os.getcwd(), "file1.csv"),
      user_config.RIGHTS_LICENSE: "CC0"}
    ingestion_manager.upload_task(values)
    sleep(1)
    (fatal_srv_err, input_csv_err, total, skips, success, fails,
     csvuploaded, finished) = ingestion_manager.get_progress()
    self.assertFalse(fatal_srv_err)
    self.assertFalse(input_csv_err)
    self.assertEqual(total, 1)
    self.assertEqual(skips, 0)
    self.assertEqual(success, 1)
    self.assertEqual(fails, 0)
    self.assertTrue(csvuploaded)
    self.assertTrue(finished)
    result = ingestion_manager.get_result()
    self.assertIsNotNone(result)

    '''Task 2, partially fails.'''
    values[user_config.CSV_PATH] = os.path.join(os.getcwd(), "file2.csv")
    ingestion_manager.upload_task(values)
    sleep(1)
    (fatal_srv_err, input_csv_err, total, skips, success, fails,
     csvuploaded, finished) = ingestion_manager.get_progress()
    self.assertFalse(fatal_srv_err)
    self.assertFalse(input_csv_err)
    self.assertEqual(total, 2)
    self.assertEqual(skips, 1)
    self.assertEqual(success, 0)
    self.assertEqual(fails, 1)
    self.assertFalse(csvuploaded)
    self.assertTrue(finished)
    result = ingestion_manager.get_result()
    self.assertIsNotNone(result)

  def runTest(self):
    self._testUploadTask()


if __name__ == '__main__':
      unittest.main()
