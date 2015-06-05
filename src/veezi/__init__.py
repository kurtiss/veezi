#!/usr/bin/env python
# encoding: utf-8
"""
__init__.py
"""

import json
import requests


class VeeziApi(object):
	ROOT = "http://api.us.veezi.com/v1{0}"

	def __init__(self, access_token):
		self.access_token = access_token
		self.http = requests.Session()

	def _get(self, *args, **kwargs):
		headers = kwargs.setdefault("headers", dict())
		headers["VeeziAccessToken"] = self.access_token
		headers["Accept"] = "text/plain"
		return self.http.get(*args, **kwargs)

	def _url(self, path):
		return self.ROOT.format(path)

	def session(self):
		r = self._get(self._url("/session"))
		j = json.loads(r.text)
		return j