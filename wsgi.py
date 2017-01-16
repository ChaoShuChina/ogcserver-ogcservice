#!/usr/bin/env python
#-*-coding:utf-8
"""WSGI application wrapper for Mapnik OGC WMS Server."""

try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

import logging
import imp

from cStringIO import StringIO

import mapnik
import traceback
from ogcserver.common import Version
from ogcserver.WMS import BaseWMSFactory
from ogcserver.configparser import SafeConfigParser
from ogcserver.wms111 import ExceptionHandler as ExceptionHandler111
from ogcserver.wms130 import ExceptionHandler as ExceptionHandler130
from ogcserver.exceptions import OGCException, ServerConfigurationError
from Config import CONFIG
import os
import re
import json

WSGI_STATUS = {
    200: '200 OK',
    404: '404 NOT FOUND',
    500: '500 SERVER ERROR',
}


def do_import(module):
    """
    Makes setuptools namespaces work
    """
    moduleobj = None
    exec 'import %s' % module
    exec 'moduleobj=%s' % module
    return moduleobj

#2017.1,to solve the proble that 'kill -9' kill process.
map_dir = CONFIG['map']['map_dir']
# layers = {}
now_dir = os.path.dirname(os.path.abspath(__file__))
def add_configfile(mapnikfile):
    xml_file = open(mapnikfile, 'r')
    conf_templete = open("%s/conf/templete.conf"%now_dir, 'r')
    conf_outputname = mapnikfile.split('/')[-2]
    conf_output = open("%s/conf/%s.conf"%(now_dir, conf_outputname), 'w')
    pattern1 = re.compile(r"\[[^\[\]]+\]")
    pattern2 = re.compile(r"[^\[^\]]+")
    while 1:
        line_xml = xml_file.readline()
        if  'Parameter name="name"' in line_xml:
            match1 = pattern1.search(line_xml)
            match2 = pattern2.search(match1.group())
            mapname = match2.group()
            break
        elif line_xml == '':
            mapname = "HiGIS OGC Server"
            logging.debug("mapname not found in mapfile! will use default name!")
            break
    xml_file.close()
    while 1:
        line_conf = conf_templete.readline()
        if line_conf != '' and "title = HiGIS" in line_conf:
            conf_output.write("title = HiGIS OGC Server:%s"%mapname)
        elif line_conf != '' and "wms_title =" in line_conf:
            conf_output.write("wms_title = %s"%mapname)
        elif line_conf != '':
            conf_output.write(line_conf)
        elif line_conf == '':
            conf_output.close()
            break
    return [mapname, conf_outputname]
