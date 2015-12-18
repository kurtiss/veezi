#!/usr/bin/env python
# encoding: utf-8
"""
backoffice.py
"""

import bs4
import contextlib
import datetime
import dateutil.parser
import enum
import json
import logging
import more_itertools
import openpyxl
import re
import tempfile

from urllib.parse import urlparse

from . import transport
from . import loggers


log = loggers.getLogger(__name__)

def _log_row_type(row_type, row):
	log.debug(u"{0}: {1}".format(row_type, u" | ".join(unicode(c.value) for c in row)))


class Reports(enum.Enum):
	distributors_by_film_and_ticket_type = 5


class NewPageForEach(enum.Enum):
	nothing = "N"
	film = "F"
	distributor = "D"


class DetailLevel(enum.Enum):
	film = "Film"
	film_by_day = "FilmDay"
	film_by_day_and_ticket_type = "FilmDayTicket"
	film_by_screen_and_day = "FilmScreenDay"
	showtime = "Show"
	showtime_by_ticket_type = "ShowTicket"


class MultiFeatureRevenue(enum.Enum):
	split_revenue_per_film = "S"
	full_revenue_per_film = "F"


class BackofficeSession(object):

	ROOT = "https://my.us.veezi.com{0}"
	LOGIN_ROOT = "https://my.veezi.com{0}"
	MAX_BOR_DAYS = 365242
	_REPORT_PATTERN = re.compile(r'"ExportUrlBase"\:(?P<value>"[^"]+")')

	@classmethod
	def _url(cls, path, root = None):
		r = root or cls.ROOT
		return r.format(path)

	@classmethod
	def login(cls, username, password, http = None, site_id = 9999):
		http = http or transport.HttpSession()
		result = cls(http, site_id)
		result._login(username, password)
		return result

	def __init__(self, http, site_id):
		self.http = http
		self.site_id = site_id

	def _login(self, username, password):
		self.http.post(self._url("/authentication/signin", root = self.LOGIN_ROOT),
			data = dict(
				Username = username,
				Password = password,
				ReturnUrl = "/"
			)
		)

	def sitedetail(self):
		r = self.http.get(self._url("/programming/getsitedetail/{0}".format(self.site_id)))
		j = json.loads(r.text)
		return j

	def sessions(self, start_date, days = None):
		days = days if days is not None else self.MAX_BOR_DAYS
		r = self.http.post(
			self._url("/programming/getsessionview/{0}".format(self.site_id)),
			data = dict(
				startDate = start_date.isoformat(),
				days = days,
				siteId = self.site_id
			)
		)
		j = json.loads(r.text)
		return j["sessions"]

	def showtimes(self, *args, **kwargs):
		sessions = self.sessions(*args, **kwargs)
		showtimes_by_film_id = dict()

		for showtime in sessions:
			film_id = showtime["filmId"]
			try:
				film_showtimes = showtimes_by_film_id[film_id]
			except KeyError:
				film_showtimes = showtimes_by_film_id[film_id] = []
			film_showtimes.append(showtime)
			showtime["start"] = dateutil.parser.parse(showtime["start"])

		for film_id in showtimes_by_film_id.keys():
			showtimes_by_film_id[film_id].sort(cmp = lambda x,y: cmp(x["start"], y["start"]))

		return showtimes_by_film_id

	def films(self):
		r = self.http.get(self._url("/films/index"))
		s = bs4.BeautifulSoup(r.text)
		trs = s.find("tbody").find_all("tr")
		films = []

		for tr in trs:
			link = tr.find("a")
			edit_url = link["href"]
			tds = tr.find_all("td")

			films.append(dict(
				title = link.text,
				edit_url = edit_url,
				session = edit_url.split("/")[-1],
				distributor_name = tds[1].text,
				release_date = datetime.datetime.strptime(tr.find("td", class_="date").text, "%m/%d/%Y"),
				genre = tds[3].text,
				is_active = tds[4].text.strip() == u"Active"
			))

		return films

	def distributors_by_film_and_ticket_type_report(self, start_date, end_date,
			distributor_id = "", film_id = "", exclude_complimentaries = False,
			new_page_for_each = NewPageForEach.nothing, detail_level = DetailLevel.showtime_by_ticket_type,
			multi_feature_revenue = MultiFeatureRevenue.full_revenue_per_film):

		dbfattr = self._report_workbook(
			Reports.distributors_by_film_and_ticket_type,
			dict(
				P193_From = start_date.strftime("%Y-%m-%d"),
				P193_To = end_date.strftime("%Y-%m-%d"),
				P194 = self.site_id,
				P199 = distributor_id,
				P198 = film_id,
				P195 = "Y" if exclude_complimentaries else "N",
				P196 = new_page_for_each.value,
				P197 = detail_level.value,
				P1251 = multi_feature_revenue.value
			)
		)

		param_keys = [
			'REPORT DATE RANGE',
			'DISTRIBUTOR',
			'FILM',
			'MULTI/DOUBLE FEATURE',
		]

		report_keys = [
			'SALES',
			'REFUNDS',
			'ADMITS',
			'GROSS PRICE',
			'NET PRICE',
			'NET TOTAL',
			'TAX TOTAL',
			'GROSS TOTAL'
		]

		engagements = dict()

		with dbfattr as wb:
			ws = wb["Sheet1"]

			report_name = ws.rows[0][1].value
			site_name = ws.rows[0][12].value
			param_key_offsets = self._get_offsets(ws.rows[3], param_keys)
			param_key_values = self._get_cell_values(ws.rows[4], param_key_offsets)

			report_key_offsets = self._get_offsets(ws.rows[9], report_keys)
			rows_it = more_itertools.peekable(ws.rows)
			more_itertools.consume(rows_it, 11)

			while rows_it.peek(None) is not None:
				distrib_row = rows_it.next()
				_log_row_type("DISTRIBUTOR", distrib_row)

				distrib_name, film_name = distrib_row[0].value.split("  -  ", 1)
				end_film_value = "{0} total".format(film_name)
				end_distrib_value = "{0} total".format(distrib_name)

				while rows_it.peek()[0].value != end_film_value:
					site_screen_row = rows_it.next()
					_log_row_type("SITE & SCREEN", site_screen_row)

					site_screen_value = site_screen_row[0].value
					site_name, screen_name = site_screen_value.split("  -  ", 1)
					end_site_value = "{0} total".format(site_screen_value)

					showtimes = []

					while rows_it.peek()[0].value != end_site_value:
						showdate_row = rows_it.next()
						_log_row_type("SHOWDATE", showdate_row)

						showdate_value = showdate_row[0].value
						end_showdate_value = "{0} total".format(showdate_value)
						showdate_dt = dateutil.parser.parse(showdate_value)

						while rows_it.peek()[0].value != end_showdate_value:
							showtime_row = rows_it.next()
							_log_row_type("SHOWTIME", showtime_row)

							showtime_value = showtime_row[0].value
							full_showtime_value = "{0} {1}".format(showdate_value, showtime_value)
							end_showtime_value = "{0} total".format(showtime_value)
							full_showtime_dt = dateutil.parser.parse(full_showtime_value)

							tickets = dict()

							while rows_it.peek()[0].value != end_showtime_value:
								tt_row = rows_it.next()
								_log_row_type("TICKET TYPE", tt_row)

								tt_name = tt_row[0].value
								if tt_name is not None:
									tickets[tt_name] = dict(
										name = tt_name,
										sales = self._get_cell_value(tt_row, report_key_offsets, 'SALES'),
										refunds = self._get_cell_value(tt_row, report_key_offsets, 'REFUNDS'),
										admits = self._get_cell_value(tt_row, report_key_offsets, 'ADMITS'),
										gross_price = self._get_cell_value(tt_row, report_key_offsets, 'GROSS PRICE'),
										net_price = self._get_cell_value(tt_row, report_key_offsets, 'NET PRICE'),
										net_total = self._get_cell_value(tt_row, report_key_offsets, 'NET TOTAL'),
										tax_total = self._get_cell_value(tt_row, report_key_offsets, 'TAX TOTAL'),
										gross_total = self._get_cell_value(tt_row, report_key_offsets, 'GROSS TOTAL')
									)
							end_showtime_row = rows_it.next()
							_log_row_type("END SHOWTIME", end_showtime_row)

							showtimes.append(dict(
								screen_name = screen_name,
								showtime = full_showtime_dt,
								tickets = tickets
							))

						end_showdate_row = rows_it.next()
						_log_row_type("END SHOWDATE", end_showdate_row)

					engagement_key = (site_name, film_name)

					try:
						engagement = engagements[engagement_key]
					except KeyError:
						engagement = engagements[engagement_key] = dict(
							site_name = site_name,
							film_name = film_name,
							distributor_name = distrib_name,
							showtimes = showtimes,
						)

					end_site_row = rows_it.next()
					_log_row_type("END SITE", end_site_row)

				end_film_row = rows_it.next()
				_log_row_type("END FILM", end_film_row)

				if rows_it.peek()[0].value == end_distrib_value:
					end_distrib_row = rows_it.next()
					_log_row_type("END DISTRIBUTOR", end_distrib_row)

					# consume any blank rows
					while True:
						post_distrib_row = rows_it.peek(False)
						if post_distrib_row != False:
							if not filter(None, [c.value for c in post_distrib_row]):
								blank_row = rows_it.next()
								_log_row_type("BLANK", blank_row)
								continue
						break

		return engagements

	def _get_offsets(self, row, expect_keys):
		cells_i = more_itertools.peekable(enumerate(row))
		expect_keys_i = more_itertools.peekable(expect_keys)
		offsets = dict()
		end = object()

		while cells_i.peek(end) != end:
			i, cell = cells_i.next()
			if expect_keys_i.peek(end) == cell.value:
				expect_key = expect_keys_i.next()
				offsets[expect_key] = i

		return offsets

	def _get_cell_values(self, row, offsets):
		values = dict()
		for offset_key, offset_value in offsets.items():
			values[offset_key] = row[offset_value].value
		return values

	def _get_cell_value(self, row, offsets, name):
		return row[offsets[name]].value

	@contextlib.contextmanager
	def _report_workbook(self, report, user_params):
		params = dict(reportId = report.value)
		params.update(user_params)

		r = self.http.post(
			self._url("/webforms/reportlauncher.aspx"),
			params = params
		)

		export_url_base = json.loads(
			self._REPORT_PATTERN.search(r.text).group("value")
		)
		export_url_base_p = urlparse.urlparse(export_url_base)
		export_url_base_params = urlparse.parse_qs(export_url_base_p.query, True)
		export_url_base_params["Format"] = "EXCELOPENXML"

		with tempfile.NamedTemporaryFile(prefix = export_url_base_params["FileName"][0], mode = 'r+b') as erf:
			e = self.http.get(
				self._url(export_url_base_p.path),
				params = export_url_base_params,
				stream = True
			)

			for chunk in e.iter_content(chunk_size = 4096):
				if chunk:
					erf.write(chunk)
					erf.flush()

			workbook = openpyxl.load_workbook(erf)
			yield workbook
