import sys, os, site
from os.path import join, exists
current_dir = os.path.abspath(os.getcwd())
site.addsitedir(join(current_dir, "lib"))

import appdirs
import argparse, ConfigParser, logging
import threading , cherrypy
from cherrypy import engine
import shutil, atexit
import logging.handlers
from datetime import datetime

from dataingestion.services import user_config, api_client

from dataingestion.services import model
from dataingestion.services import ingestion_manager
from dataingestion.web.ui.ingestui import DataIngestionUI
from dataingestion.web.rest.service_rest import DataIngestionService

APP_NAME = 'iDigBio Data Ingestion Tool'
APP_AUTHOR = 'iDigBio'
debug_mode = False
quiet_mode = False

CONFIG_DIR = 'etc'
USER_CONFIG_FILENAME = 'user.conf'
APPLIANCE_CONFIG_FILENAME = 'idigbio.conf'
HTTP_CONFIG_FILENAME = 'http.conf'
ENGINE_CONFIG_FILENAME = 'engine.conf'
STATIC_DIR  = current_dir + "/www"

LOG_NAME = APP_AUTHOR + 'Svc'
data_folder = appdirs.user_data_dir(APP_NAME, APP_AUTHOR)
db_file = None
logger = logging.getLogger( LOG_NAME + ".main")
log_level = None

class Config_Parser():
	def __init__(self):
		self.appliance_conf_path = join(current_dir, CONFIG_DIR, APPLIANCE_CONFIG_FILENAME)
		self.config = ConfigParser.ConfigParser()

	def read(self):
		self.config.read(self.appliance_conf_path)
		self.api_endpoint = self.config.get(APP_AUTHOR, 'api_endpoint')
		self.worker_thread_count = self.config.get(APP_AUTHOR, 'worker_thread_count')
		self.disable_startup_service_check = self.config.get(
		APP_AUTHOR, 'devmode_disable_startup_service_check')

class HTTPServer(threading.Thread):
	def __init__(self):
		self.http_conf_path = join(current_dir, CONFIG_DIR, HTTP_CONFIG_FILENAME)
		self.engine_conf_path = join(current_dir, CONFIG_DIR, ENGINE_CONFIG_FILENAME)
		self.static_config = {"tools.staticdir.root": STATIC_DIR}
		self.load_config()
		threading.Thread.__init__(self)
		self.sync = threading.Condition()

	def load_config(self):
		self.config(self.http_conf_path)
		self.config(self.engine_conf_path)
		self.config(self.static_config)

	def config(self, conf_path):
		cherrypy.config.update(conf_path)

	def mount(self,func,url,config):
		cherrypy.tree.mount(func, url,config=config)

	def run(self):
		with self.sync:
			cherrypy.engine.start()
			if not debug_mode and not quiet_mode:
				# In a proper run, the text written here will be the only text output
				# the end-user sees: Keep it short and simple.
				print("Starting the "+ APP_NAME + "...")
				try:
					import webbrowser
					webbrowser.open(
				    "http://127.0.0.1:{0}".format(cherrypy.config['server.socket_port']))
					logger.info("Webbrowser is opened.")
				except ImportError:
					# Gracefully fall back
					print("Open http://127.0.0.1:{0} in your webbrowser.".format(
				    cherrypy.config['server.socket_port']))
					print("Close this window or hit ctrl+c to stop the local iDigBio Data "
				    "Ingestion Tool.")
			cherrypy.engine.block()

	def stop(self):
		with self.sync:
		   cherrypy.engine.exit()
		   cherrypy.server.stop()

	def start(self):
	   if hasattr(engine, "signal_handler"):
	   	cherrypy.engine.signal_handler.subscribe()
	   if hasattr(engine, "console_control_handler"):
	   	cherrypy.engine.console_control_handler.subscribe()
		cherrypy.log("Starting...", "main")

