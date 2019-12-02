import requests as rq


class CRSession:

    def __init__(self):
        self.session_id = None

    def run(self):
        result = rq.get("https://www.handelsregister.de/rp_web/welcome.do")
        self.session_id = result.cookies["JSESSIONID"]
