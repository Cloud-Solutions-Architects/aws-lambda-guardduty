"""
lambda_function.test.py

:platform: Ihis module is compatible with Windows, Linux, and macOS
:synopsis: Configure GuardDuty Findings to the FortiGate Threat Feed - Lambda Function runtime code
:moduleauthor: Rene Sobral <rsobral@fortinet.com>
"""
__author__ = "Cloud Consulting Services"
__copyright__ = "Copyright 2025, Fortinet Inc."
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Cloud Consulting Services"
__email__ = "consulting@fortinet.com "
__status__ = "Production"

import unittest
import logging
import jsonpickle
from aws_xray_sdk.core import xray_recorder

logger = logging.getLogger()
xray_recorder.configure(
  context_missing='LOG_ERROR'
)

xray_recorder.begin_segment('test_init')
function = __import__('lambda_function')
handler = function.lambda_handler
xray_recorder.end_segment()

class TestFunction(unittest.TestCase):

  def test_function(self):
    xray_recorder.begin_segment('test_function')
    file = open('events/ignore.json', 'rb')
    try:
      ba = bytearray(file.read())
      event = jsonpickle.decode(ba)
      context = {'requestid' : '1234'}
      result = handler(event, context)
      print(str(result))
      self.assertRegex(str(result), 'body', 'Should match')
    finally:
      file.close()
    file.close()
    xray_recorder.end_segment()

if __name__ == '__main__':
    unittest.main()