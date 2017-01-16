# -*-coding:utf-8
__author__ = 'shuchao'
from geoserver.catalog import Catalog
import geoserver.util
import subprocess
from config import CONFIG
import re
import logging
import traceback
import time

url = CONFIG['ogcserver']['url']

mode = re.compile(r'\d+')
cat = Catalog(url, username="admin", password="geoserver")
"""
ogc服务
======================
    HiGIS开放地理信息服务接口，提供ogc服务到发布、查询、删除adl以及
    地图style的转换
    :platform:linux
    :author:SHU Chao
    :dependency:gsconfig1.0.3
"""


def publish_feature_from_postgis(ft_name, epsg, title, workspacename='higis', storename='postgis'):
    """
        * 接口介绍

            ======= ================ ===================================
            动作     URI              描述
            ======= ================ ===================================
            PUT                      从postgis数据库发布ogc服务，转换、上传style
            ======= ================ ===================================

        * 调用信息
            :参数:
                - ft_name:需要发布成ogc服务的数据表名称，类型为字符串
                - epsg:发布服务的坐标信息，类型为字符串，例如：'EPSG:3857'
                - style_type:发布服务的类型，1/2/3分别代表点/线/面
                - mapnik_name:mapnik的style文件，带路径的全称，类型为字符串
                - workspacename:geoserver到工作空间，默认为higis
            :返回:
                None：操作成功
                其他：操作错误
            :异常: none
    """
    that_workspace = cat.get_workspace(workspacename)
    layers = cat.get_layers(workspacename)
    surfix = 0
    try:
        existed = contains_title(title, layers)
    except Exception, e:
        logging.error('error occurs in publish_feature: %s' % str(e))
        traceback.print_exc()
    tmpname = title
    servername = title
    if not existed:  # 确保发布的地图服务名都不同
        pass
    while existed:
        surfix += 1
        servername = tmpname + '_{0}'.format(surfix)
        existed = contains_title(servername, cat.get_layers(workspacename))
    store = cat.get_store(storename, workspace='higis')
    while True:
        mm = cat.publish_featuretype(ft_name, store, epsg)
        if mm != None:
            break
        time.sleep(0.2)
    # 清加入重命名机制
    # mm = cat.get_resource(ft_name, workspace = that_workspace)
    mm.title = servername
    cat.save(mm)
    return mm


def wms_url(ft):
    url_1 = CONFIG["ogcserver"]["url_2"]
    url_2 = 'wms?service=WMS&version=1.1.0'
    url_3 = '&request=GetMap'
    url_4 = '&layers=higis:%s' % ft.name
    url_5 = '&styles='
    url_6 = '&bbox=%s,%s,%s,%s' % (
        str(ft.native_bbox[0]), str(ft.native_bbox[2]), str(ft.native_bbox[1]), str(ft.native_bbox[3]))
    url_7 = '&width=768'
    url_8 = '&height=576'
    url_9 = '&srs=%s' % (str(ft.native_bbox[4]))
    url_10 = '&format=application/openlayers'
    url = url_1 + url_2 + url_3 + url_4 + url_5 + url_6 + url_7 + url_8 + url_9 + url_10
    return url


def wfs_url(ft):
    url_1 = CONFIG["ogcserver"]["url_2"]
    url_2 = 'ows?service=WFS&version=1.0.0'
    url_3 = '&request=GetFeature'
    url_4 = '&typeName=higis:%s' % ft.name
    url_5 = '&maxFeatures=50'
    url = url_1 + url_2 + url_3 + url_4 + url_5
    return url


