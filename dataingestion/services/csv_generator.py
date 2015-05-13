#!/usr/bin/env python
#
# Copyright (c) 2012 Liu, Yonggang <myidpt@gmail.com>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

import re, os, logging, csv, hashlib, threading, time
from os.path import isdir, join, dirname, split, exists
from dataingestion.services import user_config
from etc import constants
from dataingestion.services.ingestion_manager import IngestServiceException
from time import sleep

logger = logging.getLogger('iDigBioSvc.csv_generator')

class Status:
  def __init__(self):
    self.count = 0
    self.result = 0
    self.error = None
    self.dic = None
    self.targetfile = None

status = Status()

def get_files(imagepath, recursive):

  allowed_files = re.compile(constants.ALLOWED_FILES, re.IGNORECASE)
  filenameset = []

  status.count = 0
  status.result = 0
  if isdir(imagepath): # This is a dir.
    if (recursive == 'true'):
      for dirpath, dirnames, filenames in os.walk(imagepath):
        for file_name in filenames:
          if not allowed_files.match(file_name):
            continue
          status.count =  status.count + 1
          subpath = join(dirpath, file_name)
          filenameset.append(subpath)
    else:
      for file_name in os.listdir(imagepath):
        if os.path.isfile(join(imagepath, file_name)):
          if not allowed_files.match(file_name):
            continue
          status.count =  status.count + 1
          subpath = join(imagepath, file_name)
          filenameset.append(subpath)

  else: # This is a single file.
    if allowed_files.match(imagepath):
      filenameset.append(imagepath)
    else:
      status.result = -1
      status.error = "File type is unsupported: " + imagepath
      logger.error(status.error)
      raise IngestServiceException(status.error)

  return filenameset

def get_mediaguids(guid_syntax, guid_prefix, filenameset, commonvalue):
  guidset = []
  starttime = time.time()
  startptime = time.clock()
  if guid_syntax is None or guid_syntax == "":
    status.result = -1
    status.error = "GUID Syntax is empty."
    logger.error(status.error)
    raise IngestServiceException(status.error)
  if guid_syntax == "image_hash":
    for index in range(len(filenameset)):
      image_md5 = hashlib.md5()
      with open(filenameset[index], 'rb') as mediafile:
        while True:
          image_binary = mediafile.read(128)
          if not image_binary:
            break;
          image_md5.update(image_binary)
      guidset.append(image_md5.hexdigest())
  elif guid_syntax == "hash":
    for index in range(len(filenameset)):
      md5value = hashlib.md5()
      md5value.update(str(filenameset[index]))
      md5value.update(str(commonvalue))
      guidset.append(md5value.hexdigest())
  elif guid_syntax == "fullpath" or guid_syntax == "filename":
    for index in range(len(filenameset)):
      if guid_syntax == "filename":
        guid_postfix = split(filenameset[index])[1]
      else:
        guid_postfix = filenameset[index]
      guidset.append(guid_prefix + guid_postfix)
  else:
    status.result = -1
    status.error = "GUID Syntax not defined: " + guid_syntax
    logger.error(status.error)
    raise IngestServiceException(status.error)
  duration = time.time() - starttime
  ptime = time.clock() - startptime
  logger.debug(
      "All records generated for {0} files, duration: {1} sec, processing time: {2} sec."
      .format(len(filenameset), duration, ptime))

  return guidset

