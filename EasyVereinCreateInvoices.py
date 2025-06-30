#!PyVenv/bin/python3

import functions
from functions import *
import datetime
import json
import argparse

parser = argparse.ArgumentParser(
    prog='EasyVereinScripts - CreateInvoices',
    description='Create Invoices for all bookings for a given time period',
    add_help=True
)
parser.add_argument(
    '--date__gte',
    type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d'),
    required=True,
    help='Bookings before this date will not be processed'
)
parser.add_argument(
    '--date__lte',
    type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d'),
    required=True,
    help='Bookings after this date will not be processed'
)
parser.add_argument(
    '--custom_config_file',
    required=False,
    default="conf.json",
    help='Custom conf file, which overrides defaults in conf.defaults.json'
)
args=parser.parse_args()

config=functions.configClass(args.custom_config_file)
easy_verein=easy_verein(
    api_key=config.config["EasyVerein"]["ApiKey"],
    config=config
)

bookings=easy_verein.bookings_get(
    date__gte=args.date__gte,
    date__lte=args.date__lte,
    relatedInvoice__isnull=True
)

current_time=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

with open("bkp/bookings_%s_.json" % current_time, "w") as booking_bkp:
    json.dump(bookings, booking_bkp, indent=4)

i=0
for booking in bookings:
    invoice_number="auto_%s_%s" % (current_time, i)
    invoice=easy_verein.invoice_create(
        amount=booking["amount"],
        date=booking["date"],
        receiver=booking["receiver"],
        invNumber=invoice_number,
        relatedBooking=booking["id"],
        booking=booking,
    )
    print("Invoice %s for booking %s created" % (invoice_number, ))

    i=i+1