from unittest import TestCase
from uuid import uuid4
import json

import nose
import pytest

import ckan.tests.factories as factories
from ckan.tests.helpers import call_action

import ckanext.dcatapit.plugin as plugin
from ckanext.dcatapit.mapping import themes_to_aggr_json, theme_aggr_to_theme_uris, theme_names_to_uris, \
    theme_name_to_uri
from ckanext.dcatapit.schema import FIELD_THEMES_AGGREGATE

eq_ = nose.tools.eq_
ok_ = nose.tools.ok_


# ####################################
# DCATAPITPackagePlugin test methods #
# ####################################
package_plugin = plugin.DCATAPITPackagePlugin()


def test_package_plugin():
    ok_(package_plugin)


def test_package_i18n_domain():
    eq_(package_plugin.i18n_domain(), 'ckanext-dcatapit')


def test_package_create_schema():
    schema = package_plugin.create_package_schema()
    ok_(schema)


def test_package_update_schema():
    schema = package_plugin.update_package_schema()
    ok_(schema)


def test_package_show_package_schema():
    schema = package_plugin.show_package_schema()
    ok_(schema)


def test_package_if_falback():
    eq_(package_plugin.is_fallback(), True)


def test_package_package_types():
    eq_(package_plugin.package_types(), [])


def test_package_get_validators():
    validators = package_plugin.get_validators()
    ok_(validators.get('couple_validator', None))
    ok_(validators.get('no_number', None))
    ok_(validators.get('dcatapit_id_unique', None))


def test_package_get_helpers():
    helpers = package_plugin.get_helpers()
    ok_(helpers.get('get_dcatapit_package_schema', None))
    ok_(helpers.get('get_vocabulary_items', None))
    ok_(helpers.get('get_dcatapit_resource_schema', None))
    ok_(helpers.get('list_to_string', None))
    ok_(helpers.get('couple_to_html', None))
    ok_(helpers.get('couple_to_string', None))
    ok_(helpers.get('format', None))
    ok_(helpers.get('validate_dateformat', None))
    ok_(helpers.get('get_localized_field_value', None))


# ####################################
# DCATAPITPackagePlugin test methods #
# ####################################
organization_plugin = plugin.DCATAPITOrganizationPlugin()


def test_org_plugin():
    ok_(organization_plugin)


def test_organization_get_helpers():
    helpers = organization_plugin.get_helpers()
    ok_(helpers.get('get_dcatapit_organization_schema', None))


def test_organization_group_controller():
    eq_(organization_plugin.group_controller(), 'organization')


def test_organization_group_types():
    eq_(organization_plugin.group_types()[0], 'organization')


def test_org_form_to_db_schema_api_create():
    schema = organization_plugin.form_to_db_schema_api_create()
    ok_(schema)


def test_org_form_to_db_schema_api_update():
    schema = organization_plugin.form_to_db_schema_api_update()
    ok_(schema)


def test_org_db_to_form_schema():
    schema = organization_plugin.db_to_form_schema()
    ok_(schema)


# ####################################
# DCATAPITPackagePlugin test methods #
# ####################################
configuration_plugin = plugin.DCATAPITConfigurerPlugin()


def test_config_plugin():
    ok_(configuration_plugin)


def test_config_update_config_schema():
    schema = configuration_plugin.update_config_schema({})
    ok_(schema)


def test_config_get_helpers():
    helpers = configuration_plugin.get_helpers()
    ok_(helpers.get('get_dcatapit_configuration_schema', None))


def test_package_after_show():
    data = {'id': 'none',
            'issued': '2000-00-00',
            'modified': '2013-02-01'}
    out = package_plugin.after_show({}, data)
    eq_(out['issued'], '2000-00-00')
    eq_(out['modified'], '01-02-2013')


