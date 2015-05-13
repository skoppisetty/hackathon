from os.path import join, exists 
import os, site, csv, json
current_dir = os.path.abspath(os.getcwd())
site.addsitedir(join(current_dir, "lib"))
from celery import Celery
from datetime import datetime
import threading, json, appdirs, logging
from etc import constants
from dataingestion.services import user_config, model, api_client
from dataingestion.services.api_client import (ClientException, Connection,
                                               ServerException)
from dataingestion.services.user_config import (get_user_config,
                                                set_user_config, rm_user_config)

app = Celery('celery_handler',backend='redis://localhost:6379/', broker='redis://localhost:6379/')
# app.config_from_object('celeryconfig')

logger = logging.getLogger("iDigBioSvc.celery_handler")

# Needs to go in userconfig file
APP_NAME = 'iDigBio Data Ingestion Tool'
APP_AUTHOR = 'iDigBio'
USER_CONFIG_FILENAME = 'user.conf'
data_folder = appdirs.user_data_dir(APP_NAME, APP_AUTHOR)
user_config_path = join(data_folder, USER_CONFIG_FILENAME)
user_config.setup(user_config_path)
db_file = join(data_folder, APP_AUTHOR + ".ingest.db")

import redislite
red_con = redislite.Redis('/tmp/redis.db')

def init():
	model.setup(db_file)
	api_client.init("http://beta-media.idigbio.org")
	api_client.authenticate(get_user_config('accountuuid'),
	                          get_user_config('apikey'))

init()


def _get_conn():
  """
  Get connection.
  """
  return Connection()

redis_lock = threading.Lock()
def update_stats(task_id, update, val):
	redis_lock.acquire()
	status  = json.loads(red_con.get(task_id))
	logger.debug(json.dumps(status))
	if update == "SkipCount":
		# already updated to db
		status["SkipCount"] += 1
	elif update == "recordCount":
		# already updated to db
		status["recordCount"] += 1
	else:
		if val == None:
			status["SuccessCount"] += 1
			model.update_batch(task_id, "SuccessCount", status["SuccessCount"])
		else:
			status["FailCount"] += 1
			model.update_batch(task_id, "FailCount", status["FailCount"])
			status["Errors"].append(val)
	logger.debug(json.dumps(status))
	red_con.set(task_id, json.dumps(status))
	redis_lock.release()
	if status["FailCount"] + status["FailCount"] + status["FailCount"] == status["FailCount"]:
		# task done
		return True, json.dumps(status["Errors"])
	else:
		return False, None


@app.task
def _upload_task(task_id, values):
	logger.debug("starting task " + str(task_id))
	# Get license details
	CSVfilePath = values['CSVfilePath']
	iDigbioProvidedByGUID = user_config.get_user_config(
	user_config.IDIGBIOPROVIDEDBYGUID)
	RightsLicense = values[user_config.RIGHTS_LICENSE]
	license_set = constants.IMAGE_LICENSES[RightsLicense]
	RightsLicenseStatementUrl = license_set[2]
	RightsLicenseLogoUrl = license_set[3]
	# add batch to db
	# adding task_id to batch details
	
	status = {}
	status["recordCount"] = 0
	status["SkipCount"] = 0
	status["SuccessCount"] =0
	status["FailCount"] =0
	status["Errors"] = []
	red_con.set(task_id, json.dumps(status))
	batch = model.add_batch(CSVfilePath, iDigbioProvidedByGUID,
	 RightsLicense, RightsLicenseStatementUrl, RightsLicenseLogoUrl, task_id)
	model.commit()
	logger.debug(batch)
	logger.debug(batch.id)
	batch_id = str(batch.id)
	logger.debug("batch id is " + batch_id)
	conn = _get_conn()
	with open(CSVfilePath, 'rb') as csvfile:
		csv.register_dialect('mydialect', delimiter=',', quotechar='"',
                           skipinitialspace=True)
		reader = csv.reader(csvfile, 'mydialect')
		headerline = None
		recordCount = 0
		for row in reader: # For each line do the work.
			if not headerline:
				batch.ErrorCode = "CSV File Format Error."
				headerline = row
				batch.ErrorCode = ""
				continue

			# Validity test for each line in CSV file  
			if len(row) != len(headerline):
				logger.debug("Input CSV File weird. At least one row has different"
					+ " number of columns")
				raise InputCSVException("Input CSV File weird. At least one row has"
					+ " different number of columns")

			for col in row: 
				if "\"" in col:
					logger.debug("One of CSV field contains \"(Double Quatation)")
					raise InputCSVException("One of CSV field contains Double Quatation Mark(\")") 

			# Get the image record
			image_record = model.add_image(batch, row, headerline)
			if image_record is None:
				# Skip this one because it's already uploaded.
				# Increment skips count and return.
				# Todo : Need a way to identify these skips 
				print "skip", image_record
				batch.SkipCount += 1
				update_stats(task_id, "SkipCount", 1)
			else:
				print "process", image_record
				logger.debug(image_record)
				model.commit()
				_upload_single_image.apply_async((image_record.id,batch_id,conn,task_id),link_error=_upload_images_error_handler.s())
      	recordCount = recordCount + 1 
      	update_stats(task_id , "recordCount", 1)
   	batch.RecordCount = recordCount
 	model.commit()
	logger.debug('Put all image records into db done.')

