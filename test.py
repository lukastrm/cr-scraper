from time import sleep

from comreg.search import SearchRequest, PARAM_REGISTER_ID, PARAM_REGISTER_TYPE, PARAM_KEYWORDS, PARAM_REGISTER_COURT
from comreg.service import Session

session = Session()
session.initialize()

sleep(3)

request = SearchRequest(session)
request.set_param(PARAM_KEYWORDS, "KAIYÜ Immobilien GmbH")
request.set_param(PARAM_REGISTER_TYPE, "HRB")
request.run()
print(request.result)
