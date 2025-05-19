import beangulp

from beangulp.importers import csvbase
from beangulp import mimetypes
from hoostus.beangulp.hooks import predict_posting

class Importer(csvbase.Importer):
    date = csvbase.Date("Date", "%d %b %y")
    amount = csvbase.Amount("Amount")
    narration = csvbase.Columns("Transaction Details")
    balance = csvbase.Amount("Balance")

    def identify(self, filepath):
        mimetype, encoding = mimetypes.guess_type(filepath)
        if mimetype != "text/csv":
            return False
        else:
            return True

if __name__ == '__main__':
    importers = [
            Importer('Assets:Bank', 'AUD')
    ]

    hooks = [predict_posting.simple_hook]

    ingest = beangulp.Ingest(importers, hooks)
    ingest()

