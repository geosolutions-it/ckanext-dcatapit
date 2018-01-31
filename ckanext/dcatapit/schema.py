#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ckanext.dcatapit.interfaces as interfaces

from ckan.common import _, ungettext
from ckan.plugins import PluginImplementations


def get_custom_config_schema(show=True):
    if show:
        return [
            {
                'name': 'ckanext.dcatapit_configpublisher_name',
                'validator': ['not_empty'],
                'element': 'input',
                'type': 'text',
                'label': _('Dataset Editor'),
                'placeholder': _('dataset editor'),
                'description': _('The responsible organization of the catalog'),
                'is_required': True
            },
            {
                'name': 'ckanext.dcatapit_configpublisher_code_identifier',
                'validator': ['not_empty'],
                'element': 'input',
                'type': 'text',
                'label': _('Catalog Organization Code'),
                'placeholder': _('IPA/IVA'),
                'description': _('The IVA/IPA code of the catalog organization'),
                'is_required': True
            },
            {
                'name': 'ckanext.dcatapit_config.catalog_issued',
                'validator': ['ignore_missing'],
                'element': 'input',
                'type': 'date',
                'label': _('Catalog Release Date'),
                'format': '%d-%m-%Y',
                'placeholder': _('catalog release date'),
                'description': _('The creation date of the catalog'),
                'is_required': False
            }
        ]
    else:
        return [
            {
                'name': 'ckanext.dcatapit_configpublisher_name',
                'validator': ['not_empty']
            },
            {
                'name': 'ckanext.dcatapit_configpublisher_code_identifier',
                'validator': ['not_empty']
            },
            {
                'name': 'ckanext.dcatapit_config.catalog_issued',
                'validator': ['ignore_missing']
            }
        ]


def get_custom_organization_schema():
	return [
	    {
		    'name': 'email',
		    'validator': ['ignore_missing'],
		    'element': 'input',
		    'type': 'email',
		    'label': _('EMail'),
		    'placeholder': _('organization email'),
		    'is_required': True
	    },
	    {
		    'name': 'telephone',
		    'validator': ['ignore_missing'],
		    'element': 'input',
		    'type': 'text',
		    'label': _('Telephone'),
		    'placeholder': _('organization telephone'),
		    'is_required': False
	    },
	    {
		    'name': 'site',
		    'validator': ['ignore_missing'],
		    'element': 'input',
		    'type': 'url',
		    'label': _('Site URL'),
		    'placeholder': _('organization site url'),
		    'is_required': False
	    },
	    {
		    'name': 'region',
		    'validator': ['ignore_missing', 'not_empty'],
		    'element': 'region',
		    'type': 'vocabulary',
		    'vocabulary_name': 'regions',
		    'label': _('Region'),
            'multiple': False,
		    'placeholder': _('region name'),
		    'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=regions&incomplete=?',
		    'is_required': False
	    },
        {
            'name': 'identifier',
            'label': _('IPA/IVA'),
            'validator': ['ignore_missing'],
            'element': 'input',
            'type': 'text',
            'is_required': False,
            'placeholder': _('organization IPA/IVA code')
        }
    ]


