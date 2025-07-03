#!PyVenv/bin/python3

import argparse
import functions
from functions import *
import datetime
import stripe

parser = argparse.ArgumentParser(
    prog='EasyVereinScripts - Stripe',
    description='Get Stripe bookings and import them to easyverein',
    add_help=True
)
parser.add_argument(
    '--custom_config_file',
    required=False,
    default="conf.json",
    help='Custom conf file, which overrides defaults in conf.defaults.json'
)
args=parser.parse_args()

config=functions.configClass(args.custom_config_file)
stripe.api_key = config.config["Stripe"]["ApiKey"]

last_call=last_call(
    "Stripe",
    config=config
)
current_call=datetime.datetime.now(datetime.timezone.utc)
easy_verein=easy_verein(
    api_key=config.config["EasyVerein"]["ApiKey"],
    bank_account=config.config["Stripe"]["EasyVerein"]["AccountId"],
    config=config
)

created={}
if last_call.time!=None:
    created["gte"]=last_call.time
balance_transactions = stripe.BalanceTransaction.list(
    created=created,
    expand=['data.source']
)

for transaction in balance_transactions.auto_paging_iter():
    if transaction["type"]=="payment":
        #Processing payment
        time=datetime.datetime.fromtimestamp(transaction["available_on"])
        data = {
            "amount": transaction["amount"]/100,
            "bankAccount": config.config["Stripe"]["EasyVerein"]["AccountId"],
            "date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "billingId": "%s_payment" % transaction["id"],
            "receiver": transaction["source"]["billing_details"]["name"],
            "description": "%s\nStripe-Zahlung (Einnahme)\n%s" % (time.strftime("%Y-%m-%d %H:%M:%S"), transaction["description"])
        }
        easy_verein.booking_create(data)

        #Processing fee
        data = {
            "amount": 0-transaction["fee"]/100,
            "bankAccount": config.config["Stripe"]["EasyVerein"]["AccountId"],
            "date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "billingId": "%s_fee" % transaction["id"],
            "receiver": "Stripe",
            "description": "%s\nStripe-Zahlung (Gebühren)\n%s" % (time.strftime("%Y-%m-%d %H:%M:%S"), transaction["description"])
        }
        easy_verein.booking_create(data)
    #Processing payout
    elif transaction["type"]=="payout":
        data = {
            "amount": transaction["amount"]/100,
            "bankAccount": config.config["Stripe"]["EasyVerein"]["AccountId"],
            "date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "billingId": "%s_payout" % transaction["id"],
            "billingAccount": easy_verein.billing_account_get(config.config["EasyVerein"]["BillingAccounts"]["Transit"]),
            "receiver": "Stripe",
            "description": "%s\nUmbuchung" % (time.strftime("%Y-%m-%d"))
        }
        easy_verein.booking_create(data)
    else:
        print("skipping unsupported transaction type\n%s" % transaction)


last_call.time_set(current_call.timestamp())