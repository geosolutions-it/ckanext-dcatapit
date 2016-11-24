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
		return None

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

def couple_to_string(field_couples, couple_value, format=None):
	if couple_value and ',' in couple_value:
		items = couple_value.split(',')

		_string = field_couples[0]['label'] + ': ' + items[0]
		_string = _string + ' ' + field_couples[1]['label'] + ': ' + items[1]

		return _string

def format(_string, format=None):
	if _string:
		return _string

