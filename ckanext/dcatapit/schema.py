
def get_custom_config_schema():
	return [
	    {
		    'name': 'ckanext.dcatapit_config.catalog_theme',
		    'validator': ['ignore_missing'],
		    'element': 'theme',
		    'type': 'vocabulary',
		    'vocabulary_name': 'eu_themes',
		    'label': 'Catalog Themes',
		    'placeholder': 'eg. economy, mental health, government',
		    'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=eu_themes&incomplete=?',
		    'description': 'Themes of the catalog',
		    'is_required': False
	    },
	    {
		    'name': 'ckanext.dcatapit_configpublisher_name',
		    'validator': ['not_empty'],
		    'element': 'input',
		    'type': 'text',
		    'label': 'Dataset Editor',
		    'placeholder': 'dataset editor',
		    'description': 'The responsible organization of the catalog',
		    'is_required': True
	    },
	    {
		    'name': 'ckanext.dcatapit_configpublisher_code_identifier',
		    'validator': ['not_empty'],
		    'element': 'input',
		    'type': 'number',
		    'label': 'Catalog Organization Code',
		    'placeholder': 'IPA/IVA',
		    'description': 'The IVA/IPA code of the catalog organization',
		    'is_required': True
	    },
	    {
		    'name': 'ckanext.dcatapit_config.catalog_issued',
		    'validator': ['ignore_missing'],
		    'element': 'input',
		    'type': 'date',
		    'label': 'Catalog Release Date',
		    'placeholder': 'catalog release date',
		    'description': 'The creation date of the catalog',
		    'is_required': False
	    }
	]


def get_custom_organization_schema():
	return [
	    {
		    'name': 'email',
		    'validator': ['not_empty'],
		    'element': 'input',
		    'type': 'email',
		    'label': 'EMail',
		    'placeholder': 'organization email',
		    'is_required': True
	    },
	    {
		    'name': 'telephone',
		    'validator': ['ignore_missing'],
		    'element': 'input',
		    'type': 'text',
		    'label': 'Telephone',
		    'placeholder': 'organization telephone',
		    'is_required': False
	    },
	    {
		    'name': 'site',
		    'validator': ['ignore_missing'],
		    'element': 'input',
		    'type': 'url',
		    'label': 'Site URL',
		    'placeholder': 'organization site url',
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
		    'label': 'Dataset Identifier',
		    'placeholder': 'dataset identifier',
		    'is_required': True
	    },
	    {
		    'name': 'other_identifier',
		    'validator': ['ignore_missing'],
		    'element': 'input',
		    'type': 'text',
		    'label': 'Other Identifier',
		    'placeholder': 'other identifier',
		    'is_required': False
	    },
	    {
		    'name': 'theme',
		    'validator': ['not_empty'],
		    'element': 'theme',
		    'type': 'vocabulary',
		    'vocabulary_name': 'eu_themes',
		    'label': 'Dataset Themes',
		    'placeholder': 'eg. economy, mental health, government',
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
		    'label': 'Sub Theme',
		    'placeholder': 'sub theme of the dataset',
			'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=eurovoc&incomplete=?',
		    'is_required': False
	    },
	    {
		    'name': 'publisher',
		    'validator': ['ignore_missing', 'couple_validator'],
		    'element': 'couple',
		    'type': 'text',
		    'label': 'Dataset Editor',
		    'placeholder': 'dataset editor',
		    'is_required': False,
		    'couples': [
		    	{
		    		'name': 'publisher_name',
		    		'label': 'Name'
		    	},
			    {
		    		'name': 'publisher_code_identified',
		    		'label': 'IPA/IVA'
		    	}
		    ]
	    },
	    {
		    'name': 'issued',
		    'validator': ['ignore_missing'],
		    'element': 'input',
		    'type': 'date',
		    'label': 'Release Date',
		    'placeholder': 'release date',
		    'is_required': False
	    },
	    {
		    'name': 'modified',
		    'validator': ['not_empty'],
		    'element': 'input',
		    'type': 'date',
		    'label': 'Modification Date',
		    'placeholder': 'modification date',
		    'is_required': True
	    },
	    {
		    'name': 'geographical_coverage',
		    'validator': ['ignore_missing'],
		    'element': 'theme',
		    'type': 'vocabulary',
		    'vocabulary_name': 'places',
		    'label': 'Geographical Coverage',
		    'placeholder': 'geographical coverage',
		    'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=places&incomplete=?',
		    'is_required': False
	    },
	    {
		    'name': 'language',
		    'validator': ['ignore_missing'],
		    'element': 'theme',
		    'type': 'vocabulary',
		    'vocabulary_name': 'languages',
		    'label': 'Dataset Languages',
		    'placeholder': 'eg. italian, german, english',
		    'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=languages&incomplete=?',
		    'is_required': False
	    },
	    {
		    'name': 'temporal_coverage',
		    'validator': ['ignore_missing', 'couple_validator'],
		    'element': 'couple',
		    'type': 'date',
		    'label': 'Temporal Coverage',
		    'placeholder': 'temporal coverage',
		    'is_required': False,
		    'couples': [
		    	{
		    		'name': 'start_date',
		    		'label': 'Start Date'
		    	},
			    {
		    		'name': 'end_date',
		    		'label': 'End Date'
		    	}
		    ]
	    },
	    {
		    'name': 'accrual_periodicity',
		    'validator': ['not_empty'],
		    'element': 'select',
		    'type': 'vocabulary',
		    'vocabulary_name': 'frequencies',
		    'label': 'Frequency',
		    'placeholder': 'accrual periodicity',
		    'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=frequencies&incomplete=?',
		    'is_required': True
	    },
	    {
		    'name': 'is_version_of',
		    'validator': ['ignore_missing'],
		    'element': 'input',
		    'type': 'url',
		    'label': 'Version Of',
		    'placeholder': 'is version of a related dataset URI',
		    'is_required': False
	    },
	    {
		    'name': 'conforms_to',
		    'validator': ['ignore_missing'],
		    'element': 'input',
		    'type': 'text',
		    'label': 'Conforms To',
		    'placeholder': 'conforms to',
		    'is_required': False
	    },
	    {
		    'name': 'rights_holder',
		    'validator': ['not_empty', 'couple_validator'],
		    'element': 'couple',
		    'type': 'text',
		    'label': 'Rights Holder',
		    'placeholder': 'rights holder of the dataset',
		    'is_required': True,
		    'couples': [
		    	{
		    		'name': 'holder_name',
		    		'label': 'Name'
		    	},
			    {
		    		'name': 'holder_code_identified',
		    		'label': 'IPA/IVA'
		    	}
		    ]
	    },
	    {
		    'name': 'creator',
		    'validator': ['ignore_missing', 'couple_validator'],
		    'element': 'couple',
		    'type': 'text',
		    'label': 'Creator',
		    'placeholder': 'creator of the dataset',
		    'is_required': False,
		    'couples': [
		    	{
		    		'name': 'creator_name',
		    		'label': 'Name'
		    	},
			    {
		    		'name': 'creator_code_identified',
		    		'label': 'IPA/IVA'
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
		    'label': 'Distribution Format',
		    'placeholder': 'distribution format',
		    'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=filetype&incomplete=?',
		    'is_required': False
	    }
	]