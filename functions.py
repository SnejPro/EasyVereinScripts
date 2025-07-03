import json
import datetime
import os
import requests
import re
from pathlib import Path
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

class configClass():
    def __init__(self, ccfp):
        self.base_path = Path(__file__).parent
        self.custom_config_file_path=(self.base_path / ccfp).resolve()
 
        default_config_file_path=(self.base_path / "conf.defaults.json").resolve()

        with open(default_config_file_path, "r") as config_defaults_file:
            config = json.loads(config_defaults_file.read())

        if os.path.exists(self.custom_config_file_path):
            with open(self.custom_config_file_path, "r") as config_custom_file:
                config_custom = json.loads(config_custom_file.read())
                config = selective_merge(config, config_custom)
        else:
            print("Warning: No conf.json present, using defaults")
        self.config=config

        self.create_data_dir()

    def create_data_dir(self):
        self.datadir=(self.base_path / ("datadir/%s" % re.search("[^\/\\\n]+(?=\.json$)", self.custom_config_file_path.name).group())).resolve()
        if not os.path.exists(self.datadir):
            os.makedirs(self.datadir)

    def config_update_easyverein_api_key(self, newkey):
        if os.path.exists(self.custom_config_file_path):
            with open(self.custom_config_file_path, "r+") as config_custom_file:
                config_custom = json.loads(config_custom_file.read())
                if "EasyVerein" in config_custom and "ApiKey" in config_custom["EasyVerein"]:
                    config_custom["EasyVerein"]["ApiKey"]=newkey
                    config_custom_file.seek(0)
                    json.dump(config_custom, config_custom_file, indent=4)
                    config_custom_file.truncate()
                    print("New easyverein api key saved to conf.json")
                    return True
                else:
                    raise Exception("No EasyVerein/ApiKey in conf.json")
        else:
            raise Exception("Warning: No conf.json present, can not save new easyverein api key")

class last_call():
    def __init__(self, name, config):
        self.file=(config.datadir / ("LastCall_%s.txt" % ( name ))).resolve()

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

    def __init__(self, api_key, config, bank_account=None):
        self.headers = {"Authorization": "Bearer %s" % api_key}
        self.config = config
        newkey=self.token_update_if_neccesary()
        if newkey:
            self.headers = {"Authorization": "Bearer %s" % newkey}
        if bank_account!=None:
            self.bank_account=bank_account
        

    # returns newkey when key was updated, returns False when not
    def token_update_if_neccesary(self):
        response = requests.get(
            'https://easyverein.com/api/v2.0/calendar',
            headers=self.headers
        )
        if response.headers["tokenRefreshNeeded"] not in [ "True", "False" ]:
            print("Invalid token RefreshNeededAnswer")
            return False
        if response.headers["tokenRefreshNeeded"]=="True":
            print("Token valid, but a refresh is needed.")
            response = requests.get(
                'https://easyverein.com/api/v2.0/refresh-token',
                headers=self.headers
            )
            newkey=response.json()["Bearer"]
            self.config.config_update_easyverein_api_key(newkey)
            return newkey
        else:
            print("Token valid and no refresh needed.")
            return False
        

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
        
    def bookings_get_fetch_next(self, previous_response, results=[]):
        if "next" in previous_response and previous_response["next"]!=None:
            response = requests.get(
                previous_response["next"],
                headers=self.headers
            )
            response_content=response.json()
            results=response_content["results"]
            results.extend(self.bookings_get_fetch_next(previous_response=response_content))

        return results

    def bookings_get(self, date__gte, date__lte, relatedInvoice__isnull=None):
        params={
            "date__gt": date__gte-datetime.timedelta(seconds=1),
            "date__lt": date__lte+datetime.timedelta(days=1),
            "limit": 100,
            "ordering": "date"
        }
        if relatedInvoice__isnull!=None:
            params["relatedInvoice__isnull"]=relatedInvoice__isnull

        response = requests.get(
            'https://easyverein.com/api/v2.0/booking',
            params=params,
            headers=self.headers
        )
        response_content=response.json()
        results=response_content["results"]
        results.extend(self.bookings_get_fetch_next(previous_response=response_content))
        return results

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
        if self.bank_account==None:
            raise Exception("Class easy_verein was called without parameter bank_account")
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
            #Prevent easyVerein rate limit
            time.sleep(1)

    def invoice_create(
        self,
        amount,
        date,
        invNumber,
        receiver="**Missing**",
        relatedBooking=None,
        booking=None,
    ):
        if float(amount) < 0:
            kind="expense"
        else:
            kind="revenue"
        amount_absolut=abs(float(amount))

        data={
            "charges": {
                "total": amount_absolut
            },
            "date": re.search("^\d{4}-\d{2}-\d{2}", date).group(),
            "receiver": receiver,
            "kind": kind,
            "totalPrice": amount_absolut,
            "invNumber": invNumber
        }
        if relatedBooking!=None:
            data["relatedBookings"] = [ relatedBooking ]
        if receiver==None or receiver=="":
            data["receiver"] = "**Missing**"

        invoice_response = requests.post(
            'https://easyverein.com/api/v2.0/invoice',
            json=data,
            headers=self.headers
        )
        invoice=invoice_response.json()
        if invoice_response.status_code!=201:
            raise Exception("Error creating invoice object: %s\nresponse: %s" % data, relatedBooking, invoice_response.json())

        data={
            "relatedBookings": [ relatedBooking ]
        }

        invoice_patch_response = requests.patch(
            'https://easyverein.com/api/v2.0/invoice/%s' % invoice["id"],
            json=data,
            headers=self.headers
        )
        invoice_patch=invoice_patch_response.json()
        if invoice_patch_response.status_code!=200:
            raise Exception("Error combining invoice with booking invoice: %s, booking: %s\nresponse: %s" % (invoice["id"], relatedBooking, invoice_patch_response.json()))

        return invoice_patch