from collections import deque
class BatchUploadTask(object):
  """
  State about a single batch upload task.
  Note: batchUploadTask is threadsafe.
  functions are used to do exclusive access to attributes.
  """
  STATUS_FINISHED = "finished"
  STATUS_RUNNING = "running"
  STATUS_WAITING = "waiting"

  def __init__(self, batch=None, max_continuous_fails=1000):
    self.batch = batch
    self.object_queue = deque() # Thread safe object in python.
    self.postprocess_queue = deque() # Thread safe object in python.
    self.error_queue = deque() # Thread safe object in python.

    self._id = None
    self._total_count = 0
    self._status = None
    self._error_msg = None
    self._successes = 0
    self._skips = 0
    self._fails = 0
    self._continuous_fails = 0
    self._max_continuous_fails = max_continuous_fails
    self._csv_uploaded = False

  def set_id(self, task_id):
  	self._id = task_id

  def not_started(self):
    not_started = (self._total_count == 0 and self._status != self.STATUS_FINISHED)
    return not_started

  def get_all_information(self):
    total = self._total_count
    skips = self._skips
    successes = self._successes
    fails = self._fails
    csv = self._csv_uploaded
    status = self._status

    return total, skips, successes, fails, csv, status

  def is_finished(self):
    finished = (self._skips + self._successes + self._fails == self._total_count)
    return finished

  def set_csv_uploaded(self):
    self._csv_uploaded = True

  def csv_uploaded(self):
    ret = self._csv_uploaded
    return ret

  def get_skips(self):
    count = self._skips
    return count

  def get_fails(self):
    count = self._fails
    return count

  def get_successes(self):
    count = self._successes
    return count

  def get_total_count(self):
    count = self._total_count
    return count

  def get_status(self):
    status = self._status
    return status

  def set_status(self, status):
    self._status = status

  # Increment a field's value by 1.
  def increment(self, field_name_orig):
    field_name = "_" + field_name_orig
    try:
      if hasattr(self, field_name) and type(getattr(self, field_name)) == int:
        setattr(self, field_name, getattr(self, field_name) + 1)
      else:
        logger.error("BatchUploadTask object doesn't have this field or " +
            "has a field that cannot be incremented: {0}".format(field_name))
        raise ValueError("BatchUploadTask object doesn't have this field or " +
            "has a field that cannot be incremented: {0}".format(field_name))
    finally:
    	pass

  # Update the continuous failure times.
  def check_continuous_fails(self, succ_this_time):
    """
    :return: Whether this upload should be aborted.
    """
    try:
      if succ_this_time:
        self._continuous_fails = 0
        return False
      else:
        self._continuous_fails += 1

      if self._continuous_fails <= self._max_continuous_fails:
        return False
      else:
        return True
    finally:
      pass
