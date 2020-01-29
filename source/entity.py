"""
Copyright (c) 2020 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""
import re
import requests
from html.parser import HTMLParser
from typing import List, Optional

from requests import RequestException

import utils
from search import SearchResultEntry
from service import DEFAULT_DOCUMENT_URL


REGISTRY_TYPES = ["HRA", "HRB", "GnR", "PR", "VR"]


class LegalEntityInformation:
    """This class represents the data structure for the legal entity information."""

    def __init__(self, name: Optional[str] = None, court: Optional[str] = None, registry_type: Optional[str] = None,
                 registry_id: Optional[str] = None, structure: Optional[str] = None, capital: Optional[int] = None,
                 capital_currency: Optional[str] = None, entry: Optional[str] = None, deletion: Optional[str] = None,
                 balance: Optional[List[str]] = None, address: Optional[str] = None, post_code: Optional[str] = None,
                 city: Optional[str] = None):
        """
        Initialize a `LegalEntityInformation` object.

        :param name: the entity name
        :param court: the court name where the entity is registered
        :param registry_type: the type of the registry record
        :param registry_id: the identifier of the registry record
        :param structure: the legal entity structure
        :param capital: the capital
        :param capital_currency: the capital currency
        :param entry: the entry date for that record
        :param deletion: the deletion date for that record
        :param balance: a list of dates from available balances
        :param address: the street address of the office address
        :param post_code: the post code of the office address
        :param city: the city of the office address
        """
        if registry_type is not None and registry_type not in REGISTRY_TYPES:
            raise ValueError("Unknown registry type")

        self.name: Optional[str] = name
        self.registry_court: Optional[str] = court
        self.registry_type: Optional[str] = registry_type
        self.registry_id: Optional[str] = registry_id
        self.structure: Optional[str] = structure
        self.capital: Optional[int] = capital
        self.capital_currency: Optional[str] = capital_currency
        self.entry: Optional[str] = entry
        self.deletion: Optional[str] = deletion
        self.balance: Optional[List[str]] = balance
        self.address: Optional[str] = address
        self.post_code: Optional[str] = post_code
        self.city: Optional[str] = city

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return str(self.__dict__)


class LegalEntityInformationFetcher:
    """This class fetches the legal entity information based on a given search result."""

    def __init__(self, session, search_result_entry: SearchResultEntry, url=DEFAULT_DOCUMENT_URL):
        """
        Initialize a `LegalEntityInformationFetcher` object.

        :param session: the `Session` object for the current session
        :param search_result_entry: the given search result entry for which the information should be extracted
        :param url: the legal entity information url that gives access to the information
        """

        self.__session = session
        self.__entry: SearchResultEntry = search_result_entry
        self.__url = url
        self.result: Optional[LegalEntityInformation] = None

    def fetch(self) -> Optional[LegalEntityInformation]:
        """
        Runs the fetching operation.

        :return: the `LegalEntityInformation` object containing the legal entity information or
        None if the request failed
        """

        try:
            result = requests.get(self.__url, params={"doctyp": "UT", "index": self.__entry.index},
                                  cookies={"JSESSIONID": self.__session.identifier, "language": "de"})

            if result.status_code == 200:
                parser = LegalEntityInformationParser()
                parser.feed(result.text)
                self.result = parser.result
                return self.result
        except RequestException as e:
            utils.LOGGER.exception(e)

        return None


STATE_VOID = 0
STATE_AWAIT_LEGAL_ENTITY_INFORMATION_HEADER = 1
STATE_LEGAL_ENTITY_INFORMATION_HEADER = 2
STATE_AWAIT_LEGAL_ENTITY_COURT = 3
STATE_AWAIT_REGISTRY_DETAIL_SECTION = 4
STATE_AWAIT_REGISTRY_DETAIL = 5
STATE_REGISTRY_DETAIL = 6
STATE_AWAIT_LEGAL_ENTITY_NAME = 7
STATE_LEGAL_ENTITY_NAME = 8
STATE_AWAIT_KEYWORD = 9
STATE_KEYWORD = 10
STATE_AWAIT_VALUE = 11
STATE_VALUE = 12

SUB_STATE_VOID = 0
SUB_STATE_AWAIT_STREET = 1
SUB_STATE_STREET = 2
SUB_STATE_AWAIT_CITY = 3
SUB_STATE_CITY = 4
SUB_STATE_AWAIT_BALANCE_OPTION = 5
SUB_STATE_AWAIT_BALANCE = 6


class LegalEntityInformationParser(HTMLParser):
    """
    This class parses the HTML result data that was fetched by the request of the `LegalEntityInformationFetcher`
    object. See the documentation for `HTMLParser` for more information about the implemented methods.

    This class is an implementation of a simple state machine to parse the given HTML content and extract relevant
    legal entity information. The result is a `LegalEntityInformation` object representing the extracted information.
    """

    KEYWORD_LEGAL_STRUCTURE = "Rechtsform"
    KEYWORD_CAPITAL = "Kapital"
    KEYWORD_ENTRY_DATE = "Eintragsdatum"
    KEYWORD_DELETION_DATE = "Löschdatum"
    KEYWORD_BALANCE = "Jahresabschluss"
    KEYWORD_ADDRESS = "Anschrift"

    KEYWORDS = [KEYWORD_LEGAL_STRUCTURE, KEYWORD_CAPITAL, KEYWORD_ENTRY_DATE, KEYWORD_DELETION_DATE, KEYWORD_BALANCE,
                KEYWORD_ADDRESS]

    def __init__(self):
        super().__init__()
        self.state = STATE_VOID
        self.sub_state = SUB_STATE_VOID
        self.result = LegalEntityInformation()
        self.keyword = None

    def error(self, message):
        pass

    def handle_starttag(self, tag, attrs):
        if tag == "h3":
            self.state = STATE_AWAIT_LEGAL_ENTITY_INFORMATION_HEADER
            return
        elif tag == "td":
            if self.state == STATE_LEGAL_ENTITY_INFORMATION_HEADER:
                self.state = STATE_AWAIT_LEGAL_ENTITY_COURT
            elif self.state == STATE_LEGAL_ENTITY_NAME or self.state == STATE_VALUE:
                self.state = STATE_AWAIT_KEYWORD
            elif self.state == STATE_KEYWORD:
                self.state = STATE_AWAIT_VALUE
        elif tag == "b":
            if self.state == STATE_AWAIT_REGISTRY_DETAIL_SECTION:
                self.state = STATE_AWAIT_REGISTRY_DETAIL
        elif tag == "div":
            if self.state == STATE_AWAIT_VALUE and self.sub_state == SUB_STATE_STREET:
                self.sub_state = SUB_STATE_AWAIT_CITY
        elif tag == "select":
            if self.state == STATE_AWAIT_VALUE:
                self.result.balance = []
                self.sub_state = SUB_STATE_AWAIT_BALANCE_OPTION
        elif tag == "option":
            if self.state == STATE_AWAIT_VALUE:
                if self.sub_state == SUB_STATE_AWAIT_BALANCE_OPTION:
                    self.sub_state = SUB_STATE_AWAIT_BALANCE

    def handle_data(self, data):
        if self.state == STATE_AWAIT_LEGAL_ENTITY_INFORMATION_HEADER:
            if "Unternehmensträgerdaten" in data:
                self.state = STATE_LEGAL_ENTITY_INFORMATION_HEADER
        elif self.state == STATE_AWAIT_LEGAL_ENTITY_COURT:
            if "Amtsgericht" in data:
                self.state = STATE_AWAIT_REGISTRY_DETAIL_SECTION
        elif self.state == STATE_AWAIT_REGISTRY_DETAIL:
            self.__set_registry_information(data)
            self.state = STATE_REGISTRY_DETAIL
        elif self.state == STATE_AWAIT_LEGAL_ENTITY_NAME:
            self.__set_name(data)
            self.state = STATE_LEGAL_ENTITY_NAME
        elif self.state == STATE_AWAIT_KEYWORD:
            self.state = STATE_KEYWORD

            for keyword in LegalEntityInformationParser.KEYWORDS:
                if data.strip().startswith(keyword):
                    self.keyword = keyword
                    return

            self.keyword = None
        elif self.state == STATE_AWAIT_VALUE:
            self.__handle_value(data)

    def __handle_value(self, value):
        if self.keyword == LegalEntityInformationParser.KEYWORD_LEGAL_STRUCTURE:
            self.__set_structure(value)
        elif self.keyword == LegalEntityInformationParser.KEYWORD_CAPITAL:
            self.__set_capital(value)
        elif self.keyword == LegalEntityInformationParser.KEYWORD_ENTRY_DATE:
            self.__set_date(value, True)
        elif self.keyword == LegalEntityInformationParser.KEYWORD_DELETION_DATE:
            self.__set_date(value, False)
        elif self.keyword == LegalEntityInformationParser.KEYWORD_BALANCE:
            if self.sub_state == SUB_STATE_AWAIT_BALANCE:
                self.__process_balance(value)
        elif self.keyword == LegalEntityInformationParser.KEYWORD_ADDRESS:
            if self.sub_state == SUB_STATE_VOID:
                self.sub_state = SUB_STATE_AWAIT_STREET
            elif self.sub_state == SUB_STATE_AWAIT_STREET:
                self.__set_address(value)
                self.sub_state = SUB_STATE_STREET
            elif self.sub_state == SUB_STATE_AWAIT_CITY:
                self.__set_city(value)
                self.sub_state = SUB_STATE_CITY

    def handle_endtag(self, tag):
        if tag == "h3":
            if self.state == STATE_AWAIT_LEGAL_ENTITY_INFORMATION_HEADER:
                self.state = STATE_VOID
        elif tag == "td":
            if self.state == STATE_AWAIT_LEGAL_ENTITY_COURT:
                self.state = STATE_LEGAL_ENTITY_INFORMATION_HEADER
            elif self.state == STATE_AWAIT_VALUE:
                self.state = STATE_VALUE
        elif tag == "b":
            if self.state == STATE_REGISTRY_DETAIL:
                self.state = STATE_AWAIT_LEGAL_ENTITY_NAME
        elif tag == "div":
            if self.sub_state == SUB_STATE_CITY:
                self.sub_state = SUB_STATE_VOID
                self.state = STATE_VALUE
        elif tag == "option":
            if self.sub_state == SUB_STATE_AWAIT_BALANCE:
                self.sub_state = SUB_STATE_AWAIT_BALANCE_OPTION
        elif tag == "select":
            if self.sub_state == SUB_STATE_AWAIT_BALANCE_OPTION:
                self.sub_state = SUB_STATE_VOID

    def __set_registry_information(self, data):
        match = re.match(r"^\s*(.*?)\s+(HRA|HRB|GnR|PR|VR)\s+(\d*?(?:\s+[a-zA-Z]{1,2})?)\s*$", data)

        if match is not None:
            self.result.registry_court = match.group(1)
            self.result.registry_type = match.group(2)
            self.result.registry_id = re.sub(r"\s\s+", " ", match.group(3))

    def __set_name(self, data):
        match = re.match(r"^\s*–\s*(.*?)\s*$", data)

        if match is not None:
            self.result.name = match.group(1)

    def __set_structure(self, data):
        match = re.match(r"^\s*(.*?)\s*$", data)

        if match is not None:
            self.result.structure = match.group(1)

    def __set_capital(self, data):
        match = re.match(r"^\s*((?:(?:\d{1,3})(?:\.\d{3})+|\d+)(?:,\d{1,2})?)\s*(EUR|DEM|€)?\s*$", data)

        if match is not None:
            self.result.capital = float(match.group(1).replace(".", "").replace(",", "."))
            self.result.capital_currency = match.group(2)

    def __set_date(self, data, entry):
        match = re.match(r"^\s*(\d{2}.\d{2}.\d{4})", data)

        if match is not None:
            if entry:
                self.result.entry = match.group(1)
            else:
                self.result.deletion = match.group(1)

    def __process_balance(self, data):
        match = re.match(r"^\s*(\d{2}.\d{2}.\d{4})\s*$", data)

        if match is not None:
            self.result.balance.append(match.group(1))

    def __set_address(self, data):
        match = re.match(r"^\s*(.*?)\s*$", data)

        if match is not None:
            self.result.address = match.group(1)

    def __set_city(self, data):
        match = re.match(r"^\s*(?:(\d{5})\s+)?([^\d\n]+)\s*$", data)

        if match is not None:
            self.result.post_code = match.group(1)
            self.result.city = match.group(2)
