from ckan.common import _, ungettext

def get_custom_config_schema(show=True):
	if show:
		return [
		    {
			    'name': 'ckanext.dcatapit_config.catalog_theme',
			    'validator': ['ignore_missing'],
			    'element': 'theme',
			    'type': 'vocabulary',
			    'vocabulary_name': 'eu_themes',
			    'label': _('Catalog Themes'),
			    'placeholder': _('eg. education, agriculture, energy'),
				'description': _('Themes of the catalog'),
			    'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=eu_themes&incomplete=?',
			    'is_required': False
		    },
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
			    'type': 'number',
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
			    'placeholder': _('catalog release date'),
			    'description': _('The creation date of the catalog'),
			    'is_required': False
		    }
		]
	else:
		return [
		    {
			    'name': 'ckanext.dcatapit_config.catalog_theme',
			    'validator': ['ignore_missing']
		    },
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
		    'validator': ['not_empty'],
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
	    }
	]

def get_custom_package_schema():
	return [
	    {
		    'name': 'dataset_identifier',
		    'validator': ['not_empty'],
		    'element': 'input',
		    'type': 'text',
		    'label': _('Dataset Identifier'),
		    'placeholder': _('dataset identifier'),
		    'is_required': True
	    },
	    {
		    'name': 'other_identifier',
		    'validator': ['ignore_missing'],
		    'element': 'input',
		    'type': 'text',
		    'label': _('Other Identifier'),
		    'placeholder': _('other identifier'),
		    'is_required': False
	    },
	    {
		    'name': 'theme',
		    'validator': ['not_empty'],
		    'element': 'theme',
		    'type': 'vocabulary',
		    'vocabulary_name': 'eu_themes',
		    'label': _('Dataset Themes'),
		    'placeholder': _('eg. education, agriculture, energy'),
		    'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=eu_themes&incomplete=?',
		    'is_required': True
	    },
	    {
		    'name': 'sub_theme',
		    'ignore': True,
		    'validator': ['ignore_missing'],
		    'element': 'theme',
		    'type': 'vocabulary',
		    'vocabulary_name': 'eurovoc',
		    'label': _('Sub Theme'),
		    'placeholder': _('sub theme of the dataset'),
			'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=eurovoc&incomplete=?',
		    'is_required': False
	    },
	    {
		    'name': 'publisher',
		    'validator': ['ignore_missing', 'couple_validator'],
		    'element': 'couple',
		    'type': 'text',
		    'label': _('Dataset Editor'),
		    'placeholder': _('dataset editor'),
		    'is_required': False,
		    'couples': [
		    	{
		    		'name': 'publisher_name',
		    		'label': _('Name')
		    	},
			    {
		    		'name': 'publisher_code_identified',
		    		'label': _('IPA/IVA')
		    	}
		    ]
	    },
	    {
		    'name': 'issued',
		    'validator': ['ignore_missing'],
		    'element': 'input',
		    'type': 'date',
		    'label': 'Release Date',
		    'placeholder': _('release date'),
		    'is_required': False
	    },
	    {
		    'name': 'modified',
		    'validator': ['not_empty'],
		    'element': 'input',
		    'type': 'date',
		    'label': _('Modification Date'),
		    'placeholder': _('modification date'),
		    'is_required': True
	    },
	    {
		    'name': 'geographical_coverage',
		    'validator': ['ignore_missing'],
		    'element': 'theme',
		    'type': 'vocabulary',
		    'vocabulary_name': 'places',
		    'label': _('Geographical Coverage'),
		    'placeholder': _('geographical coverage'),
		    'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=places&incomplete=?',
		    'is_required': False
	    },
	    {
		    'name': 'language',
		    'validator': ['ignore_missing'],
		    'element': 'theme',
		    'type': 'vocabulary',
		    'vocabulary_name': 'languages',
		    'label': _('Dataset Languages'),
		    'placeholder': _('eg. italian, german, english'),
		    'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=languages&incomplete=?',
		    'is_required': False
	    },
	    {
		    'name': 'temporal_coverage',
		    'validator': ['ignore_missing'],
		    'element': 'couple',
		    'type': 'date',
		    'label': _('Temporal Coverage'),
		    'placeholder': _('temporal coverage'),
		    'is_required': False,
		    'couples': [
		    	{
		    		'name': 'start_date',
		    		'label': _('Start Date')
		    	},
			    {
		    		'name': 'end_date',
		    		'label': _('End Date')
		    	}
		    ]
	    },
	    {
		    'name': 'accrual_periodicity',
		    'validator': ['not_empty'],
		    'element': 'select',
		    'type': 'vocabulary',
		    'vocabulary_name': 'frequencies',
		    'label': _('Frequency'),
		    'placeholder': _('accrual periodicity'),
		    'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=frequencies&incomplete=?',
		    'is_required': True
	    },
	    {
		    'name': 'is_version_of',
		    'validator': ['ignore_missing'],
		    'element': 'input',
		    'type': 'url',
		    'label': _('Version Of'),
		    'placeholder': _('is version of a related dataset URI'),
		    'is_required': False
	    },
	    {
		    'name': 'conforms_to',
		    'validator': ['ignore_missing'],
		    'element': 'input',
		    'type': 'text',
		    'label': _('Conforms To'),
		    'placeholder': _('conforms to'),
		    'is_required': False
	    },
	    {
		    'name': 'rights_holder',
		    'validator': ['not_empty', 'couple_validator'],
		    'element': 'couple',
		    'type': 'text',
		    'label': _('Rights Holder'),
		    'placeholder': _('rights holder of the dataset'),
		    'is_required': True,
		    'couples': [
		    	{
		    		'name': 'holder_name',
		    		'label': _('Name')
		    	},
			    {
		    		'name': 'holder_code_identified',
		    		'label': _('IPA/IVA')
		    	}
		    ]
	    },
	    {
		    'name': 'creator',
		    'validator': ['ignore_missing', 'couple_validator'],
		    'element': 'couple',
		    'type': 'text',
		    'label': _('Creator'),
		    'placeholder': _('creator of the dataset'),
		    'is_required': False,
		    'couples': [
		    	{
		    		'name': 'creator_name',
		    		'label': _('Name')
		    	},
			    {
		    		'name': 'creator_code_identified',
		    		'label': _('IPA/IVA')
		    	}
		    ]
	    }
	]

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
	    }
	]