#!/usr/bin/env python
# encoding: utf-8
"""
transport.py
"""

import requests


class HttpSession(requests.Session):
	# _VERIFY = False
	_VERIFY = True

	def request(self, *args, **kwargs):
		kwargs.setdefault("verify", self._VERIFY)
		return super(HttpSession, self).request(*args, **kwargs)