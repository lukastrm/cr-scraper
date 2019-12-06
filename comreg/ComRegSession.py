import random
from comreg.file import LegalEntityInformationFileWriter
from comreg.session import CRSession
import comreg.search as comsrc
from comreg.search import CRSearch

session = None
#cmp = [20747, 12345]
cmp = [random.randrange(100000) for _ in range(10)]
new = True

try:
    if new:
        raise IOError

    with open("session", "r") as f:
        session = f.readline()
        print(session)
except:
    i = CRSession()
    i.run()
    session = i.session_id

    with open("session", "w") as f:
        f.write(session)

print(session)

with LegalEntityInformationFileWriter("test1.csv") as csvwriter1:
    for idi in cmp:
        s = CRSearch(session)
        s.set_param(comsrc.PARAM_REGISTER_ID, idi)
        s.run()
        print(idi, end=" ")
        e = comsrc.CRLegalEntityInformationLookUp(session, 0)
        e.fetch()
        print(e.result)
        csvwriter1.write(e.result)


