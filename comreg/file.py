import csv
from comreg.search import CRLegalEntityInformation


class LegalEntityInformationFileWriter:

    def __init__(self, file):
        self.file = open(file, "w")
        self.writer = csv.writer(self.file)

    def __enter__(self):
        self.writer.writerow(["name", "registry_type", "registry_id", "court", "structure", "captital",
                              "capital_currency", "entry", "deletion", "balance", "address", "post_code", "city"])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()

    def write(self, entity: CRLegalEntityInformation):
        self.writer.writerow([entity.name, entity.registry_type, entity.registry_id, entity.court, entity.structure,
                              entity.capital, entity.capital_currency, entity.entry, entity.deletion,
                              entity.balance is not None and not entity.balance, entity.address, entity.post_code,
                              entity.city])
