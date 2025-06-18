# HowTo

1. Create virtualenv:
`python3 -m venv PyVenv`
2. Install dependencies
`PyVenv/bin/python3 -m pip install -r requirements.txt`
3. Copy `conf.defaults.json` to `conf.json` (or any other filename)
`cp conf.defaults.json conf.json`
4. Edit conf.json (with nano, vi, etc.) and enter your api keys, MerchantId (SumUp), AccountId (easyVerein)
5. Run scripts with -h to see commandline options
```
# Get all Stripe bookings (since last import):
PyVenv/bin/python3 Stripe.py -h

# Get all SumUp bookings (since last import):
PyVenv/bin/python3 SumUp.py -h

# Refresh EasyVerein Token if needed:
PyVenv/bin/python3 EasyVereinRefereshToken.py -h

# Create invoice for every booking (needed for DATEV export, if you have bookings without an invoice):
# CAVE: First you need to assign every invoice you have
PyVenv/bin/python3 CreateInvoices.py -h
```

