# -*-coding:utf-8
__author__ = 'shuchao'
import base64
from flask import request
import json
import logging
import os
import traceback

import ogcservice
from app.app_manager import App
from app.ogcservice.ogcservice_manager import Wms, Wfs
from app.ogcservice import ogcservice_api
from config import CONFIG
from osgeo import ogr, osr
from app.models import MODEL
from app.utils import SUCCESS, FAIL
import httplib
import app.app_view


"""
    @api {post} /services/register 注册服务
    @apiVersion 3.0.0
    @apiName app_create_service
    @apiGroup Services
    @apiParam {String}      user              用户id.
    @apiParam {String}      name              服务名称.
    @apiParam {String}      type              服务类型
    @apiParam {String}      desc              服务描述
    @apiParam {Array}       thumbnail         服务缩略图
    @apiSuccess {String}    app_id            注册成功后的app_id.
    @apiError {json}        error            注册失败，返回错误消息
"""


@ogcservice_api.route('/register', methods=['POST'])
def app_create_service():
    result = {}
    logging.debug('try creating service')
    try:
        if request.data != '':
            args = json.loads(request.data)
        else:
            args = request.form
        if 'wms' in args:
            wms_result = app_register_wms_service('service', '', args['wms'], '', '', '', '')
            result.update({'wms': wms_result})
        if 'wfs' in args:
            wfs_result = app_register_wfs_service('service', '', args['wfs'], '', '', '', '')
            result.update({'wfs': wfs_result})
        return json.dumps(result)
    except Exception, e:
        logging.error('error occurs in service_create: %s' % str(e))
        traceback.print_exc()
        return str(e), 500


"""
    @api {post} /services/publish_featuretable_to_ogcservice 发布数据表数据到wms/wfs服务
    @apiVersion 3.0.0
    @apiName publish_data
    @apiGroup Services
    @apiParam {String}      ft_name           需要发布成ogc服务的数据表名称(从postgis发布需要).
    @apiParam {String}      epsg              发布服务的坐标系EPSG值，只传输对应的数字编码，例如：'3857'.
    @apiParam {String}      appid             待发布数据的app_id值.
    @apiParam {String}      title             用户自定义注册服务名称.

        返回：
        [wms_url, wfs_url]:返回服务路径

"""
@ogcservice_api.route('/publish_feature_to_ogcservice', methods=['POST'])
def publish_featuretable_to_ogcservice():
    logging.debug('try publish data')
    result = {}
    try:
        if request.data != '':
            args = json.loads(request.data)
        else:
            args = request.form
        if 'app_id' in args:
            app_id = args['app_id']
            apps = App(app_id=app_id)
            app = apps.app_get()
            ft_name = app.uri
        else:
            app = None
            return json.dumps({'msg':'publish data error!'})

        # ft_name = app.uri
        # ft_name = args["ft_name"]
        if 'servername' in args and args['servername'] != '':
            title = args['servername']
        else:
            title = ft_name
        epsg = args['epsg']
        if int(epsg.split(':')[1]) >= 900913:
            epsg = 'EPSG:900913'
            # epsg = 'EPSG:4326'
        print epsg
        workspacename = 'higis'
        storename = 'postgis'
        # return json.dumps({})
        ft = ogcservice.publish_feature_from_postgis(ft_name, epsg, title, workspacename, storename)
        ft_str = json.dumps({'type': 1, 'params': [ft_name, epsg, title, workspacename, storename]})
        wms_url = ogcservice.wms_url(ft)
        wfs_url = ogcservice.wfs_url(ft)

        unique_label = get_feature_service_label(title)
        wms_result = app_register_wms_service('data', app, args, ft, wms_url, ft_str, unique_label)  # 将刚发布的服务直接注册进online中去
        wfs_result = app_register_wfs_service('data', app, args, ft, wfs_url, ft_str, unique_label)  # 将刚发布的服务直接注册进online中去
        result.update({'WMS': {'url': wms_url, 'data': wms_result}})
        result.update({'WFS': {'url': wfs_url, 'data': wfs_result}})
        return json.dumps(result)
    except Exception, e:
        logging.error('error occurs in publish_feature_to_ogcservice: %s'%str(e))
        traceback.print_exc()
        return str(e), 500


