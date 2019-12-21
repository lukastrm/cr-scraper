import random
from time import sleep

import requests

from comreg.search import SearchRequest, PARAM_REGISTER_ID, PARAM_REGISTER_TYPE, PARAM_KEYWORDS, KEYWORD_OPTION_ALL, \
    PARAM_KEYWORD_OPTIONS, PARAM_REGISTER_COURT
from comreg.service import Session
from comreg.documents import ShareHolderListsFetcher
from comreg.court import CourtListFetcher

session = Session()
session.initialize()
# session.identifier = "75E01F9391ACB741C19FE39D94775439.tc05n01"

sleep(3)

request = SearchRequest(session)
request.set_param(PARAM_KEYWORDS, "KAIYÜ Immobilien GmbH")
request.set_param(PARAM_REGISTER_COURT, "F1103")
request.set_param(PARAM_REGISTER_TYPE, "HRB")
request.set_param(PARAM_REGISTER_ID, "145579 B")
request.run()
print(request)
sleep(5)
result = requests.get("https://www.handelsregister.de/rp_web/mask.do?Typ=n", cookies={"JSESSIONID": session.identifier, "language": "de"})
sleep(5)

# request = SearchRequest(session)
# request.set_param(PARAM_KEYWORDS, "KAIYÜ Immobilien GmbH")

request.set_param(PARAM_REGISTER_COURT, "")
request.set_param(PARAM_REGISTER_TYPE, "")
request.set_param(PARAM_REGISTER_ID, "")
request.set_param(PARAM_KEYWORD_OPTIONS, KEYWORD_OPTION_ALL)
request.run()
print(request)

