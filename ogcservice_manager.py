from abc import ABCMeta, abstractmethod
import logging
import os

from app.app_manager import App
from app.utils import util, db_utils
from app.utils import BBox, AppType
from app.models import MODEL

class ServiceInfo:
    def __init__(self, box=None, srs=None, style=None, status=None, publish_param_str=None, time_constraint=None, source_id=None):
        if srs == None:
            self.srs = ''
        else:
            self.srs = srs
        self.srid = 0
        bbox = BBox()
        if box == None:
            bbox.maxx = 180
            bbox.minx = -180
            bbox.minx = 0
            bbox.maxy = 180
            bbox.miny = -180
            bbox.miny = 0
        else:
            bbox.maxx = box[2]
            bbox.minx = box[0]
            bbox.maxy = box[3]
            bbox.miny = box[1]
        self.bbox = bbox
        if style == None:
            self.style = ''
        else:
            self.style = style
        if status == None:
            self.status = ''
        else:
            self.status = status

        if publish_param_str == None:
            self.publish_param_str = ''
        else:
            self.publish_param_str = publish_param_str

        if time_constraint == None:
            self.time_constraint = ''
        else:
            self.time_constraint = time_constraint

        if source_id == None:
            self.source_id = ''
        else:
            self.source_id = source_id

    def get_srs(self):
        # spatial reference
        return self.srs

    def get_srid(self):
        # srid
        # return self.srid
        return int(self.srs.split(':')[1])

    def get_style(self):
        # style
        return self.style

    def get_bbox(self):
        return self.bbox

    def get_status(self):
        return self.status

    def get_publish_param_str(self):
        return self.publish_param_str

    def get_time_constraint(self):
        return self.time_constraint

    def get_source_id(self):
        return self.source_id


class Service(App):
    __metaclass__ = ABCMeta

    def __init__(self,
                 user_id,
                 name,
                 app_type,
                 description=''):
        super(Service, self).__init__(user_id=user_id,
                                      name=name,
                                      app_type=app_type,
                                      description=description)

    @abstractmethod
    def register(self):
        pass

    @abstractmethod
    def delete(self):
        pass

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def add(self):
        pass

    def fill_geodata(self, service):
        ''' fill geodata meta data '''
        info = self.info
        service.srid = info.get_srid()
        service.srtext = info.get_srs()
        # service.srid = info.get_srs()
        # service.srtext = info.get_srid()
        box = info.get_bbox()
        service.domain_maxx = box.maxx
        service.domain_maxy = box.maxy
        service.domain_minx = box.minx
        service.domain_miny = box.miny
        service.style = info.get_style()
        service.status = info.get_status()
        service.publish_param_str = info.get_publish_param_str()
        service.source_id = info.get_source_id()
        service.servername = self.name
        service.time_constraint = info.get_time_constraint()


class Wms(Service):
    def __init__(self,
                 app_id=None,
                 user_id=None,
                 name=None,
                 uri=None,
                 description=''
                 ):
        super(Wms, self).__init__(user_id=user_id,
                                  name=name,
                                  app_type=AppType.WMS,
                                  description=description)
        self.app_id = app_id
        self.user = user_id
        self.app_type = AppType.WMS
        self.name = name
        self.description = description
        self.uri = uri

    def register(self):
        try:
            # spec = Specification(self.logical_name, uri, self.data_type, description=self.description)
            result = self.add()
            print 'add WMS success!'
            return result
        except Exception as e:
            print str(e)
            raise Exception('Register WMS failed.')

    def delete(self):
        pass

    def update(self):
        pass

    def add(self):
        result = {}
        wms = MODEL.Wms()
        self.fill_app_with_user_info(wms)
        # info = ServiceInfo(self.bbox, self.srs, self.service)
        info = ServiceInfo(self.bbox, self.srs, self.service, self.status, self.publish_param_str, self.time_constraint, self.source_id)
        self.info = info
        self.fill_geodata(wms)

        wms.app_type = self.app_type
        wms.layers = self.layers
        wms.workspace = self.workspace
        wms.srs = self.srs
        wms.service = self.service
        wms.version = self.version
        wms.request = self.request
        wms.width = self.width
        wms.height = self.height
        wms.format = self.format
        wms.geometry_type = self.geometry_type
        wms.label = self.label

        session = MODEL.Session()
        session.add(wms)
        session.commit()

        result.update({'app_id': str(wms.app_id), 'name': self.name})
        result.update({'bbox': [info.bbox.minx, info.bbox.miny, info.bbox.maxx, info.bbox.maxy]})
        result.update({'srs': info.get_srs()})
        result.update({'url': self.path})
        return result


class Wfs(Service):
    def __init__(self,
                 app_id=None,
                 user_id=None,
                 name=None,
                 uri=None,
                 description=''
                 ):
        super(Wfs, self).__init__(user_id=user_id,
                                  name=name,
                                  app_type=AppType.WFS,
                                  description=description)
        self.app_id = app_id
        self.user = user_id
        self.app_type = AppType.WFS
        self.name = name
        self.description = description
        self.uri = uri

    def register(self):
        try:
            # spec = Specification(self.logical_name, uri, self.data_type, description=self.description)
            result = self.add()
            print 'add WFS success!'
            return result
        except Exception as e:
            print str(e)
            raise Exception('Register WFS failed.')

    def delete(self):
        pass

    def update(self):
        pass

    def add(self):
        result = {}
        wfs = MODEL.Wfs()
        self.fill_app_with_user_info(wfs)
        # info = ServiceInfo(self.bbox, self.srs, self.service)
        info = ServiceInfo(self.bbox, self.srs, self.service, self.status, self.publish_param_str, self.time_constraint, self.source_id)
        self.info = info
        self.fill_geodata(wfs)

        wfs.app_type = self.app_type
        wfs.typename = self.typename
        wfs.service = self.service
        wfs.version = self.version
        wfs.request = self.request
        wfs.srs = self.srs
        wfs.geometry_type = self.geometry_type
        wfs.label = self.label

        session = MODEL.Session()
        session.add(wfs)
        session.commit()

        result.update({'app_id': str(wfs.app_id), 'name': self.name})
        result.update({'bbox': [info.bbox.minx, info.bbox.miny, info.bbox.maxx, info.bbox.maxy]})
        result.update({'srs': info.get_srs()})
        return result
