import logging

from ckan import logic
from ckan import lib

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import ckan.plugins as plugins

import ckanext.dcatapit.validators as validators
import ckanext.dcatapit.schema as dcatapit_schema
import ckanext.dcatapit.helpers as helpers

log = logging.getLogger(__file__)

from routes.mapper import SubMapper, Mapper as _Mapper


class DCATAPITPackagePlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):

	# IDatasetForm
    plugins.implements(plugins.IDatasetForm)
	# IConfigurer
    plugins.implements(plugins.IConfigurer)
    # IValidators
    plugins.implements(plugins.IValidators)
    # ITemplateHelpers
    plugins.implements(plugins.ITemplateHelpers)
    # IRoutes
    plugins.implements(plugins.IRoutes, inherit=True)
    
    # ------------- IRoutes ---------------#
    
    def before_map(self, map):
        GET = dict(method=['GET'])

        # /api/util ver 1, 2 or none
        with SubMapper(map, controller='ckanext.dcatapit.controllers.api:DCATAPITApiController', path_prefix='/api{ver:/1|/2|}',
                       ver='/1') as m:
            m.connect('/util/vocabulary/autocomplete', action='vocabulary_autocomplete',
                      conditions=GET)
        return map
    
    # ------------- IConfigurer ---------------#

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'ckanext-dcatapit')

    # ------------- IDatasetForm ---------------#

    def _modify_package_schema(self, schema):
        for field in dcatapit_schema.get_custom_package_schema():
            if 'ignore' in field and field['ignore'] == True:
                continue

            validators = []
            for validator in field['validator']:
                validators.append(toolkit.get_validator(validator))

            converters = [toolkit.get_converter('convert_to_extras')]

            schema.update({
                field['name']: validators + converters
            })

    	schema.update({
            'notes': [
            	toolkit.get_validator('not_empty')
            ]
        })

        log.debug("Schema updated for DCAT_AP-TI:  %r", schema)

        return schema

    def create_package_schema(self):
        schema = super(DCATAPITPackagePlugin, self).create_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def update_package_schema(self):
        schema = super(DCATAPITPackagePlugin, self).update_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def show_package_schema(self):
        schema = super(DCATAPITPackagePlugin, self).show_package_schema()
        
        for field in dcatapit_schema.get_custom_package_schema():
            if 'ignore' in field and field['ignore'] == True:
                continue

            validators = []
            for validator in field['validator']:
                validators.append(toolkit.get_validator(validator))

            converters = [toolkit.get_converter('convert_from_extras')]

            schema.update({
                field['name']: converters + validators
            })

        schema.update({
            'notes': [
                toolkit.get_validator('not_empty')
            ]
        })

        log.debug("Schema updated for DCAT_AP-TI:  %r", schema)

        return schema

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True
		
    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []

    # ------------- IValidators ---------------#

    def get_validators(self):
		return {
            'couple_validator': validators.couple_validator
        }

    # ------------- ITemplateHelpers ---------------#

    def get_helpers(self):
        return {
            'get_dcatapit_package_schema': helpers.get_dcatapit_package_schema,
            'getVocabularyItems': helpers.getVocabularyItems
        }


