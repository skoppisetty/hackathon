#!/usr/bin/env python
#
# Copyright (c) 2013 Liu, Yonggang <myidpt@gmail.com>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

"""
This module implements the result file generation functionalities.
"""

import ast, os, logging, csv, zipfile
from dataingestion.services import model
from etc import constants

logger = logging.getLogger('iDigBioSvc.result_generator')

def _processTargetPaths(target_path, batch_id):
  csv_path = ""
  if target_path is "":
    csv_path = model.get_csv_path(batch_id)
    targetdir = os.path.dirname(os.path.realpath(csv_path)) 
    target_path = os.path.join(targetdir, constants.ZIP_NAME)
  else:
    targetdir = os.path.dirname(os.path.realpath(target_path)) 
  image_csv_path = os.path.join(targetdir, constants.IMAGE_CSV_NAME)
  stub_csv_path = os.path.join(targetdir, constants.STUB_CSV_NAME)
  return target_path, image_csv_path, stub_csv_path

def generateCSV(batch_id, target_path):
  if not batch_id:
    result = model.get_all_success_details()
  else:
    result = model.get_batch_details(batch_id)

  if not result:
    error = "No batch with id = {0}".format(batch_id)
    return target_path, error
  # Make the outputstream for csv_path.
  csv_headerline = model.get_batch_details_fieldnames()

  error = ""

  if not os.path.isabs(target_path):
    error = "File " + str(target_path) + " open error. It is not an absolute path."
    logger.error(error)
    return target_path, error
  elif os.path.isdir(target_path):
    error = "File " + str(target_path) + " open error. It is a directory."
    logger.error(error)
    return target_path, error

  try:
    with open(target_path, 'wb') as csv_file:
      csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"',
                              quoting=csv.QUOTE_MINIMAL)
      csv_writer.writerow(csv_headerline)
      logger.info("Write to CSV file: rows={0}.".format(len(result)))
      csv_writer.writerows(result)
      logger.info("CSV file is successfully written.")
  except IOError as ex:
    error = "File " + str(target_path) + " open error."
    logger.error(error)

  return target_path, error

def generateZip(batch_id, target_path):
  result = model.get_batch_details(batch_id)
  if not result:
    print "No batch with id = " + batch_id
    return None

  target_path, image_csv_path, stub_csv_path = _processTargetPaths(
      target_path, batch_id)

  # Make the outputstream for image_csv_file.
  image_csv_headerline = ["id", "localpath"]
  image_csv_content = []
  for item in result:
    tmp = []
    tmp.append(item[1])
    tmp.append(item[0])
    image_csv_content.append(tmp)

  with open(image_csv_path, 'wb') as image_csv_file:
    csv_writer = csv.writer(image_csv_file, delimiter=',', quotechar='"',
                            quoting=csv.QUOTE_MINIMAL)
    csv_writer.writerow(image_csv_headerline)
    csv_writer.writerows(image_csv_content)
  
  # Make the outputstream for stub_csv_path.
  stub_csv_headerline = model.get_batch_details_fieldnames()
  del stub_csv_headerline[0]
  stub_csv_headerline.insert(0, "coreid")
  del stub_csv_headerline[14]
  
  annotation = {}
  try:
    annotation = ast.literal_eval(result[0][14])
  except ex:
    annotation = {}
  for key in annotation:
    stub_csv_headerline.append(key)

  stub_csv_content = []

  for item in result:
    # Element 14 Annotations should be extended.
    record = []
    for element in item:
      record.append(element)
    annotation = item[14]
    del record[14]
    try:
      annotation = ast.literal_eval(item[14])
    except ex:
      annotation = {}
    for key in annotation:
      record.append(annotation[key])
    stub_csv_content.append(record)

  with open(stub_csv_path, 'wb') as stub_csv_file:
    csv_writer = csv.writer(stub_csv_file, delimiter=',', quotechar='"',
                            quoting=csv.QUOTE_MINIMAL)
    csv_writer.writerow(stub_csv_headerline)
    csv_writer.writerows(stub_csv_content)

  # Put the two files into zip file.
  zf = zipfile.ZipFile(target_path, "w")
  zf.write(image_csv_path, constants.IMAGE_CSV_NAME)
  zf.write(stub_csv_path, constants.STUB_CSV_NAME)
  zf.close()

  return target_path
