import logging
# celery manager - replace this with new manager if u want
from dataingestion.services.dbmodel import sql_model

logger = logging.getLogger("iDigBioSvc.Model")

model = sql_model

def setup(db_file):
	model.setup(db_file)

def close():
	model.close()

def commit():
	model.commit()

def add_batch(CSVfilePath, iDigbioProvidedByGUID,
	 RightsLicense, RightsLicenseStatementUrl, RightsLicenseLogoUrl, task_id):
	return model.add_batch(CSVfilePath, iDigbioProvidedByGUID,
		 RightsLicense, RightsLicenseStatementUrl, RightsLicenseLogoUrl, task_id)

def add_image(batch, row, headerline):
	return model.add_image(batch, row, headerline)

def update_image(image_record_id):
	logger.error(image_record_id)
	record = model.update_image(image_record_id)
	logger.error(record)
	return record

def update_status(batch_id, error):
	return model.update_status(batch_id, error)

def get_progress(task_id):
	if task_id is None:
		logger.error("No ongoing upload task.")
		return "No ongoing upload task."
	else :
		return model.get_batch_progress_brief(task_id)

def get_result(task_id):
	if task_id is None:
		logger.error("No ongoing upload task.")
		return "No ongoing upload task."
	else :
		return model.get_batch_details_brief(task_id)

def get_all_batches():
	return model.get_all_batches()

def get_batch_details_brief(batch_id):
	return model.get_batch_details_brief(batch_id)

def get_last_batch_info():
	return model.get_last_batch_info()

def update_batch(task_id, key, val):
	return model.update_batch(task_id, key, val)