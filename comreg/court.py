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
from typing import List, Tuple, Optional, Dict
from difflib import SequenceMatcher

from comreg.service import Session

_DEFAULT_SEARCH_FORM_URL = "https://www.handelsregister.de/rp_web/mask.do?Typ=n"

_STATE_VOID = 0
_STATE_AWAIT_OPTION = 1
_STATE_AWAIT_NAME = 2
_STATE_NAME = 3


class Court:
    """This class represents the data structure for a registry court."""

    def __init__(self, identifier: str = None, name: str = None):
        """
        Initialize a `Court` object.

        :param identifier: the unique registry court identifier used by the commercial register search form
        :param name: the name of the registry court displayed in the commercial register search form
        """
        self.identifier: str = identifier
        self.name: str = name

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return str(self.__dict__)


class CourtList:
    """This class represents a list of available registry courts with implementations to select a contained court
    based on a given name oder identifier """

    def __init__(self, court_list: List[Court]):
        """
        Initialize a `CourtList` object.

        :param court_list: A python list of `Court` objects that this `CourtList` object will contain
        """

        self.name_map: Dict[str, Court] = dict([(court.name, court) for court in court_list])
        self.identifier_map: Dict[str, Court] = dict([(court.identifier, court) for court in court_list])

    def get_from_name(self, name: str) -> Court:
        """
        Returns the matching `Court` object based on a given registry court name. Returns `None` if there is no
        `Court` object in the list whose name exactly matches the given string.

        :param name: the name of the desired registry court
        :return: the matching `Court` object or `None` if no match was found
        """

        return None if name is None else self.name_map.get(name)

    def get_closest_from_name(self, name: str) -> Court:
        """
        Returns the matching `Court` object based on a given registry court name. This method selects the object with
        the most similar name to the given string. Returns `None` if the list is empty.

        :param name: the name of the desired registry court
        :return: a tuple with the matching court object and the similarity ratio of both names or None and a zero ratio
        otherwise
        """
        ratio: float = 0
        court: Optional[Court] = None

        if name is None:
            return court

        for n, c in self.name_map.items():
            if re.match(r".*\({}\).*".format(name), n):
                return c

        for n, c in self.name_map.items():
            r = SequenceMatcher(None, name, n).ratio()

            if r > ratio:
                court = c
                ratio = r

        return court

    def get_from_identifier(self, identifier: str) -> Court:
        """
        Returns the matching `Court` object based on a given registry court identifier. Returns `None` if there is no
        `Court` object in the list whose identifier exactly matches the given string.

        :param identifier: the identifier of the desired registry court
        :return: the matching `Court` object or `None` if no match was found
        """
        return self.identifier_map.get(identifier)

    def __len__(self):
        return len(self.name_map)

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return str(self.name_map.values())


class CourtListFetcher:
    """This class fetches the list of available courts from the commercial register search form."""

    def __init__(self, session: Session, url: str = _DEFAULT_SEARCH_FORM_URL):
        """
        Initialize a `CourtListFetcher` object.

        :param session: the `Session` object which identifies the session that is used to perform requests on the
        commercial register web service
        :param url: the URL string on which the request should be executed,
        defaults to the commercial register search form URL
        """

        self.__session: Session = session
        self.__url: str = url
        self.result: Optional[CourtList] = None

    def run(self) -> Optional[CourtList]:
        """Runs the fetching operation."""

        result = requests.get(self.__url, cookies={"JSESSIONID": self.__session.identifier, "language": "de"})

        if result.status_code == 200:
            parser = CourtListParser()
            parser.feed(result.text)
            self.result = CourtList(parser.result)
            return self.result

        return None


class CourtListParser(HTMLParser):
    """
    This class parses the HTML result data that was fetched by the request of the `CourtListFetcher` object. See
    the documentation for `HTMLParser` for more information about the implemented methods.

    This class is an implementation of a simple state machine to parse the given HTML content and extract relevant
    registry court information. The result is a python list of `Court` objects representing the extracted information.
    """

    def __init__(self):
        super().__init__()
        self.__state: int = _STATE_VOID
        self.result: List[Court] = []
        self.__court: Optional[Court] = None

    def error(self, message):
        pass

    def handle_starttag(self, tag, attrs):
        if tag == "select":
            for attr_name, attr_value in attrs:
                if attr_name == "name" and attr_value == "registergericht":
                    self.__state = _STATE_AWAIT_OPTION
        elif tag == "option":
            if self.__state != _STATE_AWAIT_OPTION:
                return

            identifier: Optional[str] = None

            for attr_name, attr_value in attrs:
                if attr_name == "value":
                    identifier = attr_value

            if identifier and re.search(r"\A[A-Z]\d{4}\Z", identifier):
                self.__court = Court(identifier)
                self.__state = _STATE_AWAIT_NAME
            else:
                self.__state = _STATE_NAME

    def handle_data(self, data):
        if self.__state == _STATE_AWAIT_NAME:
            self.__court.name = data.strip()
            self.__state = _STATE_NAME

    def handle_endtag(self, tag):
        if tag == "select":
            if self.__state == _STATE_AWAIT_OPTION:
                self.__state = _STATE_VOID
        elif tag == "option":
            if self.__state == _STATE_NAME:
                self.__state = _STATE_AWAIT_OPTION

                if self.__court is not None:
                    self.result.append(self.__court)
                    self.__court = None
