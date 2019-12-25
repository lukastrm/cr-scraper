"""
Copyright (c) 2020 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""
import re
from typing import List, Optional

import requests
from html.parser import HTMLParser

from comreg.entity import LegalEntityInformation
from comreg.search import SearchResultEntry
from comreg.service import Session, DEFAULT_DOCUMENT_URL


class ShareholderLists:

    def __init__(self, entity: LegalEntityInformation, dates: Optional[List[str]] = None):
        self.entity = entity
        self.dates = [] if dates is None else dates

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return str(self.__dict__)


class ShareholderListsFetcher:

    def __init__(self, session: Session, url: str = DEFAULT_DOCUMENT_URL):
        self.__session: Session = session
        self.__url: str = url
        self.result: Optional[ShareholderLists] = None

    def fetch(self, search_result_entry: SearchResultEntry, entity: LegalEntityInformation) -> \
            Optional[ShareholderLists]:
        result = requests.get(self.__url, params={"doctyp": "DK", "index": search_result_entry.index},
                              cookies={"JSESSIONID": self.__session.identifier, "language": "de"})

        if result.status_code == 200:
            parser: ShareholderListsParser = ShareholderListsParser(entity)
            parser.feed(result.text)

            if parser.result is not None:
                self.result = parser.result

            return self.result

        return None


_STATE_VOID = 0
_STATE_ERROR = 1
_STATE_HEADING = 2
_STATE_AWAIT_LISTS_HEADER = 3
_STATE_LISTS_HEADER = 4
_STATE_AWAIT_TREE_ELEMENT = 5
_STATE_TREE_FILE = 6
_STATE_SUB_TREE = 7


class ShareholderListsParser(HTMLParser):

    def __init__(self, entity: LegalEntityInformation):
        super().__init__()

        self.__entity = entity
        self.__state: int = _STATE_VOID
        self.__tree_depth: int = 0
        self.__date: str = ""
        self.result: ShareholderLists = ShareholderLists(self.__entity)

    def error(self, message):
        self.__state = _STATE_ERROR
        self.result = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            if self.__state == _STATE_VOID:
                self.__state = _STATE_AWAIT_LISTS_HEADER
        elif tag == "div":
            if self.__state == _STATE_LISTS_HEADER:
                self.__state = _STATE_AWAIT_TREE_ELEMENT
            elif self.__state == _STATE_AWAIT_TREE_ELEMENT or self.__state == _STATE_SUB_TREE:
                for attr_name, attr_value in attrs:
                    if attr_name == "class":
                        if attr_value == "tree-file":
                            self.__state = _STATE_TREE_FILE
                        elif attr_value == "tree-node":
                            self.__state = _STATE_SUB_TREE
                            self.__tree_depth += 1
        elif tag == "h3":
            if self.__state == _STATE_VOID:
                self.__state = _STATE_HEADING

    def handle_data(self, data):
        if self.__state == _STATE_AWAIT_LISTS_HEADER:
            if data.strip() == "Liste der Gesellschafter":
                self.__state = _STATE_LISTS_HEADER
        elif self.__state == _STATE_TREE_FILE:
            self.__date += data.strip()
        elif self.__state == _STATE_HEADING:
            if "Fehler" in data:
                self.error(None)

    def handle_endtag(self, tag):
        if tag == "a":
            if self.__state == _STATE_AWAIT_LISTS_HEADER:
                self.__state = _STATE_VOID
        elif tag == "div":
            if self.__state == _STATE_TREE_FILE:
                match = re.match(r".*(\d{2}.\d{2}.\d{4}).*", self.__date)

                if self.result is not None:
                    self.result.dates.append(None if match is None else match.group(1))

                self.__date = ""
                self.__state = _STATE_AWAIT_TREE_ELEMENT
            elif self.__state == _STATE_AWAIT_TREE_ELEMENT:
                if self.__tree_depth > 0:
                    self.__state = _STATE_AWAIT_TREE_ELEMENT
                    self.__tree_depth -= 1
                else:
                    self.__state = _STATE_VOID
        elif tag == "h3":
            if self.__state == _STATE_HEADING:
                self.__state = _STATE_VOID
