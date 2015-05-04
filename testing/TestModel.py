#!/usr/bin/env python
#
# Copyright (c) 2013 Liu, Yonggang <myidpt@gmail.com>, University of Florida
#
# This software may be used and distribted according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

# This preprocess is to set up the paths to make sure the current module
# referencing in the files to be tested.

import sys, os, unittest, tempfile, datetime
rootdir = os.path.dirname(os.getcwd())
sys.path.append(rootdir)
sys.path.append(os.path.join(rootdir, 'lib'))

from dataingestion.services import model

class TestModel(unittest.TestCase):
  def setUp(self):
    '''Set up a tmp db file for the testing.'''
    self._testDB = os.path.join(os.getcwd(), "idigbio.ingest_test.db")
    model.setup(self._testDB)

  def tearDown(self):
    '''Clean up the tmp db file.'''
    model.close()
    os.remove(self._testDB)

  def _validateBatchFields(
      self, batch, path, accountID, license, licenseStatementUrl,
      licenseLogoUrl):
    '''Validate a upload batch has the field values same as given.'''
    self.assertEqual(batch.CSVfilePath, path)
    self.assertEqual(batch.iDigbioProvidedByGUID, accountID)
    self.assertEqual(batch.RightsLicense, license)
    self.assertEqual(batch.RightsLicenseStatementUrl, licenseStatementUrl)
    self.assertEqual(batch.RightsLicenseLogoUrl, licenseLogoUrl)
    self.assertIsNone(batch.finish_time)

  def _validateImageRecordFields(
      self, record, filepath, mediaguid, sruuid, error, warnings, mimetype,
      msize, annotations, batchID):
    '''Validate a image record has the field values same as given.'''
    self.assertEqual(record.OriginalFileName, filepath)
    self.assertEqual(record.MediaGUID, mediaguid)
    self.assertEqual(record.SpecimenRecordUUID, sruuid)
    self.assertEqual(record.Error, error)
    self.assertEqual(record.Warnings, warnings)
    self.assertEqual(record.MimeType, mimetype)
    if record.MediaSizeInBytes and msize:
      self.assertEqual(int(record.MediaSizeInBytes), int(msize))
    else:
      self.assertEqual(record.MediaSizeInBytes, msize)
    self.assertEqual(record.Annotations, annotations)
    self.assertEqual(record.BatchID, batchID)
    # We do not validate the value of the following fields because they
    # may change or there is no need.
    self.assertIsNotNone(record.ProviderCreatedTimeStamp)
    self.assertIsNotNone(record.ProviderCreatedByGUID)
    self.assertIsNotNone(record.MediaEXIF)
    self.assertIsNotNone(record.MediaMD5)
    self.assertIsNotNone(record.AllMD5)

