"""
Copyright (c) 2020 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""
import time
import requests
from typing import Tuple

DEFAULT_SEARCH_URL = "https://www.handelsregister.de/rp_web/search.do"
DEFAULT_DOCUMENT_URL = "https://www.handelsregister.de/rp_web/document.do"


def now():
    return int(round(time.time() * 1000))


class Session:

    def __init__(self, identifier: str = None, delay: int = 10, cooldown: Tuple[int, int] = (60, 60 * 50)):
        self.identifier: str = identifier
        self.delay: int = delay
        self.cooldown: Tuple[int, int] = cooldown
        self.last_fetch = -1
        self.last_request = -1

    def initialize(self) -> None:
        try:
            result = requests.get("https://www.handelsregister.de/rp_web/welcome.do", timeout=(5, 10))
            self.identifier = result.cookies["JSESSIONID"]
        except TimeoutError:
            print("Timeout")
            # TODO: Better solution

    def invalidate(self) -> None:
        self.identifier = None

    def wait_for_delay(self) -> None:
        if self.delay > 0:
            cur_time = now()

            remaining = self.delay - cur_time + self.last_request

            if remaining > 0:
                time.sleep(remaining)