def gen_csv():

  # Find all the media files.
  imagedir = ""
  dic = status.dic
  if dic.has_key(user_config.G_IMAGE_DIR):
    # To make special notations like '\' working.
    imagedir = dic[user_config.G_IMAGE_DIR]
  if not exists(imagedir):
    logger.error("IngestServiceException: " + imagedir
                 + " is not a valid path.")
    status.result = -1
    status.error = "\"" + imagedir + "\" is not a valid path."
    raise IngestServiceException(status.error)

  # This process takes the most amount of time:
  filenameset = get_files(imagedir, dic[user_config.G_RECURSIVE])

  if not filenameset:
    logger.error("IngestServiceException: No valid media file is in the path.")
    status.result = -1
    status.error = "No valid media file is in the path."
    raise IngestServiceException(status.error)

  # Find the headerline and commonvalues.
  headerline = ["idigbio:OriginalFileName", "idigbio:MediaGUID"]
  commonvalue = []

  # description
  if (dic.has_key(user_config.G_DESCRIPTION) and
      dic[user_config.G_DESCRIPTION] != ''):
    commonvalue.append(dic[user_config.G_DESCRIPTION])
    headerline.append("idigbio:Description")

  # language code
  if (dic.has_key(user_config.G_LANGUAGE_CODE) and
      dic[user_config.G_LANGUAGE_CODE] != ''):
    commonvalue.append(dic[user_config.G_LANGUAGE_CODE])
    headerline.append("idigbio:LanguageCode")

  # title
  if (dic.has_key(user_config.G_TITLE) and
      dic[user_config.G_TITLE] != ''):
    commonvalue.append(dic[user_config.G_TITLE])
    headerline.append("idigbio:Title")

  # digitalization_device
  if (dic.has_key(user_config.G_DIGI_DEVICE) and
      dic[user_config.G_DIGI_DEVICE] != ''):
    commonvalue.append(dic[user_config.G_DIGI_DEVICE])
    headerline.append("idigbio:DigitalizationDevice")

  # pixel resolution
  if (dic.has_key(user_config.G_PIX_RESOLUTION)
      and dic[user_config.G_PIX_RESOLUTION] != ''):
    commonvalue.append(dic[user_config.G_PIX_RESOLUTION])
    headerline.append("idigbio:NominalPixelResolution")

  # magnification
  if (dic.has_key(user_config.G_MAGNIFICATION)
      and dic[user_config.G_MAGNIFICATION] != ''):
    commonvalue.append(dic[user_config.G_MAGNIFICATION])
    headerline.append("idigbio:Magnification")

  # OCR output
  if (dic.has_key(user_config.G_OCR_OUTPUT)
      and dic[user_config.G_OCR_OUTPUT] != ''):
    commonvalue.append(dic[user_config.G_OCR_OUTPUT])
    headerline.append("idigbio:OcrOutput")

  # OCR technology
  if dic.has_key(user_config.G_OCR_TECH) and dic[user_config.G_OCR_TECH] != '':
    commonvalue.append(dic[user_config.G_OCR_TECH])
    headerline.append("idigbio:OcrTechnology")

  # information withheld
  if (dic.has_key(user_config.G_INFO_WITHHELD)
      and dic[user_config.G_INFO_WITHHELD] != ''):
    commonvalue.append(dic[user_config.G_INFO_WITHHELD])
    headerline.append("idigbio:InformationWithheld")

  # Collection Object GUID
  if (dic.has_key(user_config.G_COLLECTION_OBJ_GUID)
      and dic[user_config.G_COLLECTION_OBJ_GUID] != ''):
    commonvalue.append(dic[user_config.G_COLLECTION_OBJ_GUID])
    headerline.append("idigbio:CollectionObjectGUID")

  # Find the media GUIDs.
  if dic.has_key(user_config.G_GUID_SYNTAX):
    guid_syntax = dic[user_config.G_GUID_SYNTAX]
  else:
    logger.error("GUID syntax is missing.")
    status.result = -1
    status.error = "GUID syntax is missing."
    raise IngestServiceException("GUID syntax is missing.")

  if dic.has_key(user_config.G_GUID_PREFIX):
    guid_prefix = dic[user_config.G_GUID_PREFIX]

  guidset = get_mediaguids(guid_syntax, guid_prefix, filenameset, commonvalue)

  # Form the output stream
  outputstream = []
  index = 0
  for item in filenameset:
    tmp = []
    tmp.append(item)
    tmp.append(guidset[index])
    outputstream.append(tmp + commonvalue)
    index = index + 1

  # Write the CSV file.
  try:
    with open(status.targetfile, 'wb') as csvfile:
      csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"',
                             quoting=csv.QUOTE_MINIMAL)
      csvwriter.writerow(headerline)
      csvwriter.writerows(outputstream)
      status.result = 1
  except IOError as ex:
    logger.error("Cannot write to output file: " + status.targetfile)
    status.result = -1
    status.error = "Cannot write to output file: " + status.targetfile
    raise IngestServiceException("Cannot write to output file: "
                                 + status.targetfile)

# Get the target file path from the given information.
def get_targetfile():
  imagedir = ""
  dic = status.dic
  if dic.has_key(user_config.G_IMAGE_DIR):
    # To make special notations like '\' working.
    imagedir = dic[user_config.G_IMAGE_DIR]
  if not exists(imagedir):
    logger.error("IngestServiceException: " + imagedir
                 + " is not a valid path.")
    status.error = "\"" + imagedir + "\" is not a valid path."
    status.result = -1
    raise IngestServiceException("\"" + imagedir + "\" is not a valid path.")

  targetfile = ""
  if dic.has_key(user_config.G_SAVE_PATH):
    targetfile = dic[user_config.G_SAVE_PATH]
    status.targetfile = targetfile
  try:
    if targetfile == "":
      if not isdir(imagedir):
        imagedir = dirname(imagedir)
      targetfile = join(imagedir, constants.G_DEFAULT_CSV_OUTPUT_NAME)
      logger.debug("targetfile=" + targetfile)
      status.targetfile = targetfile
  except IOError as ex:
    logger.error("Output file is not a valid path: " + targetfile)
    status.result = -1
    status.error = "Output file is not a valid path: " + targetfile
    raise IngestServiceException("Output file is not a valid path: "
                                 + targetfile)

# Run as a separate thread.
def run_gencsv(dic):
  status.dic = dic
  status.count = 0
  status.result = 0
  status.error = None
  status.targetfile = None

  get_targetfile()
  t = threading.Thread(target=gen_csv)
  t.daemon = True
  t.start()

def check_progress():
  return (status.count, status.result, status.targetfile, status.error)
