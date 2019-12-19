import random

from comreg.search import SearchRequest, PARAM_REGISTER_ID, PARAM_REGISTER_TYPE
from comreg.service import Session
from comreg.documents import ShareHolderListsFetcher
from comreg.court import CourtListFetcher

session = Session()
session.run()
cmp = [456]
# cmp = [random.randrange(100000) for _ in range(10)]

request = SearchRequest(session)
request.set_param(PARAM_REGISTER_TYPE, "HRB")
request.set_param(PARAM_REGISTER_ID, 456)
request.run()

fetcher = ShareHolderListsFetcher(session, 2)
fetcher.fetch()
print(fetcher.result)

print(request.result)


