# Unoffical scripts for easyVerein

# Functions:
I developed the following scripts for tweaking my easyverein experience
1. Stripe.py
    - import payments (incl. fees) and payouts from Stripe
2. SumUp.py
    - import payments (incl. fees) and payouts from SumUp
3. CreateInvoices.py (Experimental)
    - create invoices for all bookings that do not already have an invoice attached within a given timeperiod.
    - (You need an invoice attached to all bookings to export your bookwork for DATEV)
4. EasyVereinRefreshToken.py
    - refresh easyverein token
    - run this script every week, if you do not run one of the other scripts every week

# HowTo

1. Create virtualenv:
`python3 -m venv PyVenv`
2. Install dependencies
`PyVenv/bin/python3 -m pip install -r requirements.txt`
3. Copy `conf.defaults.json` to `conf.json` (or any other filename)
`cp conf.defaults.json conf.json`
4. Edit conf.json (with nano, vi, etc.) and enter your api keys, MerchantId (SumUp), AccountId (easyVerein), TimeZone
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

# Get Help:
If you have issues with one of the scripts, please open an issue.

# If something goes wrong
I developed the scripts for my own purposes. I can not guarantee that it won't mess up your easyVerein instance or can cause problems with SumUp or Stripe.

**Use at your own risk!**

This project is not affiliated with easyVerein.