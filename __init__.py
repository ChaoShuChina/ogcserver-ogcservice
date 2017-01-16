from flask import Blueprint

ogcservice_api = Blueprint('ogcservice_api', __name__)

from . import ogcservice_manager, ogcservice_view
