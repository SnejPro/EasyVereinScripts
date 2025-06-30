#!PyVenv/bin/python3

import argparse
from functions import *
import functions

parser = argparse.ArgumentParser(
    prog='EasyVereinScripts - RefreshToken',
    description='Refresh EasyVereinApiToken if neccessary',
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

easy_verein=easy_verein(
    api_key=config.config["EasyVerein"]["ApiKey"],
    config=config
)