class ArgParser():
	def __init__(self):
		global log_level
		self.parser = argparse.ArgumentParser()
		self.parser.add_argument("--newdb", action="store_true", help='create a new db file')
		self.parser.add_argument("-d", "--debug", action="store_true")
		self.parser.add_argument("-q", "--quiet", action="store_true")
		self.args = self.parser.parse_args()
		if self.args.debug:
			debug_mode = True
			log_level = logging.DEBUG
		else:
			debug_mode = False
			log_level = logging.WARNING 
		if self.args.quiet:
			quiet_mode = True
			if debug_mode:
				raise Exception("The --quiet or -q flags are not intended to be "
		        "used with the --debug or -d flags.")
		else:
			quiet_mode = False

def setup_db(args):
	global data_folder
	global db_file
	if not exists(data_folder):
		os.makedirs(data_folder)
	db_file = join(data_folder, APP_AUTHOR + ".ingest.db")
  	if args.newdb:
		_move_db()
		logger.info("Creating a new DB file.")
	logger.info("Use DB file: {0}".format(db_file))
	model.setup(db_file)

def _move_db():
	global data_folder
	global db_file
	if exists(db_file):
		model.close()  
		move_to = join(
        data_folder, APP_AUTHOR + ".ingest." + datetime.now().strftime(
            "%Y-%b-%d_%H-%M-%S") + ".db")
		shutil.move(db_file, move_to)
		cherrypy.log.error("Moved the old DB to {0}".format(move_to), "main")

def _logout_user_if_configured(user_config_path):
	global data_folder
	global db_file
	try:
		logout = dataingestion.services.user_config.get_user_config(
		'logoutafterexit')
	except AttributeError:
		logout = 'false'
	if logout == 'true':
		_move_db(data_folder, db_file)
		os.remove(user_config_path)

def setup_log():
	# Configure the logging mechanisms
	# Default log level to DEBUG and filter the logs for console output.
	global log_level
	logging.getLogger().setLevel(logging.DEBUG)
	logging.getLogger("cherrypy").setLevel(logging.INFO) # cherrypy must be forced
	svc_log = logging.getLogger(LOG_NAME)
	handler = logging.StreamHandler()
	handler.setFormatter(
	   logging.Formatter(
	       '%(asctime)s %(thread)d %(name)s %(levelname)s - %(message)s'))
	# User-specified log level only controls console output.
	handler.setLevel(log_level)
	svc_log.addHandler(handler)
	log_folder = appdirs.user_log_dir(APP_NAME, APP_AUTHOR)
	if not exists(log_folder):
	 os.makedirs(log_folder)
	log_file = join(log_folder, APP_AUTHOR + ".ingest.log")
	print "Log file:", log_file
	handler = logging.handlers.RotatingFileHandler(log_file, backupCount=10)
	handler.setFormatter(
	   logging.Formatter(
	       '%(asctime)s %(thread)d %(name)s %(levelname)s - %(message)s'))
	handler.setLevel(logging.DEBUG)
	handler.doRollover()
	svc_log.addHandler(handler)


def start_celery():
  try:
    # os.system("celeryd -l debug")
    os.system("celery worker -l debug &")
  except:
    logger.info("Unable to start Celery")
    sys.exit()

def kill_celery():
  os.system("pkill celery")


def main(argv):
	global data_folder
	global db_file
	# Process configuration files and configure modules.
	appliance_config = Config_Parser()
	appliance_config.read()

	# Setup Cherrypy Config
	server = HTTPServer()

	# Init WebUI and Ingestion Manager
	api_client.init(appliance_config.api_endpoint)
	ingestion_manager.setup(appliance_config.worker_thread_count)

	#Mount WebUI and REST API
	server.mount(DataIngestionUI(), '/', server.engine_conf_path)
	server.mount(DataIngestionService(), '/services', server.engine_conf_path)

	# Process command-line arguments:
	parser = ArgParser()
	
	if not debug_mode:
		server.config({"environment": "production"})

	setup_log()

	# Setup the db
	setup_db(parser.args)

	# Set up the user config.
	user_config_path = join(data_folder, USER_CONFIG_FILENAME)
	user_config.setup(user_config_path)
	user_config.set_user_config(
	'devmode_disable_startup_service_check', appliance_config.disable_startup_service_check)

	server.start()
	start_celery()
	server.run()
	atexit.register(
    _logout_user_if_configured, user_config_path)
	# atexit.register(server.stop)
	atexit.register(kill_celery)
	

if __name__ == '__main__':
	main(sys.argv)