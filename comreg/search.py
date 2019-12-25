"""
Copyright (c) 2020 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""
from html.parser import HTMLParser
from typing import Dict, Optional

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


_STATE_VOID = 0
_STATE_ERROR = 1
_STATE_AWAIT_ENTRY = 2
_STATE_ENTITY_NAME = 3
_STATE_RECORD_CONTENTS = 4
_STATE_RECORD_CONTENT = 5
_STATE_ENTRY = 6


class SearchResultParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.state = _STATE_VOID
        self.result = []
        self.entry: Optional[SearchResultEntry] = None

    def error(self, message):
        pass

    def handle_starttag(self, tag, attrs):
        if tag == "td":
            if self.state == _STATE_VOID:
                for attr_name, attr_value in attrs:
                    if attr_name == "class" and attr_value == "RegPortErg_AZ":
                        self.state = _STATE_AWAIT_ENTRY
                        self.entry = SearchResultEntry()
            elif self.state == _STATE_AWAIT_ENTRY:
                for attr_name, attr_value in attrs:
                    if attr_name == "class":
                        if attr_value == "RegPortErg_FirmaKopf":
                            self.state = _STATE_ENTITY_NAME
                        elif attr_value == "RegPortErg_RandRechts":
                            self.state = _STATE_RECORD_CONTENTS

        elif tag == "a":
            if self.state == _STATE_AWAIT_ENTRY:
                for attr_name, attr_value in attrs:
                    if attr_name == "name" and attr_value.startswith("Eintrag_"):
                        self.entry.index = int(attr_value[len("Eintrag_"):])
            elif self.state == _STATE_RECORD_CONTENTS:
                self.state = _STATE_RECORD_CONTENT

    def handle_data(self, data):
        if self.state == _STATE_ENTITY_NAME:
            self.entry.name = data.strip()
        elif self.state == _STATE_RECORD_CONTENT:
            data = data.strip()

            if self.entry.contents[data] is not None:
                self.entry.contents[data] = True

    def handle_endtag(self, tag):
        if tag == "td":
            if self.state == _STATE_ENTITY_NAME:
                self.state = _STATE_AWAIT_ENTRY
            elif self.state == _STATE_RECORD_CONTENTS:
                self.state = _STATE_ENTRY
        elif tag == "tr":
            if self.state == _STATE_ENTRY:
                self.state = _STATE_VOID
                self.result.append(self.entry)
                self.entry = None
        elif tag == "a":
            if self.state == _STATE_RECORD_CONTENT:
                self.state = _STATE_RECORD_CONTENTS


RECORD_CONTENT_LEGAL_ENTITY_INFORMATION = "UT"
RECORD_CONTENT_DOCUMENTS = "DK"


class SearchResultEntry:

    def __init__(self, index: int = -1, name: str = None):
        self.index: int = index
        self.name: str = name
        self.contents: Dict[str, bool] = {
            "AD": False,
            "CD": False,
            "HD": False,
            RECORD_CONTENT_DOCUMENTS: False,
            RECORD_CONTENT_LEGAL_ENTITY_INFORMATION: False,
            "VÖ": False,
            "SI": False
        }

    def record_has_content(self, content: str) -> bool:
        return self.contents[content]

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return str(self.__dict__)
