import json
import os
import uuid
from datetime import datetime
from uuid import uuid4

from rdflib import Literal, URIRef

import pytest
import unittest
try:
    from unittest import mock
except ImportError:
    import mock

from ckan.common import config
from ckan.logic import schema
from ckan.model import User, Group, meta, repo
from ckan.model.package import Package
from ckan.model.user import User
from ckan.tests.helpers import call_action, change_config
import ckan.tests.factories as factories

try:
    from ckan.tests import helpers
except ImportError:
    from ckan.new_tests import helpers

from ckanext.harvest.model import HarvestObject

from ckanext.dcat.processors import RDFParser, RDFSerializer
from ckanext.dcat.profiles import DCT, FOAF

from ckanext.dcatapit import validators
from ckanext.dcatapit.schema import FIELD_THEMES_AGGREGATE
from ckanext.dcatapit.tests.utils import (
    LICENSES_FILE,
    get_example_file,
    get_voc_file,
    load_graph,
    load_themes,
)
from ckanext.dcatapit.harvesters.ckanharvester import CKANMappingHarvester
from ckanext.dcatapit.mapping import (
    DCATAPIT_THEME_TO_MAPPING_ADD_NEW_GROUPS,
    DCATAPIT_THEME_TO_MAPPING_SOURCE,
    DCATAPIT_THEMES_MAP,
    theme_aggr_to_theme_uris, _get_extra, theme_name_to_uri, theme_names_to_uris, _get_extra_value
)
from ckanext.dcatapit.model.license import License
from ckanext.dcatapit.commands.vocabulary import load_licenses as load_licenses

Session = meta.Session

DEFAULT_LANG = config.get('ckan.locale_default', 'en')


class BaseParseTest(unittest.TestCase):

    def _extras(self, dataset):
        extras = {}
        for extra in dataset.get('extras'):
            extras[extra['key']] = extra['value']
        return extras


