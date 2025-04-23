import datetime
import json
import os
from pprint import pprint
import requests
import time

def selective_merge(base_obj, delta_obj):
    if not isinstance(base_obj, dict):
        return delta_obj
    common_keys = set(base_obj).intersection(delta_obj)
    new_keys = set(delta_obj).difference(common_keys)
    for k in common_keys:
        base_obj[k] = selective_merge(base_obj[k], delta_obj[k])
    for k in new_keys:
        base_obj[k] = delta_obj[k]
    return base_obj

def fetch_next(resp, headers):
    transactions=[]
    if "links" in resp:
        for link in resp["links"]:
            if link["rel"] == "next":
                response = requests.get(
                    "https://api.sumup.com/v2.1/merchants/%s/transactions/history?%s" % (config["SumUp"]["MerchantId"], link["href"]),
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
        "https://api.sumup.com/v2.1/merchants/%s/transactions" % (config["SumUp"]["MerchantId"]),
        params=params,
        headers=headers
    )
    return response.json()


with open("conf.defaults.json", "r") as config_defaults_file:
    config = json.loads(config_defaults_file.read())

if os.path.exists("conf.json"):
    with open("conf.json", "r") as config_custom_file:
        config_custom = json.loads(config_custom_file.read())
        config = selective_merge(config, config_custom)

if os.path.exists("SumUp_LastCall.txt"):
    with open("SumUp_LastCall.txt", "r+") as LastCallFile:
        LastCall=datetime.datetime.fromtimestamp(float(LastCallFile.read()))
else:
    LastCall=None

headers = {"Authorization": "Bearer %s" % config["SumUp"]["ApiKey"]}
parameter={
    "limit": 10
}
if LastCall!=None:
    parameter["oldest_time"] =LastCall.strftime('%Y-%m-%dT%H:%M:%SZ')

transactions=[]
CurrentCall=datetime.datetime.now(datetime.timezone.utc).timestamp()

try:
    response = requests.get(
        'https://api.sumup.com/v2.1/merchants/%s/transactions/history' % (config["SumUp"]["MerchantId"]),
        params=parameter,
        headers=headers
    )
    transactions=response.json()["items"]
    transactions.extend(fetch_next(resp=response.json(), headers=headers))


    for transaction in transactions:
        transaction["detail"]=transaction_detail_get(transaction, headers=headers)


    headers = {"Authorization": "Bearer %s" % config["EasyVerein"]["ApiKey"]}
    for transaction in transactions:
        if transaction["status"] != "SUCCESSFUL":
            continue

        response = requests.get(
            'https://easyverein.com/api/v2.0/booking',
            params={
                "billingId__in": "%s_payment" % transaction["transaction_code"]
            },
            headers=headers
        )
        if response.json()["count"]>0:
            print("Booking '%s_payment' already exists. Skipping" % transaction["transaction_code"])
            continue

        time=datetime.datetime.fromisoformat(transaction["detail"]["local_time"])
        data = {
            "amount": transaction["amount"],
            "bankAccount": config["SumUp"]["EasyVerein"]["AccountId"],
            "date": transaction["detail"]["local_time"],
            "billingId": "%s_payment" % transaction["transaction_code"],
            "receiver": transaction["payment_type"],
            "description": "%s\nKartenzahlung (Einnahme)\n%s - %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), transaction["payment_type"], transaction["card_type"])
        }
        response = requests.post(
            'https://easyverein.com/api/v2.0/booking',
            data=data,
            headers=headers
        )
        data = {
            "amount": 0-float(transaction["detail"]["events"][0]["fee_amount"]),
            "bankAccount": config["SumUp"]["EasyVerein"]["AccountId"],
            "date": transaction["detail"]["local_time"],
            "billingId": "%s_fee" % transaction["transaction_code"],
            "receiver": "SumUp",
            "description": "%s\nKartenzahlung (Gebühren)\n%s - %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), transaction["payment_type"], transaction["card_type"])
        }
        response = requests.post(
            'https://easyverein.com/api/v2.0/booking',
            data=data,
            headers=headers
        )
        #Prevent easyVerein rate limit
        time.sleep(1)

except Exception as e:
    raise e
else:
    with open("SumUp_LastCall.txt", "w") as LastCallFile:
        LastCallFile.write(str(CurrentCall))