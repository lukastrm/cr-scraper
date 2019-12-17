"""
Copyright (c) 2020 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""
import requests as rq


class Session:

    def __init__(self):
        self.identifier = None

    def run(self):
        try:
            result = rq.get("https://www.handelsregister.de/rp_web/welcome.do", timeout=(5, 10))
            self.identifier = result.cookies["JSESSIONID"]
        except TimeoutError:
            print("Timeout")
            # TODO: Better solution