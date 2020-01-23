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


def date_components(date: str):
    if date:
        match = re.match(r"(\d{1,2}).(\d{1,2}).(\d{2,4})", date)

        if match:
            return [match.group(1), match.group(2), match.group(3)]

    return [None, None, None]


class SearchInputRecord:

    def __init__(self, name: str = None, registry_court: Optional[str] = None, registry_type: Optional[str] = None,
                 registry_id: Optional[str] = None):
        self.name: str = name
        self.registry_court: Optional[str] = registry_court
        self.registry_type: Optional[str] = registry_type
        self.registry_id: Optional[str] = registry_id

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
        self.__index_name = -1
        self.__index_registry_type = -1
        self.__index_registry_id = -1
        self.__index_registry_court = -1

    def __enter__(self):
        self.__file = open(self.__path, "r", encoding=ENCODING)
        self.__reader = csv.reader(self.__file, delimiter=self.__delimiter)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__file.close()

    def __iter__(self):
        return self

    def __next__(self) -> Optional[SearchInputRecord]:
        raw: str = next(self.__reader)

        if self.__header:
            self.__index_name = raw.index("firm")
            self.__index_registry_court = raw.index("city")
            self.__index_registry_type = raw.index("hrsection")
            self.__index_registry_id = raw.index("hrid")
            self.__header = False
            raw = next(self.__reader)

        if len(raw) < 6:
            return None

        name: str = raw[self.__index_name]
        registry_court: Optional[str] = raw[self.__index_registry_court].strip()
        registry_type: Optional[str] = raw[self.__index_registry_type].strip()
        registry_id: Optional[str] = re.match(r"^\D*(\d+ ?\w{0,2})\s*$", raw[self.__index_registry_id])

        if registry_type is not None and registry_type not in REGISTRY_TYPES:
            utils.LOGGER.error("Omitting invalid registry type {} for search record {}".format(registry_type, name))
            registry_type = None

        return SearchInputRecord(name, registry_court, registry_type,
                                 None if registry_id is None else registry_id.group(1).strip())


_COL_NAME = "name"
_COL_REGISTRY_TYPE = "registry_type"
_COL_REGISTRY_ID = "registry_id"
_COL_REGISTRY_COURT = "registry_court"
_COL_STRUCTURE = "structure"
_COL_CAPITAL = "capital"
_COL_CAPITAL_CURRENCY = "capital_currency"
_COL_ENTRY_DAY = "entry_day"
_COL_ENTRY_MONTH = "entry_month"
_COL_ENTRY_YEAR = "entry_year"
_COL_DELETION_DAY = "deletion"
_COL_DELETION_MONTH = "deletion_month"
_COL_DELETION_YEAR = "deletion_year"
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
                                _COL_CAPITAL, _COL_CAPITAL_CURRENCY, _COL_ENTRY_DAY, _COL_ENTRY_MONTH, _COL_ENTRY_YEAR,
                                _COL_DELETION_DAY, _COL_DELETION_MONTH, _COL_DELETION_YEAR, _COL_BALANCE, _COL_ADDRESS,
                                _COL_POST_CODE, _COL_CITY])
        self.__file.flush()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__file.close()

    def write(self, entity: LegalEntityInformation):
        self.__writer.writerow([entity.name, entity.registry_type, entity.registry_id, entity.registry_court,
                                entity.structure, entity.capital, entity.capital_currency,
                                *date_components(entity.entry),  *date_components(entity.deletion),
                                entity.balance is not None and not entity.balance, entity.address,
                                entity.post_code, entity.city])
        self.__file.flush()


_COL_BALANCE_DAY = "balance_day"
_COL_BALANCE_MONTH = "balance_month"
_COL_BALANCE_YEAR = "balance_year"


class LegalEntityBalanceDatesFileWriter:

    def __init__(self, path: str, delimiter: str = ","):
        self.__path = path
        self.__delimiter = delimiter

        self.__file = None
        self.__writer = None

    def __enter__(self):
        self.__file = open(self.__path, "w", encoding=ENCODING, newline="")
        self.__writer = csv.writer(self.__file, delimiter=self.__delimiter)
        self.__writer.writerow([_COL_NAME, _COL_REGISTRY_TYPE, _COL_REGISTRY_ID, _COL_REGISTRY_COURT, _COL_BALANCE_DAY,
                                _COL_BALANCE_MONTH, _COL_BALANCE_YEAR])
        self.__file.flush()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__file.close()

    def write(self, entity: LegalEntityInformation):
        if entity.balance:
            for date in entity.balance:
                self.__writer.writerow([entity.name, entity.registry_type, entity.registry_id, entity.registry_court,
                                        *date_components(date)])
                self.__file.flush()


_COL_LIST_INDEX = "list_index"
_COL_LIST_DATE_DAY = "list_date_day"
_COL_LIST_DATE_MONTH = "list_date_month"
_COL_LIST_DATE_YEAR = "list_date_year"


class ShareHolderListsFileWriter:

    def __init__(self, path: str, delimiter: str = ","):
        self.__path = path
        self.__delimiter = delimiter

    def __enter__(self):
        self.__file = open(self.__path, "w", encoding=ENCODING, newline="")
        self.__writer = csv.writer(self.__file, delimiter=self.__delimiter)
        self.__writer.writerow([_COL_NAME, _COL_REGISTRY_TYPE, _COL_REGISTRY_ID, _COL_REGISTRY_COURT, _COL_STRUCTURE,
                                _COL_LIST_INDEX, _COL_LIST_DATE_DAY, _COL_LIST_DATE_MONTH, _COL_LIST_DATE_YEAR])
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
                                    entity.structure, i, *date_components(date)])
            self.__file.flush()
