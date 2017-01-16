"""
configuration object, wrapper of config file, global read-only
"""

import os
import json

config_path = os.path.dirname(os.path.abspath(__file__))
json_dir = "%s/conf/config.json"%config_path
CONFILE = open(json_dir)
CONFIG = json.load(CONFILE)
META_CONFIG = CONFIG['meta']
CONFILE.close()