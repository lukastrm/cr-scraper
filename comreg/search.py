"""
Copyright (c) 2020 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""
import requests as rq
from html.parser import HTMLParser
from typing import Dict, Optional, List

from comreg.service import Session

DEFAULT_SEARCH_URL = "https://www.handelsregister.de/rp_web/search.do"


class SearchParameters:
    """This class represents the data structure for the parameters of a search request."""

    KEYWORDS_OPTION_ALL = 1
    """Option that results' names must contain all keywords"""

    KEYWORDS_OPTION_AT_LEAST_ONE = 2
    """Option that results's names must contain at least one of the keywords"""

    KEYWORDS_OPTION_EQUAL_NAME = 3
    """Option that result's names must match the name given as keywords"""

    def __init__(self, keywords: str = None, register_type: str = None, register_id: str = None,
                 register_court: str = None, establishment: str = None, search_option_deleted: bool = False,
                 keywords_option: int = KEYWORDS_OPTION_AT_LEAST_ONE, results_per_page: int = 10):
        """
        Initialize a `SearchParameters` object. Properties for parameters that will not be set receive a default value
        or None.

        :param keywords: the search request keywords (i.e. the legal entity name)
        :param register_type: the register type token
        :param register_id: the register id
        :param register_court: the register court identifier (obtained from a `CourtList` object)
        :param establishment: the entity's establishment
        :param search_option_deleted: True if deleted entries should be listed or False otherwise
        :param keywords_option: the option on how to process the keywords, see static class properties
        :param results_per_page: the option on how many results should be displayed per page, for this library no
        results from other pages will be analyzed
        """

        self.results_per_page = results_per_page
        self.establishment: str = establishment
        self.register_type: str = register_type
        self.register_id: str = register_id
        self.register_court: str = register_court
        self.keywords: str = keywords
        self.keywords_option: int = keywords_option
        self.search_option_deleted: bool = search_option_deleted

    def as_request_data(self) -> Dict[str, str]:
        """Returns a Python dictionary to use as request data parameter dictionary."""

        return {
            "btnSuche": "Suchen",
            "suchTyp": "n",
            "ergebnisseProSeite": self.results_per_page,
            "niederlassung": self.establishment,
            "registerArt": self.register_type if self.register_type is not None else "",
            "registerNummer": self.register_id if self.register_id is not None else "",
            "registergericht": self.register_court if self.register_court is not None else "",
            "schlagwoerter": self.keywords if self.keywords is not None else "",
            "schlagwortOptionen": self.keywords_option,
            "suchOptionenGeloescht": self.search_option_deleted
        }

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return str(self.__dict__)


RECORD_CONTENT_LEGAL_ENTITY_INFORMATION = "UT"
RECORD_CONTENT_DOCUMENTS = "DK"


class SearchResultEntry:
    """This class represents the data structure for a single search request result."""

    def __init__(self, index: int = -1, name: str = None):
        """
        Initialize a `SearchResultEntry`.

        :param index: the search result index as presented by the commercial register search request
        :param name: the legal entity's name as presented by the commercial register search request
        """
        self.index: int = index
        self.name: str = name
        self.contents: Dict[str, bool] = {
            """Python dictionary that contains flags indicating the existence of the different record contents"""

            "AD": False,
            "CD": False,
            "HD": False,
            RECORD_CONTENT_DOCUMENTS: False,
            RECORD_CONTENT_LEGAL_ENTITY_INFORMATION: False,
            "VÖ": False,
            "SI": False
        }

    def record_has_content(self, content: str) -> bool:
        """
        Returns whether a specific record content exists or not.

        :param content: the record content token (e.g. DK for documents, UT for legal entity information)
        :return: True if the content exists or False otherwise
        """
        return self.contents[content]

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return str(self.__dict__)


class SearchRequestHelper:
    """This class performs search requests with given search parameters."""

    def __init__(self, session: Session, url=DEFAULT_SEARCH_URL):
        """
        Initialize a `SearchRequestHelper` object.

        :param session: the `Session` object which identifies the session that is used to perform requests on the
        commercial register web service
        :param url: the URL string on which the request should be executed, defaults to the commercial register
        search URL
        """
        if not session or not session.identifier:
            raise ValueError("session oder session identifier must not be None or empty")

        if url is None:
            raise ValueError("url must not be None")

        self.__session = session
        self.__url = url

    def perform_request(self, parameters: SearchParameters) -> Optional[List[SearchResultEntry]]:
        """
        Performs a search request to the commercial register web service with the given parameters.

        :param parameters: the `SearchParameters` object containing the parameter values
        :return: a Python list of `SearchResultEntry` objects or None if the request failed
        """
        result = rq.post(self.__url + ";jsessionid=" + self.__session.identifier, data=parameters.as_request_data(),
                         cookies={"JSESSIONID": self.__session.identifier, "language": "de"})

        if result.status_code == 200 and result.text is not None:
            parser = SearchResultParser()
            parser.feed(result.text)
            return parser.result

        return None

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
    """
    This class parses the HTML result data that was fetched by the request of the `SearchRequestHelper` object. See
    the documentation for `HTMLParser` for more information about the implemented methods.

    This class is an implementation of a simple state machine to parse the given HTML content and extract relevant
    search result information. The result is a python list of `SearchResultEntry` objects representing the extracted
    information."""

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
