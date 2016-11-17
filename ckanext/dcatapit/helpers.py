import logging

import ckan.plugins.toolkit as toolkit
import ckanext.dcatapit.schema as dcatapit_schema

log = logging.getLogger(__file__)


def get_dcatapit_package_schema():
    log.debug('Retrieving DCAT-AP_IT package schema fields...')
    return dcatapit_schema.get_custom_package_schema()

def get_dcatapit_organization_schema():
    log.debug('Retrieving DCAT-AP_IT organization schema fields...')
    return dcatapit_schema.get_custom_organization_schema()

def get_dcatapit_configuration_schema():
    log.debug('Retrieving DCAT-AP_IT configuration schema fields...')
    return dcatapit_schema.get_custom_config_schema()

def getVocabularyItems(vocabulary_name):
	try:
		tag_list = toolkit.get_action('tag_list')
		items = tag_list(data_dict={'vocabulary_id': vocabulary_name})

		tag_list = []
		for item in items:
			tag_list.append({'name': item, 'value': item})

		return tag_list
	except toolkit.ObjectNotFound:
		return None