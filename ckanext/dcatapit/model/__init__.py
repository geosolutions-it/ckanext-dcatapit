# this is a namespace package
try:
    import pkg_resources
    pkg_resources.declare_namespace(__name__)
except ImportError:
    import pkgutil
    __path__ = pkgutil.extend_path(__path__, __name__)

from ckanext.dcatapit.model.dcatapit_model import *
from ckanext.dcatapit.model.license import *
from ckanext.dcatapit.model.subtheme import *
