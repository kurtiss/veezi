#!/usr/bin/env python
# encoding: utf-8
"""
transport.py
"""

import requests


class HttpSession(requests.Session):
	_VERIFY = False
	#_VERIFY = True
	# _PROXIES = dict()
	_PROXIES = dict(http = "http://localhost:8888", https = "https://localhost:8888")

	def request(self, *args, **kwargs):
		kwargs.setdefault("verify", self._VERIFY)
		kwargs.setdefault("proxies", self._PROXIES)
		return super(HttpSession, self).request(*args, **kwargs)