def get_feature_service_label(label):
    try:
        surfix = 0
        new_label = ''
        session = MODEL.Session()
        existed = (session.query(MODEL.Wms)
                   .filter(MODEL.Wms.label == label).count() > 0) or (session.query(MODEL.Wfs)
                                                                      .filter(MODEL.Wfs.label == label).count() > 0)
        session.commit()
        if not existed:
            new_label = label

        while existed:
            session = MODEL.Session()
            surfix += 1
            new_label = label + '_{0}'.format(surfix)
            existed = (session.query(MODEL.Wms)
                       .filter(MODEL.Wms.label == new_label).count() > 0) or (session.query(MODEL.Wfs)
                                                                              .filter(
                MODEL.Wfs.label == new_label).count() > 0)
            session.commit()
        return new_label
    except Exception, e:
        logging.error('error occurs in get_feature_service_label: %s' % str(e))
        traceback.print_exc()
        return str(e), 500


def get_raster_service_label(label):
    try:
        surfix = 0
        new_label = ''
        session = MODEL.Session()
        existed = (session.query(MODEL.Wms)
                   .filter(MODEL.Wms.label == label).count() > 0)
        session.commit()
        if not existed:
            new_label = label

        while existed:
            session = MODEL.Session()
            surfix += 1
            new_label = label + '_{0}'.format(surfix)
            existed = (session.query(MODEL.Wms)
                       .filter(MODEL.Wms.label == new_label).count() > 0)
            session.commit()
        return new_label
    except Exception, e:
        logging.error('error occurs in get_raster_service_label: %s' % str(e))
        traceback.print_exc()
        return str(e), 500


"""
    @api {post} /services/publish_coverage_to_ogcservice 发布数据服务
    @apiVersion 3.0.0
    @apiName publish_data
    @apiGroup Services
    @apiParam{String}       storename         从postgis发布/发布coverage时要提供，从postgis发布缺损默认为"postgis"，发布coverage不可缺损.
    @apiParam{String}       data_dir          从文件系统发布需要提供，为待发布文件带路径全名
    @apiParam{String}       servername        发布服务名称，缺损为None时候，则使用数据名
        返回：
        wms_url:返回服务路径
"""


@ogcservice_api.route('/publish_coverage_to_ogcservice', methods=['POST'])
def publish_coverage_to_ogcservice():
    result = {}
    try:
        if request.data != '':
            args = json.loads(request.data)
        else:
            args = request.form
        apps = App(app_id=args['app_id'])
        data_dir = apps.app_get().uri
        # data_dir = args['data_dir']
        servername = args['servername']
        if servername == '':
            servername = data_dir.split('/')[-1].split('.')[0]
        storename = data_dir.split('/')[-1].split('.')[0]
        # if data_dir.split('/')[1] != 'cluster':
        #     data_dir = RASRER_PATH + data_dir
        data_dir = 'file:' + data_dir
        ft = ogcservice.publish_coverage(storename, data_dir, servername)
        ft_str = json.dumps({'type': 3, 'params': [storename, data_dir, servername]})
        wms_url = ogcservice.wms_url(ft)

        label = servername
        unique_label = get_raster_service_label(label)
        wms_result = app_register_wms_service('data', '', args, ft, wms_url, ft_str, unique_label)  # 不会有app
        result.update({'WMS': {'url': wms_url, 'data': wms_result}})
        return json.dumps(result)
    except Exception, e:
        logging.error('error occurs in publish_coverage_to_ogcservice: %s' % str(e))
        traceback.print_exc()
        return str(e), 500


