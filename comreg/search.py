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
        self.result = CRLegalEntityInformation()
        self.keyword_tag = False
        self.keyword = None
        self.data_tag = False
        self.previous = None
        self.address_index = 0

    def error(self, message):
        pass

    def handle_starttag(self, tag, attrs):
        self.previous = tag

        if tag == "td":
            if self.keyword is None and not self.data_tag:
                self.keyword_tag = True
            elif self.keyword is not None:
                self.data_tag = True

    def handle_data(self, data):
        if self.keyword_tag:
            for keyword in LegalEntityInformationParser.KEYWORDS:
                if data.strip().startswith(keyword):
                    self.keyword = keyword
                    return

        if not self.data_tag:
            return

        data = data.strip()

        if not data:
            return

        if self.keyword == LegalEntityInformationParser.KEYWORD_LEGAL_STRUCTURE:
            self.result.structure = data if self.result.structure is None else self.result.structure + data
        elif self.keyword == LegalEntityInformationParser.KEYWORD_CAPITAL:
            self.__set_capital(data)
        elif self.keyword == LegalEntityInformationParser.KEYWORD_ENTRY_DATE:
            self.__set_date(data, True)
        elif self.keyword == LegalEntityInformationParser.KEYWORD_DELETION_DATE:
            self.__set_date(data, False)
        elif self.keyword == LegalEntityInformationParser.KEYWORD_BALANCE:
            self.result.balance = data if self.result.balance is None else self.result.balance + data
        elif self.keyword == LegalEntityInformationParser.KEYWORD_ADDRESS:
            if self.previous == "div":
                self.__set_city(data)
            else:
                self.__set_address(data)

    def handle_endtag(self, tag):
        if tag == "td":
            if self.data_tag:
                self.keyword = None
                self.data_tag = False

            if self.keyword_tag:
                self.keyword_tag = False

    def __set_capital(self, data):
        p = re.compile("^(?:(?:\d{1,3})(?:\.\d{3})+|\d+)(?:,\d{1,2}){0,1} *(?:EUR|DEM|€){0,1}$")
        capital = p.findall(data)

        if len(capital) > 0:
            self.result.capital = capital[0]

            if len(capital) > 1:
                raise ValueError("Multiple capital entries:" + str(capital))

    def __set_date(self, data, entry):
        p = re.compile("^\d{2}.\d{2}.\d{4}")
        date = p.findall(data)

        if len(date) > 0:
            if entry:
                self.result.entry = date[0]
            else:
                self.result.deletion = date[0]

            if len(date) > 1:
                raise ValueError("Multiple entry dates:" + str(date))

    def __set_address(self, data):
        p = re.compile("^([^\d\n]*[^\d\n\s])\s*(\d+[^\d\n\s-]?(?:-\d+[^\d\n\s]?)?)?$")
        address = p.match(data)

        if address is not None:
            self.result.address = address.group(1)
            self.result.address += " " + address.group(2)

    def __set_city(self, data):
        p = re.compile("^(?:(\d{5})\s+)?([^\d\n]+)$")
        city = p.match(data)

        if city is not None:
            self.result.post_code = city.group(1)
            self.result.city = city.group(2)



class CRLegalEntityInformation:

    def __init__(self, structure=None, capital=None, entry=None, deletion=None, balance=None, address=None, post_code=None, city=None):
        self.structure = structure
        self.capital = capital
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
