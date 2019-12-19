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

from comreg.entity import ShareHolderLists, LegalEntityInformation
from comreg.search import SearchResultEntry
from comreg.service import Session, DEFAULT_DOCUMENT_URL

_STATE_VOID = 0
_STATE_AWAIT_LISTS_HEADER = 1
_STATE_LISTS_HEADER = 2
_STATE_AWAIT_TREE_ELEMENT = 3
_STATE_TREE_FILE = 4
_STATE_SUB_TREE = 5


class ShareHolderListsFetcher:

    def __init__(self, session: Session, url: str = DEFAULT_DOCUMENT_URL):
        self.__session: Session = session
        self.__url: str = url
        self.result: Optional[ShareHolderLists] = None

    def fetch(self, search_result_entry: SearchResultEntry, entity: LegalEntityInformation = None) -> \
            Optional[ShareHolderLists]:
        result = requests.get(self.__url, params={"doctyp": "DK", "index": search_result_entry.index},
                              cookies={"JSESSIONID": self.__session.identifier, "language": "de"})

        if result.status_code == 200:
            parser: ShareHolderListsParser = ShareHolderListsParser()
            parser.feed(result.text)
            self.result = ShareHolderLists(entity, parser.result)
            return self.result

        return None


class ShareHolderListsParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.__state: int = _STATE_VOID
        self.__tree_depth: int = 0
        self.__data: str = ""
        self.result: List[str] = []

    def error(self, message):
        pass

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

    def handle_data(self, data):
        if self.__state == _STATE_AWAIT_LISTS_HEADER:
            if data.strip() == "Liste der Gesellschafter":
                self.__state = _STATE_LISTS_HEADER
        if self.__state == _STATE_TREE_FILE:
            self.__data += data.strip()

    def handle_endtag(self, tag):
        if tag == "a":
            if self.__state == _STATE_AWAIT_LISTS_HEADER:
                self.__state = _STATE_VOID
        elif tag == "div":
            if self.__state == _STATE_TREE_FILE:
                date = re.match(r".*(\d{2}.\d{2}.\d{4}).*", self.__data)
                self.result.append(None if date is None else date.group(1))
                self.__data = ""
                self.__state = _STATE_AWAIT_TREE_ELEMENT
            elif self.__state == _STATE_AWAIT_TREE_ELEMENT:
                if self.__tree_depth > 0:
                    self.__state = _STATE_AWAIT_TREE_ELEMENT
                    self.__tree_depth -= 1
                else:
                    self.__state = _STATE_VOID
