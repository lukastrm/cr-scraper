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

from requests import RequestException

import utils
from entity import LegalEntityInformation
from search import SearchResultEntry
from service import Session, DEFAULT_DOCUMENT_URL


class DocumentsTreeElement:
    """This class represents the data structure for a single element in the web service's documents tree."""

    def __init__(self, name: str = None, as_directory: bool = False, parent: "DocumentsTreeElement" = None):
        """
        Initialize a `DocumentsTreeElement`.

        :param name: the name of that element
        :param as_directory: True if that element serves as a directory for other elements, False otherwise
        :param parent: the parent element or None for the root of the tree
        """

        self.name: Optional[str] = name
        self.parent: Optional[DocumentsTreeElement] = parent
        self.children: Optional[List[DocumentsTreeElement]] = [] if as_directory else None

    def create_child(self, name: str = None, as_directory: bool = False) -> "DocumentsTreeElement":
        """
        Creates a child element if this element is a directory.

        :param name: the name of the child element
        :param as_directory: True if the child element is a directory, False otherwise
        :return: the element that was created
        """

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
    """This class represents the data structure for a list of shareholder list dates"""

    def __init__(self, entity: LegalEntityInformation, documents: DocumentsTreeElement):
        """
        Initialize a `ShareholderLists` object.

        :param entity: the corresponding legal entity the documents refer to
        :param documents: the documents as `DocumentsTreeElement` as obtained from `DocumentsTreeFetcher`
        """

        self.entity = entity
        self._documents = documents
        self.dates: List[Optional[str]] = self.__extract(documents.children)

    def __extract(self, documents: List[DocumentsTreeElement], is_shareholder_lists: bool = False) -> \
            List[Optional[str]]:
        """
        Extracts the shareholder list dates from a given document tree.

        :param documents: the document directory as `DocumentsTreeElement` object
        :param is_shareholder_lists: True if the documents object is a subdirectory of a shareholder lists directory,
        False otherwise
        :return: a python string list of shareholder list dates
        """

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
    """This class fetches the documents tree for a legal entity based on a given search result."""

    def __init__(self, session: Session, url: str = DEFAULT_DOCUMENT_URL):
        """
        Initialize a `DocumentsTreeFetcher` object.

        :param session: the `Session` object for the current session
        :param url: the documents url that gives access to the information
        """

        self.__session: Session = session
        self.__url: str = url
        self.result: Optional[DocumentsTreeElement] = None

    def fetch(self, search_result_entry: SearchResultEntry) -> Optional[DocumentsTreeElement]:
        """
        Runs the fetching operation.

        :return: the `DocumentsTreeElement` object containing the documents' information or None if the request failed
        """

        try:
            result = requests.get(self.__url, params={"doctyp": "DK", "index": search_result_entry.index},
                                  cookies={"JSESSIONID": self.__session.identifier, "language": "de"})

            if result.status_code == 200:
                parser = DocumentsTreeParser()
                parser.feed(result.text)

                if parser.result is not None:
                    self.result = parser.result

                return self.result
        except RequestException as e:
            utils.LOGGER.exception(e)

        return None


_STATE_VOID = 0
_STATE_ERROR = 1
_STATE_DIRECTORY_ROOT = 2
_STATE_DIRECTORY_CONTENTS = 3
_STATE_FILE_ROOT = 4
_STATE_FINISHED = 5


class DocumentsTreeParser(HTMLParser):
    """
    This class parses the HTML result data that was fetched by the request of the `DocumentsTreeFetcher`
    object. See the documentation for `HTMLParser` for more information about the implemented methods.

    This class is an implementation of a simple state machine to parse the given HTML content and extract relevant
    documents' information. The result is a `DocumentsTreeElement` object representing the extracted information.
    """

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