commit_lock = threading.Lock()

@app.task
def _upload_single_image(image_record_id, batch_id, conn, task_id):
	filename = ""
	mediaGUID = ""
	commit_lock.acquire()
	image_record = model.update_image(image_record_id)
	try:
		if not image_record:
			logger.error("image_record is None.")
			raise ClientException("image_record is None.")
		
		logger.info("Image job started: OriginalFileName: {0}"
        .format(image_record.OriginalFileName))

		if image_record.Error:
			logger.error("image record has error: {0}".format(image_record.Error))
			raise ClientException(image_record.Error)
		filename = image_record.OriginalFileName
		mediaGUID = image_record.MediaGUID
	finally:
		commit_lock.release()

	try:
		# Post image to API.
		# ma_str is the return from server
		img_str = conn.post_image(filename, mediaGUID)
		#    image_record.OriginalFileName, image_record.MediaGUID)
		result_obj = json.loads(img_str)
		url = result_obj["file_url"]
		# img_etag is not stored in the db.
		img_etag = result_obj["file_md5"]

		commit_lock.acquire()
		# try:
		# First, change the batch ID to this one. This field is overwriten.
		image_record.BatchID = batch_id
		image_record.MediaAPContent = img_str
		# Check the image integrity.
		if img_etag and image_record.MediaMD5 == img_etag:
			image_record.UploadTime = str(datetime.utcnow())
			image_record.MediaURL = url
		else:
			logger.error("Upload failed because local MD5 does not match the eTag"
				+ " or no eTag is returned.")
			raise ClientException("Upload failed because local MD5 does not match"
				+ " the eTag or no eTag is returned.")
		# commit model
		model.commit()
		# finally:
		commit_lock.release()

		if conn.attempts > 1:
			logger.debug('Done after %d attempts' % (conn.attempts))

		logger.debug("uploaded " + filename + str(batch_id) )
    	# update_status(task_id, "success", "")
		# Increment the successes by 1.
		# fn = partial(ongoing_upload_task.increment, 'successes')
		# ongoing_upload_task.postprocess_queue.put(fn) # Multi-thread
		# It's sccessful this time.
		# fn = partial(ongoing_upload_task.check_continuous_fails, True)
		# ongoing_upload_task.postprocess_queue.put(fn) # Multi-thread
		Error = None
	except ClientException as ex:
		# update_status(task_id, "failure", "ClientException: An image job failed. Reason: " + str(ex))
		logger.error("ClientException: An image job failed. Reason: %s" %ex)
		Error = "ClientException"
		# fn = partial(ongoing_upload_task.increment, 'fails')
		# ongoing_upload_task.postprocess_queue.put(fn) # Multi-thread
		#def _abort_if_necessary():
		#  if ongoing_upload_task.check_continuous_fails(False):
		#    logger.info("Aborting threads because continuous failures exceed the"
		#        + " threshold.")
		#    map(lambda x: x.abort_thread(), ongoing_upload_task.object_threads)
		#ongoing_upload_task.postprocess_queue.put(_abort_if_necessary) # Multi-thread
		raise
	except IOError as err:
		logger.error("IOError: An image job failed.")
		Error = "IOError"
		if err.errno == ENOENT:
			logger.error("ENOENT")
	      # update_status(task_id, "failure", 'Local file ' + repr(image_record.OriginalFileName) + ' not found')
			# No such file or directory.
			# error_queue.put(
			    # 'Local file %s not found' % repr(image_record.OriginalFileName))
			# fn = partial(ongoing_upload_task.increment, 'fails')
			# ongoing_upload_task.postprocess_queue.put(fn) # Multi-thread
		else:
			logger.error("Error IOError")
			raise
	except:
		logger.error("Unhandled error")
		Error = "Unhandled error"
		
	finally:
		# commit_lock.acquire()
		logger.debug("updating status " + str(batch_id))
		status, err =  update_stats(task_id, "Finish", Error)
		if status:
			model.update_status(batch_id, err)
		# model.update_status(batch_id, Error)
		# model.commit()
		# commit_lock.release()


@app.task(bind=True)
def _upload_task_error_handler(self, uuid):
	result = self.app.AsyncResult(uuid)
	print('Task {0} raised exception: {1!r}\n{2!r}'.format(
	    uuid, result.result, result.traceback))

@app.task(bind=True)
def _upload_images_error_handler(self, uuid):
	result = self.app.AsyncResult(uuid)
	print('Task {0} raised exception: {1!r}\n{2!r}'.format(
	    uuid, result.result, result.traceback))
