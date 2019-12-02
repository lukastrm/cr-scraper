import random
from comreg.ComRegInit import ComRegInit
import comreg.search as comsrc
from comreg.search import CRSearch

session = None
cmp = [10000, 23747, 10001, 10002, 234, 345, 457]
cmp = [random.randrange(100000) for _ in range(100)]
new = True

try:
    if new:
        raise IOError

    with open("session", "r") as f:
        session = f.readline()
        print(session)
except:
    i = ComRegInit()
    i.run()
    session = i.session

    with open("session", "w") as f:
        f.write(session)

print(session)

for idi in cmp:
    s = CRSearch(session)
    s.set_param(comsrc.PARAM_REGISTER_ID, idi)
    s.run()
    print(idi, end=" ")
    e = comsrc.CRLegalEntityInformationLookUp(session, 0)
    e.fetch()
