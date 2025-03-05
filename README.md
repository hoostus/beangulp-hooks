# hoostus-beangulp-hooks

This uses machine learning, trained on your previous postings, to
predict what the second posting of an imported transaction should be.

That is, the importer will generate something like

```
2025-03-01 * "Cookie Store"
  Assets:AUS:NAB:PersonalAccount -117 AUD
```

Which is missing the second posting -- the Expense account the spending
went towards. You can enter that second posting manually or use
this hook which will look at your previous transactions to the
"Cookie Store" payee and predict that it should be attributed to
the ```Expenses:Eating``` and will modify the resulting import so
that beangulp outputs

```
2025-03-01 * "Cookie Store"
  Assets:AUS:NAB:PersonalAccount -117 AUD
  Expenses:Eating
```


# How to use it with beangulp.

The package name in pypi is ```hoostus-beangulp-hooks``` so
install it with pypi or add to pyproject.toml with that name.

```
pip install hoostus-beangulp-hooks
```

or
```
dependencies = [
    "hoostus-beangulp-hooks"
]
```

## The easiest way.

1. Import it: ```from hoostus.beangulp.hooks import predict_posting```
1. Add the ```simple_hook``` to the list of hooks you send to beangulp.

In the ```importer.py``` you use with beangulp this might look something like:

```
from hoostus.beangulp.hooks import predict_posting
if __name__ == '__main__':
    importers = [ ... ]
    hooks = [predict_posting.simple_hook]
    ingest = beangulp.Ingest(importers, hooks)
    ingest()
```

## If you want to configure it.

Use ```predict_posting.hook``` directly and pass in a map of weights
and a list of denied accounts -- accounts you don't want to use for
training the machine learning model. Note that beangulp expects hooks to take
2 parameters but ```predict_posting.hook``` takes 4 parameters. This
means you will need to use functools.partial (or similar) to wrap it.

In the ```importer.py``` you use with beangulp this might look something like:
```
from hoostus.beangulp.hooks import predict_posting
import functools
if __name__ == '__main__':
    importers = [ ... ]
    
    my_weights = {'meta.category': 0.8, 'payee': 0.5}
    my_denied_accounts = ['Expenses:Donuts']
    my_hook = functools.partial(predict_posting.hook, my_weights, my_denied_accounts)
    hooks = [my_hook]
    ingest = beangulp.Ingest(importers, hooks)
    ingest()
```

If you want to reuse the default weights (e.g. to only provide a denied_list)
it is at ```predict_posting.default_weights```. Like so
```
from hoostus.beangulp.hooks import predict_posting
import functools
if __name__ == '__main__':
    importers = [ ... ]
    
    my_denied_accounts = ['Expenses:Donuts']
    my_hook = functools.partial(predict_posting.hook, predict_posting.default_weights, my_denied_accounts)
    hooks = [my_hook]
    ingest = beangulp.Ingest(importers, hooks)
    ingest()
```

# Implementation Notes

The training is done on a per-account basis. Only transactions from the imported_account
are considered.

Transactions involving closed accounts are removed from the training data.

Any transactions in the training data with a single leg are removed. This isn't valid
beancount syntax anyway and is an artifact of (what I believe to be) a bug in beangulp
which adds all of the recently imported transactions into the list of existing entries
provided to hooks. This muddies the training data, in some cases making it useless.

This is basically recycled from https://github.com/beancount/smart_importer but adapted
to the beangulp framework

