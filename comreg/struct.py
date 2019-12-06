"""
Copyright (c) 2019 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""
from typing import List


class SearchInputRecord:

    def __init__(self, name: str = None, registry_type: str = None, registry_id: int = None,
                 registry_court: str = None):
        self.name: str = name
        self.registry_type: str = registry_type
        self.registry_id: int = registry_id
        self.registry_court: str = registry_court

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return str(self.__dict__)


class SearchParameters:

    def __init__(self):
        pass

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return str(self.__dict__)


class LegalEntityInformation:

    def __init__(self, name: str = None, court: str = None, registry_type: str = None, registry_id: int = None,
                 structure: str = None, capital: int = None, capital_currency: str = None, entry: str = None,
                 deletion: str = None, balance: List[str] = None, address: str = None, post_code: str = None,
                 city: str = None):
        self.name: str = name
        self.registry_court: str = court
        self.registry_type: str = registry_type
        self.registry_id: int = registry_id
        self.structure: str = structure
        self.capital: int = capital
        self.capital_currency: str = capital_currency
        self.entry: str = entry
        self.deletion: str = deletion
        self.balance: List[str] = balance
        self.address: str = address
        self.post_code: str = post_code
        self.city: str = city

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return str(self.__dict__)