def get_custom_package_schema():
    package_schema = [
        {
            'name': 'identifier',
            'validator': ['not_empty', 'dcatapit_id_unique'],
            'element': 'input',
            'type': 'text',
            'label': _('Dataset Identifier'),
            'placeholder': _('dataset identifier'),
            'is_required': True,
            'help': _('package_identifier_help'),
        },
        {
            'name': 'alternate_identifier',
            'validator': ['ignore_missing', 'no_number', 'dcatapit_alternate_identifier'],
            'element': 'alternate_identifier',
            'type': 'text',
            'label': _('Other Identifier'),
            'placeholder': _('other identifier'),
            'is_required': False,
            'help': _('package_alternate_identifier_help'),
        },
        {
            'name': 'theme',
            'validator': ['not_empty'],
            'element': 'themes',
            'type': 'vocabulary',
            'vocabulary_name': 'eu_themes',
            'label': _('Dataset Themes'),
            'placeholder': _('eg. education, agriculture, energy'),
            'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=eu_themes&incomplete=?',
            'is_required': True,
            'help': _('package_theme_help'),
        },
        {
            'name': 'publisher',
            'element': 'couple',
            'label': _('Dataset Editor'),
            'is_required': True,
            'couples': [
                {
                    'name': 'publisher_name',
                    'validator': ['not_empty'],
                    'label': _('Name'),
                    'type': 'text',
                    'placeholder': _('publisher name'),
                    'localized': True
                },
                {
                    'name': 'publisher_identifier',
                    'validator': ['not_empty'],
                    'label': _('IPA/IVA'),
                    'type': 'text',
                    'placeholder': _('publisher identifier')
                }
            ],
            'help': _('package_publisher_help'),
        },
        {
            'name': 'issued',
            'validator': ['ignore_missing'],
            'element': 'input',
            'type': 'date',
            'label': _('Release Date'),
            'format': '%d-%m-%Y',
            'placeholder': _('release date'),
            'is_required': False,
            'help': _('package_issued_help'),
        },
        {
            'name': 'modified',
            'validator': ['not_empty'],
            'element': 'input',
            'type': 'date',
            'label': _('Modification Date'),
            'format': '%d-%m-%Y',
            'placeholder': _('modification date'),
            'is_required': True,
            'help': _('package_modified_help')
        },
        {
            'name': 'geographical_name',
            'validator': ['ignore_missing'],
            'element': 'vocabulary',
            'type': 'vocabulary',
            'vocabulary_name': 'places',
            'label': _('Geographical Name'),
            'placeholder': _('geographical name'),
            'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=places&incomplete=?',
            'is_required': False,
            'default': _('Organizational Unit Responsible Competence Area'),
            'help': _('package_geographical_name_help')
        },
        {
            'name': 'geographical_geonames_url',
            'validator': ['ignore_missing'],
            'element': 'geonames',
            'type': 'geonames',
            'label': _('GeoNames URL'),
            'placeholder': _('http://www.geonames.org/3175395'),
            'is_required': False,
            'help': _('package_geographical_geonames_url_help')
        },
        {
            'name': 'language',
            'validator': ['ignore_missing'],
            'element': 'vocabulary',
            'type': 'vocabulary',
            'vocabulary_name': 'languages',
            'label': _('Dataset Languages'),
            'placeholder': _('eg. italian, german, english'),
            'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=languages&incomplete=?',
            'is_required': False,
            'help': _('package_language_help')
        },
        {
            'name': 'temporal_coverage',
            'element': 'temporal_coverage',
            'label': _('Temporal Coverage'),
            'validator': ['ignore_missing', 'dcatapit_temporal_coverage'],
            'is_required': False,
            '_couples': [
                {
                    'name': 'temporal_start',
                    'label': _('Start Date'),
                    'validator': ['ignore_missing'],
                    'type': 'date',
                    'format': '%d-%m-%Y',
                    'placeholder': _('temporal coverage')
                },
                {
                    'name': 'temporal_end',
                    'label': _('End Date'),
                    'validator': ['ignore_missing'],
                    'type': 'date',
                    'format': '%d-%m-%Y',
                    'placeholder': _('temporal coverage')
                }
            ],

            'help': _('package_temporal_coverage_help')
        },

        {
            'name': 'rights_holder',
            'element': 'couple',
            'label': _('Rights Holder'),
            'is_required': False,
            'read_only': True,
            'couples': [
                {
                    'name': 'holder_name',
                    'label': _('Name'),
                    'validator': ['ignore_missing'],
                    'type': 'text',
                    'placeholder': _('rights holder of the dataset'),
                    'localized': True

                },
                {
                    'name': 'holder_identifier',
                    'label': _('IPA/IVA'),
                    'validator': ['ignore_missing'],
                    'type': 'text',
                    'placeholder': _('rights holder of the dataset')
                }
            ],
            'help': _('package_rights_holder_name_help')
        },
        {
            'name': 'frequency',
            'validator': ['not_empty'],
            'element': 'select',
            'type': 'vocabulary',
            'vocabulary_name': 'frequencies',
            'label': _('Frequency'),
            'placeholder': _('accrual periodicity'),
            'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=frequencies&incomplete=?',
            'is_required': True,
            'help': _('package_frequency_help')
        },
        {
            'name': 'is_version_of',
            'validator': ['ignore_missing'],
            'element': 'input',
            'type': 'url',
            'label': _('Version Of'),
            'placeholder': _('is version of a related dataset URI'),
            'is_required': False,
            'help': _('package_is_version_of_help')
        },
        {
            'name': 'conforms_to',
            'validator': ['ignore_missing', 'dcatapit_conforms_to'],
            'element': 'conforms_to',
            'type': 'conforms_to',
            'label': _('Conforms To'),
            'placeholder': _('conforms to'),
            'is_required': False,
            'help': _('package_conforms_to_help')
        },
	    {
		    'name': 'creator',
		    'element': 'creator',
		    'label': _('Creator'),
            'type': 'creator',
            'placeholder': '-',
            'validator': ['ignore_missing', 'dcatapit_creator'],
            'is_required': False,
            '_couples': [
                {
                    'name': 'creator_name',
                    'label': _('Name'),
                    'validator': ['ignore_missing'],
                    'type': 'text',
                    'placeholder': _('creator of the dataset'),
                    'localized': True
                },
                {
                    'name': 'creator_identifier',
                    'label': _('IPA/IVA'),
                    'validator': ['ignore_missing'],
                    'type': 'text',
                    'placeholder': _('creator of the dataset')
                }
            ],
            'help': _('package_creator_help')
        }
    ]


    for plugin in PluginImplementations(interfaces.ICustomSchema):
        extra_schema = plugin.get_custom_schema()

        for extra in extra_schema:
            extra['external'] = True

        package_schema = package_schema + extra_schema

    return package_schema

def get_custom_resource_schema():
    return [
         {
            'name': 'distribution_format',
            'validator': ['ignore_missing'],
            'element': 'select',
            'type': 'vocabulary',
            'vocabulary_name': 'filetype',
            'label': _('Distribution Format'),
            'placeholder': _('distribution format'),
            'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=filetype&incomplete=?',
            'is_required': False
        },
        {
            'name': 'license_type',
            'validator': ['ignore_missing'],
            'element': 'licenses_tree',
            'label': _('License'),
            'placeholder': _('license type'),
            'is_required': True,
            'help': _(u"""Questa proprietà si riferisce alla licenza con cui viene """
                      u"""pubblicato il dataset. Scegliere una delle due licenze """
                      u"""Creative Commons proposte.""")
        }
    ]
