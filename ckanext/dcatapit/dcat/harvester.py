import os
import json
import logging
from ConfigParser import SafeConfigParser as ConfigParser

import ckan.plugins as p
from ckan.lib.base import config
from paste.deploy.converters import asbool



from ckanext.dcat.interfaces import IDCATRDFHarvester

from ckanext.dcatapit.dcat.profiles import LOCALISED_DICT_NAME_BASE, LOCALISED_DICT_NAME_RESOURCES
import ckanext.dcatapit.interfaces as interfaces

log = logging.getLogger(__name__)

DCATAPIT_THEMES_MAP = 'ckanext.dcatapit.nonconformant_themes_mapping.file'
DCATAPIT_THEMES_MAP_SECTION = 'terms_theme_mapping'


def _map_themes_json(fdesc):
    data = json.load(fdesc)
    out = {}
    for map_item in data['data']:
        for syn in map_item['syn']:
            try:
                out[syn].append(map_item['name'])
            except KeyError:
                out[syn] = [map_item['name']]
    return out


def _map_themes_ini(fdesc):
    c = ConfigParser()
    c.readfp(fdesc)
    out = {}
    section = 'dcatapit:{}'.format(DCATAPIT_THEMES_MAP_SECTION)
    for theme_in, themes_out in c.items(section_name, raw=True):
        out[theme_in] = [t.strip() for t in themes_out.replace('\n', ',').split(',') if t.strip()]
    return out


def map_nonconformant_themes(dataset_dict, temp_dict):
    fpath = config.get(DCATAPIT_THEMES_MAP)
    if not fpath:
        return
    if not os.path.exists(fpath):
        log.warning("Mapping themes in %s doesn't exist", fpath)
        return
    base, ext = os.path.splitext(fpath)
    if ext == '.json':
        handler = _map_themes_json
    else:
        handler = _map_themes_ini

    with open(fpath) as f:
        map_data = handler(f)
    themes = dataset_dict['extras'].get('themes') or []
    new_themes = []

    # if theme is not in mapping list, keep it
    # otherwise, replace it with mapped themes
    for theme in themes:
        map_to = map_data.get(theme)
        if map_to:
            new_themes.extend(map_to)
        else:
            new_themes.append(theme)
    return new_themes

        
class DCATAPITHarvesterPlugin(p.SingletonPlugin):

    p.implements(IDCATRDFHarvester)

    def before_download(self, url, harvest_job):
        return url, []

    def after_download(self, content, harvest_job):
        return content, []

    def before_update(self, harvest_object, dataset_dict, temp_dict):
        self._before(dataset_dict, temp_dict)

    def after_update(self, harvest_object, dataset_dict, temp_dict):
        return self._after(dataset_dict, temp_dict)

    def before_create(self, harvest_object, dataset_dict, temp_dict):
        self._before(dataset_dict, temp_dict)

    def after_create(self, harvest_object, dataset_dict, temp_dict):
        return self._after(dataset_dict, temp_dict)

    def _map_themes(self, dataset_dict, temp_dict):
        print(dataset_dict)
        new_themes = map_nonconformant_themes(dataset_dict, temp_dict)
        dataset_dict['extras']['themes'] = new_themes

    def _before(self, dataset_dict, temp_dict):
        loc_dict = dataset_dict.pop(LOCALISED_DICT_NAME_BASE, {})
        res_dict = dataset_dict.pop(LOCALISED_DICT_NAME_RESOURCES, {})
        if loc_dict or res_dict:
            temp_dict['dcatapit'] = {
                LOCALISED_DICT_NAME_BASE: loc_dict,
                LOCALISED_DICT_NAME_RESOURCES: res_dict
            }

        self._map_themes(dataset_dict, temp_dict)


    def _after(self, dataset_dict, temp_dict):
        dcatapit_dict = temp_dict.get('dcatapit')
        if not dcatapit_dict:
            return None

        base_dict = dcatapit_dict[LOCALISED_DICT_NAME_BASE]
        if base_dict:
            pkg_id = dataset_dict['id']
            err = self._save_package_multilang(pkg_id, base_dict)
            if err:
                return err

        resources_dict = dcatapit_dict[LOCALISED_DICT_NAME_RESOURCES]
        if resources_dict:
            err = self._save_resources_multilang(pkg_id, resources_dict)
            if err:
                return err

        ##
        # Managing Solr indexes for harvested package dict
        ## 
        interfaces.update_solr_package_indexes(dataset_dict)

        return None

    def _save_package_multilang(self, pkg_id, base_dict):
        try:
            for field, lang_dict in base_dict.iteritems():
                for lang, text in lang_dict.iteritems():
                    interfaces.upsert_package_multilang(pkg_id, field, 'package', lang, text)

        except Exception, e:
            return str(e)

        return None

    def _save_resources_multilang(self, pkg_id, resources_dict):
        try:
            uri_id_mapping = self._get_resource_uri_id_mapping(pkg_id)

            for res_uri, res_dict in resources_dict.iteritems():
                res_id = uri_id_mapping.get(res_uri, None)
                if not res_id:
                    log.warn("Could not find resource id for URI %s", res_uri)
                    continue
                for field, lang_dict in res_dict.iteritems():
                    for lang, text in lang_dict.iteritems():
                        interfaces.upsert_resource_multilang(res_id, field, lang, text)

        except Exception, e:
            return str(e)

        return None

    def _get_resource_uri_id_mapping(self, pkg_id):
        ret = {}
#        log.info("DATASET DICT: %s", dataset_dict)
        dataset = p.toolkit.get_action('package_show')({}, {'id': pkg_id})
#        log.info("DATASET ----------- %s", dataset)
        for resource in dataset.get('resources', []): 
            res_id = resource.get('id', None)
            res_uri = resource.get('uri', None)
            if res_id and res_uri:
                log.debug('Mapping resource id %s to URI "%s"', res_id, res_uri)
                ret[res_uri] = res_id
            else:
                log.warn("Can't map URI for resource \"%s\"", resource.get('name', '---'))

        return ret
