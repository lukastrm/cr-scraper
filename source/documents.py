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

from entity import LegalEntityInformation
from search import SearchResultEntry
from service import Session, DEFAULT_DOCUMENT_URL


class DocumentsTreeElement:

    def __init__(self, name: str = None, as_directory: bool = False, parent: "DocumentsTreeElement" = None):
        self.name: Optional[str] = name
        self.parent: Optional[DocumentsTreeElement] = parent
        self.children: Optional[List[DocumentsTreeElement]] = [] if as_directory else None

    def create_child(self, name: str = None, as_directory: bool = False) -> "DocumentsTreeElement":
        element = DocumentsTreeElement(name, as_directory, self)

        if self.children is not None:
            self.children.append(element)
        else:
            raise ValueError("Cannot create a child for an element that is not a directory")

        return element

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return str(self.__dict__)


class ShareholderLists:

    def __init__(self, entity: LegalEntityInformation, documents: DocumentsTreeElement):
        self.entity = entity
        self._documents = documents
        self.dates: List[Optional[str]] = self.__extract(documents.children)

    def __extract(self, documents: List[DocumentsTreeElement], is_shareholder_lists: bool = False) -> List[Optional[str]]:
        dates = []

        for document in documents:
            if document.children is not None:
                dates.extend(self.__extract(document.children, is_shareholder_lists or document.name == "Liste der Gesellschafter"))
            elif is_shareholder_lists:
                if document.name.startswith("Liste der Gesellschafter"):
                    match = re.search(r"(\d{1,2}.\d{1,2}.\d{2,4})", document.name)

                    if match is not None:
                        dates.append(match.group(1))
                    else:
                        dates.append(None)

        return dates

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return str(self.__dict__)


class DocumentsTreeFetcher:

    def __init__(self, session: Session, url: str = DEFAULT_DOCUMENT_URL):
        self.__session: Session = session
        self.__url: str = url
        self.result: Optional[DocumentsTreeElement] = None

    def fetch(self, search_result_entry: SearchResultEntry) -> Optional[DocumentsTreeElement]:
        result = requests.get(self.__url, params={"doctyp": "DK", "index": search_result_entry.index},
                              cookies={"JSESSIONID": self.__session.identifier, "language": "de"})

        if result.status_code == 200:
            parser = DocumentsTreeParser()
            parser.feed(result.text)

            if parser.result is not None:
                self.result = parser.result

            return self.result

        return None


_STATE_VOID = 0
_STATE_ERROR = 1
_STATE_DIRECTORY_ROOT = 2
_STATE_DIRECTORY_CONTENTS = 3
_STATE_FILE_ROOT = 4
_STATE_FINISHED = 5


class DocumentsTreeParser(HTMLParser):

    def __init__(self):
        super().__init__()

        self._state: int = _STATE_VOID
        self._depth: int = 0
        self._element: Optional[DocumentsTreeElement] = None
        self.result: Optional[DocumentsTreeElement] = None

    def error(self, message):
        self._element = None
        self._state = _STATE_ERROR

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            for key, value in attrs:
                if key == "id":
                    if value == "tree-root" and self._state == _STATE_VOID:
                        self._element = DocumentsTreeElement("", True)
                        self._state = _STATE_DIRECTORY_ROOT
                        self._depth = 1
                elif key == "class":
                    if (value == "tree-open" or value == "tree-closed") and self._state == _STATE_DIRECTORY_ROOT:
                        self._state = _STATE_DIRECTORY_CONTENTS
                    elif value == "tree-node" and self._state == _STATE_DIRECTORY_CONTENTS:
                        self._element = self._element.create_child("", True)
                        self._state = _STATE_DIRECTORY_ROOT
                        self._depth += 1
                    elif value == "tree-file" and self._state == _STATE_DIRECTORY_CONTENTS:
                        self._element = self._element.create_child("")
                        self._state = _STATE_FILE_ROOT

    def handle_data(self, data):
        if self._state == _STATE_DIRECTORY_ROOT or self._state == _STATE_FILE_ROOT:
            self._element.name += data

    def handle_endtag(self, tag):
        if tag == "div":
            if self._state == _STATE_FILE_ROOT:
                self._element.name = self._element.name.strip()
                self._element = self._element.parent
                self._state = _STATE_DIRECTORY_CONTENTS
            elif self._state == _STATE_DIRECTORY_CONTENTS:
                self._state = _STATE_DIRECTORY_ROOT
            elif self._state == _STATE_DIRECTORY_ROOT:
                self._element.name = self._element.name.strip()
                self._depth -= 1

                if self._depth > 0:
                    self._element = self._element.parent
                    self._state = _STATE_DIRECTORY_CONTENTS
                else:
                    self.result = self._element
                    self._state = _STATE_FINISHED
