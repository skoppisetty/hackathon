from dataingestion.services.manager.celery_handler import _upload_task, _upload_task_error_handler
# from dataingestion.services.manager import celery_handler
import logging , sys

logger = logging.getLogger("iDigBioSvc.celery_manager")

class Celery_manager(object):
	"""Celery manager class"""
	def __init__(self):
		pass

	def setup(self, worker_thread_count):
		self.worker_thread_count = worker_thread_count

	def start_upload(self, values, task_id):
		logger.debug("received task")
		try:
			_upload_task.apply_async((task_id,values),link_error=_upload_task_error_handler.s())
			return ''
		except:
			error = "Unexpected error:" + str(sys.exc_info()[0])
			logger.error(error)
			return error