#change by shuchao
class WSGIApp:
    def __init__(self):
        self.higis_layers = {}
        self.debug = 0
        self.max_age = None

    def __call__(self, environ, start_response):
    #     self.higis_layers[1000000] = {
    #         "config_file": "%s/conf/%s.conf"%(now_dir, mapid),
    #         "mapnik_file": mapnikfile,
    #         "config": None,
    #         "mapfactory": None,
    # }


        # self.higis_layers[] = {
        #
        # }


        reqparams = {}
        base = True
        try:
            for key, value in parse_qs(environ['QUERY_STRING'], True).items():
                reqparams[key.lower()] = value[0]

                #2017.1,9.to solve the proble that 'kill -9' kill process.
                if key=='map':
                    map_dir = CONFIG['map']['map_dir']
                    # map_dir = '/cluster/higis/carto/maps/'
                    mapnikfile = "%s%s/style.xml"%(map_dir, value[0])
                    [mapname, mapid] = add_configfile(mapnikfile)
                    self.higis_layers[value[0]]={
                        "config_file": str("%s/conf/%s.conf"%(now_dir, mapid)),
                        "mapnik_file": str(mapnikfile),
                        "config": None,
                        "mapfactory": None,
                    }

                #响应删除请求，清除内存中app_id，相应的服务
                if key == "app_id":
                    if self.higis_layers.has_key(key):
                        del self.higis_layers[value[0]]
                    logging.info("删除内存中对应图层成功！")
                    result = {'status': 'failed'}
                    result.update({'status': '200'})
                    s = json.dumps(result)
                    return


                base = False
        except Exception, e:
            logging.error('error occurs in publish_map 1: %s' % str(e))
            traceback.print_exc()

        try:
            if reqparams == {}:
                return
            map_str = reqparams["map"]
            _higis_obj = self.higis_layers[map_str];
            _config = _higis_obj["config"];
            _mapfactory = _higis_obj["mapfactory"];
        except Exception, e:
            logging.error('error occurs in publish_map 1: %s' % str(e))
            traceback.print_exc()
        if _config == None:
            try:
                _config = SafeConfigParser()
                _config.readfp(open(_higis_obj["config_file"]))
                _mapfactory = BaseWMSFactory(_higis_obj["config_file"])
            except Exception,e:
                logging.error('error occurs in publish_map 2: %s' % str(e))
            try:
               _mapfactory.loadXML(_higis_obj["mapnik_file"])
            except Exception, e:
                logging.error('error occurs in publish_map 3: %s' % str(e))
                traceback.print_exc()
            _mapfactory.finalize()
        try:
            if _config.has_option_with_value('service', 'baseurl'):
                onlineresource = '%s' % _config.get('service', 'baseurl')
            else:
                # if there is no baseurl in the config file try to guess a valid one
                onlineresource = 'http://%s%s%s?map=%s' % (environ['HTTP_HOST'], environ['SCRIPT_NAME'], environ['PATH_INFO'],map_str)
        except Exception,e:
            logging.error('error occurs in publish_map 4: %s' % str(e))
            traceback.print_exc()
        try:
            if not reqparams.has_key('request'):
                raise OGCException('Missing request parameter.')
            request = reqparams['request']
            del reqparams['request']
            if request == 'GetCapabilities' and not reqparams.has_key('service'):
                raise OGCException('Missing service parameter.')
            if request in ['GetMap', 'GetFeatureInfo']:
                service = 'WMS'
            else:
                try:
                    service = reqparams['service']
                except:
                    service = 'WMS'
                    request = 'GetCapabilities'
            if reqparams.has_key('service'):
                del reqparams['service']
            try:
                ogcserver = do_import('ogcserver')
            except:
                raise OGCException('Unsupported service "%s".' % service)
            service = service.upper()
            ServiceHandlerFactory = getattr(ogcserver, service).ServiceHandlerFactory
            servicehandler = ServiceHandlerFactory(_config, _mapfactory, onlineresource,
                                                   reqparams.get('version', None))
            if reqparams.has_key('version'):
                del reqparams['version']
            if request not in servicehandler.SERVICE_PARAMS.keys():
                raise OGCException('Operation "%s" not supported.' % request, 'OperationNotSupported')
            ogcparams = servicehandler.processParameters(request, reqparams)
            try:
                requesthandler = getattr(servicehandler, request)
            except:
                raise OGCException('Operation "%s" not supported.' % request, 'OperationNotSupported')

            # stick the user agent in the request params
            # so that we can add ugly hacks for specific buggy clients
            ogcparams['HTTP_USER_AGENT'] = environ.get('HTTP_USER_AGENT', '')

            response = requesthandler(ogcparams)
        except:
            version = reqparams.get('version', None)
            if not version:
                version = Version()
            else:
                version = Version(version)
            if version >= '1.3.0':
                eh = ExceptionHandler130(self.debug, base, self.home_html)
            else:
                eh = ExceptionHandler111(self.debug, base, self.home_html)
            response = eh.getresponse(reqparams)
        response_headers = [('Content-Type', response.content_type), ('Content-Length', str(len(response.content)))]
        if self.max_age:
            response_headers.append(('Cache-Control', self.max_age))
        status = WSGI_STATUS.get(response.status_code, '500 SERVER ERROR')
        start_response(status, response_headers)
        yield response.content


