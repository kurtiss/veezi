#!/usr/bin/env python
# encoding: utf-8
"""
libveezi.py
"""

import collections
import datetime
import dateutil.parser

from . import backoffice


class VeeziClient(object):
	# CINEMA_EPOCH = datetime.datetime(1895, 12, 28, 6)
	CINEMA_EPOCH = datetime.datetime(1900, 1, 1, 6)

	def __init__(self, api, bo):
		self.api = api
		self.bo = bo

	def _box_office_report(self, start_date = None, end_date = None):
		start_date = start_date or self.CINEMA_EPOCH
		return self.bo.distributors_by_film_and_ticket_type_report(
			start_date,
			end_date or datetime.datetime.now()
		)

	def showdata(self, start_date = None, end_date = None):
		start_date = start_date or self.CINEMA_EPOCH
		if not end_date:
			end_date = start_date + datetime.timedelta(days = backoffice.BackofficeSession.MAX_BOR_DAYS)

		screens = self.api.screen()
		screens_by_name = dict()

		for screen in screens:
			screens_by_name[screen["Name"]] = screen

		bor = self._box_office_report(start_date = start_date, end_date = end_date)
		sessions = self.bo.sessions(start_date, days = (end_date - start_date).days)

		film_names_by_showkey = dict()
		distrib_names_by_showkey = dict()
		films = dict()
		shows = dict()

		for (site_name, film_name), engagement in bor.items():
			for show in engagement["showtimes"]:
				screen_name = show["screen_name"]
				screen = screens_by_name[screen_name]
				screen_id = screen["Id"]
				showtime = show["showtime"]

				show_key = (showtime, screen_id)
				shows[show_key] = dict(tickets = show["tickets"])
				film_names_by_showkey[show_key] = film_name
				distrib_names_by_showkey[show_key] = engagement["distributor_name"]

		for session in sessions:
			screen_id = session["screenId"]
			showtime = dateutil.parser.parse(session["start"])
			show_key = (showtime, screen_id)
			film_id = session["filmId"]

			try:
				show = shows[show_key]
			except KeyError:
				show = shows[show_key] = dict(tickets = dict())
			else:
				film_name = film_names_by_showkey[show_key]
				distributor_name = distrib_names_by_showkey[show_key]
				films[film_id] = dict(id = film_id, name = film_name, distributor_name = distributor_name)

			show["session"] = session

		return dict(
			films = films,
			shows = shows
		)
