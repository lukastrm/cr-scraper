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

from requests import RequestException

import utils

DEFAULT_SEARCH_URL = "https://www.handelsregister.de/rp_web/search.do"
DEFAULT_DOCUMENT_URL = "https://www.handelsregister.de/rp_web/document.do"

SESSION_COOKIE_NAME = "JSESSIONID"


class Session:
    """This class models a temporary web service session with relevant parameters that will be used
    during a search request"""

    def __init__(self, identifier: str = None, delay: int = -1, request_limit: int = -1, limit_interval: int = -1):
        """
        Initialize a `Session` object.

        :param identifier: the session identifier string as obtained by the web service
        :param delay: the delay in seconds between search requests
        :param request_limit: the maximum number of requests in a given interval
        :param limit_interval: the interval for the maximum number of requests
        """

        if request_limit > 0:
            if limit_interval < 0:
                raise ValueError

        self.identifier: str = identifier
        self.delay: int = delay
        self.request_limit: int = request_limit
        self.limit_interval: int = limit_interval
        self.delay_start: int = -1
        self.limit_start: int = -1
        self.limited_requests: int = 0

    def initialize(self) -> None:
        """Initializes the session identifier by performing a basic web service request to the index page"""

        try:
            result = requests.get("https://www.handelsregister.de/rp_web/welcome.do")

            if result.status_code == 200 and SESSION_COOKIE_NAME in result.cookies:
                self.identifier = result.cookies[SESSION_COOKIE_NAME]
        except RequestException as e:
            utils.LOGGER.exception(e)

    def invalidate(self) -> None:
        """Invalidates this session by resetting the identifier"""
        self.identifier = None

    def is_limit_reached(self) -> bool:
        """
        Returns if the limit for the current time interval has been reached without blocking

        :return: True if the limit has been reached, False otherwise
        """

        if self.request_limit <= 0 or self.limit_interval <= 0:
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
        """Indicates an upcoming request and blocks if the request has to be delayed because of a simple delay
        between requests or because of the total rate limit"""

        if self.request_limit > 0 and self.limit_interval > 0:
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
