#!/usr/bin/env python
# encoding: utf-8
"""
api.py
"""

import json

from . import transport


class VeeziApi(object):

	ROOT = "http://api.us.veezi.com/v1{0}"

	def __init__(self, access_token, http = None):
		self.access_token = access_token
		self.http = http or transport.HttpSession()

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

	def film(self, id):
		r = self._get(self._url("/film/{0}".format(id)))
		j = json.loads(r.text)
		return j

	def session(self, id):
		r = self._get(self._url("/session/{0}".format(id)))
		j = json.loads(r.text)
		return j

	def site(self):
		r = self._get(self._url("/site"))
		j = json.loads(r.text)
		return j

	def screen(self):
		r = self._get(self._url("/screen"))
		j = json.loads(r.text)
		return j