def publish_coverage(storename, data_dir, servername=None, workspacename='higis'):
    """
        * 接口介绍

            ======= ================ ===================================
            动作     URI              描述
            ======= ================ ===================================
            PUT                      从文件发布栅格数据服务
            ======= ================ ===================================

        * 调用信息
            :参数:
                - storename:数据库名称，类型为字符串
                - data_dir:带有路径的待发布数据名称，类型为字符串
                - workspacename：工作空间名称
            :返回:
                None：操作成功
                其他：操作错误
            :异常: none
    """
    data_name = data_dir.split("/")[-1].split('.')[0]
    if servername == None:
        servername = data_name
    resources = cat.get_resources(workspace=workspacename)
    surfix = 0
    existed = contains(servername, resources)
    tmpname = servername
    if not existed:  # 确保发布的地图服务名都不同
        pass
    while existed:
        surfix += 1
        servername = tmpname + '_{0}'.format(surfix)
        existed = contains(servername, cat.get_resources(workspace=workspacename))
    # storename = servername
    cmd1 = "curl -u admin:geoserver -v -XPOST -H 'Content-Type: application/xml' -d '<coverageStore><name>%s</name><workspace>%s</workspace><enabled>true</enabled></coverageStore>' http://202.197.18.63:8080/geoserver/rest/workspaces/%s/coveragestores" % (
        storename, workspacename, workspacename)
    cmd2 = "curl -u admin:geoserver -v -XPUT -H 'Content-type: text/plain' -d '%s' http://202.197.18.63:8080/geoserver/rest/workspaces/%s/coveragestores/%s/external.geotiff?configure=first\&coverageName=%s" % (
        data_dir, workspacename, storename, servername)
    print data_dir, workspacename, storename, servername

    a = subprocess.call([cmd1], shell=True)
    b = subprocess.call([cmd2], shell=True)
    while True:
        m = cat.get_resource(servername, workspace=workspacename)
        if m != None:
            break;
        time.sleep(0.5)
    # print m.projection
    # if a == 0 and b == 0:
    return m


def get_service_list(workspacename='higis'):
    # stores = cat.get_stores(workspacename)
    resources = cat.get_resources(workspace=workspacename)
    return resources
    # layers = cat.get_layers(workspacename)
    # return layers


# def get_service_Param(servicename='higis'):
#     params = cat.get_resource(servicename)
#     rooturl = cat.gs_base_url
#     resource = {'obj': params, 'rooturl': rooturl}
#     return resource


def get_service_Param(servicename):
    result = {}
    wms_params = {}
    wfs_params = {}
    params = cat.get_resource(servicename)
    bbox_minx = 'bbox_minx : {0}'.format(params.native_bbox[0])
    bbox_miny = 'bbox_miny : {0}'.format(params.native_bbox[2])
    bbox_maxx = 'bbox_maxx : {0}'.format(params.native_bbox[1])
    bbox_maxy = 'bbox_maxy : {0}'.format(params.native_bbox[3])
    srs = 'srs : {0}'.format(params.projection)
    workspace = 'workspace : {0}'.format(params._workspace.name)
    layers = 'layers : {0}'.format(servicename)
    wms_params = [workspace, layers, srs, 'service : WMS', bbox_minx, bbox_miny, bbox_maxx, bbox_maxy,
                  'request : GetMap', 'width : 768', 'height : 768', 'version : 1.1.0', 'styles : None',
                  'format : application/openlayers']
    result.update({'wms_params': wms_params})
    # if params.keywords[0] == 'features':
    if ele_contains('features',params.keywords):
        typename = 'typeName : {0}'.format(servicename)
        wfs_params = [workspace, typename, 'service : WFS', 'request : GetFeature', 'version : 1.1.0',
                      'maxFeatures : 50',srs, bbox_minx,bbox_miny,bbox_maxx,bbox_maxy]
        result.update({'wfs_params': wfs_params})
    rooturl = cat.gs_base_url
    result.update({'rooturl': rooturl})
    return result

def ele_contains(ele, list):
    for temp in list:
        if temp == ele:
            return True
    return False

