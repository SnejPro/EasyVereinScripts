#!PyVenv/bin/python3

import argparse
import datetime
import functions
from functions import *
import fractions
import json
import os
from pprint import pprint
import requests
import time
from zoneinfo import ZoneInfo

parser = argparse.ArgumentParser(
    prog='EasyVereinScripts - SumUp',
    description='Get SumUp bookings and import them to easyverein',
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

def fetch_next(resp, headers):
    transactions=[]
    if "links" in resp:
        for link in resp["links"]:
            if link["rel"] == "next":
                response = requests.get(
                    "https://api.sumup.com/v2.1/merchants/%s/transactions/history?%s" % (config.config["SumUp"]["MerchantId"], link["href"]),
                    headers=headers
                )
                if "items" in response.json():
                    transactions=response.json()["items"]
                    transactions.extend(fetch_next(resp=response.json(), headers=headers))
    return transactions

def transaction_detail_get(transaction, headers):
    params={
        "id": transaction["transaction_id"]
    }
    response = requests.get(
        "https://api.sumup.com/v2.1/merchants/%s/transactions" % (config.config["SumUp"]["MerchantId"]),
        params=params,
        headers=headers
    )
    return response.json()


last_call=last_call(
    "SumUp",
    config=config
)
local_time_zone=ZoneInfo(config.config["Preferences"]["TimeZone"])

headers = {"Authorization": "Bearer %s" % config.config["SumUp"]["ApiKey"]}
parameter={
    "limit": 10
}
if last_call.time!=None:
    parameter["oldest_time"]=last_call.time.strftime('%Y-%m-%dT%H:%M:%SZ')

transactions=[]
current_call=datetime.datetime.now(datetime.timezone.utc)

easy_verein=easy_verein(
    api_key=config.config["EasyVerein"]["ApiKey"],
    bank_account=config.config["SumUp"]["EasyVerein"]["AccountId"],
    config=config
)

response = requests.get(
    'https://api.sumup.com/v2.1/merchants/%s/transactions/history' % (config.config["SumUp"]["MerchantId"]),
    params=parameter,
    headers=headers
)
transactions=response.json()["items"]
transactions.extend(fetch_next(resp=response.json(), headers=headers))


for transaction in transactions:
    transaction["detail"]=transaction_detail_get(transaction, headers=headers)

for transaction in transactions:
    if transaction["status"] != "SUCCESSFUL":
        print("skipping unsuccessfull transaction\n%s" % transaction)
        continue

    transaction_time=datetime.datetime.fromisoformat(transaction["detail"]["local_time"]).replace(tzinfo=local_time_zone)
    data = {
        "amount": transaction["amount"],
        "bankAccount": config.config["SumUp"]["EasyVerein"]["AccountId"],
        "date": transaction_time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "billingId": "%s_payment" % transaction["transaction_code"],
        "receiver": transaction["payment_type"],
        "description": "%s\nKartenzahlung (Einnahme)\n%s - %s" % (transaction_time.strftime("%Y-%m-%d %H:%M:%S"), transaction["payment_type"], transaction["card_type"])
    }
    easy_verein.booking_create(data)

    data = {
        "amount": 0-float(transaction["detail"]["events"][0]["fee_amount"]),
        "bankAccount": config.config["SumUp"]["EasyVerein"]["AccountId"],
        "date": transaction_time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "billingId": "%s_fee" % transaction["transaction_code"],
        "receiver": "SumUp",
        "description": "%s\nKartenzahlung (Gebühren)\n%s - %s" % (transaction_time.strftime("%Y-%m-%d %H:%M:%S"), transaction["payment_type"], transaction["card_type"])
    }
    easy_verein.booking_create(data)
    #Prevent easyVerein rate limit
    time.sleep(1)

parameter={
}
if last_call.time!=None:
    parameter["start_date"]=last_call.time.strftime('%Y-%m-%d')
else:
    parameter["start_date"]="%s-01-01" % datetime.now().year

parameter["end_date"]=current_call.strftime('%Y-%m-%d')

response = requests.get(
    'https://api.sumup.com/v1.0/merchants/%s/payouts' % (config.config["SumUp"]["MerchantId"]),
    params=parameter,
    headers=headers
)
transactions=response.json()
payouts={}
for transaction in transactions:
    if transaction["status"] != "SUCCESSFUL":
        print("skipping unsuccessfull transaction\n%s" % transaction)
        continue
    if transaction["type"] != "PAYOUT":
        print("skipping unsupported transaction type\n%s" % transaction)
        continue

    if transaction["reference"] in payouts:
        payouts[transaction["reference"]]["amount"]+=transaction["amount"]
        payouts[transaction["reference"]]["amount"]=round(payouts[transaction["reference"]]["amount"],2)
    else:
        payouts[transaction["reference"]]={
            "date": transaction["date"],
            "amount": transaction["amount"]
        }

for key, payout in payouts.items():
    data = {
        "amount": 0-payout["amount"],
        "bankAccount": config["SumUp"]["EasyVerein"]["AccountId"],
        "date": "%sT00:00" % payout["date"],
        "billingId": key,
        "billingAccount": easy_verein.billing_account_get(config.config["EasyVerein"]["BillingAccounts"]["Transit"]),
        "receiver": "SumUp",
        "description": "%s\nUmbuchung" % (payout["date"])
    }
    easy_verein.booking_create(data)

last_call.time_set(current_call.timestamp())
