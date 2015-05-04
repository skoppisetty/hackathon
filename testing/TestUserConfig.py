#!/usr/bin/env python
#
# Copyright (c) 2013 Liu, Yonggang <myidpt@gmail.com>, University of Florida
#
# This software may be used and distribted according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

# This preprocess is to set up the paths to make sure the current module
# referencing in the files to be tested.
import sys, os, unittest, tempfile, datetime
rootdir = os.path.dirname(os.getcwd())
sys.path.append(rootdir)
sys.path.append(os.path.join(rootdir, 'lib'))

from dataingestion.services import user_config


class TestUserConfig(unittest.TestCase):
  def setUp(self):
    f = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    self._filePath = f.name
    f.close()

  def runTest(self):
    # Test setup, set_user_config and get_user_config.
    user_config.setup(self._filePath)
    name_values = {'account_uuid': 'id1', 'api_key': 'key1'}
    user_config.set_user_config('account_uuid', name_values['account_uuid'])
    user_config.set_user_config('api_key', name_values['api_key'])
    self.assertTrue(user_config.get_user_config('account_uuid'),
                    name_values['account_uuid'])
    self.assertTrue(user_config.get_user_config('api_key'),
                    name_values['api_key'])
    # Test rm_user_config and try_get_user_config.
    user_config.rm_user_config()
    self.assertRaises(AttributeError, user_config.get_user_config,
                      'account_uuid')


if __name__ == '__main__':
   unittest.main()
