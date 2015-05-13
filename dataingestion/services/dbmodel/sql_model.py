#!/usr/bin/env python
#
# Copyright (c) 2013 Liu, Yonggang <myidpt@gmail.com>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php
"""
This module implements the data model for the service.
"""
from sqlalchemy import (create_engine, Column, Integer, String, DateTime,
                        Boolean, types, distinct)
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import ForeignKey
from sqlalchemy.sql.expression import desc
import logging, hashlib, argparse, os, time, struct, re, json
# import pyexiv2
from datetime import datetime
import types as pytypes
from etc import constants

THRESHOLD_TIME = 2 # sec

if os.name == 'posix':
  import pwd
elif os.name == 'nt':
  from dataingestion.services import win_api

__images_tablename__ = constants.IMAGES_TABLENAME
__batches_tablename__ = constants.BATCHES_TABLENAME

Base = declarative_base()

logger = logging.getLogger('iDigBioSvc.model')

def check_session(func):
  def wrapper(*args):
    if session is None:
      raise ValueError('DB session is None.')
    return func(*args)
  return wrapper


class ModelException(Exception):
  def __init__(self, msg, reason=''):
    Exception.__init__(self, msg)
    self.reason = reason


class UploadBatch(Base):
  """
  Represents a batch which is the operation executed when the user clicks the 
  "Upload" button.
  
  .. note:: When a batch fails and is resumed, the same batch record is reused.
  """
  __tablename__ = __batches_tablename__
  id = Column(Integer, primary_key=True)
  """The path for the batch upload."""
  CSVfilePath = Column(String)
  """Log in information."""
  iDigbioProvidedByGUID = Column(String)
  """The license key."""
  RightsLicense = Column(String)
  RightsLicenseStatementUrl = Column(String)
  RightsLicenseLogoUrl = Column(String)
  """The GUID user provided for the record set."""
  start_time = Column(DateTime)
  """The local time that the batch upload finishes. None if not successful."""
  finish_time = Column(DateTime)

  RecordCount = Column(Integer)
  SkipCount = Column(Integer)
  FailCount = Column(Integer)
  SuccessCount = Column(String)
  ErrorCode = Column(String)
  TaskId = Column(Integer)

  """Records if the CSV file is uploaded."""
  CSVUploaded = Column(Boolean)

  AllMD5 = Column(String) # The md5 of the CSV file + uuid.
  
  def __init__(self, path, accountID, license, licenseStatementUrl,
               licenseLogoUrl, s_time, md5, taskid):
    """7 parameters"""
    self.CSVfilePath = path
    self.iDigbioProvidedByGUID = accountID
    self.RightsLicense = license
    self.RightsLicenseStatementUrl = licenseStatementUrl
    self.RightsLicenseLogoUrl = licenseLogoUrl
    self.start_time = s_time
    self.AllMD5 = md5
    self.RecordCount = 0
    self.SkipCount = 0
    self.FailCount = 0
    self.SuccessCount = 0
    self.ErrorCode = None
    self.finish_time = None
    self.CSVUploaded = False
    self.TaskId = taskid


