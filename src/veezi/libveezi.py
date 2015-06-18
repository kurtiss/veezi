#!/usr/bin/env python
# encoding: utf-8
"""
libveezi.py
"""

import datetime
import dateutil.parser


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

	def showtimes(self, start_date = None, end_date = None):
		start_date = start_date or self.CINEMA_EPOCH

		screens = self.api.screen()
		screens_by_name = dict()

		for screen in screens:
			screens_by_name[screen["Name"]] = screen

		bor = self._box_office_report(start_date = start_date, end_date = end_date)
		sessions = self.bo.sessions(start_date)

		films = dict()
		showtimes = dict()

		for (site_name, film_name), engagement in bor.items():
			for showtime in engagement["showtimes"]:
				screen_id = screens_by_name[showtime["screen_name"]]["Id"]

				try:
					screen_showtimes = showtimes[screen_id]
				except KeyError:
					screen_showtimes = showtimes[screen_id] = dict()

				screen_showtimes[showtime["showtime"]] = dict(
					film_name = film_name,
					sales = showtime["sales"]
				)

		screenless_sessions = []
		showtimeless_sessions = []

		for session in sessions:
			screen_id = session["screenId"]
			showtime_dt = dateutil.parser.parse(session["start"])

			try:
				showtime_screen = showtimes[screen_id]
			except KeyError:
				screenless_sessions.append(session)
				continue

			try:
				showtime = showtime_screen[showtime_dt]
			except KeyError:
				showtimeless_sessions.append(session)
				continue

			film_name = showtime.pop("film_name")
			film_id = session["filmId"]
			showtime["session"] = session
			showtime["film_id"] = film_id
			films[film_id] = dict(name = film_name)

		return dict(
			films = films,
			showtimes = showtimes,
			screenless_sessions = screenless_sessions,
			showtimeless_sessions = showtimeless_sessions
		)