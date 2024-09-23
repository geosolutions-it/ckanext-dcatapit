import datetime
import json
import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan import lib, logic
from ckan.common import config
from flask import Blueprint

# from routes.mapper import SubMapper
from ckanext.dcatapit.controllers.api import get_blueprints

import ckanext.dcatapit.helpers as helpers
import ckanext.dcatapit.interfaces as interfaces
import ckanext.dcatapit.schema as dcatapit_schema
import ckanext.dcatapit.validators as validators
from ckanext.dcatapit.commands import dcatapit as dcatapit_cli
from ckanext.dcatapit.controllers.harvest import HarvesterController
from ckanext.dcatapit.helpers import get_org_context
from ckanext.dcatapit.mapping import populate_theme_groups, theme_name_to_uri
from ckanext.dcatapit.mapping import populate_theme_groups
from ckanext.dcatapit.controllers.thesaurus import ThesaurusController, get_thesaurus_admin_page, update_vocab_admin
from ckanext.dcatapit.model.license import License
from ckanext.dcatapit.schema import FIELD_THEMES_AGGREGATE

log = logging.getLogger(__name__)

try:
    from ckan.lib.plugins import DefaultTranslation
except ImportError:
    class DefaultTranslation():
        pass

LOCALIZED_RESOURCES_KEY = 'ckanext.dcatapit.localized_resources'
LOCALIZED_RESOURCES_ENABLED = toolkit.asbool(config.get(LOCALIZED_RESOURCES_KEY, 'False'))
MLR = None
if LOCALIZED_RESOURCES_ENABLED:
    from ckanext.multilang.plugin import MultilangResourcesAux
    MLR = MultilangResourcesAux()
    # admin chose to enable the localized resource, so let the ImportError out


class DCATAPITPackagePlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm, DefaultTranslation):

    plugins.implements(plugins.IClick)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.ITemplateHelpers)
    # IRoutes is deprecated for CKAN 2.10
    # plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IBlueprint, inherit=True)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IFacets, inherit=True)
    plugins.implements(plugins.ITranslation, inherit=True)



    # IClick

    def get_commands(self):
        return dcatapit_cli.get_commands()

    # ------------- ITranslation -------------4--#

    def i18n_domain(self):
        return 'ckanext-dcatapit'

    '''
    # ------------- IRoutes ---------------#

    def before_map(self, map):
        GET = dict(method=['GET'])

        # /api/util ver 1, 2 or none
        with SubMapper(map, controller='ckanext.dcatapit.controllers.api:DCATAPITApiController', path_prefix='/api{ver:/1|/2|}',
                       ver='/1') as m:
            m.connect('/util/vocabulary/autocomplete', action='vocabulary_autocomplete',
                      conditions=GET)
        return map
    '''

    #--------------IBlueprint -----------------#
    # from ckanext.dcatapit.controllers.api import dcatapit_blp
    # from flask_smorest import Api

    # ckan.config["api"] = "/util/vocabulary/autocomplete" 
    # api = Api(ckan)
    #api.register_blueprint(dcatapit_blp)


    def get_blueprint(self):
        return get_blueprints()

    # ------------- IConfigurer ---------------#

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'ckanext-dcatapit')

    # ------------- IDatasetForm ---------------#

    def _update_schema_field(self, schema, field):
        validators = [toolkit.get_validator(v) for v in field['validator']]
        validators.append(toolkit.get_converter('convert_to_extras'))

        schema[field['name']] = validators

    def _modify_package_schema(self, schema):
        # Package schema
        for field in dcatapit_schema.get_custom_package_schema():
            if field.get('ignore'):
                continue

            if 'couples' in field:
                for couple in field['couples']:
                    self._update_schema_field(schema, couple)
            else:
                self._update_schema_field(schema, field)

        schema['notes'] = [toolkit.get_validator('not_empty')]

        # ignore theme extra fields
        junk = schema.get('__junk', [])
        junk.append(toolkit.get_validator('dcatapit_remove_theme'))
        schema['__junk'] = junk

        # Resource schema
        for field in dcatapit_schema.get_custom_resource_schema():
            if field.get('ignore'):
                continue

            validators = []
            for validator in field['validator']:
                validators.append(toolkit.get_validator(validator))

            schema['resources'].update({
                field['name']: validators
            })

        # conditionally include schema fields from MultilangResourcesPlugin
        if MLR:
            schema = MLR.update_schema(schema)

        return schema

    def create_package_schema(self):
        schema = super(DCATAPITPackagePlugin, self).create_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def update_package_schema(self):
        schema = super(DCATAPITPackagePlugin, self).update_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def update_show_schema_field(self, schema, field):
        validators = []
        for validator in field['validator']:
            validators.append(toolkit.get_validator(validator))

        converters = [toolkit.get_converter('convert_from_extras')]

        schema.update({
            field['name']: converters + validators
        })

    def show_package_schema(self):
        schema = super(DCATAPITPackagePlugin, self).show_package_schema()

        ##
        # Getting custom package schema
        ##

        for field in dcatapit_schema.get_custom_package_schema():
            if 'ignore' in field and field['ignore'] == True:
                continue

            if 'couples' in field:
                for couple in field['couples']:
                    self.update_show_schema_field(schema, couple)
            else:
                self.update_show_schema_field(schema, field)

        schema.update({
            'notes': [
                toolkit.get_validator('not_empty')
            ]
        })

        ##
        # Getting custom resource schema
        ##

        for field in dcatapit_schema.get_custom_resource_schema():
            if 'ignore' in field and field['ignore'] == True:
                continue

            validators = []
            for validator in field['validator']:
                validators.append(toolkit.get_validator(validator))

            schema['resources'].update({
                field['name']: validators
            })

        # conditionally include schema fields from MultilangResourcesPlugin
        if MLR:
            schema = MLR.update_schema(schema)

        return schema

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []

    if MLR:
        def read_template(self):
            return MLR.read_template()

        def edit_template(self):
            return MLR.edit_template()

        def resource_form(self):
            return MLR.resource_form()

    # ------------- IValidators ---------------#

    def get_validators(self):
        return {
            'couple_validator': validators.couple_validator,
            'no_number': validators.no_number,
            'dcatapit_id_unique': validators.dcatapit_id_unique,
            'dcatapit_conforms_to': validators.dcatapit_conforms_to,
            'dcatapit_alternate_identifier': validators.dcatapit_alternate_identifier,
            'dcatapit_creator': validators.dcatapit_creator,
            'dcatapit_temporal_coverage': validators.dcatapit_temporal_coverage,
            'dcatapit_subthemes': validators.dcatapit_subthemes,
            'dcatapit_copy_to_context': validators.dcatapit_copy_to_context,
            'dcatapit_remove_theme': validators.dcatapit_remove_theme,
        }

    # ------------- ITemplateHelpers ---------------#

    def get_helpers(self):
        dcatapit_helpers = {
            'get_dcatapit_package_schema': helpers.get_dcatapit_package_schema,
            'get_vocabulary_items': helpers.get_vocabulary_items,
            'get_vocabulary_item': helpers.get_vocabulary_item,
            'get_dcatapit_resource_schema': helpers.get_dcatapit_resource_schema,
            'list_to_string': helpers.list_to_string,
            'couple_to_html': helpers.couple_to_html,
            'couple_to_string': helpers.couple_to_string,
            'couple_to_dict': helpers.couple_to_dict,
            'format': helpers.format,
            'validate_dateformat': helpers.validate_dateformat,
            'get_localized_field_value': helpers.get_localized_field_value,
            'get_package_resource_dcatapit_format_list': helpers.get_package_resource_dcatapit_format_list,
            'get_resource_licenses_tree': helpers.get_resource_licenses_tree,
            'get_dcatapit_license': helpers.get_dcatapit_license,
            'load_json_or_list': helpers.load_json_or_list,
            'get_geonames_config': helpers.get_geonames_config,
            'load_dcatapit_subthemes': helpers.dcatapit_string_to_localized_aggregated_themes,
            'get_dcatapit_subthemes': helpers.get_dcatapit_subthemes,
            'dump_dcatapit_subthemes': helpers.dcatapit_string_to_aggregated_themes,
            'get_localized_subtheme': helpers.get_localized_subtheme,
            'dcatapit_enable_form_tabs': helpers.get_enable_form_tabs,
            'dcatapit_get_icustomschema_fields': helpers.get_icustomschema_fields,
        }

        if MLR:
            dcatapit_helpers.update(MLR.get_helpers())
        return dcatapit_helpers

    # ------------- IPackageController ---------------#

    def after_create(self, context, pkg_dict):
        # During the harvest the get_lang() is not defined
        lang = interfaces.get_language()
        otype = pkg_dict.get('type')
        if lang and otype == 'dataset':
            for extra in pkg_dict.get('extras') or []:
                for field in dcatapit_schema.get_custom_package_schema():

                    couples = field.get('couples', [])
                    if couples and len(couples) > 0:
                        for couple in couples:
                            if extra.get('key') == couple.get('name', None) and couple.get('localized', False) == True:
                                log.debug(':::::::::::::::Localizing custom schema field: %r', couple['name'])
                                # Create the localized field recorcd
                                self.create_loc_field(extra, lang, pkg_dict.get('id'))
                    else:
                        if extra.get('key') == field.get('name', None) and field.get('localized', False) == True:
                            log.debug(':::::::::::::::Localizing custom schema field: %r', field['name'])
                            # Create the localized field record
                            self.create_loc_field(extra, lang, pkg_dict.get('id'))

    def after_update(self, context, pkg_dict):
        # During the harvest the get_lang() is not defined
        lang = interfaces.get_language()
        otype = pkg_dict.get('type')

        if lang and otype == 'dataset':
            for extra in pkg_dict.get('extras') or []:
                for field in dcatapit_schema.get_custom_package_schema():
                    couples = field.get('couples', [])
                    if couples and len(couples) > 0:
                        for couple in couples:
                            self.update_loc_field(extra, pkg_dict.get('id'), couple, lang)
                    else:
                        self.update_loc_field(extra, pkg_dict.get('id'), field, lang)

    def before_index(self, dataset_dict):
        '''
        Insert `dcat_theme` into solr
        '''

        extra_theme = dataset_dict.get(f'extras_{FIELD_THEMES_AGGREGATE}', None) or ''
        aggr_themes = helpers.dcatapit_string_to_aggregated_themes(extra_theme)

        search_terms = [t['theme'] for t in aggr_themes]
        if search_terms:
            dataset_dict['dcat_theme'] = search_terms

        search_subthemes = []
        for t in aggr_themes:
            search_subthemes.extend(t.get('subthemes') or [])

        if search_subthemes:
            dataset_dict['dcat_subtheme'] = search_subthemes
            localized_subthemes = interfaces.get_localized_subthemes(search_subthemes)
            for lang, subthemes in localized_subthemes.items():
                dataset_dict['dcat_subtheme_{}'.format(lang)] = subthemes

        ddict = json.loads(dataset_dict['data_dict'])
        resources = ddict.get('resources') or []
        _licenses = list(set([r.get('license_type') for r in resources if r.get('license_type')]))

        for l in _licenses:
            lic = License.get(l)
            if lic:
                for loclic in lic.get_names():
                    lname = loclic['name']
                    lang = loclic['lang']
                    if lname:
                        dataset_dict['resource_license_{}'.format(lang)] = lname
            else:
                log.warning('Bad license: license not found: %r ', l)
        dataset_dict['resource_license'] = _licenses

        org_id = dataset_dict['owner_org']
        organization_show = plugins.toolkit.get_action('organization_show')
        if org_id:
            org = organization_show(get_org_context(), {'id': org_id,
                                                        'include_tags': False,
                                                        'include_users': False,
                                                        'include_groups': False,
                                                        'include_extras': True,
                                                        'include_followers': False,
                                                        'include_datasets': False,
                                                        })
        else:
            org = {}
        if org.get('region'):

            # multilang values
            # note region can be in {val1,val2} notation for multiple values
            region_base = org['region']
            if not isinstance(region_base, (list, tuple,)):
                region_base = region_base.strip('{}').split(',')
            tags = {}

            for region_name in region_base:
                ltags = interfaces.get_all_localized_tag_labels(region_name)
                for tlang, tvalue in ltags.items():
                    try:
                        tags[tlang].append(tvalue)
                    except KeyError:
                        tags[tlang] = [tvalue]

            for lang, region in tags.items():
                dataset_dict['organization_region_{}'.format(lang)] = region

        self._update_pkg_rights_holder(dataset_dict, org=org)
        return dataset_dict

    def before_search(self, search_params):
        '''
        # this code may be needed with different versions of solr

        fq_all = []

        if isinstance(search_params['fq'], str):
            fq = [search_params['fq']]
        else:
            fq = search_params['fq']
        if fq and fq[0] and not fq[0].startswith(('+', '-')):
            fq[0] = u'+{}'.format(fq[0])
        search_params['fq'] = ' '.join(fq)
        '''

        return search_params

    def after_search(self, search_results, search_params):
        ## #####################################################################
        # This method moves the dcatapit fields into the extras array (needed for
        # the CKAN harvester).
        # Basically it dynamically reverts what is done by the
        # 'convert_from_extras' to allow harvesting this plugin's custom fields.
        ## #####################################################################
        search_dicts = search_results.get('results', [])

        dcatapit_schema_fields = dcatapit_schema.get_custom_package_schema()

        for _dict in search_dicts:
            _dict_extras = _dict.get('extras', None)

            if not _dict_extras:
                _dict_extras = []
                _dict['extras'] = _dict_extras

            for field in dcatapit_schema_fields:
                field_couple = field.get('couples', [])
                if len(field_couple) > 0:
                    for couple in field_couple:
                        self.manage_extras_for_search(couple, _dict, _dict_extras)
                else:
                    self.manage_extras_for_search(field, _dict, _dict_extras)

            # remove holder info if pkg is local, use org as a source
            # see https://github.com/geosolutions-it/ckanext-dcatapit/pull/213#issuecomment-410668740
            _dict['dataset_is_local'] = helpers.dataset_is_local(_dict['id'])
            if _dict['dataset_is_local']:
                _dict.pop('holder_identifier', None)
                _dict.pop('holder_name', None)
            self._update_pkg_rights_holder(_dict)

        lang = interfaces.get_language()
        facets = search_results['search_facets']
        if 'dcat_theme' in facets:
            themes = facets['dcat_theme']
            for item in themes['items']:
                name = item['name']
                label = interfaces.get_localized_tag_name(tag_name=name, lang=lang)
                item['display_name'] = label

        return search_results

    def manage_extras_for_search(self, field, _dict, _dict_extras):
        field_name = field.get('name', None)

        if field_name and field_name in _dict:
            field_value = _dict.get(field_name, None)
            _dict_extras.append({'key': field_name, 'value': field_value})
            del _dict[field_name]

    def update_loc_field(self, extra, pkg_id, field, lang):
        interfaces.update_extra_package_multilang(extra, pkg_id, field, lang)

    def create_loc_field(self, extra, lang, pkg_id):
        interfaces.save_extra_package_multilang({'id': pkg_id, 'text': extra.get('value'), 'field': extra.get('key')}, lang, 'extra')

    def before_view(self, pkg_dict):
        return self._update_pkg_rights_holder(pkg_dict)

    def after_show(self, context, pkg_dict):
        schema = dcatapit_schema.get_custom_package_schema()
        # quick hack on date fields that are in wrong format
        for fdef in schema:
            if fdef.get('type') != 'date':
                continue
            fname = fdef['name']
            df_value = pkg_dict.get(fname)
            if df_value:
                tmp_value = validators.parse_date(df_value, df_value)
                if isinstance(tmp_value, datetime.date):
                    try:
                        tmp_value = tmp_value.strftime(fdef.get('format') or '%d-%m-%Y')
                    except ValueError as err:
                        log.warning('dataset %s, field %s: cannot reformat date for %s (from input %s): %s',
                                    pkg_dict['name'], fname, tmp_value, df_value, err, exc_info=err)
                        tmp_value = df_value
                pkg_dict[fname] = tmp_value

        # themes are parsed by dcat, which requires a list of URI
        # we have the format like this:
        # [{"theme": "AGRI", "subthemes": ["http://eurovoc.europa.eu/100253", "http://eurovoc.europa.eu/100258"]},
        # {"theme": "ENVI", "subthemes": []}]
        # We need to fix this.

        if not context.get('for_view'):
            if not any(x['key'] == 'theme' for x in pkg_dict.get('extras', [])):
                # there's no theme, add the list from the aggreagate
                aggr_raw = pkg_dict.get(FIELD_THEMES_AGGREGATE)
                if aggr_raw is None:
                    # let's try and find it in extras:
                    aggr_raw = next((x['value'] for x in pkg_dict.get('extras', [])
                                     if x['key'] == FIELD_THEMES_AGGREGATE), None)

                if aggr_raw is None or json.loads(aggr_raw) is None:
                    log.error(f'No Aggregates in dataset {pkg_dict.get("id", "_")}')
                    aggr_raw = json.dumps([{'theme': 'OP_DATPRO', 'subthemes':[]}])
                    pkg_dict[FIELD_THEMES_AGGREGATE] = aggr_raw

                themes = []
                for aggr in json.loads(aggr_raw):
                    themes.append(theme_name_to_uri(aggr['theme']))

                extras = pkg_dict.get('extras', [])
                extras.append({'key': 'theme', 'value': json.dumps(themes)})
                pkg_dict['extras'] = extras

        # in some cases (automatic solr indexing after update)
        # pkg_dict may come without validation and thus
        # without extras converted to main dict.
        # this will ensure that holder keys are extracted to main dict
        pkg_update = {}
        to_remove = []
        for eidx, ex in enumerate(pkg_dict.get('extras') or []):
            if ex['key'].startswith('holder_'):
                to_remove.append(eidx)
                pkg_update[ex['key']] = ex['value']

        for k in pkg_update.keys():
            if k in pkg_dict:
                if pkg_update[k] == pkg_dict[k]:
                    log.warning(f'Ignoring duplicated key {k} with same value {pkg_update[k]}')
                else:
                    raise KeyError(f'Duplicated key in pkg_dict: {k}: {pkg_update[k]} in extras'
                                   f' vs {pkg_dict[k]} in pkg')

        for tr in reversed(to_remove):
            val = pkg_dict['extras'].pop(tr)
            assert val['key'].startswith('holder_'), val
        pkg_dict.update(pkg_update)

        # remove holder info if pkg is local, use org as a source
        # see https://github.com/geosolutions-it/ckanext-dcatapit/pull/213#issuecomment-410668740
        pkg_dict['dataset_is_local'] = helpers.dataset_is_local(pkg_dict['id'])
        if pkg_dict['dataset_is_local']:
            pkg_dict.pop('holder_identifier', None)
            pkg_dict.pop('holder_name', None)
        return self._update_pkg_rights_holder(pkg_dict)

    def _update_pkg_rights_holder(self, pkg_dict, org=None):
        if pkg_dict.get('type') != 'dataset':
            return pkg_dict
        if not (pkg_dict.get('holder_identifier') and pkg_dict.get('holder_name')):
            if not pkg_dict.get('owner_org'):
                return pkg_dict
            if org is None:
                get_org = toolkit.get_action('organization_show')
                ctx = get_org_context()
                # force multilang use
                ctx['for_view'] = True
                org = get_org(ctx, {'id': pkg_dict['owner_org'],
                                    'include_tags': False,
                                    'include_users': False,
                                    'include_groups': False,
                                    'include_extras': True,
                                    'include_followers': False,
                                    'include_datasets': False,
                                    })
            pkg_dict['holder_name'] = org['title']
            pkg_dict['holder_identifier'] = org.get('identifier') or None
        return pkg_dict

    def edit_template(self):
        return 'package/dcatapit_edit.html'

    def new_template(self):
        return 'package/dcatapit_new.html'

    # IFacets
    def dataset_facets(self, facets_dict, package_type):
        # remove dataset license facet
        facets_dict.pop('license_id', None)
        lang = interfaces.get_language() or validators.DEFAULT_LANG
        facets_dict['resource_license_{}'.format(lang)] = plugins.toolkit._('Resources licenses')
        facets_dict['dcat_theme'] = plugins.toolkit._('Dataset Themes')
        facets_dict['dcat_subtheme_{}'.format(lang)] = plugins.toolkit._('Subthemes')
        return facets_dict