"""
    @api {post} /services/publish_shapefile_to_ogcservice 发布数据服务
    @apiVersion 3.0.0
    @apiName publish_data
    @apiGroup Services
    @apiParam{String}       storename         从postgis发布/发布coverage时要提供，从postgis发布缺损默认为"postgis"，发布coverage不可缺损.
    @apiParam{String}       data_dir          从文件系统发布需要提供，为待发布文件带路径全名
    @apiParam{String}       servername        发布服务名称，缺损为None时候，则使用数据名

"""
@ogcservice_api.route('/publish_shapefile_to_ogcservice', methods=['POST'])
def publish_shapefile_to_ogcservice():
    result = {}
    try:
        if request.data != '':
            args = json.loads(request.data)
        else:
            args = request.form
        data_dir = args['data_dir']
        servername = args['servername']
        workspacename = 'higis'
        print servername
        ft = ogcservice.publish_feature_from_dir(data_dir, servername, workspacename)
        ft_str = json.dumps({'type': 2, 'params': [data_dir, servername, workspacename]})
        wms_url = ogcservice.wms_url(ft)
        wfs_url = ogcservice.wfs_url(ft)
        wms_result = app_register_wms_service('data', '', args, ft, wms_url, ft_str)  # 将刚发布的服务直接注册进online中去
        wfs_result = app_register_wfs_service('data', '', args, ft, wfs_url, ft_str)  # 将刚发布的服务直接注册进online中去
        result.update({'WMS': {'url': wms_url, 'data': wms_result}})
        result.update({'WFS': {'url': wfs_url, 'data': wfs_result}})
        # result = app_register_service('data', app, args, ft)  # 将刚发布的服务直接注册进online中去
        return json.dumps(result)
    except Exception, e:
        logging.error('error occurs in publish_data: %s' % str(e))
        traceback.print_exc()
        return str(e), 500

def app_register_wms_service(type, app, args, result, url, paramstr, label=None):
    try:
        service = Wms()
        service.user = args['user']
        service.path = None
        if type == 'data':
            # service.name = result.name + '_wms'
            service.name = args['servername'] + '_wms'
            # service.name = 'wms' + '_' + args['servername']
            service.publish_param_str = paramstr
            service.label = label
            service.group_id = ''
            service.source_id = args['app_id']
        elif type == 'map':
            service.name = args['servername']
            service.group_id = ''
            service.label = label
            service.source_id = args['app_id']
        elif type == 'service':
            service.name = args['name'] + '_wms'
            service.publish_param_str = ''
            service.label = args['name']
            service.source_id = ''
            # service.name = 'wms' + '_' + args['name']
        if app != '':
            if None != app and app.app_type != 4:
                service.geometry_type = app.geometry_type
            else:
                service.geometry_type = None
        else:
            service.geometry_type = None
        service.app_type = 11
        service.service = 'WMS'
        if type == 'data':
            if result.native_bbox[4] != 'EPSG:4326' and result.native_bbox[4] != 'EPSG:900913':
            # if result.native_bbox[4] != 'EPSG:4326' and result.native_bbox[4] != 'EPSG:900913':
                ldstr = 'POINT({0} {1})'.format(result.native_bbox[0], result.native_bbox[2])
                rustr = 'POINT({0} {1})'.format(result.native_bbox[1], result.native_bbox[3])
                plist = [ldstr, rustr]
                source = osr.SpatialReference()
                source.ImportFromEPSG(int(result.native_bbox[4].split(':')[1]))  # 平面坐标系
                target = osr.SpatialReference()
                target.ImportFromEPSG(4326)  # 经纬度坐标系
                transform = osr.CoordinateTransformation(source, target)  # 将输入坐标转换为经纬度
                bound = []
                for tmp in plist:
                    geometry = ogr.CreateGeometryFromWkt(tmp)
                    geometry.Transform(transform)
                    str = geometry.ExportToWkt()

                    for value in str.split("(")[1].split(")")[0].split(" "):
                        bound.append(float(value))
                service.bbox = bound
                service.srs = 'EPSG:4326'
            else:
                service.bbox = [result.native_bbox[0], result.native_bbox[2], result.native_bbox[1],
                                result.native_bbox[3]]
                service.srs = result.native_bbox[4]
            service.layers = result.workspace.name + ':' + result.name
            service.workspace = result.workspace.name

            service.version = '1.0.0'
            service.request = 'GetMap'
            service.height = 768
            service.width = 768
            service.format = 'application/openlayers'
            service.path = '{0}?service=WMS&request={1}&layers={2}&srs={3}'.format(url.split('?')[0], service.request,
                                                                                   service.layers, service.srs)
        elif type == 'service':
            service.bbox = [args['bbox_minx'], args['bbox_miny'], args['bbox_maxx'], args['bbox_maxy']]
            service.layers = args['workspace'] + ':' + args['layers']
            service.workspace = args['workspace']
            service.srs = args['srs']
            service.version = args['version']
            service.request = args['request']
            service.height = args['height']
            service.width = args['width']
            service.format = args['format']
            service.path = '{0}?service=WMS&request={1}&layers={2}&srs={3}'.format(args['url'], service.request,
                                                                                   service.layers, service.srs)
        elif type == "map":
            app = App(app_id=args['app_id']).app_get()
            service.bbox = [app.domain_minx, app.domain_miny, app.domain_maxx, app.domain_maxy]
            # service.srs = "EPSG:{0}".format(app.srid)
            service.srs = "EPSG:4326"
            service.layers = '__all__'
            service.workspace = None
            service.version = "1.1.1"
            service.request = 'GetMap'
            service.height = "720"
            service.width = "768"
            service.format = "image%2Fpng"
            service.path = '{0}?map={1}&layers=__all__&styles=&format=image%2Fpng&service=WMS&request=GetMap&srs=EPSG:4326'.format(url, args['app_id'])
            # service.path = url
        service.servername = service.layers
        service.status = 0  # 0为注册状态
        service.time_constraint = ""
        service.publish_param_str = ''
        service.info=''
        result = service.register()
        return result
    except Exception, e:
        logging.error('error occurs in register_wms_service: %s' % str(e))
        traceback.print_exc()
        return str(e), 500


