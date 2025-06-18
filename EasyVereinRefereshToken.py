#!PyVenv/bin/python3

from functions import *

config=config_get()
easy_verein=easy_verein(
    api_key=config["EasyVerein"]["ApiKey"],
)