class DCATAPITOrganizationPlugin(plugins.SingletonPlugin, toolkit.DefaultOrganizationForm):

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
        schema = logic.schema.default_group_schema()
        schema = self._modify_group_schema(schema)
        return schema

    def form_to_db_schema_api_update(self):
        schema = logic.schema.default_update_group_schema()
        schema = self._modify_group_schema(schema)
        return schema

    def form_to_db_schema(self):
        schema = logic.schema.group_form_schema()
        schema = self._modify_group_schema(schema)
        return schema

    def _modify_group_schema(self, schema):
        TO_EXTRAS = toolkit.get_converter('convert_to_extras')

        for field in dcatapit_schema.get_custom_organization_schema():
            schema[field['name']] = [toolkit.get_validator(v) for v in field['validator']] + [ TO_EXTRAS ]

        return schema

    def db_to_form_schema(self):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''
        schema = logic.schema.default_show_group_schema()
        schema['extras'] = logic.schema.default_extras_schema()

        FROM_EXTRAS = toolkit.get_converter('convert_from_extras')

        for field in dcatapit_schema.get_custom_organization_schema():
            schema[field['name']] = [ FROM_EXTRAS ] + [toolkit.get_validator(v) for v in field['validator']]

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
        toolkit.add_public_directory(config, 'public')
        toolkit.add_resource('fanstatic', 'ckanext-dcatapit')

    def update_config_schema(self, schema):
        for field in dcatapit_schema.get_custom_config_schema(False):

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
            'get_dcatapit_configuration_schema': helpers.get_dcatapit_configuration_schema,
            'json_load': helpers.json_load,
            'json_dump': helpers.json_dump,

        }


