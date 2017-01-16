#!/usr/bin/env python
__author__ = 'shuchao'
import os
import logging
from wsgi import WSGIApp
from Config import CONFIG

if __name__ == '__main__':
    # log_dir = CONFIG['ogcserver']['log_dir']
    log_dir = "/var/log/ogcserver/running"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(filename = log_dir, level=logging.DEBUG, format=FORMAT)
    now_dir = os.path.dirname(os.path.abspath(__file__))
    map_dir = CONFIG['map']['map_dir']
    now_dir = os.path.dirname(os.path.abspath(__file__))
    logging.debug("...server begin...")
    application = WSGIApp()
    from wsgiref import simple_server
    simple_server.make_server('', 8082, application).serve_forever()