class ImageRecord(Base):
  __tablename__ = __images_tablename__
  '''
  Note that "None" should not be used in DB because when the fields are returned
  to the Bootstrap UI as a list, the "None" element is ignored by Bootstrap,
  which leads to a mistake in list element indexes or list size.
  '''

  id = Column(Integer, primary_key=True)
  """
  Path does not have to be unique as there can be multiple 
  unrelated */USBVolumne1/DCIM/Image1.JPG*s.
  """
  OriginalFileName = Column(String)
  """
  MediaGUID (providerid) is unique for each media record within the record set.
  """
  MediaGUID = Column(String)
  """The UUID of the specimen for this image."""
  SpecimenRecordUUID = Column(String)
  """Indicates if there is a fatal error in the processing."""
  Error = Column(String)
  """Indicates if there are warnings in the processing."""
  Warnings = Column(String)
  """MadiaAP record in JSON String."""
  MediaAPContent = Column(String)
  """
  The UTC time measured by the local machine. 
  None if the image is not uploaded.
  """
  UploadTime = Column(String)
  """The URL of the Media after posting the image."""
  MediaURL = Column(String)
  """MadiaRecord record in JSON String."""
  """
  Technical type (format) of digital multimedia object. 
  When using the image ingestion appliance, this is automatically filled based
  on the extension of the filename.
  """
  MimeType = Column(String)
  """
  Size in bytes of the multimedia resource accessible through the MediaUrl. 
  Derived from the object when using the ingestion appliance.
  """
  MediaSizeInBytes = Column(String)
  """
  Date and time when the record was originally created on the provider data
  management system.
  """
  ProviderCreatedTimeStamp = Column(String)
  """File owner"""
  ProviderCreatedByGUID = Column(String)
  """
  Blob of text containing the EXIF metadata from the media.
  Derived from the object when using the ingestion appliance.
  """
  MediaEXIF = Column(String)
  """All the annotations to the image by the user."""
  Annotations = Column(String)
  """Returned by server at post_mediarecord."""
  etag = Column(String)
  """Checksum of the media object accessible via MediaUrl, using MD5."""
  MediaMD5 = Column(String)
  """Hash got from "record set uuid + CSV record line + media file hash"."""
  AllMD5 = Column(String, index=True, unique=True)
  """This image belongs to a specific batch."""
  BatchID = Column(Integer)

  def __init__(self, path, mediaguid, sruuid, error, warnings, mimetype,
               msize, ctime, fowner, exif, annotations, mmd5, amd5, batch):
    self.OriginalFileName = path
    self.MediaGUID = mediaguid
    self.SpecimenRecordUUID = sruuid
    self.Error = error
    self.Warnings = warnings
    self.MimeType = mimetype
    self.MediaSizeInBytes = msize
    self.ProviderCreatedTimeStamp = ctime
    self.ProviderCreatedByGUID = fowner
    self.MediaEXIF = exif
    self.Annotations = annotations
    self.MediaMD5 = mmd5
    self.AllMD5 = amd5
    self.BatchID = batch.id


session = None

def setup(db_file):
  """
  Set up the database.
  """
  global session

  db_conn = "sqlite:///%s" % db_file
  logger.info("DB Connection: %s" % db_conn)
  engine = create_engine(db_conn, connect_args={'check_same_thread':False})
  engine.Echo = True
  Base.metadata.create_all(engine)

  Session = scoped_session(sessionmaker(bind=engine))
  session = Session()
  print "DB Connection: %s" % db_conn

def _md5_file(f, block_size=2 ** 20):
  """
  Get MD5 of the file.
  """
  md5 = hashlib.md5()
  while True:
    data = f.read(block_size)
    if not data:
      break
    md5.update(data)
  return md5

