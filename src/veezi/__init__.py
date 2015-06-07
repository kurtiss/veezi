#!/usr/bin/env python
# encoding: utf-8
"""
__init__.py
"""

import bs4
import datetime
import dateutil.parser
import enum
import json
import openpyxl
import re
import requests
import tempfile
import urlparse


def login(*args, **kwargs):
	return BackofficeSession.login(*args, **kwargs)


class HttpSession(requests.Session):
	# _VERIFY = False
	_VERIFY = True

	def request(self, *args, **kwargs):
		kwargs.setdefault("verify", self._VERIFY)
		return super(HttpSession, self).request(*args, **kwargs)


class VeeziApi(object):
	ROOT = "http://api.us.veezi.com/v1{0}"

	def __init__(self, access_token, http = None):
		self.access_token = access_token
		self.http = http or HttpSession()

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
	_LUMIERE = datetime.datetime(1895, 12, 28, 6)
	_REPORT_PATTERN = re.compile(r'"ExportUrlBase"\:(?P<value>"[^"]+")')

	@classmethod
	def _url(cls, path, root = None):
		r = root or cls.ROOT
		return r.format(path)

	@classmethod
	def login(cls, username, password, api_access_token):
		http = HttpSession()
		http.post(cls._url("/authentication/signin", root = cls.LOGIN_ROOT),
			data = dict(
				Username = username,
				Password = password,
				ReturnUrl = "/"
			)
		)

		api = VeeziApi(api_access_token, http = http)
		return cls(http, api)

	def __init__(self, http, api):
		self.http = http
		self.api = api

	def sitedetail(self, site_id):
		r = self.http.get(self._url("/programming/getsitedetail/{0}".format(site_id)))
		j = json.loads(r.text)
		return j

	def sessions(self, site_id, start_date = None, days = 365242):
		start_date = start_date or self._LUMIERE
		r = self.http.post(
			self._url("/programming/getsessionview/{0}".format(site_id)),
			data = dict(
				startDate = start_date.isoformat(),
				days = days,
				siteId = site_id
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

	def film(self, id):
		return self.api.film(id)

	def session(self, id):
		return self.api.session(id)

	def distributors_by_film_and_ticket_type_report(self, site_id, start_date, end_date,
			distributor_id = "", film_id = "", exclude_complimentaries = False,
			new_page_for_each = NewPageForEach.nothing, detail_level = DetailLevel.showtime_by_ticket_type,
			multi_feature_revenue = MultiFeatureRevenue.full_revenue_per_film):

		return self._report(
			Reports.distributors_by_film_and_ticket_type,
			dict(
				P193_From = start_date.strftime("%Y-%m-%d"),
				P193_To = end_date.strftime("%Y-%m-%d"),
				P194 = site_id,
				P199 = distributor_id,
				P198 = film_id,
				P195 = "Y" if exclude_complimentaries else "N",
				P196 = new_page_for_each.value,
				P197 = detail_level.value,
				P1251 = multi_feature_revenue.value
			)
		)

	def _report(self, report, user_params):
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
			for sheet_name in workbook.get_sheet_names():
				print "SHEET[" + sheet_name + "]"
				print ""
				for row in workbook[sheet_name].rows:
					print u"ROW[" + u" | ".join(unicode(r.value) for r in row) + "]"
					print ""
				print ""
				print ""
				print ""

# SHEET[Sheet1]

# ROW[None | Distributors by Film and Ticket Type | None | None | None | None | None | None | None | None | None | None | The Nightlight | None | None | None | None | None | None | None]

# ROW[None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[REPORT DATE RANGE | None | DISTRIBUTOR | None | None | None | FILM | None | None | MULTI/DOUBLE FEATURE | None | None | None | None | 30 N. High St.
#  44308 | None | None | None | None | None]

# ROW[Saturday, June 6, 2015  -
# Sunday, June 7, 2015 | None | All | None | None | None | All | None | None | Full Revenue per Film | None | None | None | None | None | None | None | None | None | None]

# ROW[None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[None | None | None | SALES | REFUNDS | None | None | ADMITS | GROSS PRICE | None | NET PRICE | NET TOTAL | None | None | TAX TOTAL | GROSS TOTAL | None | None | None | None]

# ROW[None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[A24 Films  -  Ex Machina | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[The Nightlight  -  Main | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[Saturday, June 6, 2015 | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[6:30 PM | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[Adult | None | None | 19 | 0 | None | None | 19 | 8.5 | None | 8.5 | 161.5 | None | None | 0.0 | 161.5 | None | None | None | None]

# ROW[Member | None | None | 4 | 0 | None | None | 4 | 6.5 | None | 6.5 | 26.0 | None | None | 0.0 | 26.0 | None | None | None | None]

# ROW[6:30 PM total | None | None | 23 | 0 | None | None | 23 | None | None | None | 187.5 | None | None | 0.0 | 187.5 | None | None | None | None]

# ROW[Saturday, June 6, 2015 total | None | None | 23 | 0 | None | None | 23 | None | None | None | 187.5 | None | None | 0.0 | 187.5 | None | None | None | None]

# ROW[Sunday, June 7, 2015 | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[3:30 PM | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[Adult | None | None | 3 | 0 | None | None | 3 | 8.5 | None | 8.5 | 25.5 | None | None | 0.0 | 25.5 | None | None | None | None]

# ROW[Senior Citizen | None | None | 2 | 0 | None | None | 2 | 7.5 | None | 7.5 | 15.0 | None | None | 0.0 | 15.0 | None | None | None | None]

# ROW[Aficionado Complimentary | None | None | 1 | 0 | None | None | 1 | 0 | None | 0 | 0.0 | None | None | 0.0 | 0.0 | None | None | None | None]

# ROW[3:30 PM total | None | None | 6 | 0 | None | None | 6 | None | None | None | 40.5 | None | None | 0.0 | 40.5 | None | None | None | None]

# ROW[Sunday, June 7, 2015 total | None | None | 6 | 0 | None | None | 6 | None | None | None | 40.5 | None | None | 0.0 | 40.5 | None | None | None | None]

# ROW[The Nightlight  -  Main total | None | None | 29 | 0 | None | None | 29 | None | None | None | 228.0 | None | None | 0.0 | 228.0 | None | None | None | None]

# ROW[Ex Machina total | None | None | 29 | 0 | None | None | 29 | None | None | None | 228.0 | None | None | 0.0 | 228.0 | None | None | None | None]

# ROW[A24 Films total | None | None | 29 | 0 | None | None | 29 | None | None | None | 228.0 | None | None | 0.0 | 228.0 | None | None | None | None]

# ROW[Independent Unknown  -  When Marnie Was There | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[The Nightlight  -  Main | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[Saturday, June 6, 2015 | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[4:15 PM | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[* General Admission | None | None | 14 | 0 | None | None | 14 | 9.0 | None | 9.0 | 126.0 | None | None | 0.0 | 126.0 | None | None | None | None]

# ROW[* General Admission (Web) | None | None | 8 | 0 | None | None | 8 | 8.5 | None | 8.5 | 68.0 | None | None | 0.0 | 68.0 | None | None | None | None]

# ROW[* Child (11-) (Web) | None | None | 2 | 0 | None | None | 2 | 7.5 | None | 7.5 | 15.0 | None | None | 0.0 | 15.0 | None | None | None | None]

# ROW[* Member (Web) | None | None | 1 | 0 | None | None | 1 | 6.5 | None | 6.5 | 6.5 | None | None | 0.0 | 6.5 | None | None | None | None]

# ROW[4:15 PM total | None | None | 25 | 0 | None | None | 25 | None | None | None | 215.5 | None | None | 0.0 | 215.5 | None | None | None | None]

# ROW[9:00 PM | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[* General Admission | None | None | 9 | 0 | None | None | 9 | 9.0 | None | 9.0 | 81.0 | None | None | 0.0 | 81.0 | None | None | None | None]

# ROW[* General Admission (Web) | None | None | 11 | 0 | None | None | 11 | 8.5 | None | 8.5 | 93.5 | None | None | 0.0 | 93.5 | None | None | None | None]

# ROW[* College Student | None | None | 2 | 0 | None | None | 2 | 8.0 | None | 8.0 | 16.0 | None | None | 0.0 | 16.0 | None | None | None | None]

# ROW[* Child (11-) (Web) | None | None | 2 | 0 | None | None | 2 | 7.5 | None | 7.5 | 15.0 | None | None | 0.0 | 15.0 | None | None | None | None]

# ROW[* College Student (Web) | None | None | 1 | 0 | None | None | 1 | 7.5 | None | 7.5 | 7.5 | None | None | 0.0 | 7.5 | None | None | None | None]

# ROW[* Member | None | None | 2 | 0 | None | None | 2 | 7.0 | None | 7.0 | 14.0 | None | None | 0.0 | 14.0 | None | None | None | None]

# ROW[* Aficionado Comp | None | None | 1 | 0 | None | None | 1 | 0 | None | 0 | 0.0 | None | None | 0.0 | 0.0 | None | None | None | None]

# ROW[* Staff Comp | None | None | 2 | 0 | None | None | 2 | 0 | None | 0 | 0.0 | None | None | 0.0 | 0.0 | None | None | None | None]

# ROW[9:00 PM total | None | None | 30 | 0 | None | None | 30 | None | None | None | 227.0 | None | None | 0.0 | 227.0 | None | None | None | None]

# ROW[Saturday, June 6, 2015 total | None | None | 55 | 0 | None | None | 55 | None | None | None | 442.5 | None | None | 0.0 | 442.5 | None | None | None | None]

# ROW[Sunday, June 7, 2015 | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[6:00 PM | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[* General Admission | None | None | 7 | 0 | None | None | 7 | 9.0 | None | 9.0 | 63.0 | None | None | 0.0 | 63.0 | None | None | None | None]

# ROW[* General Admission (Web) | None | None | 1 | 0 | None | None | 1 | 8.5 | None | 8.5 | 8.5 | None | None | 0.0 | 8.5 | None | None | None | None]

# ROW[* Child (11-) | None | None | 3 | 0 | None | None | 3 | 8.0 | None | 8.0 | 24.0 | None | None | 0.0 | 24.0 | None | None | None | None]

# ROW[* Child (11-) (Web) | None | None | 1 | 0 | None | None | 1 | 7.5 | None | 7.5 | 7.5 | None | None | 0.0 | 7.5 | None | None | None | None]

# ROW[6:00 PM total | None | None | 12 | 0 | None | None | 12 | None | None | None | 103.0 | None | None | 0.0 | 103.0 | None | None | None | None]

# ROW[Sunday, June 7, 2015 total | None | None | 12 | 0 | None | None | 12 | None | None | None | 103.0 | None | None | 0.0 | 103.0 | None | None | None | None]

# ROW[The Nightlight  -  Main total | None | None | 67 | 0 | None | None | 67 | None | None | None | 545.5 | None | None | 0.0 | 545.5 | None | None | None | None]

# ROW[When Marnie Was There total | None | None | 67 | 0 | None | None | 67 | None | None | None | 545.5 | None | None | 0.0 | 545.5 | None | None | None | None]

# ROW[Independent Unknown total | None | None | 67 | 0 | None | None | 67 | None | None | None | 545.5 | None | None | 0.0 | 545.5 | None | None | None | None]

# ROW[Janus Films  -  Rome, Open City | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[The Nightlight  -  Main | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[Sunday, June 7, 2015 | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[1:00 PM | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[Adult | None | None | 13 | 0 | None | None | 13 | 0.0 | None | 0.0 | 0.0 | None | None | 0.0 | 0.0 | None | None | None | None]

# ROW[1:00 PM total | None | None | 13 | 0 | None | None | 13 | None | None | None | 0.0 | None | None | 0.0 | 0.0 | None | None | None | None]

# ROW[Sunday, June 7, 2015 total | None | None | 13 | 0 | None | None | 13 | None | None | None | 0.0 | None | None | 0.0 | 0.0 | None | None | None | None]

# ROW[The Nightlight  -  Main total | None | None | 13 | 0 | None | None | 13 | None | None | None | 0.0 | None | None | 0.0 | 0.0 | None | None | None | None]

# ROW[Rome, Open City total | None | None | 13 | 0 | None | None | 13 | None | None | None | 0.0 | None | None | 0.0 | 0.0 | None | None | None | None]

# ROW[Janus Films total | None | None | 13 | 0 | None | None | 13 | None | None | None | 0.0 | None | None | 0.0 | 0.0 | None | None | None | None]

# ROW[Lions Gate Films  -  The Blair Witch Project | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[The Nightlight  -  Main | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[Saturday, June 6, 2015 | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[11:30 PM | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None | None]

# ROW[* General Admission | None | None | 4 | 0 | None | None | 4 | 9.0 | None | 9.0 | 36.0 | None | None | 0.0 | 36.0 | None | None | None | None]

# ROW[* General Admission (Web) | None | None | 4 | 0 | None | None | 4 | 8.5 | None | 8.5 | 34.0 | None | None | 0.0 | 34.0 | None | None | None | None]

# ROW[* Aficionado Comp | None | None | 1 | 0 | None | None | 1 | 0 | None | 0 | 0.0 | None | None | 0.0 | 0.0 | None | None | None | None]

# ROW[11:30 PM total | None | None | 9 | 0 | None | None | 9 | None | None | None | 70.0 | None | None | 0.0 | 70.0 | None | None | None | None]

# ROW[Saturday, June 6, 2015 total | None | None | 9 | 0 | None | None | 9 | None | None | None | 70.0 | None | None | 0.0 | 70.0 | None | None | None | None]

# ROW[The Nightlight  -  Main total | None | None | 9 | 0 | None | None | 9 | None | None | None | 70.0 | None | None | 0.0 | 70.0 | None | None | None | None]

# ROW[The Blair Witch Project total | None | None | 9 | 0 | None | None | 9 | None | None | None | 70.0 | None | None | 0.0 | 70.0 | None | None | None | None]

# ROW[Lions Gate Films total | None | None | 9 | 0 | None | None | 9 | None | None | None | 70.0 | None | None | 0.0 | 70.0 | None | None | None | None]

		return None