# PasteDeploy factories [kiorky kiorky@cryptelium.net]

class BasePasteWSGIApp(WSGIApp):
    def __init__(self,
                 configpath,
                 fonts=None,
                 home_html=None,
                 **kwargs
                 ):
        conf = SafeConfigParser()
        conf.readfp(open(configpath))
        # TODO - be able to supply in config as well
        self.home_html = home_html
        self.conf = conf
        if fonts:
            mapnik.register_fonts(fonts)
        if 'debug' in kwargs:
            self.debug = bool(kwargs['debug'])
        else:
            self.debug = False
        if self.debug:
            self.debug = 1
        else:
            self.debug = 0
        if 'maxage' in kwargs:
            self.max_age = 'max-age=%d' % kwargs.get('maxage')
        else:
            self.max_age = None


class MapFilePasteWSGIApp(BasePasteWSGIApp):
    def __init__(self,
                 configpath,
                 mapfile,
                 fonts=None,
                 home_html=None,
                 **kwargs
                 ):
        BasePasteWSGIApp.__init__(self,
                                  configpath,
                                  font=fonts, home_html=home_html, **kwargs)
        wms_factory = BaseWMSFactory(configpath)
        wms_factory.loadXML(mapfile)
        wms_factory.finalize()
        self.mapfactory = wms_factory


class WMSFactoryPasteWSGIApp(BasePasteWSGIApp):
    def __init__(self,
                 configpath,
                 server_module,
                 fonts=None,
                 home_html=None,
                 **kwargs
                 ):
        BasePasteWSGIApp.__init__(self,
                                  configpath,
                                  font=fonts, home_html=home_html, **kwargs)
        try:
            mapfactorymodule = do_import(server_module)
        except ImportError:
            raise ServerConfigurationError('The factory module could not be loaded.')
        if hasattr(mapfactorymodule, 'WMSFactory'):
            self.mapfactory = getattr(mapfactorymodule, 'WMSFactory')(configpath)
        else:
            raise ServerConfigurationError('The factory module does not have a WMSFactory class.')





def ogcserver_base_factory(base, global_config, **local_config):
    """
    A paste.httpfactory to wrap an ogcserver WSGI based application.
    """
    log = logging.getLogger('ogcserver.wsgi')
    wconf = global_config.copy()
    wconf.update(**local_config)
    debug = False
    if global_config.get('debug', 'False').lower() == 'true':
        debug = True
    configpath = wconf['ogcserver_config']
    server_module = wconf.get('mapfile', None)
    fonts = wconf.get('fonts', None)
    home_html = wconf.get('home_html', None)
    app = None
    if base == MapFilePasteWSGIApp:
        mapfile = wconf['mapfile']
        app = base(configpath,
                   mapfile,
                   fonts=fonts,
                   home_html=home_html,
                   debug=False)
    elif base == WMSFactoryPasteWSGIApp:
        server_module = wconf['server_module']
        app = base(configpath,
                   server_module,
                   fonts=fonts,
                   home_html=home_html,
                   debug=False)

    def ogcserver_app(environ, start_response):
        from webob import Request
        req = Request(environ)
        try:
            resp = req.get_response(app)
            return resp(environ, start_response)
        except Exception, e:
            if not debug:
                log.error('%r: %s', e, e)
                log.error('%r', environ)
                from webob import exc
                return exc.HTTPServerError(str(e))(environ, start_response)
            else:
                raise

    return ogcserver_app


def ogcserver_map_factory(global_config, **local_config):
    return ogcserver_base_factory(MapFilePasteWSGIApp,
                                  global_config,
                                  **local_config)


def ogcserver_wms_factory(global_config, **local_config):
    return ogcserver_base_factory(WMSFactoryPasteWSGIApp,
                                  global_config,
                                  **local_config)