def app_register_wfs_service(type, app, args, result, url, paramstr, label):
    try:
        service = Wfs()
        service.user = args['user']
        service.path = None
        if type == 'data':
            service.name = args['servername'] + '_wfs'
            # service.name = 'wfs' + '_' + args['servername']
            service.publish_param_str = paramstr
            service.label = label
            service.group_id = ''
            service.source_id = args['app_id']
        elif type == 'map':
            service.name = result['layers']
            service.source_id = args['app_id']
        elif type == 'service':
            service.name = args['name'] + '_wfs'
            service.publish_param_str = ''
            service.label = args['name']
            service.source_id = ''
            # service.name = 'wfs' + '_' + args['name']
        if app != '':
            if None != app and app.app_type != 4:
                service.geometry_type = app.geometry_type
            else:
                service.geometry_type = None
        else:
            service.geometry_type = None
        service.app_type = 12

        service.service = 'WFS'
        if type == 'data':
            if result.native_bbox[4] != 'EPSG:4326' and result.native_bbox[4] != 'EPSG:900913':
                ldstr = 'POINT({0} {1})'.format(result.native_bbox[0], result.native_bbox[2])
                rustr = 'POINT({0} {1})'.format(result.native_bbox[1], result.native_bbox[3])
                plist = [ldstr, rustr]
                source = osr.SpatialReference()
                source.ImportFromEPSG(int(result.native_bbox[4].split(':')[1]))  # 平面坐标系
                target = osr.SpatialReference()
                target.ImportFromEPSG(4326)  # 经纬度坐标系
                transform = osr.CoordinateTransformation(source, target)  # 将输入坐标转换为经纬度
                bound = []
                for tmp in plist:
                    geometry = ogr.CreateGeometryFromWkt(tmp)
                    geometry.Transform(transform)
                    str = geometry.ExportToWkt()

                    for value in str.split("(")[1].split(")")[0].split(" "):
                        bound.append(float(value))
                service.bbox = bound
                service.srs = 'EPSG:4326'
            else:
                service.bbox = [result.native_bbox[0], result.native_bbox[2], result.native_bbox[1],
                                result.native_bbox[3]]
                service.srs = result.native_bbox[4]
            # service.bbox = [result.native_bbox[0], result.native_bbox[2], result.native_bbox[1], result.native_bbox[3]]
            # service.srs = result.native_bbox[4]
            service.typename = result.workspace.name + ':' + result.name
            service.maxFeatures = 50
            service.version = '1.0.0'
            service.request = 'GetFeature'
            service.path = url
            # service.uri = url
        elif type == 'service':
            service.bbox = [args['bbox_minx'], args['bbox_miny'], args['bbox_maxx'], args['bbox_maxy']]
            service.srs = args['srs']
            service.typename = args['workspace'] + ':' + args['typeName']
            service.maxFeatures = args['maxFeatures']
            service.version = args['version']
            service.request = args['request']
            service.path = '{0} {1}/ows?service=WFS&version={2}&request={3}&typeName={4}&maxFeatures={5}'.format(
                args['url'], args['workspace'], service.version,
                service.request, service.typename, service.maxFeatures)

        service.servername = service.typename
        service.status = 0  # 0为注册状态
        service.time_constraint = ""
        result = service.register()
        return result
    except Exception, e:
        logging.error('error occurs in register_wfs_service: %s' % str(e))
        traceback.print_exc()
        return str(e), 500