# @pytest.mark.usefixtures('with_plugins', 'clean_db', 'clean_index')
@pytest.mark.usefixtures("with_plugins", "with_request_context")
class TestDCATAPITProfileParsing(BaseParseTest):

    # def setUp(self):
    #     helpers.reset_db()

    def tearDown(self):
        Session.rollback()


    # ensure it localse, as dataset parsing is config-dependent
    @change_config('ckan.locale_default', 'it')
    def test_graph_to_dataset(self):
        Session.expunge_all()

        with open(get_example_file('dataset.rdf'), 'r') as f:
            contents = f.read()

        p = RDFParser(profiles=['it_dcat_ap'])

        p.parse(contents)
        datasets = [d for d in p.datasets()]

        self.assertEqual(len(datasets), 1)

        dataset = datasets[0]

        # Basic fields
        self.assertEqual(dataset['title'], 'Dataset di test DCAT_AP-IT')
        self.assertEqual(dataset['notes'], 'dcatapit dataset di test')

        #  Simple values
        self.assertEqual(dataset['issued'], '2016-11-29')
        self.assertEqual(dataset['modified'], '2016-11-29')
        self.assertEqual(dataset['identifier'], 'ISBN')
        #self.assertEqual(dataset['temporal_start'], '2016-11-01')
        #self.assertEqual(dataset['temporal_end'], '2016-11-30')
        self.assertEqual(dataset['frequency'], 'UPDATE_CONT')

        geographical_name = dataset['geographical_name'][1:-1].split(',') if ',' in dataset['geographical_name'] else [dataset['geographical_name']]
        geographical_name.sort()
        geographical_name = '{' + ','.join([str(x) for x in geographical_name]) + '}'
        self.assertEqual(geographical_name, '{ITA_BZO}')

        self.assertEqual(dataset['publisher_name'], 'bolzano it')
        self.assertEqual(dataset['publisher_identifier'], '234234234')
        self.assertEqual(dataset['creator_name'], 'test')
        self.assertEqual(dataset['creator_identifier'], '412946129')
        self.assertEqual(dataset['holder_name'], 'bolzano')
        self.assertEqual(dataset['holder_identifier'], '234234234')

        alternate_identifier = set([i['identifier'] for i in json.loads(dataset['alternate_identifier'])])
        self.assertEqual(alternate_identifier, set(['ISBN:123', 'TEST']))

        theme = json.loads(dataset[FIELD_THEMES_AGGREGATE])
        allowed_themes = ('ECON', 'ENVI',)
        assert theme, 'got {}'.format(dataset[FIELD_THEMES_AGGREGATE])
        for t in theme:
            assert t.get('theme') in allowed_themes, 'themes {} not in {}'.format(theme, allowed_themes)

        self.assertEqual(dataset['geographical_geonames_url'], 'http://www.geonames.org/3181913')

        language = dataset['language'][1:-1].split(',') if ',' in dataset['language'] else [dataset['language']]
        language.sort()
        language = '{' + ','.join([str(x) for x in language]) + '}'
        self.assertEqual(language, '{DEU,ENG,ITA}')

        self.assertEqual(dataset['is_version_of'], 'http://dcat.geo-solutions.it/dataset/energia-da-fonti-rinnovabili2')

        conforms_to = json.loads(dataset['conforms_to'])
        conforms_to_ids = set([c['identifier'] for c in conforms_to])
        self.assertEqual(conforms_to_ids, set('CONF1,CONF2,CONF3'.split(',')))

        # Multilang values
        self.assertTrue(dataset['DCATAPIT_MULTILANG_BASE'])

        multilang_notes = dataset['DCATAPIT_MULTILANG_BASE'].get('notes', None)
        self.assertTrue(multilang_notes)
        self.assertEqual(multilang_notes['de'], 'dcatapit test-dataset')
        self.assertEqual(multilang_notes['it'], 'dcatapit dataset di test')
        self.assertEqual(multilang_notes['en'], 'dcatapit dataset test')

        multilang_holder_name = dataset['DCATAPIT_MULTILANG_BASE'].get('holder_name', None)
        self.assertTrue(multilang_holder_name)
        self.assertEqual(multilang_holder_name['de'], 'bolzano')
        self.assertEqual(multilang_holder_name['it'], 'bolzano')
        self.assertEqual(multilang_holder_name['en'], 'bolzano')

        multilang_title = dataset['DCATAPIT_MULTILANG_BASE'].get('title', None)
        self.assertTrue(multilang_title)
        self.assertEqual(multilang_title['de'], 'Dcatapit Test-Dataset')
        self.assertEqual(multilang_title['it'], 'Dataset di test DCAT_AP-IT')
        self.assertEqual(multilang_title['en'], 'DCAT_AP-IT test dataset')

        multilang_pub_name = dataset['DCATAPIT_MULTILANG_BASE'].get('publisher_name', None)
        self.assertTrue(multilang_pub_name)
        self.assertEqual(multilang_pub_name['en'], 'bolzano en')
        self.assertEqual(multilang_pub_name['it'], 'bolzano it it')

    @pytest.mark.usefixtures("clean_dcatapit_db")
    def test_groups_to_themes_mapping(self):
        config[DCATAPIT_THEMES_MAP] = os.path.join(os.path.dirname(__file__),
                                                   '..',
                                                   '..',
                                                   '..',
                                                   'examples',
                                                   'themes_mapping.json')

        url = 'http://some.test.harvest.url'

        groups_non_mappable = [{'name': 'non-mappable', 'display_name': 'non-mappable'}], []
        groups_mappable = [{'name': 'agriculture', 'display_name': 'agricoltura-e-allevamento', 'identifier': 'dummy'}],\
            [{'key': 'theme', 'value': 'AGRI'}]
        mapped_theme_name = 'AGRI'

        harvest_obj = self._make_harvest_object(url, groups_non_mappable[0])

        harvester = CKANMappingHarvester()

        licenses_file = get_voc_file(LICENSES_FILE)
        self.g = load_graph(path=licenses_file)
        load_licenses(self.g)
        Session.flush()

        # clean, no mapping
        harvester.import_stage(harvest_obj)
        hdata = json.loads(harvest_obj.content)
        self.assertEqual([t for t in hdata.get('extras', []) if t['key'] == 'theme'], [])

        # test mapping
        hdata = json.loads(harvest_obj.content)
        hdata['groups'] = groups_mappable[0]
        harvest_obj.content = json.dumps(hdata)

        harvester.import_stage(harvest_obj)
        hdata = json.loads(harvest_obj.content)
        extras = hdata.get('extras', [])
        # self.assertEqual([t for t in hdata.get('extras', []) if t['key'] == 'theme'], groups_mappable[1])

        theme_uri_list_extra = _get_extra(extras, 'theme')
        self.assertIsNotNone(theme_uri_list_extra)
        theme_uri_list = json.loads(theme_uri_list_extra['value'])
        expected_theme_uri_list = [theme_name_to_uri(mapped_theme_name)]
        self.assertListEqual(expected_theme_uri_list, theme_uri_list)

        aggr_extra = _get_extra(extras, FIELD_THEMES_AGGREGATE)
        self.assertIsNotNone(aggr_extra)
        aggr = json.loads(aggr_extra['value'])
        self.assertEqual(mapped_theme_name, aggr[0]['theme'])

    def _make_harvest_object(self, mock_url, groups):
        org = factories.Organization(identifier=uuid.uuid4())
        source_dict = {
            'owner_org': org['id'],
            'title': 'Test RDF DCAT Source',
            'name': 'test-rdf-dcat-source',
            'url': mock_url,
            'source_type': 'dcat_rdf',
            'created': datetime.now(),
            'metadata_created': datetime.now(),
        }
        default_ctx = {'ignore_auth': True,
                       'defer_commit': False}
        harvest_source = helpers.call_action('harvest_source_create',
                                             default_ctx, **source_dict)

        Session.flush()
        harvest_job = helpers.call_action('harvest_job_create',
                                          default_ctx,
                                          source_id=harvest_source['id'],
                                          )

        hdata = {'groups': groups}
        Session.flush()

        harvest_object = helpers.call_action('harvest_object_create',
                                             default_ctx,
                                             job_id=harvest_job['id'],
                                             )

        Session.flush()

        hobj = HarvestObject.get(harvest_object['id'])
        hobj.content = json.dumps(hdata)
        return hobj


    @pytest.mark.usefixtures('with_request_context', 'remove_dataset_groups')
    def test_theme_to_group_mapping(self):
        # multilang requires lang to be set
        # class dummyreq(object):
        #     class p(object):
        #         translator = object()
        #     environ = {'pylons.pylons': p()}

        # CKANRequest(dummyreq)
        # pylons.request = dummyreq()
        # pylons.translator.pylons_lang = ['en_GB']

        #set_lang('en_GB')
        #assert get_lang() == ['en_GB']
        assert 'dcatapit_theme_group_mapper' in config['ckan.plugins'], 'No dcatapit_theme_group_mapper plugin in config'

        with open(get_example_file('dataset.rdf'), 'r') as f:
            contents = f.read()

        p = RDFParser(profiles=['it_dcat_ap'])

        p.parse(contents)
        datasets = [d for d in p.datasets()]
        self.assertEqual(len(datasets), 1)
        package_dict = datasets[0]

        user = User.get('dummy')

        if not user:
            user = call_action('user_create',
                               name='dummy',
                               password='dummydummy',
                               email='dummy@dummy.com')
            user_name = user['name']
        else:
            user_name = user.name
        org = Group.by_name('dummy')
        if org is None:
            org = call_action('organization_create',
                              context={'user': user_name},
                              name='dummy',
                              identifier='aaaaaa')
        existing_g = Group.by_name('existing-group')
        if existing_g is None:
            existing_g = call_action('group_create',
                                     context={'user': user_name},
                                     name='existing-group')

        context = {'user': 'dummy',
                   'ignore_auth': True,
                   'defer_commit': False}
        package_schema = schema.default_create_package_schema()
        context['schema'] = package_schema
        _p = {'frequency': 'manual',
              'publisher_name': 'dummy',
              'extras': [{'key': 'theme', 'value': ['non-mappable', 'thememap1']}],
              'groups': [] , #  [{'name':existing_g.name}],
              'title': 'dummy',
              'holder_name': 'dummy',
              'holder_identifier': 'dummy',
              'name': 'dummy-' + uuid4().hex,
              'identifier': 'dummy' + uuid4().hex,
              'notes': 'dummy',
              'owner_org': 'dummy',
              'modified': datetime.now(),
              'publisher_identifier': 'dummy',
              'metadata_created': datetime.now(),
              'metadata_modified': datetime.now(),
              'guid': str(uuid.uuid4),
              }

        package_dict.update(_p)

        config[DCATAPIT_THEME_TO_MAPPING_SOURCE] = ''
        config[DCATAPIT_THEME_TO_MAPPING_ADD_NEW_GROUPS] = 'false'

        package_data = call_action('package_create', context=context, **package_dict)

        p = Package.get(package_data['id'])

        # no groups should be assigned at this point (no map applied)
        assert {'theme': ['non-mappable', 'thememap1']} == p.extras, '{} vs {}'.format(_p['extras'], p.extras)
        assert [] == p.get_groups(group_type='group'), 'should be {}, got {}'.format([], p.get_groups(group_type='group'))

        package_data = call_action('package_show', context=context, id=package_data['id'])

        # use test mapping, which replaces thememap1 to thememap2 and thememap3
        test_map_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'examples', 'test_map.ini')

        config[DCATAPIT_THEME_TO_MAPPING_SOURCE] = test_map_file
        config[DCATAPIT_THEME_TO_MAPPING_ADD_NEW_GROUPS] = 'false'

        # package_dict['theme'] = ['non-mappable', 'thememap1']

        package_dict.pop('extras', None)
        p = Package.get(package_data['id'])
        context['package'] = p

        package_data = call_action('package_update',
                                   context=context,
                                   **package_dict)

        # check - only existing group should be assigned
        p = Package.get(package_data['id'])
        groups = [g.name for g in p.get_groups(group_type='group')]

        # the map file maps ECON to existing group, and 2 other unexisting groups that will not be created
        expected_groups = ['existing-group']
        self.assertSetEqual(set(expected_groups), set(groups), 'Error in assigned groups')

        config[DCATAPIT_THEME_TO_MAPPING_SOURCE] = test_map_file
        config[DCATAPIT_THEME_TO_MAPPING_ADD_NEW_GROUPS] = 'true'

        # package_dict['theme'] = ['non-mappable', 'thememap1']
        package_data = call_action('package_update', context=context, **package_dict)

        meta.Session.flush()

        # recheck - this time, new groups should appear
        p = Package.get(package_data['id'])
        groups = [g.name for g in p.get_groups(group_type='group')]

        # the map file maps ECON to existing group and 2 other groups that have been automatically created
        expected_groups = expected_groups + ['somegroup1', 'somegroup2']
        self.assertSetEqual(set(expected_groups), set(groups), 'Groups differ')

        # package_dict['theme'] = ['non-mappable', 'thememap1', 'thememap-multi']
        aggr = json.loads(package_dict[FIELD_THEMES_AGGREGATE])
        aggr.append({'theme':'thememap-multi', 'subthemes':[]})
        package_dict[FIELD_THEMES_AGGREGATE] = json.dumps(aggr)

        package_data = call_action('package_update', context=context, **package_dict)

        meta.Session.flush()

        # recheck - there should be no duplicates
        p = Package.get(package_data['id'])
        groups = [g.name for g in p.get_groups(group_type='group')]

        # added theme 'thememap-multi', that maps to 'othergroup' and other already exisintg groups
        expected_groups = expected_groups + ['othergroup']
        self.assertEqual(len(expected_groups), len(groups), 'New groups differ - there may be duplicated groups')
        self.assertSetEqual(set(expected_groups), set(groups), 'New groups differ')

        package_data = call_action('package_update', context=context, **package_dict)

        meta.Session.flush()

        # recheck - there still should be no duplicates
        p = Package.get(package_data['id'])
        groups = [g.name for g in p.get_groups(group_type='group')]

        self.assertEqual(len(expected_groups), len(groups), 'New groups differ - there may be duplicated groups')
        self.assertSetEqual(set(expected_groups), set(groups), 'New groups differ')

        meta.Session.rollback()

    def test_license(self):
        g = load_graph(path=get_voc_file(LICENSES_FILE))
        load_licenses(g)
        Session.flush()

        dataset = {'title': 'some title',
                   'id': 'sometitle',
                   'resources': [
                            {
                                'id': 'resource/1111',
                                'uri': 'http://resource/1111',
                                'license_type': 'invalid',
                            },
                       {
                                'id': 'resource/2222',
                                'uri': 'http://resource/2222',
                                'license_type': 'https://w3id.org/italia/controlled-vocabulary/licences/A311_GFDL13'
                            }
                   ]
                   }

        p = RDFParser(profiles=['euro_dcat_ap', 'it_dcat_ap'])

        s = RDFSerializer()

        dataset_ref = s.graph_from_dataset(dataset)

        g = s.g

        r1 = URIRef(dataset['resources'][0]['uri'])
        r2 = URIRef(dataset['resources'][1]['uri'])

        unknown = License.get(License.DEFAULT_LICENSE)

        license_ref = g.value(r1, DCT.license)

        assert license_ref is not None
        assert str(license_ref) == unknown.uri,\
            'got license {}, instead of {}'.format(license_ref, unknown.license_type)

        gpl = License.get(dataset['resources'][1]['license_type'])
        assert gpl is not None

        license_ref = g.value(r2, DCT.license)
        license_type = g.value(license_ref, DCT.type)

        assert license_ref is not None

        assert str(license_ref) == gpl.document_uri
        assert str(license_type) == str(gpl.license_type)

        serialized = s.serialize_dataset(dataset)

        p.parse(serialized)
        datasets = list(p.datasets())
        assert len(datasets) == 1
        new_dataset = datasets[0]
        resources = new_dataset['resources']

        def _find_res(res_uri):
            for res in resources:
                if res_uri == res['uri']:
                    return res
            raise ValueError('No resource for {}'.format(res_uri))

        new_res_unknown = _find_res(str(r1))
        new_res_gpl = _find_res(str(r2))

        assert new_res_unknown['license_type'] == unknown.uri, (new_res_unknown['license_type'], unknown.uri,)
        assert new_res_gpl['license_type'] == dataset['resources'][1]['license_type']

    def test_conforms_to(self):

        conforms_to_in = [{'identifier': 'CONF1',
                           'uri': 'http://conf01/abc',
                           'title': {'en': 'title', 'it': 'title'},
                           'referenceDocumentation': ['http://abc.efg/'], },
                          {'identifier': 'CONF2',
                           'title': {'en': 'title', 'it': 'title'},
                           'description': {'en': 'descen', 'it': 'descit'},
                           'referenceDocumentation': ['http://abc.efg/'], },
                          ]
        dataset = {
            'id': '4b6fe9ca-dc77-4cec-92a4-55c6624a5bd6',
            'name': 'test-dataset',
            'title': 'Dataset di test DCAT_AP-IT',
            'notes': 'dcatapit dataset di test',
            'metadata_created': '2015-06-26T15:21:09.034694',
            'metadata_modified': '2015-06-26T15:21:09.075774',
            'tags': [{'name': 'Tag 1'}, {'name': 'Tag 2'}],
            'issued': '2016-11-29',
            'modified': '2016-11-29',
            'identifier': 'ISBN',
            'temporal_start': '2016-11-01',
            'temporal_end': '2016-11-30',
            'frequency': 'UPDATE_CONT',
            'publisher_name': 'bolzano',
            'publisher_identifier': '234234234',
            'creator_name': 'test',
            'creator_identifier': '412946129',
            'holder_name': 'bolzano',
            'holder_identifier': '234234234',
            'alternate_identifier': 'ISBN,TEST',
            'theme': '{ECON,ENVI}',
            'geographical_geonames_url': 'http://www.geonames.org/3181913',
            'language': '{DEU,ENG,ITA}',
            'is_version_of': 'http://dcat.geo-solutions.it/dataset/energia-da-fonti-rinnovabili2',
            'conforms_to': json.dumps(conforms_to_in)
        }

        s = RDFSerializer()
        p = RDFParser(profiles=['euro_dcat_ap', 'it_dcat_ap'])

        serialized = s.serialize_dataset(dataset)

        p.parse(serialized)
        datasets = list(p.datasets())

        assert len(datasets) == 1
        d = datasets[0]

        conforms_to = dict((d['identifier'], d) for d in conforms_to_in)
        dataset_conforms_to = json.loads(d['conforms_to'])

        assert len(dataset_conforms_to) == len(conforms_to_in), 'got {}, should be {}'.format(len(d['conforms_to']), len(conforms_to_in))
        for conf in dataset_conforms_to:
            check = conforms_to[conf['identifier']]
            for k, v in check.items():
                # there should be no empty uri
                if k == 'uri' and not v:
                    assert conf.get(k) is None
                else:
                    assert conf.get(k) == v
            for k, v in conf.items():
                src_v = check.get(k)
                # ref may be extracted from rdf, but it can be
                # generated by serializer
                if not src_v and k == 'uri':
                    continue
                # no value, may be missing key in source
                elif not src_v:
                    assert not check.get(k)
                else:
                    assert check[k] == v

    def test_creators(self):

        creators = [{'creator_name': {DEFAULT_LANG: 'abc', 'it': 'abc it'}, 'creator_identifier': 'ABC'},
                    {'creator_name': {DEFAULT_LANG: 'cde', 'it': 'cde it'}, 'creator_identifier': 'CDE'},
                    ]
        dataset = {
            'id': '4b6fe9ca-dc77-4cec-92a4-55c6624a5bd6',
            'name': 'test-dataset',
            'title': 'Dataset di test DCAT_AP-IT',
            'notes': 'dcatapit dataset di test',
            'metadata_created': '2015-06-26T15:21:09.034694',
            'metadata_modified': '2015-06-26T15:21:09.075774',
            'tags': [{'name': 'Tag 1'}, {'name': 'Tag 2'}],
            'issued': '2016-11-29',
            'modified': '2016-11-29',
            'identifier': 'ISBN',
            'temporal_start': '2016-11-01',
            'temporal_end': '2016-11-30',
            'frequency': 'UPDATE_CONT',
            'publisher_name': 'bolzano',
            'publisher_identifier': '234234234',
            'creator_name': 'test',
            'creator_identifier': '412946129',
            'holder_name': 'bolzano',
            'holder_identifier': '234234234',
            'alternate_identifier': 'ISBN,TEST',
            'theme': '{ECON,ENVI}',
            'geographical_geonames_url': 'http://www.geonames.org/3181913',
            'language': '{DEU,ENG,ITA}',
            'is_version_of': 'http://dcat.geo-solutions.it/dataset/energia-da-fonti-rinnovabili2',
            'creator': json.dumps(creators)
        }

        s = RDFSerializer()
        p = RDFParser(profiles=['euro_dcat_ap', 'it_dcat_ap'])

        serialized = s.serialize_dataset(dataset)

        p.parse(serialized)
        datasets = list(p.datasets())

        assert len(datasets) == 1
        d = datasets[0]
        creators.append({'creator_identifier': dataset['creator_identifier'],
                         'creator_name': {DEFAULT_LANG: dataset['creator_name']}})

        creators_dict = dict((v['creator_identifier'], v) for v in creators)

        creators_in = json.loads(d['creator'])

        for c in creators_in:
            assert c['creator_identifier'] in creators_dict.keys(), 'no {} key in {}'.format(c['creator_identifier'],
                                                                                             creators_dict.keys())
            assert c['creator_name'] == creators_dict[c['creator_identifier']]['creator_name'],\
                '{} vs {}'.format(c['creator_name'], creators_dict[c['creator_identifier']]['creator_name'])
        for c in creators_dict.keys():
            assert c in [_c['creator_identifier'] for _c in creators_in]
            cdata = creators_dict[c]
            assert cdata in creators_in

    def test_temporal_coverage(self):
        from ckanext.dcatapit.tests.utils import load_themes

        load_themes()
        temporal_coverage = [{'temporal_start': '2001-01-01T00:00:00', 'temporal_end': '2001-02-01T10:11:12'},
                             {'temporal_start': '2001-01-01T00:00:00', 'temporal_end': '2001-02-01T10:11:12'},
                             ]
        dataset = {
            'id': '4b6fe9ca-dc77-4cec-92a4-55c6624a5bd6',
            'name': 'test-dataset',
            'title': 'Dataset di test DCAT_AP-IT',
            'notes': 'dcatapit dataset di test',
            'metadata_created': '2015-06-26T15:21:09.034694',
            'metadata_modified': '2015-06-26T15:21:09.075774',
            'tags': [{'name': 'Tag 1'}, {'name': 'Tag 2'}],
            'issued': '2016-11-29',
            'modified': '2016-11-29',
            'identifier': 'ISBN',
            'temporal_start': '2016-11-01T00:00:00',
            'temporal_end': '2016-11-30T00:00:00',
            'temporal_coverage': json.dumps(temporal_coverage),
            'frequency': 'UPDATE_CONT',
            'publisher_name': 'bolzano',
            'publisher_identifier': '234234234',
            'creator_name': 'test',
            'creator_identifier': '412946129',
            'holder_name': 'bolzano',
            'holder_identifier': '234234234',
            'alternate_identifier': 'ISBN,TEST',
            'theme': '{ECON,ENVI}',
            'geographical_geonames_url': 'http://www.geonames.org/3181913',
            'language': '{DEU,ENG,ITA}',
            'is_version_of': 'http://dcat.geo-solutions.it/dataset/energia-da-fonti-rinnovabili2',
        }

        s = RDFSerializer()
        p = RDFParser(profiles=['euro_dcat_ap', 'it_dcat_ap'])

        serialized = s.serialize_dataset(dataset)

        p.parse(serialized)
        datasets = list(p.datasets())

        assert len(datasets) == 1
        d = datasets[0]

        temporal_coverage.append({'temporal_start': dataset['temporal_start'],
                                  'temporal_end': dataset['temporal_end']})

        try:
            validators.dcatapit_temporal_coverage(d['temporal_coverage'], {})
            # this should not raise exception
            assert True
        except validators.Invalid as err:
            assert False, 'Temporal coverage should be valid: {}'.format(err)

        temp_cov = json.loads(d['temporal_coverage'])

        assert len(temp_cov) == len(temporal_coverage),\
            'got {} items instead of {}'.format(len(temp_cov),
                                                len(temporal_coverage))

        set1 = set([tuple(d.items()) for d in temp_cov])
        set2 = set([tuple(d.items()) for d in temporal_coverage])

        assert set1 == set2, 'Got different temporal coverage sets: \n{}\n vs\n {}'.format(set1, set2)

    def test_subthemes(self):

        load_themes()

        subthemes = [{'theme': 'AGRI', 'subthemes': ['http://eurovoc.europa.eu/100253',
                                                     'http://eurovoc.europa.eu/100258']},
                     {'theme': 'ENVI', 'subthemes': []}]

        dataset = {
            'id': '4b6fe9ca-dc77-4cec-92a4-55c6624a5bd6',
            'name': 'test-dataset',
            'title': 'Dataset di test DCAT_AP-IT',
            'notes': 'dcatapit dataset di test',
            'metadata_created': '2015-06-26T15:21:09.034694',
            'metadata_modified': '2015-06-26T15:21:09.075774',
            'tags': [{'name': 'Tag 1'}, {'name': 'Tag 2'}],
            'issued': '2016-11-29',
            'modified': '2016-11-29',
            'frequency': 'UPDATE_CONT',
            'publisher_name': 'bolzano',
            'publisher_identifier': '234234234',
            'creator_name': 'test',
            'creator_identifier': '412946129',
            'holder_name': 'bolzano',
            'holder_identifier': '234234234',
            'alternate_identifier': 'ISBN,TEST',
            FIELD_THEMES_AGGREGATE: json.dumps(subthemes),
            'theme': theme_aggr_to_theme_uris(subthemes)  # this is added dinamically when retrieving datasets from the db
        }

        s = RDFSerializer()
        p = RDFParser(profiles=['euro_dcat_ap', 'it_dcat_ap'])

        serialized = s.serialize_dataset(dataset)

        p.parse(serialized)
        datasets = list(p.datasets())

        assert len(datasets) == 1
        parsed_dataset = datasets[0]

        # test themes
        parsed_themes_raw = _get_extra_value(parsed_dataset.get('extras'), 'theme')
        self.assertIsNotNone(parsed_themes_raw, f'Themes not found in parsed dataset {parsed_dataset}')
        parsed_themes = json.loads(parsed_themes_raw)
        self.assertEqual(2, len(parsed_themes))
        self.assertSetEqual(set(theme_names_to_uris(['AGRI','ENVI'])), set(parsed_themes))

        # test aggregated themes
        parsed_aggr_raw = parsed_dataset.get(FIELD_THEMES_AGGREGATE, None)
        self.assertIsNotNone(parsed_aggr_raw, f'Aggregated themes not found in parsed dataset {parsed_dataset}')
        parsed_aggr = json.loads(parsed_aggr_raw)
        self.assertIsNotNone(parsed_aggr, 'Aggregate is None')
        self.assertEquals(2, len(parsed_aggr))
        for t in parsed_aggr:
            if t['theme'] == 'ENVI':
                self.assertSetEqual(set([]), set(t['subthemes']))
            elif t['theme'] == 'AGRI':
                self.assertSetEqual(set(subthemes[0]['subthemes']), set(t['subthemes']))
            else:
                self.fail(f'Unknown theme: {t}')

    @pytest.mark.usefixtures('clean_dcatapit_db')
    def test_alternate_identifiers(self):

        with open(get_example_file('dataset_identifier.rdf'), 'r') as f:
            contents = f.read()

        p = RDFParser(profiles=['it_dcat_ap'])
        p.parse(contents)

        datasets = [d for d in p.datasets()]
        assert len(datasets) == 1
        assert datasets[0]['alternate_identifier'] == '[{"identifier": "ISBN:alt id 123", "agent": {}}]',\
            datasets[0]['alternate_identifier']

    def test_publisher(self):

        with open(get_example_file('catalog_dati_unibo.rdf'), 'r') as f:
            contents = f.read()

        p = RDFParser(profiles=['it_dcat_ap'])

        p.parse(contents)
        g = p.g

        datasets = [d for d in p.datasets()]
        assert(len(datasets) > 1)
        for d in datasets:
            did = d['identifier']
            pname = d.get('publisher_name')
            pid = d.get('publisher_identifier')
            dat_ref = list(g.subjects(DCT.identifier, Literal(did)))[0]
            pub_ref = g.value(dat_ref, DCT.publisher)
            pubnames = list(g.objects(pub_ref, FOAF.name))
            if not pubnames:
                assert pname is None and pid is None,\
                    'Got {}/{} for publisher, when no ref in graph'.format(pname, pid)
            else:
                assert pname and pid, 'no pname {} and pid {} for {}'.format(pname, pid, pubnames)

                lang_hit = False
                for lname in pubnames:
                    if hasattr(lname, 'lang'):
                        if lname.lang and lname.lang == DEFAULT_LANG:
                            lang_hit = pname == lname.value
                    else:
                        if not lang_hit:
                            lang_hit = pname == lname.value
                assert lang_hit, 'There should be lang hit'
