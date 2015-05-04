#!/usr/bin/env python
#
# Copyright (c) 2013 Liu, Yonggang <myidpt@gmail.com>, University of Florida
#
# This software may be used and distribted according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

# Test functions in result_generator.

import sys, os, unittest, tempfile, datetime

rootdir = os.path.dirname(os.getcwd())
sys.path.append(rootdir)
sys.path.append(os.path.join(rootdir, 'lib'))

from dataingestion.services import model, result_generator

class TestResultGenerator(unittest.TestCase):
  def setUp(self):
    '''Set up a tmp db, with a batch and a record for the testing.'''
    self._testDB = os.path.join(os.getcwd(), "idigbio.ingest_test.db")
    model.setup(self._testDB)

    path = os.path.join(os.getcwd(), "image1.jpg")
    accountID = "accountID"
    license = "license"
    licenseStatementUrl = "licenseurl"
    licenseLogoUrl = "licenselogourl"
    recordset_guid = "rs_guid"
    recordset_uuid = "rs_uuid"

    '''Test add_batch with minimum correct information.'''
    batch = model.add_batch(
        path, accountID, license, licenseStatementUrl, licenseLogoUrl,
        recordset_guid, recordset_uuid, None, None, None, None, None)

    # Batch information will be used in _testAddImage.
    self.assertIsNotNone(batch)

    mediaguid = "123123123" # Random

    '''A correct file path with minimum input.'''
    orig_filepath = os.path.join(os.getcwd(), "image1.jpg")
    csvrow = [orig_filepath, mediaguid]
    annotation = {"Field1": "Value1", "Field2": "Value2", "Field3": "Value3"}
    headerline = ["idigbio:OriginalFileName", "idigbio:MediaGUID", "Field1",
                   "Field2", "Field3"]
    csvrow = [orig_filepath, mediaguid, annotation["Field1"],
               annotation["Field2"], annotation["Field3"]]
    record = model.add_image(batch, csvrow, headerline)

    model.commit()


  def tearDown(self):
    '''Clean up the tmp db file.'''
    model.close()
    os.remove(self._testDB)

#----------------------------------------------------
# Tests.

  def _testGenerate(self):
    path = os.path.join(rootdir, os.path.join("testing", "test.zip"))
    result_generator.generate("1", path)

  def runTest(self):
    self._testGenerate()


if __name__ == '__main__':
      unittest.main()
