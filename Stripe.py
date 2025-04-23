import functions

import datetime
import json
import os
from pprint import pprint
import requests
import stripe
import time

config=functions.config_get()
stripe.api_key = config["Stripe"]["ApiKey"]


if os.path.exists("Stripe_LastCall.txt"):
    with open("Stripe_LastCall.txt", "r+") as LastCallFile:
        LastCall=datetime.datetime.fromtimestamp(float(LastCallFile.read()))
else:
    LastCall=None

created={}
if LastCall!=None:
    created["gte"]=LastCall.timestamp()
balance_transactions = stripe.BalanceTransaction.list(created=created)

for transaction in balance_transactions.auto_paging_iter():
    pprint(transaction)