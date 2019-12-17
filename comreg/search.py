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
import re

from comreg.session import Session
from comreg.struct import LegalEntityInformation

DEFAULT_SEARCH_URL = "https://www.handelsregister.de/rp_web/search.do"
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

    def __init__(self, session: Session, url=DEFAULT_SEARCH_URL, params=None):
        if not session or not session.identifier:
            raise ValueError("session oder session identifier must not be None or empty")

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
        result = rq.post(self.url + ";jsessionid=" + self.session.identifier, data=self.params,
                         cookies={"JSESSIONID": self.session.identifier, "language": "de"})
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
