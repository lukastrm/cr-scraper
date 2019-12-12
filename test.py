import random
from comreg.session import Session
from comreg.court import CourtListFetcher

i = None
session = None
# cmp = [20747, 12345]
cmp = [random.randrange(100000) for _ in range(10)]
new = True

try:
    if new:
        raise IOError

    with open("session", "r") as f:
        session = f.readline()
        print(session)
except:
    i = Session()
    i.run()
    session = i.identifier

    with open("session", "w") as f:
        f.write(session)

print(session)

fetcher = CourtListFetcher(i)
fetcher.run()
print(fetcher.result)
