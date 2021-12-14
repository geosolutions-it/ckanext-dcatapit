#!/usr/bin/env python3

import json

from ckanext.dcatapit.harvesters.utils import map_ckan_license
from ckanext.dcatapit.mapping import map_nonconformant_groups
from ckanext.harvest.harvesters.ckanharvester import CKANHarvester


class CKANMappingHarvester(CKANHarvester):

    def info(self):
        return {
            'name': 'CKAN-DCATAPIT',
            'title': 'CKAN harvester for DCATAPIT',
            'description': 'Special version of CKANHarvester, which will map groups to themes',
            'form_config_interface': 'Text'
        }

    def import_stage(self, harvest_object):
        map_nonconformant_groups(harvest_object)
        data = map_ckan_license(harvest_object=harvest_object)
        harvest_object.content = json.dumps(data)
        return super(CKANMappingHarvester, self).import_stage(harvest_object)