def _generate_record(csvrow, headerline):
  mediapath = ""
  mediaguid = ""
  sruuid = ""
  error = ""
  warnings = ""
  mimetype = ""
  msize = ""
  ctime = ""
  fowner = ""
  exif = ""
  annotations_dict = {}
  mmd5 = ""
  amd5 = ""

  index = 0
  for index, elem in enumerate(headerline):
    if elem == "idigbio:OriginalFileName":
      mediapath = csvrow[index]
    elif elem == "idigbio:MediaGUID":
      mediaguid = csvrow[index]
    elif elem == "idigbio:SpecimenRecordUUID":
      sruuid = csvrow[index].replace(" ", "")
    else:
      annotations_dict[elem] = csvrow[index]

  recordmd5 = hashlib.md5()
  # Note that mediapath can be different and the image is the same,
  # so mediapath is not considered in the md5 calculation.
  recordmd5.update(mediaguid)
  recordmd5.update(sruuid)

  exifinfo = None
  filemd5hexdigest = ""

  if not re.compile(constants.ALLOWED_FILES, re.IGNORECASE).match(mediapath):
    error = "File type unsupported."
  else:
    try:
      mimetype = constants.EXTENSION_MEDIA_TYPES[
          os.path.splitext(mediapath)[1].lower()]
    except os.error:
      logger.error("os path splitext error: " + mediapath)

    try:
      with open(mediapath, 'rb') as f:
        filemd5 = _md5_file(f)
        filemd5hexdigest = filemd5.hexdigest()
    except IOError as err:
      logger.error("File " + mediapath + " open error.")
      error = "File not found."

  if error: # File not exist, cannot go further. Just return.
    logger.debug('Generating image record done with error.')
    return (mediapath, mediaguid, sruuid, error, warnings, mimetype,
        msize, ctime, fowner, exif, json.dumps(annotations_dict), filemd5hexdigest,
        recordmd5.hexdigest())

  recordmd5.update(filemd5hexdigest)

  try:
    msize = os.path.getsize(mediapath)
  except os.error:
    logger.error("os path getsize error: " + mediapath)
    warnings += "[File getsize error.]"

  ctime = time.ctime(os.path.getmtime(mediapath))

  if os.name == 'posix':
    fowner = pwd.getpwuid(os.stat(mediapath).st_uid)[0]
  elif os.name == 'nt':
    try:
      fowner = win_api.get_file_owner(mediapath)
    except Exception as e:
      logger.error("WIN API error: %s" % e)
      traceback.print_exc()
      warnings += "Windows NT get file owner error."
  else:
    logger.error("Operating system not supported:" + os.name)
    warnings += "[OS not supported when getting file owner.]"

  try:
    # exifinfo = pyexiv2.ImageMetadata(mediapath)
    # exifinfo.read()
    # if not exifinfo:
    #   exif = ""
    #   warnings += "[Cannot extract EXIF information.]"
    # else:
    #   exif_dict = {}
    #   for exif_key in exifinfo.keys():
    #     try:
    #       if type(exifinfo[exif_key].value) in (
    #           pytypes.IntType, pytypes.LongType, pytypes.FloatType):
    #         exif_dict[exif_key] = exifinfo[exif_key].value
    #       elif exifinfo[exif_key].type in ("Flash"):
    #         exif_dict[exif_key] = exifinfo[exif_key].value
    #       elif exifinfo[exif_key].type == "Undefined":
    #         continue
    #       else:
    #         exif_dict[exif_key] = str(exifinfo[exif_key].value)
    #     except: # There are some fields that cannot be extracted, just continue.
    #       continue
    #   exif = json.dumps(exif_dict)
    exif = "{}"
  except IOError as err:
    warnings += "[Cannot extract EXIF information.]"

  return (mediapath, mediaguid, sruuid, error, warnings, mimetype, msize,
          ctime, fowner, exif, json.dumps(annotations_dict), filemd5hexdigest,
          recordmd5.hexdigest())

# @check_session
# def update_status(batch_id, error):
#   """ Update status for an image to batch
#   """
#   batch = session.query(UploadBatch).filter_by(id=batch_id).first()
#   logger.debug(batch_id)
#   if error == None:
#   	batch.SuccessCount = int(batch.SuccessCount) + 1
#   else:
#   	batch.FailCount += int(batch.FailCount) + 1
#   if int(batch.SuccessCount) + int(batch.FailCount) + int(batch.SkipCount) == int(batch.RecordCount):
#   	batch.finish_time = datetime.now()
#   	logger.debug("Upload batch finished")

@check_session
def update_batch(task_id, key, val):
	batch = session.query(UploadBatch).filter_by(TaskId=task_id).first()
	if key == 'SuccessCount':
		batch.SuccessCount = val
	elif key == 'FailCount':
		batch.FailCount = val
	logger.debug("Updating" + key + ": " + str(val))
	commit()

@check_session
def update_status(batch_id, error):
  """ Update status to batch
  """
  batch = session.query(UploadBatch).filter_by(id=batch_id).first()
  batch.ErrorCode = error
  batch.finish_time = datetime.now()
  logger.debug("Upload batch finished at " + str(batch.finish_time))
  commit()


