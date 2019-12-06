import random
from comreg.file import LegalEntityInformationFileWriter, LegalEntityBalanceDatesFileWriter
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
    session = i.identifier

    with open("session", "w") as f:
        f.write(session)

print(session)

with LegalEntityInformationFileWriter("test1.txt") as csvwriter1, \
        LegalEntityBalanceDatesFileWriter("test2.csv") as csvwriter2:
    for idi in cmp:
        s = CRSearch(session)
        s.set_param(comsrc.PARAM_REGISTER_ID, idi)
        s.run()
        print(idi, end=" ")
        e = comsrc.CRLegalEntityInformationLookUp(session, 0)
        e.fetch()
        print(e.result)
        csvwriter1.write(e.result)
        csvwriter2.write(e.result)


