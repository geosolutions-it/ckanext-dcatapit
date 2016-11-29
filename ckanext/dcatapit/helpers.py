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

def get_dcatapit_resource_schema():
    log.debug('Retrieving DCAT-AP_IT resource schema fields...')
    return dcatapit_schema.get_custom_resource_schema()

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
						tag_list.append(localized_tag_name)
			else:
				localized_tag_name = interfaces.get_localized_tag_name(item)
				tag_list.append({'text': localized_tag_name, 'value': item})

		return tag_list
	except toolkit.ObjectNotFound:
		return []

def list_to_string(_list, _format=None):
	if _list:
		_string = ''

		first_item = True
		for item in _list:
			if first_item:
				first_item = False
				element = item

				if _format:
					element = format(element, _format)

				_string = _string + element
			else:
				element = item

				if _format:
					element = format(element, _format)

				_string = _string + ', ' + item

		return _string

def couple_to_string(field_couples, pkg_dict, format=None):
	if field_couples and pkg_dict:
		_string = ''
		for couple in field_couples:
			if couple['name'] in pkg_dict:
				field_value = pkg_dict[couple['name']]
				if field_value and couple['label']: 
					_string = _string + ' ' + couple['label'] + ': ' + field_value

		return _string
	return None

def format(_string, format=None):
	##
	# TODO: manage the string format if needed
	##
	return _string