@check_session
def update_image(image_record_id):
  """ gets a new image record instance in current thread
  """
  record = session.query(ImageRecord).filter_by(id=image_record_id).first()
  logger.error("checking in model")
  logger.error(record)
  return record

@check_session
def add_image(batch, csvrow, headerline):
  """
  Parameters:
    batch: The UploadBatch instance this image belongs to.
    csvrow: A list of values of the current csvrow.
    headerline: The header line of the csv file.
  Return the image or None is the image should not be uploaded.
  Return type: ImageRecord or None.
  Note: Image identity is not determined by path but rather by its MD5.
  """
  (mediapath, mediaguid, sruuid, error, warnings, mimetype, msize, ctime,
   fowner, exif, annotations, mmd5, amd5) = _generate_record(
       csvrow, headerline)

  try:
    record = session.query(ImageRecord).filter_by(AllMD5=amd5).first()
  except Exception as e:
    logger.error('add_image: error occur during SQLITE access:{0}'.format(e))
    raise ModelException("Error occur during SQLITE access:{0}".format(e))
  if record is None: # New record. Add the record.
    logger.debug('add_image: new record: {0}'.format(mediapath))
    record = ImageRecord(mediapath, mediaguid, sruuid, error, warnings,
                         mimetype, msize, ctime, fowner, exif, annotations,
                         mmd5, amd5, batch)
    try:
      session.add(record)
    except Exception as e:
      logger.error('add_image: error occur during SQLITE add:{0}'.format(e))
      raise ModelException("Error occur during SQLITE add:{0}".format(e))
    return record
  elif record.UploadTime: # Found the duplicate record, already uploaded.
    logger.debug('add_image: already uploaded: {0}'.format(mediapath))
    return None
  else: # Found the duplicate record, but not uploaded or file not found.
    record.BatchID = batch.id
    return record

@check_session
def add_batch(path, accountID, license, licenseStatementUrl, licenseLogoUrl, task_id):
  """
  Add a batch to the database.
  Returns: An UploadBatch instance created by the information.
  Throws ModelException:
    1. If path, accountID, license, licenseLogoUrl are not all provided.
    2. If the provided CSV file path is not to a valid file.
  """
  if (not path or not accountID or not license or not licenseLogoUrl or not task_id):
    logger.error('add_batch: At least one required field is not provided.')
    raise ModelException("At lease one required field is not provided.")

  start_time = datetime.now()
  try:
    with open(path, 'rb') as f:
      md5value = _md5_file(f)
  except:
    raise ModelException("CSV File %s is not a valid file." %path)
  md5value.update(accountID)
  md5value.update(license)

  # Always add new record.
  newrecord = UploadBatch(path, accountID, license, licenseStatementUrl,
      licenseLogoUrl, start_time, md5value.hexdigest(), task_id)
  session.add(newrecord)
  logger.debug('New batch added: {0}'.format(path))
  return newrecord

def get_batch_details_fieldnames():
  '''
  This function returns the format of the returned list of
  get_batch_details.
  '''

  return [
      "MediaGUID", "OriginalFileName",
      "SpecimenUUID", "Error",
      "Warnings", "UploadTime",
      "MediaURL", "MimeType",
      "MediaSizeInBytes", "ProviderCreatedTimeStamp",
      "providerCreatedByGUID",
      # 0 - 10 above.
      "Annotations",
      "MediaRecordEtag", "MediaMD5",
      "CSVfilePath", "iDigbioProvidedByGUID",
      "RightsLicense", "RightsLicenseStatementUrl",
      "RightsLicenseLogoUrl", "batchID"]
      # 11 - 19 above.

@check_session
def get_batch_progress_brief(task_id):
  '''Gets all the image records for a batch with batch_id.'''
  logger.debug(task_id)
  batch = session.query(UploadBatch).filter_by(TaskId=task_id).first()
  logger.debug(batch)
  if batch.finish_time is None:
  	status = False
  else:
  	status = True
  progressObj = {}
  progressObj["total"] = batch.RecordCount
  progressObj["skips"] = batch.SkipCount
  progressObj["successes"] = batch.SuccessCount
  progressObj["fails"] = batch.FailCount
  progressObj["csvuploaded"] = batch.CSVUploaded
  progressObj["finished"] = status
  return progressObj