def app_register_service(type, app, args, result):
    try:
        service = Wms()
        service.user = args['user']
        service.path = None
        if type == 'data':
            service.name = result.name
        elif type == 'map':
            service.name = result['layers']
        if None != app and app.app_type != 4:
            service.geometry_type = app.geometry_type
        else:
            service.geometry_type = None
        if result['service'] == 'WMS':
            service.app_type = 11
        url = 'http://202.197.18.63:8080/geoserver/higis/wms?service=WMS&version=1.1.0&request=GetMap&layers=higis:r&width=768&height=330&srs=EPSG:4326&format=application/openlayers'
        service.path = url
        service.bbox = result['bbox']
        service.layers = result['layers']
        service.workspace = result['workspacename']
        service.srs = result['srs']
        service.service = result['service']
        service.version = result['version']
        service.request = result['request']
        service.width = result['width']
        service.height = result['height']
        service.format = result['format']
        result = service.register()
        return result
    except Exception, e:
        logging.error('error occurs in register_service: %s' % str(e))
        traceback.print_exc()
        return str(e), 500


def app_run_service():
    try:
        "SS"
    except Exception, e:
        logging.error('error occurs in app_run_service: %s' % str(e))
        traceback.print_exc()
        return str(e), 500


def app_stop_service():
    try:
        "SS"
    except Exception, e:
        logging.error('error occurs in app_stop_service: %s' % str(e))
        traceback.print_exc()
        return str(e), 500


@ogcservice_api.route('/layers', methods=['POST'])
def app_get_layers():
    result = {}
    services = []
    try:
        workspace = request.form['workspace'];
        if workspace == '':
            workspace = 'higis'
        res = ogcservice.get_service_list(workspace)
        for tmp in res:
            services.append(tmp.name)
        result = {'count': len(res), 'services': services}
        return json.dumps(result)
    except Exception, e:
        logging.error('error occurs in app_get_layers: %s' % str(e))
        traceback.print_exc()
        return str(e), 500


@ogcservice_api.route('/params', methods=['POST'])
def app_get_params():
    result = {}
    params = []
    try:
        layer = request.form['layer']
        result = ogcservice.get_service_Param(layer)
        return json.dumps(result)
    except Exception, e:
        logging.error('error occurs in app_get_params: %s' % str(e))
        traceback.print_exc()
        return str(e), 500


