"""
Copyright (c) 2019 trm factory, Lukas Trommer
"""

from html.parser import HTMLParser
import requests as rq
import re

DEFAULT_URL = "https://www.handelsregister.de/rp_web/search.do"
DEFAULT_ENTITY_INFORMATION_URL = "https://www.handelsregister.de/rp_web/charge-info.do"
DEFAULT_DOCUMENT_URL = "https://www.handelsregister.de/rp_web/document.do"

PARAM_BUTTON_SEARCH = "btnSuche"
PARAM_RESULTS_PER_PAGE = "ergebnisseProSeite"
PARAM_ESTABLISHMENT = "niederlassung"
PARAM_REGISTER_TYPE = "registerArt"
PARAM_REGISTER_COURT = "registergericht"
PARAM_REGISTER_ID = "registerNummer"
PARAM_KEYWORDS = "schlagwoerter"
PARAM_KEYWORD_OPTIONS = "schlagwortOptionen"
PARAM_SEARCH_TYPE = "suchTyp"


class CRSearch:
    """ This class performs a single search request with given registry parameters.
    """

    def __init__(self, session, url=DEFAULT_URL, params=None):
        if session is None:
            raise ValueError("session must not be None")

        if url is None:
            raise ValueError("url must not be None")

        self.session = session
        self.url = url
        self.params = params if params is not None else {
            PARAM_BUTTON_SEARCH: "Suchen",
            PARAM_RESULTS_PER_PAGE: 10,
            PARAM_ESTABLISHMENT: None,
            PARAM_REGISTER_TYPE: None,
            PARAM_REGISTER_COURT: None,
            PARAM_REGISTER_ID: None,
            PARAM_KEYWORDS: None,
            PARAM_KEYWORD_OPTIONS: 2,
            PARAM_SEARCH_TYPE: None
        }

        self.result = None

    def set_param(self, name, value):
        self.params[name] = value

    def run(self):
        raw = self.__fetch()
        self.__parse(raw)
        return self.result

    def __fetch(self):
        result = rq.post(self.url + ";jsessionid=" + self.session, data=self.params, cookies={"JSESSIONID": self.session, "language": "de"})
        return result.text

    def __parse(self, result):
        p = CRSearchResultParser()
        p.feed(result)
        self.result = p.result


class CRSearchResultParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.result = []
        self.index = -1
        self.name_flag = False

    def error(self, message):
        pass

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for attr_name, attr_value in attrs:
                if attr_name == "name" and attr_value.startswith("Eintrag_"):
                    self.index = int(attr_value[len("Eintrag_"):])

        if tag == "td":
            for attr_name, attr_value in attrs:
                if attr_name == "class" and attr_value == "RegPortErg_FirmaKopf":
                    self.name_flag = True

    def handle_data(self, data):
        if self.name_flag:
            self.result.append(CRSearchResultEntry(self.index, data))

    def handle_endtag(self, tag):
        self.name_flag = False


class CRSearchResultEntry:

    def __init__(self, index, name):
        self.index = index
        self.name = name

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "{}: {}".format(self.index, self.name)


class CRLegalEntityInformationLookUp:

    def __init__(self, session, search_result_index, url=DEFAULT_DOCUMENT_URL):
        self.session = session
        self.index = search_result_index
        self.url = url

    def fetch(self):
        result = rq.get(self.url, params={"doctyp": "UT", "index": self.index}, cookies={"JSESSIONID": self.session, "language": "de"})

        p = LegalEntityInformationParser()
        p.feed(result.text)

        if "Fehler" in result.text:
            print("FEHLER")

        print(p.result)


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