@check_session
def get_batch_details_brief(batch_id):
  '''Gets all the image records for a batch with batch_id.'''
  # batch = session.query(UploadBatch).filter_by(id=batch_id).first()
  batch_id = int(batch_id)
  
  query = session.query(
      ImageRecord.OriginalFileName,
      ImageRecord.Error,
      ImageRecord.MediaURL,
    ).filter(ImageRecord.BatchID == batch_id).filter(UploadBatch.id == batch_id
    ).order_by(ImageRecord.id) # 3 elements.

  logger.debug("get_batch_details: record count={0}.".format(query.count()))

  return query.all()

@check_session
def get_batch_details(batch_id):
  '''Gets all the image records for a batch with batch_id.'''
  batch_id = int(batch_id)
  if (batch_id == 0): # Get the last batch.
    batch_id = int(session.query(UploadBatch.id).order_by(desc(UploadBatch.id)).first()[0])
  query = session.query(
      ImageRecord.MediaGUID,
      ImageRecord.OriginalFileName,
      ImageRecord.SpecimenRecordUUID,
      ImageRecord.Error,
      ImageRecord.Warnings,
      ImageRecord.UploadTime,
      ImageRecord.MediaURL,
      ImageRecord.MimeType,
      ImageRecord.MediaSizeInBytes,
      ImageRecord.ProviderCreatedTimeStamp,
      ImageRecord.ProviderCreatedByGUID,
      # 0 - 10 above.
      ImageRecord.Annotations,
      ImageRecord.etag,
      ImageRecord.MediaMD5,
      UploadBatch.CSVfilePath,
      UploadBatch.iDigbioProvidedByGUID,
      UploadBatch.RightsLicense,
      UploadBatch.RightsLicenseStatementUrl,
      UploadBatch.RightsLicenseLogoUrl,
      ImageRecord.BatchID
      # 11 - 19 above
    ).filter(ImageRecord.BatchID == batch_id).filter(UploadBatch.id == batch_id
    ).order_by(ImageRecord.id) # 20 elements.

  logger.debug("get_batch_details: record count={0}.".format(query.count()))
  return query.all()

@check_session
def get_unuploaded_information():
  '''Gets all the image records for a batch with batch_id.'''
  query = session.query(
      ImageRecord.MediaGUID,
      ImageRecord.OriginalFileName,
      ImageRecord.SpecimenRecordUUID,
      ImageRecord.Error,
      ImageRecord.Warnings,
      ImageRecord.UploadTime,
      ImageRecord.MediaURL,
      ImageRecord.MimeType,
      ImageRecord.MediaSizeInBytes,
      ImageRecord.ProviderCreatedTimeStamp,
      ImageRecord.ProviderCreatedByGUID,
      # 0 - 10 above.
      ImageRecord.Annotations,
      ImageRecord.etag,
      ImageRecord.MediaMD5,
      UploadBatch.CSVfilePath,
      UploadBatch.iDigbioProvidedByGUID,
      UploadBatch.RightsLicense,
      UploadBatch.RightsLicenseStatementUrl,
      UploadBatch.RightsLicenseLogoUrl,
      ImageRecord.BatchID
      # 11 - 19 above
    ).filter(UploadBatch.CSVUploaded == False).filter(ImageRecord.BatchID == UploadBatch.id
    ).order_by(ImageRecord.id) # 20 elements.

  logger.debug("get_unuploaded_information: record count={0}.".format(query.count()))

  return query.all()

@check_session
def set_all_csv_uploaded():
  session.query(UploadBatch).filter(UploadBatch.CSVUploaded==False).update(
      {"CSVUploaded": True})