#----------------------------------------------------
# Tests.

  def _testAddBatch(self):
    '''Test add_batch with various inputs.'''
    # The following fields will be reused.
    path = os.path.join(os.getcwd(), "image1.jpg")
    accountID = "accountID"
    license = "license"
    licenseStatementUrl = "licenseurl"
    licenseLogoUrl = "licenselogourl"

    '''Test add_batch with minimum correct information.'''
    batch = model.add_batch(
        path, accountID, license, licenseStatementUrl, licenseLogoUrl)
    self._validateBatchFields(
        batch, path, accountID, license, licenseStatementUrl, licenseLogoUrl)

    # Batch information will be used in _testAddImage.
    self._batch1 = batch

    '''Test add_batch with full correct information.'''
    batch = model.add_batch(
        path, accountID, license, licenseStatementUrl, licenseLogoUrl)
    self._validateBatchFields(
        batch, path, accountID, license, licenseStatementUrl, licenseLogoUrl)

    # Batch information will be used in _testAddImage.
    self._batch2 = batch

    '''Test add_batch with invalid file path.'''
    invalid_path = "invalid/path/file.csv"
    self.assertRaises(model.ModelException, model.add_batch,
        invalid_path, accountID, license, licenseStatementUrl, licenseLogoUrl)

    '''Test add_batch with required field "license" empty.'''
    self.assertRaises(model.ModelException, model.add_batch,
        invalid_path, accountID, "", licenseStatementUrl, licenseLogoUrl)

  def _testAddImage(self):
    '''Test add_image with various inputs.'''
    # We are going to use the batches, make sure they are valid and different.
    self.assertIsNotNone(self._batch1)
    self.assertIsNotNone(self._batch2)
    self.assertNotEqual(self._batch1, self._batch2)

    headerline = ["idigbio:OriginalFileName", "idigbio:MediaGUID"]
    mediaguid = "123123123" # Random

    '''A correct file path with minimum input.'''
    orig_filepath = os.path.join(os.getcwd(), "image1.jpg")
    csvrow = [orig_filepath, mediaguid]
    record = model.add_image(self._batch1, csvrow, headerline)
    self._validateImageRecordFields(record, orig_filepath, mediaguid, "", "", "",
                                    "image/jpeg", 143978, "{}", self._batch1.id)

    '''If the image is a retry, update the batch ID.'''
    model.commit()
    record = model.add_image(self._batch2, csvrow, headerline)
    self._validateImageRecordFields(record, orig_filepath, mediaguid, "", "", "",
                                    "image/jpeg", 143978, "{}", self._batch2.id)

    '''If the image is uploaded, just return None.'''
    # Update the UploadTime of the record.
    record.UploadTime = str(datetime.datetime.utcnow())
    model.commit()
    self.assertIsNone(model.add_image(self._batch1, csvrow, headerline))
    # Record the imagerecord information for testing other functions.
    self._record = record

    '''A correct large input.'''
    annotation = {"Field1": "Value1", "Field2": "Value2", "Field3": "Value3"}
    headerline2 = ["idigbio:OriginalFileName", "idigbio:MediaGUID", "Field1",
                   "Field2", "Field3"]
    mediaguid2 = "1231231232" # Random
    csvrow2 = [orig_filepath, mediaguid2, annotation["Field1"],
               annotation["Field2"], annotation["Field3"]]
    record = model.add_image(self._batch2, csvrow2, headerline2)
    self._validateImageRecordFields(
        record, orig_filepath, mediaguid2, "", "", "", "image/jpeg", 143978,
        str(annotation), self._batch2.id)

    '''An input that contains SpecimenRecordUUID'''
    headerline3 = ["idigbio:OriginalFileName", "idigbio:MediaGUID",
        "idigbio:SpecimenRecordUUID"]
    csv_sruuid = "19878432498316, 0984823912374"
    mediaguid3 = "123123072" # Random
    csvrow3 = [orig_filepath, mediaguid3, csv_sruuid]
    record = model.add_image(self._batch2, csvrow3, headerline3)
    self._validateImageRecordFields(
        record, orig_filepath, mediaguid3, csv_sruuid.replace(" ", ""),
        "", "", "image/jpeg", 143978, "{}", self._batch2.id)

    '''File path is wrong.'''
    invalid_filepath = "Invalid/path/file.jpg"
    csvrow = [invalid_filepath, mediaguid]
    record = model.add_image(self._batch1, csvrow, headerline)
    self._validateImageRecordFields(
        record, invalid_filepath, mediaguid, "", "File not found.", "",
        "image/jpeg", "", "{}", self._batch1.id)

  def _testGetAllBatches(self):
    '''
    Test get_all_batches. Compare the queried batches with the recorded
    information.
    '''
    # We are going to use _batch1 and _batch2, make sure they are valid.
    self.assertIsNotNone(self._batch1)
    self.assertIsNotNone(self._batch2)

    model.commit()
    batches = model.get_all_batches()
    batch1 = batches[0]
    self._validateBatchFields(
        self._batch1, batch1[1], batch1[2], batch1[3], batch1[4], batch1[5])
    batch2 = batches[1]
    self._validateBatchFields(
        self._batch2, batch2[1], batch2[2], batch2[3], batch2[4], batch2[5])

  def _testGetBatchDetails(self):
    '''
    Test get_batch_details. Compare the queried imagerecord with the recorded
    information.
    '''
    # We are going to use _record and _batch2, make sure they are valid.
    self.assertIsNotNone(self._record)
    self.assertIsNotNone(self._batch2)

    model.commit()
    records = model.get_batch_details(self._batch2.id)
    record = records[0]

    self._validateImageRecordFields(
        self._record, record[1], record[0], record[2], record[3], record[4],
        record[7], record[8], record[12], record[20])

    self._validateBatchFields(
        self._batch2, record[15], record[16], record[17], record[18], record[19])

  def _testGetLastBatchInfo(self):
    '''Test get_last_batch_info.'''
    # We are going to use _batch2, make sure it is valid.
    self.assertIsNotNone(self._batch2)
    self.assertIsNone(self._batch2.finish_time)

    model.commit()
    '''The batch is not finished.'''
    retdict = model.get_last_batch_info()
    self.assertFalse(retdict["Empty"])
    self.assertEqual(retdict["path"], self._batch2.CSVfilePath)
    self.assertIsNotNone(retdict["start_time"])
    self.assertIsNone(retdict["ErrorCode"])
    self.assertFalse(retdict["finished"])

    '''The batch is finished.'''
    self._batch2.finish_time = datetime.datetime.now()
    retdict = model.get_last_batch_info()
    self.assertFalse(retdict["Empty"])
    self.assertEqual(retdict["path"], self._batch2.CSVfilePath)
    self.assertIsNotNone(retdict["start_time"])
    self.assertIsNone(retdict["ErrorCode"])
    self.assertTrue(retdict["finished"])

  def runTest(self):
    self._testAddBatch()
    self._testAddImage()
    self._testGetAllBatches()
    self._testGetBatchDetails()
    self._testGetLastBatchInfo()


if __name__ == '__main__':
      unittest.main()