@pytest.mark.usefixtures("with_request_context")
class ValidationTests(TestCase):

    DEFAULT_AGGR = 'ENVI'
    DEFAULT_THEME = 'ECON'

    def _get_dataset(self):
        org = factories.Organization(identifier=uuid4().hex, is_org=True, name=uuid4().hex)

        return {
            # 'id': '4b6fe9ca-dc77-4cec-92a4-55c6624a5bd6',
            'owner_org': org['id'],
            'name': uuid4().hex,
            'identifier': str(uuid4()),
            'title': 'Dataset di test DCAT_AP-IT',
            'notes': 'dcatapit dataset di test',
            'issued': '2016-11-29',
            'modified': '2016-11-29',
            'frequency': 'UPDATE_CONT',
            'publisher_name': 'pubbo',
            'publisher_identifier': '234234234',
            'creator_name': 'test',
            'creator_identifier': '412946129',
            'holder_name': 'holdo',
            'holder_identifier': '234234234',
            'geographical_geonames_url': 'http://www.geonames.org/3181913',
            'language': '{ITA}',
            FIELD_THEMES_AGGREGATE: themes_to_aggr_json([__class__.DEFAULT_AGGR]),
            # 'theme': json.dumps(theme_names_to_uris([__class__.DEFAULT_THEME])),
            'extras': [
                {
                    'key': 'theme',
                    'value': json.dumps(theme_names_to_uris([__class__.DEFAULT_THEME]))
                },
            ],
        }

    context = {'user': 'dummy',
               'ignore_auth': True,
               'defer_commit': False}

    def test_package_no_theme_no_aggr(self):
        src = self._get_dataset()
        src.pop('extras')
        src.pop(FIELD_THEMES_AGGREGATE)

        created = call_action('package_create', {'defer_commit': False}, **src)
        reloaded = call_action('package_show', context=__class__.context, id=created['id'])

        for pkg in (created, reloaded):
            self._ensure_aggr(pkg, ['OP_DATPRO'])
            self._ensure_themes(pkg, ['OP_DATPRO'])

    def test_package_theme_no_aggr(self):
        src = self._get_dataset()
        src.pop(FIELD_THEMES_AGGREGATE)

        created = call_action('package_create', {'defer_commit': False}, **src)
        reloaded = call_action('package_show', context=__class__.context, id=created['id'])

        for pkg in (created, reloaded):
            self._ensure_aggr(pkg, [__class__.DEFAULT_THEME])
            self._ensure_themes(pkg, [__class__.DEFAULT_THEME])

    def test_package_no_theme_aggr(self):
        src = self._get_dataset()
        src.pop('extras')

        created = call_action('package_create', {'defer_commit': False}, **src)
        reloaded = call_action('package_show', context=__class__.context, id=created['id'])

        for pkg in (created, reloaded):
            self._ensure_aggr(pkg, [__class__.DEFAULT_AGGR])
            self._ensure_themes(pkg, [__class__.DEFAULT_AGGR])

    def test_package_theme_aggr(self):
        src = self._get_dataset()

        created = call_action('package_create', {'defer_commit': False}, **src)
        reloaded = call_action('package_show', context=__class__.context, id=created['id'])

        for pkg in (created, reloaded):
            self._ensure_aggr(pkg, [__class__.DEFAULT_AGGR])
            self._ensure_themes(pkg, [__class__.DEFAULT_AGGR])

    def _ensure_aggr(self, pkg, expected_themes: list):
        self.assertIn(FIELD_THEMES_AGGREGATE, pkg.keys(), 'Aggregate not found')
        aggr = json.loads(pkg[FIELD_THEMES_AGGREGATE])
        aggr_themes = [a['theme'] for a in aggr]
        self.assertSetEqual(set(expected_themes), set(aggr_themes))

    def _ensure_themes(self, pkg, expected_themes: list):
        expected_uris = [theme_name_to_uri(name) for name in expected_themes]
        print(pkg)
        extras = pkg.get('extras')
        self.assertIsNotNone(extras, 'Extras not found')
        theme = next((x['value'] for x in extras if x['key'] == 'theme'), None)
        self.assertIsNotNone(theme, 'Theme not found')
        theme_uri_list = json.loads(theme)
        self.assertEquals(len(expected_themes), len(theme_uri_list))
        self.assertSetEqual(set(expected_uris), set(theme_uri_list))
