#!/usr/bin/env python
# encoding: utf-8
"""
libveezi.py
"""

import collections
import datetime
import dateutil.parser

from .constants import DEFAULT_SITE_ID
from . import backoffice


class VeeziClient(object):
	# CINEMA_EPOCH = datetime.datetime(1895, 12, 28, 6)
	CINEMA_EPOCH = datetime.datetime(1900, 1, 1, 6)

	def __init__(self, backoffice_session, api_session):
		self.backoffice_session = backoffice_session
		self.api_session = api_session

	def _box_office_report(self, start_date, end_date):
		start_date = start_date or self.CINEMA_EPOCH
		return self.backoffice_session.distributors_by_film_and_ticket_type_report(
			start_date,
			end_date or datetime.datetime.now()
		)

	def _sites(self):
		site_response = self.api_session.site()
		return {
			DEFAULT_SITE_ID : dict(
				id = DEFAULT_SITE_ID,
				name = site_response["Name"],
				short_name = site_response["ShortName"],
				legal_name = site_response["LegalName"],
				screen_ids = [s["Id"] for s in site_response["Screens"]],
				address = "\n".join(filter(None, [
					site_response["Address1"] or "",
					site_response["Address2"] or "",
					site_response["Country"] or "" + site_response["Postcode"] or ""
				])),
				phone = site_response["Phone1"],
				phone_2 = site_response["Phone2"],
				fax = site_response["Fax"],
				receipt_message = "\n".join(filter(None, [
					site_response["ReceiptMessage1"],
					site_response["ReceiptMessage2"],
					site_response["ReceiptMessage3"],
					site_response["ReceiptMessage4"],
					site_response["ReceiptMessage5"],
					site_response["ReceiptMessage6"],
				])),
				ticket_message = "\n".join(filter(None, [
					site_response["TicketMessage1"] or "",
					site_response["TicketMessage2"] or ""
				])),
				national_code = site_response["NationalCode"],
				timezone_identifier = site_response["TimeZoneIdentifier"],
				sales_tax_registration = site_response["SalesTaxRegistration"]
			)
		}

	def _sites_by_screen_id(self, sites):
		result = dict()
		for site_id, site in sites.items():
			for screen_id in site["screen_ids"]:
				result[screen_id] = site
		return result

	def _screens(self, sites_by_screen_id):
		screens = self.api_session.screen()
		result = dict()

		for screen in screens:
			result[screen["Id"]] = dict(
				site_id = sites_by_screen_id[screen["Id"]]["id"],
				id = screen["Id"],
				name = screen["Name"],
				number = int(screen["ScreenNumber"]),
				attributes = screen["Attributes"],
				has_custom_layout = screen["HasCustomLayout"],
				total_seats = screen["TotalSeats"],
				wheelchair_seats = screen["WheelchairSeats"],
				house_seats = screen["HouseSeats"],
			)
		return result

	def _screens_by_name(self, screens):
		result = dict()
		for screen_id, screen in screens.items():
			result[screen["name"]] = screen
		return result

	def _show(self, tickets = None):
		return dict(boxoffice = tickets or dict())

	def query(self, start_date = None, end_date = None):
		start_date = start_date or self.CINEMA_EPOCH
		if not end_date:
			end_date = start_date + datetime.timedelta(days = backoffice.BackofficeSession.MAX_BOR_DAYS)

		sites = self._sites()
		sites_by_screen_id = self._sites_by_screen_id(sites)
		screens = self._screens(sites_by_screen_id)
		screens_by_name = self._screens_by_name(screens)
		bor = self._box_office_report(start_date = start_date, end_date = end_date)
		sessions = self.backoffice_session.sessions(start_date, days = (end_date - start_date).days)

		film_names_by_show_key = dict()
		distrib_names_by_show_key = dict()
		films = dict()
		shows = dict()

		for (site_name, film_name), engagement in bor.items():
			for show in engagement["showtimes"]:
				screen_id = screens_by_name[show["screen_name"]]["id"]
				site_id = sites_by_screen_id[screen_id]["id"]
				show_key = (site_id, screen_id, show["showtime"])

				shows[show_key] = self._show(tickets = show["tickets"])
				film_names_by_show_key[show_key] = film_name
				distrib_names_by_show_key[show_key] = engagement["distributor_name"]

		for session in sessions:
			screen_id = session["screenId"]
			site_id = sites_by_screen_id[screen_id]["id"]
			showtime = dateutil.parser.parse(session["start"])
			show_key = (site_id, screen_id, showtime)
			film_id = session["filmId"]

			try:
				show = shows[show_key]
			except KeyError:
				show = shows[show_key] = self._show()
			else:
				film_name = film_names_by_show_key[show_key]
				distributor_name = distrib_names_by_show_key[show_key]
				films[film_id] = dict(
					id = film_id,
					name = film_name,
					distributor_name = distributor_name
				)
			show.update(dict(
				advance_revenue = session["advanceRevenue"],
				cleanup_duration = session["cleanupDuration"],
				code = session["code"],
				complimentaries = session["complimentaries"] == "Y",
				distributor_share = session["distributorShare"],
				film_id = session["filmId"],
				finish = session["finish"],
				id = session["id"],
				intermission = session["intermission"],
				is_stopped = session["isStopped"],
				language_id = session["languageId"],
				play_through_group_code = session["playThruGroupCode"],
				price_card_id = session["priceCardId"],
				sales_types = session["salesTypes"],
				seats = session["seats"],
				seats_available = session["seatsAvailable"],
				seats_held = session["seatsHeld"],
				seats_house = session["seatsHouse"],
				seats_sold = session["seatsSold"],
				status = session["sessionStatus"],
				show_number = session["showNumber"],
				show_type = session["showType"],
				start = session["start"],
				validation_errors = session["validationErrors"],
				site_id = site_id,
				screen_id = screen_id
			))

		return dict(
			films = films,
			shows = shows,
			sites = sites,
			screens = screens,
		)
