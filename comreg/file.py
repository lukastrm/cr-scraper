"""
Copyright (c) 2020 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""
import csv

from comreg.entity import LegalEntityInformation, ShareHolderLists
from comreg.struct import SearchInputRecord

ENCODING = "utf-8"


class SearchInputDataFileReader:

    def __init__(self, path: str, header: bool = True):
        self.path: str = path
        self.reader = None
        self.header: bool = header

    def __enter__(self):
        self.file = open(self.path, "r", encoding=ENCODING)
        self.reader = csv.reader(self.file, delimiter=";")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()

    def __iter__(self):
        return self

    def __next__(self) -> SearchInputRecord:
        if self.header:
            next(self.reader)
            self.header = False

        raw: str = next(self.reader)
        return SearchInputRecord(*raw)


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

    def __init__(self, file: str):
        self.file = open(file, "w", encoding=ENCODING, newline="")
        self.writer = csv.writer(self.file, delimiter=";")

    def __enter__(self):
        self.writer.writerow([_COL_NAME, _COL_REGISTRY_TYPE, _COL_REGISTRY_ID, _COL_REGISTRY_COURT, _COL_STRUCTURE,
                              _COL_CAPITAL, _COL_CAPITAL_CURRENCY, _COL_ENTRY, _COL_DELETION, _COL_BALANCE, _COL_ADDRESS,
                              _COL_POST_CODE, _COL_CITY])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()

    def write(self, entity: LegalEntityInformation):
        self.writer.writerow([entity.name, entity.registry_type, entity.registry_id, entity.registry_court,
                              entity.structure, entity.capital, entity.capital_currency, entity.entry, entity.deletion,
                              entity.balance is not None and not entity.balance, entity.address, entity.post_code,
                              entity.city])


class LegalEntityBalanceDatesFileWriter:

    def __init__(self, file: str):
        self.__file = open(file, "w", encoding=ENCODING, newline="")
        self.__writer = csv.writer(self.__file, delimiter=";")

    def __enter__(self):
        self.__writer.writerow([_COL_NAME, _COL_REGISTRY_TYPE, _COL_REGISTRY_ID, _COL_REGISTRY_COURT, _COL_BALANCE])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__file.close()

    def write(self, entity: LegalEntityInformation):
        if entity.balance:
            for date in entity.balance:
                self.__writer.writerow([entity.name, entity.registry_type, entity.registry_id, entity.registry_court,
                                        date])


_COL_LIST_INDEX = "list_index"
_COL_LIST_DATE = "list_date"


class ShareHolderListsFileWriter:

    def __init__(self, file: str):
        self.__file = open(file, "w", encoding=ENCODING, newline="")
        self.__writer = csv.writer(self.__file)

    def __enter__(self):
        self.__writer.writerow([_COL_NAME, _COL_REGISTRY_TYPE, _COL_REGISTRY_ID, _COL_REGISTRY_COURT, _COL_STRUCTURE,
                                _COL_LIST_INDEX, _COL_LIST_DATE])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__file.close()

    def write(self, lists: ShareHolderLists):
        entity = lists.entity

        for i, date in enumerate(lists.dates):
            self.__writer.writerow([entity.name, entity.registry_type, entity.registry_id, entity.registry_court,
                                    entity.structure, i, date])
