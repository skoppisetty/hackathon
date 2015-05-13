import logging, os, sys
# celery manager - replace this with new manager if u want
from dataingestion.services.manager.celery_manager import Celery_manager  
from dataingestion.services import user_config
from dataingestion.services import model
from dataingestion.services.user_config import (get_user_config,
                                                set_user_config, rm_user_config)

logger = logging.getLogger("iDigBioSvc.ingestion_manager")

class IngestServiceException(Exception):
  def __init__(self, msg, reason=''):
    Exception.__init__(self, msg)
    self.reason = reason

class InputCSVException(Exception): 
  def __init__(self, msg, reason=''):
    Exception.__init__(self, msg)
    self.reason = reason

manager = Celery_manager()

def setup(worker_thread_count):
	manager.setup(worker_thread_count)

def get_last_batch_info():
	return model.get_last_batch_info()

def get_progress(task_id):
	return model.get_progress(task_id)

def get_result(task_id):
	return model.get_result(task_id)

def get_history(table_id):
	"""
	If batch_id is not given, return all batches.
	Otherwise, return the details of the batch with batch_id.
	"""
	if table_id is None or table_id == "":
		return model.get_all_batches()
	else:
		return model.get_batch_details_brief(table_id)

def start_upload(values, task_id):
	if values == None:
		logger.debug("resuming task")
		pass
	else:
		logger.debug("starting new task")
		    # Initial checks before the task is added to the queue.
		path = values[user_config.CSV_PATH]
		if not os.path.exists(path):
			error = 'CSV file \"' + path + '\" does not exist.'
			logger.error(error)
			return error
			# raise ValueError(error)
		elif os.path.isdir(path):
			error = 'The CSV path is a directory.'
			logger.error(error)
			return error
			# raise ValueError(error)
		logger.debug("All checks done")
		try:
			error = manager.start_upload(values, task_id)
			return error
		except:
			logger.debug("Unexpected error:" + str(sys.exc_info()[0]))
			return str(sys.exc_info()[0])
