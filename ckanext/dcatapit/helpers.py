import logging

import ckan.plugins.toolkit as toolkit
import ckanext.dcatapit.schema as dcatapit_schema

import ckanext.dcatapit.interfaces as interfaces

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
			localized_tag_name = interfaces.getLocalizedTagName(item)
			tag_list.append({'text': localized_tag_name, 'value': item})

		return tag_list
	except toolkit.ObjectNotFound:
		return None