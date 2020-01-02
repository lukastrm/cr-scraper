"""
Copyright (c) 2020 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""
import requests
from time import sleep, time

DEFAULT_SEARCH_URL = "https://www.handelsregister.de/rp_web/search.do"
DEFAULT_DOCUMENT_URL = "https://www.handelsregister.de/rp_web/document.do"

SESSION_COOKIE_NAME = "JSESSIONID"


class Session:

    def __init__(self, identifier: str = None, delay: int = -1, request_limit: int = -1, limit_interval: int = -1):
        if request_limit > 0:
            if limit_interval < 0:
                raise ValueError

        self.identifier: str = identifier
        self.delay: int = delay
        self.request_limit: int = request_limit
        self.limit_interval = limit_interval
        self.delay_start = -1
        self.limit_start = -1
        self.limited_requests = 0

    def initialize(self) -> None:
        try:
            result = requests.get("https://www.handelsregister.de/rp_web/welcome.do", timeout=(5, 10))

            if result.status_code == 200 and SESSION_COOKIE_NAME in result.cookies:
                self.identifier = result.cookies[SESSION_COOKIE_NAME]
        except TimeoutError:
            print("Timeout")
            # TODO: Better solution

    def invalidate(self) -> None:
        self.identifier = None

    def is_limit_reached(self) -> bool:
        if self.request_limit <= 0:
            return False

        current = time()
        passed = current - self.limit_start

        if passed < self.limit_interval:
            if self.limited_requests >= self.request_limit:
                return True
        else:
            self.limited_requests = 0

        return False

    def make_limited_request(self) -> None:
        if self.request_limit > 0:
            current = time()

            if self.limited_requests == 0:
                self.limit_start = current

            remaining = self.limit_interval - current + self.limit_start

            if remaining > 0:
                if self.limited_requests >= self.request_limit:
                    sleep(remaining)
                    self.limited_requests = 1
                    self.limit_start = time()
                else:
                    self.limited_requests += 1
            else:
                self.limited_requests += 1

        if self.delay > 0:
            current = time()
            remaining = self.delay - current + self.delay_start

            if remaining > 0:
                sleep(remaining)

            self.delay_start = time()
