#!/usr/bin/env python
# encoding: utf-8
"""
__init__.py
"""

from . import api
from . import backoffice
from . import libveezi
from . import transport

import pkg_resources as _pkg_resources


__version__ =_pkg_resources.get_distribution(__name__).version

def client(username, password, api_access_token):
	http = transport.HttpSession()
	bo = backoffice.BackofficeSession.login(username, password)
	a = api.VeeziApi(api_access_token, http = http)
	return libveezi.VeeziClient(a, bo)
