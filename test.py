from time import sleep

from comreg.search import SearchRequestHelper, PARAM_REGISTER_ID, PARAM_REGISTER_TYPE, PARAM_KEYWORDS, PARAM_REGISTER_COURT
from comreg.service import Session

session = Session()
session.initialize()

sleep(3)

request = SearchRequestHelper(session)
request.set_param(PARAM_KEYWORDS, "KAIYÜ Immobilien GmbH")
request.set_param(PARAM_REGISTER_TYPE, "HRB")
request.perform_request()
print(request.result)
