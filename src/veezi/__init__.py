#!/usr/bin/env python
# encoding: utf-8
"""
__init__.py
"""

from . import api
from . import backoffice
from . import libveezi
from . import transport


def client(username, password, api_access_token):
	http = transport.HttpSession()
	bo = backoffice.BackofficeSession.login(username, password)
	a = api.VeeziApi(api_access_token, http = http)
	return libveezi.VeeziClient(a, bo)