def publish_feature_from_dir(data_dir, servername=None, workspacename='higis'):
    """
        * 接口介绍

            ======= ================ ===================================
            动作     URI              描述
            ======= ================ ===================================
            PUT                      从文件系统发布矢量ogc服务，转换、上传style
            ======= ================ ===================================

        * 调用信息
            :参数:
                - data_dir:带有路径的待发布数据名称，类型为字符串
                - style_type:发布服务的类型，1/2/3分别代表点/线/面
                - mapnik_name:mapnik的style文件，带路径的全称，类型为字符串
                - servername:ogc服务名称
                - workspacename:geoserver到工作空间，默认为higis
            :返回:
                None：操作成功
                其他：操作错误
            :异常: none
    """
    print data_dir, servername, workspacename
    data_dir_chaik = data_dir.split('/')
    data_name = data_dir_chaik[-1]
    if servername == None:
        servername = data_name
    that_workspace = cat.get_workspace(workspacename)
    shapefile_plus_sidecars = geoserver.util.shapefile_and_friends(data_dir)
    stores = cat.get_stores(workspacename)

    surfix = 0
    existed = contains(servername, stores)
    tmpname = servername
    if not existed:  # 确保发布的地图服务名都不同
        pass
    while existed:
        surfix += 1
        servername = tmpname + '_{0}'.format(surfix)
        existed = contains(servername, cat.get_stores(workspacename))
    while True:
        fs = cat.create_featurestore(servername, shapefile_plus_sidecars, that_workspace)
        if fs != None:
            break
        time.sleep(0.1)
    m = cat.get_resource(servername, workspace=workspacename)
    # 加入异常管理机制，如果输入的文件路径有误，返回路径重新输入提示语句
    # try:
    #     ft = cat.create_featurestore(servername, shapefile_plus_sidecars, that_workspace)
    # except Exception:
    #     info = {'status':"failed", 'message':"the dir " + data_dir_chaik + " not exist, please input again!"}
    #     return info

    # print m.latlon_bbox[0], m.latlon_bbox[1], m.latlon_bbox[2], m.latlon_bbox[3]  # ,m.latlon_bbox[4]
    # if None != style_type:
    #     layer = cat.get_layer(servername)
    #     stylename = createStyleFromMapnik(mapnik_name, style_type)
    #     layer._set_default_style(stylename)
    #     cat.save(layer)
    # info = {'service':'WMS',
    #         'version':'1.1.0',
    #         'request':'GetMap',
    #         'workspacename': workspacename,
    #         'layers':'%s:%s'%(workspacename,data_name),
    #         'styles':None,
    #         'bbox':(list(m.latlon_bbox)[0],list(m.latlon_bbox)[2],list(m.latlon_bbox)[1],list(m.latlon_bbox)[3]),
    #         'width':768,
    #         'height':768,
    #         'srs':m.projection,
    #         'format':'application/openlayers'}
    # # cat.save(ft)
    return m


