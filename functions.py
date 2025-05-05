import json
import datetime
import os
import requests

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

def config_get():
    try:
        with open("conf.defaults.json", "r") as config_defaults_file:
            config = json.loads(config_defaults_file.read())

        if os.path.exists("conf.json"):
            with open("conf.json", "r") as config_custom_file:
                config_custom = json.loads(config_custom_file.read())
                config = selective_merge(config, config_custom)
        
        return config
    except Exception as e:
        print("Error loading config: %s" % e)

class last_call():
    def __init__(self, name):
        self.file="LastCall_%s.txt" % name

        if os.path.exists(self.file):
            try:
                with open(self.file, "r+") as LastCallFile:
                    self.time=datetime.datetime.fromtimestamp(float(LastCallFile.read()))
            except Exception as e:
                self.time=None
        else:
            self.time=None

    def time_set(self, time):
        print("Set last_call.time")
        with open(self.file, "w") as LastCallFile:
            LastCallFile.write(str(time))

class easy_verein():
    billing_accounts= {}

    def __init__(self, api_key, bank_account):
        self.headers = {"Authorization": "Bearer %s" % api_key}
        self.bank_account=bank_account

    def billing_account_get(self, number):
        if number in self.billing_accounts:
            return self.billing_accounts[number]

        response = requests.get(
            'https://easyverein.com/api/v2.0/billing-account',
            params={
                "number__gte": number,
                "number__lte": number
            },
            headers=self.headers
        )
        if response.json()["count"]==1:
            self.billing_accounts[number]=response.json()["results"][0]["id"]
            return response.json()["results"][0]["id"]
        else:
            raise Exception("Billing account number %s could not be found" % (number))

    def booking_id_exists(self, id):
        response = requests.get(
            'https://easyverein.com/api/v2.0/booking',
            params={
                "billingId__in": id
            },
            headers=self.headers
        )
        if response.json()["count"]>0:
            return True

    def booking_create(self, transaction):
        if not self.booking_id_exists(transaction["billingId"]):
            print("Transaction '%s' does not exist. Creating ..." % transaction["billingId"])
            data = transaction
            data["bankAccount"]=self.bank_account
            response = requests.post(
                'https://easyverein.com/api/v2.0/booking',
                data=data,
                headers=self.headers
            )
            if response.status_code == 201:
                print("Transaction '%s' created successfully" % transaction["billingId"])
            else:
                raise Exception("Error creating Transaction %s:\n%s" % (transaction["billingId"], response.json()))
        else:
            print("Transaction '%s' already exists. Skipping" % transaction["billingId"])