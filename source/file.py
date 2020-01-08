"""
Copyright (c) 2020 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""
import csv
import re
from typing import Optional

import utils
from documents import ShareholderLists
from entity import LegalEntityInformation, REGISTRY_TYPES

ENCODING = "utf-8"


class SearchInputRecord:

    def __init__(self, name: str = None, registry_type: Optional[str] = None, registry_id: Optional[str] = None,
                 registry_court: Optional[str] = None):
        self.name: str = name
        self.registry_type: Optional[str] = registry_type
        self.registry_id: Optional[str] = registry_id
        self.registry_court: Optional[str] = registry_court

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return str(self.__dict__)


class SearchInputDataFileReader:

    def __init__(self, path: str, header: bool = True, delimiter: str = ","):
        self.__path: str = path
        self.__header: bool = header
        self.__delimiter = delimiter

        self.__file = None
        self.__reader = None

    def __enter__(self):
        self.__file = open(self.__path, "r", encoding=ENCODING)
        self.__reader = csv.reader(self.__file, delimiter=self.__delimiter)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__file.close()

    def __iter__(self):
        return self

    def __next__(self) -> Optional[SearchInputRecord]:
        if self.__header:
            next(self.__reader)
            self.__header = False

        raw: str = next(self.__reader)

        if len(raw) < 6:
            return None

        name: str = raw[0]
        registry_id: Optional[str] = re.match(r"^\D*(\d+ ?\w{0,2})\s*$", raw[2])
        registry_type: Optional[str] = raw[3]
        registry_court: Optional[str] = raw[5]

        if registry_type is not None and registry_type not in REGISTRY_TYPES:
            utils.LOGGER.error("Omitting invalid registry type {} for search record {}".format(registry_type, name))
            registry_type = None

        return SearchInputRecord(name, registry_type, None if registry_id is None else registry_id.group(1),
                                 registry_court)


_COL_NAME = "name"
_COL_REGISTRY_TYPE = "registry_type"
_COL_REGISTRY_ID = "registry_id"
_COL_REGISTRY_COURT = "registry_court"
_COL_STRUCTURE = "structure"
_COL_CAPITAL = "capital"
_COL_CAPITAL_CURRENCY = "capital_currency"
_COL_ENTRY = "entry"
_COL_DELETION = "deletion"
_COL_BALANCE = "balance"
_COL_ADDRESS = "address"
_COL_POST_CODE = "post_code"
_COL_CITY = "city"


class LegalEntityInformationFileWriter:

    def __init__(self, path: str, delimiter: str = ","):
        self.__path: str = path
        self.__delimiter: str = delimiter

        self.__file = None
        self.__writer = None

    def __enter__(self):
        self.__file = open(self.__path, "w", encoding=ENCODING, newline="")
        self.__writer = csv.writer(self.__file, delimiter=self.__delimiter)
        self.__writer.writerow([_COL_NAME, _COL_REGISTRY_TYPE, _COL_REGISTRY_ID, _COL_REGISTRY_COURT, _COL_STRUCTURE,
                                _COL_CAPITAL, _COL_CAPITAL_CURRENCY, _COL_ENTRY, _COL_DELETION, _COL_BALANCE,
                                _COL_ADDRESS, _COL_POST_CODE, _COL_CITY])
        self.__file.flush()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__file.close()

    def write(self, entity: LegalEntityInformation):
        self.__writer.writerow([entity.name, entity.registry_type, entity.registry_id, entity.registry_court,
                                entity.structure, entity.capital, entity.capital_currency, entity.entry,
                                entity.deletion, entity.balance is not None and not entity.balance, entity.address,
                                entity.post_code, entity.city])
        self.__file.flush()


class LegalEntityBalanceDatesFileWriter:

    def __init__(self, path: str, delimiter: str = ","):
        self.__path = path
        self.__delimiter = delimiter

        self.__file = None
        self.__writer = None

    def __enter__(self):
        self.__file = open(self.__path, "w", encoding=ENCODING, newline="")
        self.__writer = csv.writer(self.__file, delimiter=self.__delimiter)
        self.__writer.writerow([_COL_NAME, _COL_REGISTRY_TYPE, _COL_REGISTRY_ID, _COL_REGISTRY_COURT, _COL_BALANCE])
        self.__file.flush()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__file.close()

    def write(self, entity: LegalEntityInformation):
        if entity.balance:
            for date in entity.balance:
                self.__writer.writerow([entity.name, entity.registry_type, entity.registry_id, entity.registry_court,
                                        date])
                self.__file.flush()


_COL_LIST_INDEX = "list_index"
_COL_LIST_DATE = "list_date"


class ShareHolderListsFileWriter:

    def __init__(self, path: str, delimiter: str = ","):
        self.__path = path
        self.__delimiter = delimiter

    def __enter__(self):
        self.__file = open(self.__path, "w", encoding=ENCODING, newline="")
        self.__writer = csv.writer(self.__file, delimiter=self.__delimiter)
        self.__writer.writerow([_COL_NAME, _COL_REGISTRY_TYPE, _COL_REGISTRY_ID, _COL_REGISTRY_COURT, _COL_STRUCTURE,
                                _COL_LIST_INDEX, _COL_LIST_DATE])
        self.__file.flush()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__file.close()

    def write(self, lists: ShareholderLists):
        if lists is None:
            return

        entity = lists.entity

        for i, date in enumerate(lists.dates):
            self.__writer.writerow([entity.name, entity.registry_type, entity.registry_id, entity.registry_court,
                                    entity.structure, i, date])
            self.__file.flush()
