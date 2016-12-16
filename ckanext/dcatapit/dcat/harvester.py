import logging

import ckan.plugins as p

from ckanext.dcat.interfaces import IDCATRDFHarvester

from ckanext.dcatapit.dcat.profiles import LOCALISED_DICT_NAME
import ckanext.dcatapit.interfaces as interfaces

log = logging.getLogger(__name__)

class DCATAPITHarvesterPlugin(p.SingletonPlugin):

    p.implements(IDCATRDFHarvester)

    def before_download(self, url, harvest_job):
        return url, []

    def after_download(self, content, harvest_job):
        return content, []

    def before_update(self, harvest_object, dataset_dict, temp_dict):
        loc_dict = dataset_dict.pop(LOCALISED_DICT_NAME, None)
        if loc_dict:
            temp_dict['dcatapit'] = loc_dict

    def after_update(self, harvest_object, dataset_dict, temp_dict):
        dcatapit_dict = temp_dict.get('dcatapit')
        if not dcatapit_dict:
            return None

        pkg_id = dataset_dict['id']
        log.debug('Updating multilang fields for dataset %s', pkg_id)
        return self._save(pkg_id, dcatapit_dict)

    def before_create(self, harvest_object, dataset_dict, temp_dict):
        loc_dict = dataset_dict.pop(LOCALISED_DICT_NAME, None)
        if loc_dict:
            temp_dict['dcatapit'] = loc_dict

    def after_create(self, harvest_object, dataset_dict, temp_dict):
        dcatapit_dict = temp_dict.get('dcatapit')

        if not dcatapit_dict:
            return None

        pkg_id = dataset_dict['id']
        log.debug('Adding multilang fields for dataset %s', pkg_id)
        return self._save(pkg_id, dcatapit_dict)

    def _save(self, pkg_id, dcatapit_dict):
        try:
            for field, lang_dict in dcatapit_dict.iteritems():
                for lang, text in lang_dict.iteritems():
                    interfaces.upsert_package_multilang(pkg_id, field, 'package', lang, text)

        except Exception, e:
            return str(e)

        return None
