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

def get_vocabulary_items(vocabulary_name, keys=None):
	try:
		tag_list = toolkit.get_action('tag_list')
		items = tag_list(data_dict={'vocabulary_id': vocabulary_name})

		tag_list = []
		for item in items:
			if keys:
				for key in keys:
					if key == item:
						localized_tag_name = interfaces.get_localized_tag_name(item)
						tag_list.append(localized_tag_name.encode('utf-8'))
			else:
				localized_tag_name = interfaces.get_localized_tag_name(item)
				tag_list.append({'text': localized_tag_name, 'value': item})

		return tag_list
	except toolkit.ObjectNotFound:
		return None