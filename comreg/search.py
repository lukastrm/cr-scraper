"""
Copyright (c) 2020 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""
from html.parser import HTMLParser
import requests as rq

from comreg.service import Session

DEFAULT_SEARCH_URL = "https://www.handelsregister.de/rp_web/search.do"

PARAM_BUTTON_SEARCH = "btnSuche"
PARAM_RESULTS_PER_PAGE = "ergebnisseProSeite"
PARAM_ESTABLISHMENT = "niederlassung"
PARAM_REGISTER_TYPE = "registerArt"
PARAM_REGISTER_COURT = "registergericht"
PARAM_REGISTER_ID = "registerNummer"
PARAM_KEYWORDS = "schlagwoerter"
PARAM_KEYWORD_OPTIONS = "schlagwortOptionen"
PARAM_SEARCH_TYPE = "suchTyp"
PARAM_SEARCH_OPTION_DELETED = "suchOptionenGeloescht"

KEYWORD_OPTION_ALL = 1
KEYWORD_OPTION_AT_LEAST_ONE = 2
KEYWORD_OPTION_EQUAL_NAME = 3


class SearchParameters:

    def __init__(self):
        pass

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return str(self.__dict__)


class SearchRequest:
    """ This class performs a single search request with given registry parameters.
    """

    def __init__(self, session: Session, url=DEFAULT_SEARCH_URL, parameters=None):
        if not session or not session.identifier:
            raise ValueError("session oder session identifier must not be None or empty")

        if url is None:
            raise ValueError("url must not be None")

        self.session = session
        self.__url = url
        self.__parameters = parameters if parameters is not None else {
            PARAM_BUTTON_SEARCH: "Suchen",
            PARAM_RESULTS_PER_PAGE: 10,
            PARAM_ESTABLISHMENT: "",
            PARAM_REGISTER_TYPE: "",
            PARAM_REGISTER_COURT: "",
            PARAM_REGISTER_ID: "",
            PARAM_KEYWORDS: "",
            PARAM_KEYWORD_OPTIONS: KEYWORD_OPTION_AT_LEAST_ONE,
            PARAM_SEARCH_TYPE: 'n',
            PARAM_SEARCH_OPTION_DELETED: False
        }

        self.result = None

    def set_param(self, name, value):
        self.__parameters[name] = value

    def run(self):
        raw = self.__request()

        if raw is not None:
            parser = SearchResultParser()
            parser.feed(raw)
            self.result = parser.result
        else:
            self.result = None

        return self.result

    def __request(self):
        result = rq.post(self.__url + ";jsessionid=" + self.session.identifier, data=self.__parameters,
                         cookies={"JSESSIONID": self.session.identifier, "language": "de"})
        return result.text

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return str(self.__dict__)


class SearchResultParser(HTMLParser):

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
            self.result.append(SearchResultEntry(self.index, data))

    def handle_endtag(self, tag):
        self.name_flag = False


class SearchResultEntry:

    def __init__(self, index, name):
        self.index = index
        self.name = name

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return str(self.__dict__)
