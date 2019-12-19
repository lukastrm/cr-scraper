"""
Copyright (c) 2020 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""


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
