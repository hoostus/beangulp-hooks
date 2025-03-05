from sklearn.pipeline import FeatureUnion, make_pipeline
from sklearn.svm import SVC
import functools
from beancount.core import data
from .pipelines import get_pipeline

import logging
logger = logging.getLogger(__name__)

default_weights = {'payee': 0.8, 'narration': 0.5, 'date.day': 0.1}

def get_open_accounts(entries: data.Directives):
    accounts = {}
    for entry in data.sorted(entries):
        if isinstance(entry, data.Open):
            accounts[entry.account] = entry
        elif isinstance(entry, data.Close):
            accounts.pop(entry.account)
    return accounts

def is_account_open(open_accounts, entry):
    for pos in entry.postings:
        if pos.account not in open_accounts:
            return False
    return True

def is_allowed_account(denied_accounts, entry):
    for pos in entry.postings:
        if pos.account in denied_accounts:
            return False
    return True

def matches_account(account, entry):
    return account in [p.account for p in entry.postings]

def update_postings(transaction: data.Transaction, accounts: list[str]) -> data.Transaction:
    if len(transaction.postings) != 1:
        return transaction
    
    posting = transaction.postings[0]

    new_postings = [
        data.Posting(account, None, None, None, None, None) for account in accounts
    ]
    if posting.account in accounts:
        new_postings[accounts.index(posting.account)] = posting
    else:
        new_postings.append(posting)

    return transaction._replace(postings=new_postings)

def simple_hook(extracted_entries_list, ledger_entries: data.Directives):
    return hook(default_weights, [], extracted_entries_list, ledger_entries)

def hook(weights, denied_accounts, extracted_entries_list, ledger_entries: data.Directives):
    """
        extracted_entries_list is a list of tuples of the form
        (filename_import_is_from, account_name, imported_entries, importer_instance)
    """
    open_accounts = get_open_accounts(ledger_entries)
    transactions = data.filter_txns(ledger_entries)

    filters = [functools.partial(is_account_open, open_accounts),
               functools.partial(is_allowed_account, denied_accounts)]

    # First remove all unwanted data from our training. Closed accounts,
    # any excluded/denied accounts, ...
    for f in filters:
        transactions = filter(f, transactions)
    transactions = list(transactions)

    # Now we can define the pipelines we are going to use.
    transformers = [
        (attribute, get_pipeline(attribute, None))
        for attribute in weights
    ]

    # We want per-account pipelines, training data, and targets
    result = []
    for import_file, imported_entries, import_account, importer in extracted_entries_list:
        imported_txns = list(data.filter_txns(imported_entries))
        if len(imported_txns) == 0:
            # There are no transactions for us to predict
            # (only other entries in the imported data)
            result.append((import_file, imported_entries, import_account, importer))
            continue

        pipeline = make_pipeline(FeatureUnion(transformer_list=transformers, transformer_weights=weights),
            SVC(kernel='linear'))
        matcher = functools.partial(matches_account, import_account)
        training = list(filter(matcher, transactions))

        # remove any postings with a single leg. This is caused by
        # beangulp adding the newly imported entries into the existing
        # entries list. All the single legs confuse/break the predictor.
        training = list(filter(lambda x: len(x.postings) > 1, training))

        targets = [
            " ".join(sorted(posting.account for posting in txn.postings))
            for txn in training
        ]
        pipeline.fit(training, targets)
        predictions = pipeline.predict(imported_txns)

        entries = [
            update_postings(entry, prediction.split(" "))
            for entry, prediction in zip(imported_entries, predictions)
        ]
        non_txns = [e for e in imported_entries if e not in imported_txns]
        entries.extend(non_txns)

        result.append((import_file, entries, import_account, importer))
        
    return result