@ogcservice_api.route('/get_feature_srs', methods=['GET'])
def get_feature_srs():
    result = {}
    try:
        if request.data != '':
            args = json.loads(request.data)
        else:
            args = request.values
        app_id = args['app_id']
        apps = App(app_id=app_id)
        app = apps.app_get()
        if app.srid != -1 and app.srid != 0 and app.srid != None:
            result = {'status': 'T', 'srs': app.srid}
        else:
            result = {'status': 'F'}
        return json.dumps(result)
    except Exception, e:
        logging.error('error occurs in get_feature_srs: %s' % str(e))
        traceback.print_exc()
        return str(e), 500


"""
    @api {post} /services/publish_map 发布地图服务
    @apiVersion 3.0.0
    @apiName publish_data
    @apiGroup Services
    @apiParam{Array}        postgisdata       需要发布到矢量数据名称列表
    @apiParam {String}      epsg              发布服务的坐标信息，例如：'EPSG:3857'.
    @apiParam {String}      servicename       ogc服务名称
    @apiParam {Array}       coveragedata      需要发布的栅格数据全称列表,可有可无，默认为None
    @apiParam {String}      workspacename     geoserver工作空间名，默认为"higis"

"""
@ogcservice_api.route('/publish_map', methods=['POST'])
def publish_map():
    logging.debug('try publish map')
    result = {'status': 'failed'}
    args = request.form
    app = App(app_id=args['app_id']).app_get()
    try:
        app_id = request.form['app_id']
        try:
            wms_url = CONFIG['ogcserver']['wms_url']
            # wms_url = "http://202.197.18.52:8082/"
            url = '%s?map=%s&layers=__all__&styles=&format=png&service=WMS&version=1.1.1&request=GetCapabilities'%(wms_url, app_id)
            ogc_url = CONFIG['ogcserver']['ogc_url']
            # ogc_url = '202.197.18.52'
            httpClient = httplib.HTTPConnection(ogc_url, '8082', timeout=30)
            httpClient.request('GET', url)
            response = httpClient.getresponse()
        except AssertionError:
            logging.error('error  %s'%response.status)
        finally:
            print("url:", url)
            ft_str = json.dumps({'type': 2, 'params': " "})#这句话没用但是不能少
            wms_result = app_register_wms_service('map', None, args, None, wms_url, ft_str)
            update_source_info(args['app_id'],wms_result['app_id']) #更新地图或者数据资源的发布服务目标id

            print("wms_result:",wms_result)
            #url为getcability的url，wms_url为获取图片的url
            result.update({'status': 'success'})
            result.update({'WMS': {'url': url, 'data': wms_result}})
            print "result:",json.dumps(result)
            return json.dumps(result)
    except Exception, e:
        logging.error('error occurs in publish_map: %s' % str(e))
        traceback.print_exc()
        return str(e), 500

"""
    更新地图或者数据资源的发布服务目标id
"""
def update_source_info(source_id, target_id):
    result = {}
    try:
        session = MODEL.Session()
        session.query(MODEL.Map).filter(MODEL.Map.app_id == source_id).update({'target_id': target_id})
        session.commit()
        result.update(SUCCESS)
        return result
    except Exception, e:
        logging.error('error occurs in update_source_info: %s' % str(e))
        traceback.print_exc()
        return str(e), 500

def handler(signum, frame):
    raise AssertionError

def delete_map():
    logging.debug('try delete map')
    result = {'status': 'failed'}
    try:
        app_id = request.form['app_id']
        map_dir = CONFIG['map']['map_dir']
        xml_file = "%s%s/style.xml"%(map_dir,app_id)
        log_dir = CONFIG['log']['log_dir']
        now_dir = os.path.dirname(os.path.abspath(__file__))
        publish_cmd = "nohup python -u %s/higis_wms_script.py '%s' 'start' > %sogcserver.log &"%(now_dir, xml_file, log_dir)
        os.system(publish_cmd)
        result = {'OK':'OK'}
        return json.dumps(result)

    except Exception, e:
        logging.error('error occurs in delete_map: %s' % str(e))
        traceback.print_exc()
        return str(e), 500