@check_session
def get_all_success_details():
  '''Gets all the image records for all batches.'''
  
  query = session.query(
      ImageRecord.MediaGUID,
      ImageRecord.OriginalFileName,
      ImageRecord.SpecimenRecordUUID,
      ImageRecord.Error,
      ImageRecord.Warnings,
      ImageRecord.UploadTime,
      ImageRecord.MediaURL,
      ImageRecord.MimeType,
      ImageRecord.MediaSizeInBytes,
      ImageRecord.ProviderCreatedTimeStamp,
      ImageRecord.ProviderCreatedByGUID,
      # 0 - 10 above.
      ImageRecord.Annotations,
      ImageRecord.etag,
      ImageRecord.MediaMD5,
      UploadBatch.CSVfilePath,
      UploadBatch.iDigbioProvidedByGUID,
      UploadBatch.RightsLicense,
      UploadBatch.RightsLicenseStatementUrl,
      UploadBatch.RightsLicenseLogoUrl,
      ImageRecord.BatchID
      # 11 - 19 above
    ).filter(ImageRecord.UploadTime != None
    ).filter(ImageRecord.BatchID == UploadBatch.id
    ).order_by(ImageRecord.id) # 20 elements.

  logger.debug("get_all_success_details: record count={0}.".format(query.count()))

  return query.all()


@check_session
def get_all_batches():
  """
  Get all the batches in the batch table.
  Return: A list of all batches, each batch is a list of all fields.
  """

  query = session.query(
    UploadBatch.id,
    UploadBatch.CSVfilePath,
    UploadBatch.iDigbioProvidedByGUID,
    UploadBatch.RightsLicense,
    UploadBatch.RightsLicenseStatementUrl, 
    UploadBatch.RightsLicenseLogoUrl,
    UploadBatch.start_time,
    UploadBatch.finish_time,
    UploadBatch.RecordCount,
    UploadBatch.FailCount,
    UploadBatch.SkipCount,
    UploadBatch.SuccessCount
    ).order_by(UploadBatch.id) # 11 elements

  ret = []
  for elem in query:
    newelem = []
    index = 0
    for origitem in elem:
      item = str(origitem)
      if index == 6: # start_time?
        item = item[0:item.index('.')]
      newelem.append(str(item))
      index = index + 1
    ret.append(newelem)

  logger.debug("get_all_batches: batch count={0}.".format(len(ret)))
  return ret

@check_session
def get_last_batch_info():
  """
  Returns info about the last batch.
  Returns:
    A dictionary of simple information about last batch. 
  """
  batch = session.query(UploadBatch).order_by(desc(UploadBatch.id)).first()
  if batch:
    starttime = str(batch.start_time)
    starttime = starttime[0:starttime.index('.')]
    retdict = {'Empty': False, 'path': batch.CSVfilePath,
               'start_time': starttime, 'ErrorCode': batch.ErrorCode}
    if batch.finish_time is None:
      retdict['finished'] = False
    else:
      retdict['finished'] = True
    dt = datetime.now() - batch.start_time
    logger.debug("get_last_batch_info, last batch exists.")
    if dt.seconds > THRESHOLD_TIME:
      # TODO: Avoid this trick
      # This is a trick, because network failure does not write to db.
      # Then we think the last record you get must be "old enough".
      # In contrast, the CSV file failure writes to db.
      # The the last record you get is just written a second ago.
      retdict['ErrorCode'] = 'Network Connection Error.'
    return retdict
  else:
    logger.debug("get_last_batch_info, last batch is empty.")
    # TODO: Avoid this trick
    # If there's no record before, it is possible a network connection failure.
    retdict = {'Empty': True, 'ErrorCode': 'Network Connection Error.'}
    return retdict

@check_session
def load_last_batch():
  batch = session.query(UploadBatch).order_by(desc(UploadBatch.id)).first()
  return batch

@check_session
def get_csv_path(batch_id):
  batch = session.query(UploadBatch).filter_by(id=batch_id).first()
  return batch.CSVfilePath

@check_session
def commit():
  session.commit()

def close():
  global session
  if session:
    session.close()
    session = None
