#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php
"""
This module encapulates the communication with iDigBio's storage service API.
"""
import cherrypy
import socket
import argparse, json, urllib2, logging, time, sys
import uuid
import base64
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
from time import sleep
from httplib import HTTPException

logger = logging.getLogger("iDigBioSvc.api_client")
register_openers()

api_endpoint = None

def init(api_ep):
  global api_endpoint
  api_endpoint = api_ep

TIMEOUT = 3

def _build_url(collection):
  assert api_endpoint
  if collection == "check":
    ret = "%s/%s" % (api_endpoint, collection)    
  else:
    ret = "%s/upload/%s" % (api_endpoint, collection)
  return ret

def _post_image(path, reference):
  url = _build_url("images")
  try:
    params = {"file": open(path, "rb"), "filereference": reference}
  except IOError as e:
    logger.error("File IO error: {0}".format(e))
    raise
  size = sys.getsizeof(params)
  datagen, headers = multipart_encode(params)
  try:
    request = urllib2.Request(url, datagen, headers)
    request.add_header("Authorization", "Basic %s" % auth_string)
    starttime = time.time()
    startptime = time.clock()
    resp = urllib2.urlopen(request, timeout=TIMEOUT).read()
    duration = time.time() - starttime
    ptime = time.clock() - startptime
    logger.debug("POSTing image done. Size: {0} Duration: {1} sec. Processing time: {2} sec."
        .format(size, duration, ptime))
    return resp
  except urllib2.HTTPError as e:
    logger.error("urllib2.HTTPError caught: {0}".format(e.code))
    if e.code == 500:
      logger.error("Fatal Server Exception Detected. HTTP Error code:{0}"
          .format(e.code))
      raise ServerException(
          "Fatal Server Exception Detected. HTTP Error code:{0}".format(e.code))
    logger.error("Failed to POST the media to server. url={0}, http_status={1},\
        http_response_content={2}, local_path={3}"
        .format(request.get_full_url(), e.code, e.read(), path))
    raise ClientException(
        "Failed to POST the media to server", url=request.get_full_url(),
        http_status=e.code, http_response_content=e.read(), local_path=path)
  except (urllib2.URLError, socket.error, socket.timeout, HTTPException) as e:
    # URLError: server down, network down.
    logger.error("{0} caught while POSTing the media. reason={1}, url={2}."
        .format(type(e), str(e), url))
    raise ClientException("{0} caught while POSTing the media.".format(type(e)),
                          reason=str(e), url=url)

def _post_csv(path):
  url = _build_url("datasets")
  try:
    params = {"file": open(path, "rb")}
  except IOError as e:
    logger.error("File IO error: {0}".format(e))
    raise
  size = sys.getsizeof(params)
  datagen, headers = multipart_encode(params)
  try:
    request = urllib2.Request(url, datagen, headers)
    request.add_header("Authorization", "Basic %s" % auth_string)
    starttime = time.time()
    startptime = time.clock()
    resp = urllib2.urlopen(request, timeout=TIMEOUT).read()    
    duration = time.time() - starttime
    ptime = time.clock() - startptime
    logger.debug("POSTing CSV file done. Size: {0} Duration: {1} sec. Processing time: {2} sec."
        .format(size, duration, ptime))
    return resp
  except urllib2.HTTPError as e:
    logger.debug("urllib2.HTTPError caught: {0}".format(e.code))
    if e.code == 500:
      logger.error("Fatal Server Exception Detected. HTTP Error code:{0}"
          .format(e.code))
      raise ServerException(
          "Fatal Server Exception Detected. HTTP Error code:{0}".format(e.code))
    logger.error("Failed to POST the media to server. url={0}, http_status={1},\
        http_response_content={2}, local_path={3}"
        .format(request.get_full_url(), e.code, e.read(), path))
    raise ClientException(
        "Failed to POST the CSV file to server", url=request.get_full_url(),
        http_status=e.code, http_response_content=e.read())
  except (urllib2.URLError, socket.error, socket.timeout, HTTPException) as e:
    logger.error("{0} caught while POSTing the media. reason={1}, url={2}."
        .format(type(e), str(e), url))
    raise ClientException("{0} caught while POSTing the CSV file.".format(type(e)),
                          reason=str(e), url=url)

auth_string = None