class DCATAPITOrganizationPlugin(plugins.SingletonPlugin, toolkit.DefaultGroupForm):

    # IConfigurer
    plugins.implements(plugins.IConfigurer)
    # ITemplateHelpers
    plugins.implements(plugins.ITemplateHelpers)
    # IGroupForm
    plugins.implements(plugins.IGroupForm, inherit=True)
    
    # ------------- IConfigurer ---------------#

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'ckanext-dcatapit')

    # ------------- ITemplateHelpers ---------------#

    def get_helpers(self):
        return {
            'get_dcatapit_organization_schema': helpers.get_dcatapit_organization_schema
        }

    # ------------- IGroupForm ---------------#

    def group_form(self):
        return 'organization/new_organization_form.html'

    def setup_template_variables(self, context, data_dict):
        pass

    def new_template(self):
        return 'organization/new.html'

    def about_template(self):
        return 'organization/about.html'

    def index_template(self):
        return 'organization/index.html'

    def admins_template(self):
        return 'organization/admins.html'

    def bulk_process_template(self):
        return 'organization/bulk_process.html'

    def read_template(self):
        return 'organization/read.html'

    # don't override history_template - use group template for history

    def edit_template(self):
        return 'organization/edit.html'

    def activity_template(self):
        return 'organization/activity_stream.html'

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # group types not handled by any other IGroupForm plugin.
        return False

    def group_types(self):
        # This plugin doesn't handle any special group types, it just
        # registers itself as the default (above).
        return ['organization']

    def form_to_db_schema_options(self, options):
        ''' This allows us to select different schemas for different
        purpose eg via the web interface or via the api or creation vs
        updating. It is optional and if not available form_to_db_schema
        should be used.
        If a context is provided, and it contains a schema, it will be
        returned.
        '''
        schema = options.get('context', {}).get('schema', None)
        if schema:
            return schema

        if options.get('api'):
            if options.get('type') == 'create':
                return self.form_to_db_schema_api_create()
            else:
                return self.form_to_db_schema_api_update()
        else:
            return self.form_to_db_schema()

    def form_to_db_schema_api_create(self):
        schema = super(DCATAPITOrganizationPlugin, self).form_to_db_schema_api_create()
        schema = self._modify_group_schema(schema)
        return schema

    def form_to_db_schema_api_update(self):
        schema = super(DCATAPITOrganizationPlugin, self).form_to_db_schema_api_update()
        schema = self._modify_group_schema(schema)
        return schema

    def form_to_db_schema(self):
        schema = super(DCATAPITOrganizationPlugin, self).form_to_db_schema()
        schema = self._modify_group_schema(schema)
        return schema

    def _modify_group_schema(self, schema):
        for field in dcatapit_schema.get_custom_organization_schema():

            validators = []
            for validator in field['validator']:
                validators.append(toolkit.get_validator(validator))

            schema.update({
                field['name']: validators + [
                    toolkit.get_converter('convert_to_extras')
                ]
            })

        return schema

    def db_to_form_schema(self):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''
        schema = self.default_show_group_schema()

        for field in dcatapit_schema.get_custom_organization_schema():

            validators = []
            for validator in field['validator']:
                validators.append(toolkit.get_validator(validator))

            schema.update({
                field['name']: [
                    toolkit.get_converter('convert_from_extras')
                ] + validators
            })

        return schema

    def default_show_group_schema(self):
        schema = logic.schema.default_group_schema()

        # make default show schema behave like when run with no validation
        schema['num_followers'] = []
        schema['created'] = []
        schema['display_name'] = []
        #schema['extras'] = {'__extras': [ckan.lib.navl.validators.keep_extras]}
        schema['package_count'] = []
        schema['packages'] = {'__extras': [lib.navl.validators.keep_extras]}
        schema['revision_id'] = []
        schema['state'] = []
        schema['users'] = {'__extras': [lib.navl.validators.keep_extras]}

        return schema

class DCATAPITConfigurerPlugin(plugins.SingletonPlugin):

    # IConfigurer
    plugins.implements(plugins.IConfigurer)
    # ITemplateHelpers
    plugins.implements(plugins.ITemplateHelpers)
    
    # ------------- IConfigurer ---------------#

    def update_config(self, config):
        # Add extension templates directory
        toolkit.add_template_directory(config, 'templates')

    def update_config_schema(self, schema):        
        for field in dcatapit_schema.get_custom_config_schema():

            validators = []
            for validator in field['validator']:
                validators.append(toolkit.get_validator(validator))

            schema.update({
                field['name']: validators
            })

        return schema

    # ------------- ITemplateHelpers ---------------#

    def get_helpers(self):
        return {
            'get_dcatapit_configuration_schema': helpers.get_dcatapit_configuration_schema
        }