def publish_layergroup(postgisdata, stylelist, mapniklist, epsg, servername, coveragedata=None, workspacename='higis'):
    """
        * 接口介绍

            ======= ================ ===================================
            动作     URI              描述
            ======= ================ ===================================
            PUT                      发布图层组数据服务，矢量数据来自postgis，栅格数据来自文件
            ======= ================ ===================================

        * 调用信息
            :参数:
                - postgisdata:需要发布到矢量数据名称列表
                - epsg:对应的坐标信息
                - servername:ogc服务名称
                - coveragedata：需要发布的栅格数据全称列表
                - workspacename:geoserver到工作空间，默认为higis
            :返回:
                None：操作成功
                其他：操作错误
            :异常: none
    """
    # that_workspace = cat.get_workspace(workspacename)
    info = {}
    servername = servername.encode('utf-8')
    if None != coveragedata:
        coveragedataname = coveragedata.split('/')[-1]
        lyrs = [coveragedataname] + postgisdata
        if cat.get_layer(coveragedataname) == None:
            publish_coverage(coveragedataname, coveragedata)
    else:
        lyrs = postgisdata

    layergroups = cat.get_layergroups()
    surfix = 0
    existed = contains(servername, layergroups)
    tmpname = servername

    if not existed:  # 确保发布的地图服务名都不同
        pass
    while existed:
        surfix += 1
        servername = tmpname + '_{0}'.format(surfix)
        existed = contains(servername, cat.get_layergroups())

    _index = -1
    for featurename in postgisdata:
        _index += 1
        style = stylelist[_index]
        mapnik = mapniklist[_index]
        if None == cat.get_layer(featurename):
            publish_feature_from_postgis(featurename, epsg=epsg, style_type=style, mapnik_name=mapnik)
    # lg = cat.create_layergroup(servername, lyrs, styles = (), bounds=[cat.get_resource(lyrs[1],store=None).native_bbox[0], cat.get_resource(lyrs[1],store=None).native_bbox[1],cat.get_resource(lyrs[1],store=None).native_bbox[2],cat.get_resource(lyrs[1],store=None).native_bbox[3],epsg])

    lg = cat.create_layergroup(servername, lyrs, styles=(),
                               bounds=[cat.get_resource(lyrs[_index], store=None).native_bbox[0],
                                       cat.get_resource(lyrs[_index], store=None).native_bbox[1],
                                       cat.get_resource(lyrs[_index], store=None).native_bbox[2],
                                       cat.get_resource(lyrs[_index], store=None).native_bbox[3], epsg])
    info = {'service': 'WMS',
            'version': '1.1.0',
            'request': 'GetMap',
            'workspacename': workspacename,
            'layers': '%s' % (servername),
            'styles': None,
            'bbox': (lg.dirty['bounds'][0], lg.dirty['bounds'][2], lg.dirty['bounds'][1], lg.dirty['bounds'][3]),
            'width': 768,
            'height': 768,
            'srs': epsg,
            'format': 'application/openlayers',
            'url': cat.gs_base_url}
    cat.save(lg)
    return info


# def app_stop_service(servername):





def contains(elem, list):
    try:
        for temp in list:
            if elem == temp.name:
                return True
        return False
    except ValueError:
        return False


def contains_title(elem, list):
    try:
        for temp in list:
            if elem == cat.get_resource(temp.name).title:
                return True
        return False
    except ValueError:
        return False


# 删除操作
def delete_layer(layername):
    ft = cat.get_layer(layername)
    cat.delete(ft)


def delete_layergroups(groupname):
    ft = cat.get_layergroup(groupname)
    cat.delete(ft)


# style转换操作
def tranPointStyle(mapnikFileName, exportFileName):
    styleList = getMapnikStyle(mapnikFileName)
    # 取出点文件对应svg的名字
    for line in styleList:
        line = line.lstrip()
        if "PointSymbolizer" in line:
            svgname = line.split(' ')[1].split('/')[-1][:-1]
            # print svgname

    # 打开点sld模板
    fTemplate = open("/home/shuchao/geo_app/mapnikxml/Temp/newpoint.xml", 'r')

    # 写入更改内容
    outputsld = open(exportFileName, 'w')
    for line in fTemplate.readlines():
        line = line.lstrip()
        if "<OnlineResource" in line:
            line = '<OnlineResource xlink:type="simple" xlink:href=\'%s\' />' % svgname + '\n'
            outputsld.writelines(line)
        else:
            outputsld.writelines(line)
    outputsld.close()
    fTemplate.close()


def tranLineStyle(mapnikFileName, exportFileName):
    styleList = getMapnikStyle(mapnikFileName)
    # 取出线对应的颜色
    for line in styleList:
        line = line.lstrip()
        if "<LineSymbolizer" in line:
            rgb = mode.findall(line)
    r = str(hex(int(rgb[0])))[2:]
    if len(r) == 1: r = '0' + r
    g = str(hex(int(rgb[1])))[2:]
    if len(g) == 1: g = '0' + g
    b = str(hex(int(rgb[2])))[2:]
    if len(b) == 1: b = '0' + b
    # print r,g,b

    # 打开模板
    fTemplate = open("/home/shuchao/geo_app/mapnikxml/Temp/newline.xml", 'r')

    # 重写sld
    outputsld = open(exportFileName, 'w')
    for line in fTemplate.readlines():
        line = line.lstrip()
        if "<CssParameter" in line:
            line = '<CssParameter name="stroke">#%s%s%s</CssParameter>' % (r, g, b) + '\n'
            outputsld.writelines(line)
        else:
            outputsld.writelines(line)
    outputsld.close()
    fTemplate.close()