def authenticate(user, key):
  """
  Connect with the server to authenticate the accountID/key pair.
  Params:
    user: user account ID.
    key: The API key for the account ID.
  Returns:
    True if authentication is successful.
    False if authentication fails due to incorrect accountID/key pair.
  Except:
    ClientException: if the network connection corrupts or the server side is
                     unavailable.
  """

  global auth_string
  if auth_string: # This means the authentication was already successful.
    return True
  url = _build_url('check')
  try:
    req = urllib2.Request(url, '{ "idigbio:data": { } }',
                          {'Content-Type': 'application/json'})
    base64string = base64.encodestring('%s:%s' % (user, key)).replace('\n', '')
    req.add_header("Authorization", "Basic %s" % base64string)
    urllib2.urlopen(req, timeout=TIMEOUT)
    logger.info("Successfully logged in.")
    auth_string = base64string
    return True
  except urllib2.HTTPError as e:
    if e.code == 403 or e.code == 401:
      logger.error("authenticate error: {0}".format(e))
      return False
    else:
      logger.error("Failed to authenticate with server. url={0}, http_status={1},\
          http_response_content={2}, user={3}, key={4}"
          .format(url, e.code, e.read(), user, key))
      raise ClientException("Failed to authenticate with server.", url=url,
                            http_status=e.code, http_response_content=e.read(),
                            reason=user)
  except (urllib2.URLError, socket.error, socket.timeout, HTTPException) as e:
    logger.error("{0} caught while POSTing the media: url={1}, user={2}, key={3}"
        .format(type(e), url, user, key))
    raise ClientException("{0} caught while POSTing the media.".format(type(e)),
                          url=url, reason=user)
  return False

class ClientException(Exception):
  def __init__(self, msg, url='', http_status=None, reason='', local_path='',
         http_response_content=''):
    Exception.__init__(self, msg)
    self.msg = msg
    self.url = url
    self.http_status = http_status
    self.reason = reason
    self.local_path = local_path
    self.http_response_content = http_response_content

  def __str__(self):
    a = self.msg
    b = ''
    if self.url:
      b += self.url
    if self.http_status:
      if b:
        b = '%s %s' % (b, self.http_status)
      else:
        b = str(self.http_status)
    if self.reason:
      if b:
        b = '%s %s' % (b, self.reason)
      else:
        b = '- %s' % self.reason
    if self.local_path:
      if b:
        b = '%s %s' % (b, self.local_path)
      else:
        b = '- %s' % self.local_path
    if self.http_response_content:
      if len(self.http_response_content) <= 200:
        b += '   %s' % self.http_response_content
      else:
        b += '  [first 60 chars of response] %s' % \
           self.http_response_content[:200]
    return b and '%s: %s' % (a, b) or a


"""
This class is for Fatal Server Failure at server side.
If permanent server failure occurs, the appliance should elegantly finish itself.
Added by Kyuho on 06/17/2013
"""
class ServerException(Exception):
  def __init__(self, msg, http_status=None):
    Exception.__init__(self, msg)
    self.msg = msg
    self.http_status = http_status

  def __str__(self):
    return self.msg + str(self.http_status)


class Connection(object):
  """Convenience class to make requests that will also retry the request"""

  def __init__(self, authurl=None, user=None, key=None, retries=4,
               preauthurl=None, preauthtoken=None, snet=False,
               starting_backoff=1, auth_version="1"):
    """
    Params:
      authurl: authenitcation URL
      user: user name to authenticate as
      key: key/password to authenticate with
      retries: Number of times to retry the request before failing
      preauthurl: storage URL (if you have already authenticated)
      preauthtoken: authentication token (if you have already authenticated)
      snet: use SERVICENET internal network default is False
      auth_version: Openstack auth version.
    """
    self.authurl = authurl
    self.user = user
    self.key = key
    self.retries = retries
    self.http_conn = None
    self.url = preauthurl
    self.token = preauthtoken
    self.attempts = 0
    self.snet = snet
    self.starting_backoff = starting_backoff
    self.auth_version = auth_version

  def _retry(self, reset_func, func, *args, **kwargs):
    self.attempts = 0
    backoff = self.starting_backoff
    while self.attempts <= self.retries:
      self.attempts += 1
      try:
        rv = func(*args, **kwargs)
        return rv
      except ClientException as err:
        logger.error("ClientException caught: {0}, Current retry attempts: {1}"
            .format(err, self.attempts))

        if self.attempts > self.retries:
          logger.error("Retries exhausted. retry threshold: {0}"
              .format(self.retries))
          raise

        if err.http_status == 401: # Unauthorized
          if self.attempts > 1:
            raise
        elif err.http_status == 408: # Request Timeout
          pass
        elif 500 <= err.http_status <= 599:
          pass
        elif err.http_status is None:
          pass
        else:
          raise

      sleep(backoff)
      backoff *= 2
      if reset_func:
        reset_func(func, *args, **kwargs)

  def post_image(self, path, reference):
    return self._retry(None, _post_image, path, reference)

  def post_csv(self, path):
    return self._retry(None, _post_csv, path)
