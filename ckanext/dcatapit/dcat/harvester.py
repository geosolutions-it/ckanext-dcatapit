import logging
import json

import ckan.plugins as p
from ckan.lib.munge import munge_name

from ckanext.dcat.interfaces import IDCATRDFHarvester

from ckanext.dcatapit.dcat.profiles import LOCALISED_DICT_NAME_BASE, LOCALISED_DICT_NAME_RESOURCES
import ckanext.dcatapit.interfaces as interfaces
from ckanext.dcatapit import helpers as dcatapit_helpers
from ckanext.dcatapit.mapping import map_nonconformant_groups

log = logging.getLogger(__name__)

        
class DCATAPITHarvesterPlugin(p.SingletonPlugin):

    p.implements(IDCATRDFHarvester, inherit=True)

    def before_download(self, url, harvest_job):
        return url, []

    def update_session(self, session):
        return session

    def after_download(self, content, harvest_job):
        return content, []

    def before_update(self, harvest_object, dataset_dict, temp_dict):
        self._before(dataset_dict, temp_dict, harvest_object)

    def after_update(self, harvest_object, dataset_dict, temp_dict):
        return self._after(dataset_dict, temp_dict)

    def before_create(self, harvest_object, dataset_dict, temp_dict):
        self._before(dataset_dict, temp_dict, harvest_object)

    def after_create(self, harvest_object, dataset_dict, temp_dict):
        return self._after(dataset_dict, temp_dict)

    def _before(self, dataset_dict, temp_dict, job):
        loc_dict = dataset_dict.pop(LOCALISED_DICT_NAME_BASE, {})
        res_dict = dataset_dict.pop(LOCALISED_DICT_NAME_RESOURCES, {})
        if loc_dict or res_dict:
            temp_dict['dcatapit'] = {
                LOCALISED_DICT_NAME_BASE: loc_dict,
                LOCALISED_DICT_NAME_RESOURCES: res_dict
            }
        try:
            self._handle_rights_holder(dataset_dict, temp_dict, job)
        except Exception, err:
            raise

    def _handle_rights_holder(self, dataset_dict, temp_dict, job):
        try:
            config = json.loads(job.source.config) if job.source.config else {}
        except (TypeError, ValueError,), err:
            log.warning("Cannot parse job config to get rights holder: %s", err, exc_info=err)
            config = {}

        orgs_conf = config.get('remote_orgs', None)
        ctx = {'ignore_auth': True,
               'user': self._get_user_name()}

        if orgs_conf in ('create',):
            holder_name = dataset_dict.get('holder_name', None)
            holder_identifier = dataset_dict.get('holder_identifier', None)

            if holder_identifier and holder_name:

                org = dcatapit_helpers.get_organization_by_identifier(ctx, holder_identifier)
                if not org:
                    org_dict = {'identifier': holder_identifier,
                                'name': munge_name(holder_name),
                                'title': holder_name}
                    org = p.toolkit.get_action('organization_create')(context=ctx, data_dict=org_dict)

                dataset_dict['owner_org'] = org['name']
                # remove holder fields, as this info will be handled in org 
                dataset_dict.pop('holder_name', None)
                dataset_dict.pop('holder_identifier', None)

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

    def _get_user_name(self):
        if getattr(self, '_user_name', None):
            return self._user_name

        user = p.toolkit.get_action('get_site_user')(
            {'ignore_auth': True, 'defer_commit': True},
            {})
        self._user_name = user['name']

        return self._user_name