class LegalEntityInformationParser(HTMLParser):

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
        self.result = CRLegalEntityInformation()
        self.keyword = None
        self.address_index = 0

    def error(self, message):
        pass

    def handle_starttag(self, tag, attrs):
        if tag == "h3":
            self.state = STATE_AWAIT_LEGAL_ENTITY_INFORMATION_HEADER
            return

        if tag == "td":
            if self.state == STATE_LEGAL_ENTITY_INFORMATION_HEADER:
                self.state = STATE_AWAIT_LEGAL_ENTITY_COURT
            elif self.state == STATE_LEGAL_ENTITY_NAME or self.state == STATE_VALUE:
                self.state = STATE_AWAIT_KEYWORD
            elif self.state == STATE_KEYWORD:
                self.state = STATE_AWAIT_VALUE

        if tag == "b":
            if self.state == STATE_AWAIT_REGISTRY_DETAIL_SECTION:
                self.state = STATE_AWAIT_REGISTRY_DETAIL

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
            self.state = STATE_VALUE
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
            self.result.balance = value if self.result.balance is None else self.result.balance + value
        elif self.keyword == LegalEntityInformationParser.KEYWORD_ADDRESS:
            pass

    def handle_endtag(self, tag):
        if tag == "h3":
            if self.state == STATE_AWAIT_LEGAL_ENTITY_INFORMATION_HEADER:
                self.state = STATE_VOID

        if tag == "td":
            if self.state == STATE_AWAIT_LEGAL_ENTITY_COURT:
                self.state = STATE_LEGAL_ENTITY_INFORMATION_HEADER

        if tag == "b":
            if self.state == STATE_REGISTRY_DETAIL:
                self.state = STATE_AWAIT_LEGAL_ENTITY_NAME

    def __set_registry_information(self, data):
        p = re.compile("^\s*(.*?)\s+(HRA|HRB|GnR|PR|VR)\s+(\d*?)\s*$")
        information = p.match(data)

        if information is not None:
            self.result.court = information.group(1)
            self.result.registry_type = information.group(2)
            self.result.registry_id = int(information.group(3))

    def __set_name(self, data):
        p = re.compile("^\s*–\s*(.*?)\s*$")
        name = p.match(data)

        if name is not None:
            self.result.name = name.group(1)

    def __set_structure(self, data):
        p = re.compile("^\s*(.*?)\s*$")
        structure = p.match(data)

        if structure is not None:
            self.result.structure = structure.group(1)

    def __set_capital(self, data):
        p = re.compile("^\s*((?:(?:\d{1,3})(?:\.\d{3})+|\d+)(?:,\d{1,2}){0,1})\s*(EUR|DEM|€){0,1}\s*$")
        capital = p.match(data)

        if capital is not None:
            self.result.capital = capital.group(1)
            self.result.capital_currency = capital.group(2)

    def __set_date(self, data, entry):
        p = re.compile("^\s*(\d{2}.\d{2}.\d{4})")
        date = p.match(data)

        if date is not None:
            if entry:
                self.result.entry = date.group(1)
            else:
                self.result.deletion = date.group(1)

    def __set_address(self, data):
        p = re.compile("^([^\d\n]*[^\d\n\s])\s*(\d+[^\d\n\s-]?(?:-\d+[^\d\n\s]?)?)?$")
        address = p.match(data)

        if address is not None:
            self.result.address = address.group(1)

            if self.result.address is not None:
                number = address.group(2)

                if number is not None:
                    self.result.address += " " + number

    def __set_city(self, data):
        p = re.compile("^(?:(\d{5})\s+)?([^\d\n]+)$")
        city = p.match(data)

        if city is not None:
            self.result.post_code = city.group(1)
            self.result.city = city.group(2)


class CRLegalEntityInformation:

    def __init__(self, name=None, court=None, registry_type=None, registry_id=None, structure=None, capital=None,
                 capital_currency=None, entry=None, deletion=None, balance=None, address=None, post_code=None,
                 city=None):
        self.name = name
        self.court = court
        self.registry_type = registry_type
        self.registry_id = registry_id
        self.structure = structure
        self.capital = capital
        self.capital_currency = capital_currency
        self.entry = entry
        self.deletion = deletion
        self.balance = balance
        self.address = address
        self.post_code = post_code
        self.city = city

    def __repr__(self):
        return str(self)

    def __str__(self):
        return str(self.__dict__)
