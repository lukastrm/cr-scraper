import requests as rq


class ComRegInit:

    def __init__(self):
        self.session = None

    def run(self):
        result = rq.get("https://www.handelsregister.de/rp_web/welcome.do")
        self.session = result.cookies["JSESSIONID"]