class DCATAPITGroupMapper(plugins.SingletonPlugin):

    plugins.implements(plugins.IPackageController, inherit=True)

    def after_create(self, context, pkg_dict):
        return populate_theme_groups(pkg_dict)

    def after_update(self, context, pkg_dict):
        return populate_theme_groups(pkg_dict)


class DCATAPITFacetsPlugin(plugins.SingletonPlugin, DefaultTranslation):

    plugins.implements(plugins.IFacets, inherit=True)

    if plugins.toolkit.check_ckan_version(min_version='2.5.0'):
        plugins.implements(plugins.ITranslation, inherit=True)

    # IFacets
    def dataset_facets(self, facets_dict, package_type):

        # remove dataset license facet
        facets_dict.pop('license_id', None)

        lang = interfaces.get_language() or validators.DEFAULT_LANG
        facets_dict['source_catalog_title'] = plugins.toolkit._('Source catalogs')
        facets_dict['organization_region_{}'.format(lang)] = plugins.toolkit._('Organization regions')

        return facets_dict

    def organization_facets(self, facets_dict, organization_type, package_type):
        lang = interfaces.get_language() or validators.DEFAULT_LANG
        facets_dict['organization_region_{}'.format(lang)] = plugins.toolkit._('Region')
        return facets_dict


class DCATAPITHarvestListPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IBlueprint, inherit=True)

    def get_blueprint(self):
        blueprint = Blueprint(self.name, self.__module__)
        # blueprint.template_folder = 'templates'
        blueprint.add_url_rule(
            rule='/harvest/list',
            view_func=HarvesterController.as_view('harvest_list'),
        )
        return blueprint