def tranPolyStyle(mapnikFileName, exportFileName):
    styleList = getMapnikStyle(mapnikFileName)
    # 取出边线以及填充颜色
    for line in styleList:
        line = line.lstrip()
        if "<LineSymbolizer" in line:
            rgb_line = mode.findall(line)
    # print rgb_line
    # rgb_line = rgbstring_line.split(',')
    r_line = str(hex(int(rgb_line[0])))[2:]
    if len(r_line) == 1: r_line = '0' + r_line
    g_line = str(hex(int(rgb_line[1])))[2:]
    if len(g_line) == 1: g_line = '0' + g_line
    b_line = str(hex(int(rgb_line[2])))[2:]
    if len(b_line) == 1: b_line = '0' + b_line
    # print r_line,g_line,b_line
    for line in styleList:
        line = line.lstrip()
        if "<PolygonSymbolizer" in line:
            rgb_poly = mode.findall(line)
    # rgb_poly = rgbstring_poly.split(',')
    # print rgb_poly
    r_poly = str(hex(int(rgb_poly[0])))[2:]
    if len(r_poly) == 1: r_poly = '0' + r_poly
    g_poly = str(hex(int(rgb_poly[1])))[2:]
    if len(g_poly) == 1: g_poly = '0' + g_poly
    b_poly = str(hex(int(rgb_poly[2])))[2:]
    if len(b_poly) == 1: b_poly = '0' + b_poly
    # print r_poly,g_poly,b_poly

    # 打开模板
    fTemplate = open("/home/shuchao/geo_app/mapnikxml/Temp/newpoly.xml", 'r')
    # 重写sld
    outputsld = open(exportFileName, 'w')
    for line in fTemplate.readlines():
        line = line.lstrip()
        if '<CssParameter name="fill"' in line:
            line = "<CssParameter name='fill'>#%s%s%s</CssParameter>" % (r_poly, g_poly, b_poly)
            outputsld.writelines(line)
        elif '<CssParameter name="stroke">' in line:
            line = '<CssParameter name="stroke">#%s%s%s</CssParameter>' % (r_line, g_line, b_line)
            outputsld.writelines(line)
        else:
            outputsld.writelines(line)
    outputsld.close()
    fTemplate.close()


# 取出mapnik中style部分
def getMapnikStyle(filename):
    f = open(filename, 'r')
    i = 0
    list = []
    for line in f.readlines():
        list.append(line)
        if '<Style' in line and '<StyleName' not in line:
            j = i
        if '</Style>' in line:
            k = i
        i = i + 1
    styleList = list[j:k + 1]
    f.close()
    return styleList


def createStyleFromMapnik(mapnikName, styleType, styleName=None):
    if styleName == None:
        styleName = mapnikName.split('/')[-1]
    # print styleName
    if styleType == 1:
        tranPointStyle(mapnikName, "/home/shuchao/geo_app/mapnikxml/export/%s.xml" % styleName)
        cat.create_style(styleName, open("/home/shuchao/geo_app/mapnikxml/export/%s.xml" % styleName, 'r'))
    if styleType == 2:
        tranLineStyle(mapnikName, "/home/shuchao/geo_app/mapnikxml/export/%s.xml" % styleName)
        cat.create_style(styleName, open("/home/shuchao/geo_app/mapnikxml/export/%s.xml" % styleName, 'r'))
    if styleType == 3:
        tranPolyStyle(mapnikName, "/home/shuchao/geo_app/mapnikxml/export/%s.xml" % styleName)
        cat.create_style(styleName, open("/home/shuchao/geo_app/mapnikxml/export/%s.xml" % styleName, 'r'))
    return styleName

    # def serverquery(servername,workspacename = 'higis'):


    # def deletesource(resourcename,workspacename = 'higis'):
    #     ft = cat.get_resource(resourcename,workspace = workspacename)
    #     cat.delete(ft)