@ogcservice_api.route('/delete', methods=['DELETE'])
def delete():
    logging.debug('try delete')
    try:
        # args = request.form
        # args = json.loads(request.data)
        if request.data != '':
            args = json.loads(request.data)
        else:
            args = request.form

        type = args['type']
        name = args['name']
        if type == 1:
            ogcservice.delete_layer(name)
        if type == 2:
            ogcservice.delete_layergroups(name)
    except Exception, e:
        logging.error('error occurs in delete: %s' % str(e))
        traceback.print_exc()
        return str(e), 500


'''
    @api {post} /services/status_change 服务状态变更,启用服务或者停用服务
    @apiVersion 3.0.0
    @apiName service_status_changes
    @apiGroup Services
    @apiParam{Array}        target_status     服务变更的目标状态，0为注册，1为启用，2为停用
    @apiParam {String}      servername        服务名称

'''


@ogcservice_api.route('/status_change', methods=['POST'])
def service_status_changes():
    result = {}
    try:
        args = json.loads(request.data)
        app_id = args['app_id']
        target_status = args['target_status']
        apps = App(app_id=app_id)
        app = apps.app_get()
        publish_str = app.publish_param_str
        label = app.label
        if target_status == 1:
            app_run_service()
        elif target_status == 2:
            app_stop_service()
        if label is not None:
            # if target_status == 1:
            #     app_run_service()
            # elif target_status == 2:
            #     app_stop_service()
            session = MODEL.Session()
            wms_service = session.query(MODEL.Wms).filter(MODEL.Wms.label == label).first()
            wfs_service = session.query(MODEL.Wfs).filter(MODEL.Wfs.label == label).first()
            if wms_service is not None:
                session.query(MODEL.Service).filter(MODEL.Service.app_id == wms_service.app_id).update({'status': target_status})
            if wfs_service is not None:
                session.query(MODEL.Service).filter(MODEL.Service.app_id == wfs_service.app_id).update({'status': target_status})
            session.commit()
        else:
            session = MODEL.Session()
            wms_service = session.query(MODEL.Wms).filter(MODEL.Wms.app_id == app_id).first()
            wfs_service = session.query(MODEL.Wfs).filter(MODEL.Wfs.app_id == app_id).first()
            if wms_service is not None:
                session.query(MODEL.Service).filter(MODEL.Service.app_id == wms_service.app_id).update({'status': target_status})
            if wfs_service is not None:
                session.query(MODEL.Service).filter(MODEL.Service.app_id == wfs_service.app_id).update({'status': target_status})
            session.commit()

        apps = App(app_id=app_id)
        status = apps.app_get().status

        result.update(SUCCESS)
        result.update({'service_status': status})
        return json.dumps(result)
    except Exception, e:
        logging.error('error occurs in service_status_changes: %s' % str(e))
        traceback.print_exc()
        return str(e), 500

@ogcservice_api.route('/wmts_getcapabilities', methods=['POST'])
def wmts_getcapabilities():
    return

@ogcservice_api.route('/logout/<app_id>', methods=['DELETE'])
def service_logout(app_id):
    try:
        apps = App(app_id=app_id)
        source_id = apps.app_get().source_id
        result = apps.app_delete()
        update_source_info(source_id, None)
        try:
            #向服务发送删除请求
            wms_url = CONFIG['ogcserver']['wms_url']
            # wms_url = "http://202.197.18.52:8082/"
            url = '%s?app_id=%s'%(wms_url, source_id)
            ogc_url = CONFIG['ogcserver']['ogc_url']
            # ogc_url = '202.197.18.52'
            httpClient = httplib.HTTPConnection(ogc_url, '8082', timeout=30)
            httpClient.request('GET', url)
            logging.info("清除内存中的服务成功！")
            response = httpClient.getresponse()
        except Exception, e:
            logging.error('error occurs in service_logout_memory: %s' % str(e))
            traceback.print_exc()
            return str(e), 500
        finally:
            return json.dumps(result)
    except Exception, e:
        logging.error('error occurs in service_logout: %s' % str(e))
        traceback.print_exc()
        return str(e), 500