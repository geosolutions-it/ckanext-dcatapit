import os
import uuid
import json
from datetime import datetime
import uuid

import nose
try:
    from unittest import mock
except ImportError:
    import mock

from rdflib import Graph, URIRef, BNode, Literal
from rdflib.namespace import RDF


from ckan.model.meta import Session
from ckan.model import User, Group
from ckan.plugins import toolkit
from ckan.lib.base import config
from ckan.logic import schema

from ckan.tests.helpers import call_action
from ckan.model import meta, repo
from ckan.model.user import User
from ckan.model.group import Group
from ckan.model.package import Package


try:
    from ckan.tests import helpers
except ImportError:
    from ckan.new_tests import helpers

from ckanext.dcat.processors import RDFParser, RDFSerializer
from ckanext.dcatapit.dcat.profiles import (DCATAPIT)
from ckanext.dcatapit import  validators

from ckanext.dcat.profiles import (DCAT, DCT, FOAF, OWL)

from ckanext.dcatapit.mapping import DCATAPIT_THEMES_MAP, map_nonconformant_groups
from ckanext.dcatapit.mapping import DCATAPIT_THEME_TO_MAPPING_SOURCE, DCATAPIT_THEME_TO_MAPPING_ADD_NEW_GROUPS
from ckanext.dcatapit.harvesters.ckanharvester import CKANMappingHarvester
from ckanext.harvest.model import HarvestObject

from ckanext.dcatapit.plugin import DCATAPITGroupMapper
from ckanext.dcatapit.tests.utils import load_themes

from ckanext.dcatapit.model.license import _get_graph, load_from_graph, License

DEFAULT_LANG = config.get('ckan.locale_default', 'en')

eq_ = nose.tools.eq_
ok_ = nose.tools.ok_
assert_true = nose.tools.assert_true


class BaseParseTest(object):

    def _extras(self, dataset):
        extras = {}
        for extra in dataset.get('extras'):
            extras[extra['key']] = extra['value']
        return extras

    def _get_file_contents(self, file_name):
        path = os.path.join(os.path.dirname(__file__),
                            '..', '..', '..', 'examples',
                            file_name)
        with open(path, 'r') as f:
            return f.read()

class TestDCATAPITProfileParsing(BaseParseTest):

    def test_graph_to_dataset(self):

        contents = self._get_file_contents('dataset.rdf')

        p = RDFParser(profiles=['it_dcat_ap'])

        p.parse(contents)

        datasets = [d for d in p.datasets()]

        eq_(len(datasets), 1)

        dataset = datasets[0]

        # Basic fields
        eq_(dataset['title'], u'Dataset di test DCAT_AP-IT')
        eq_(dataset['notes'], u'dcatapit dataset di test')

        #  Simple values
        eq_(dataset['issued'], u'2016-11-29')
        eq_(dataset['modified'], u'2016-11-29')
        eq_(dataset['identifier'], u'ISBN')
        #eq_(dataset['temporal_start'], '2016-11-01')
        #eq_(dataset['temporal_end'], '2016-11-30')
        eq_(dataset['frequency'], 'UPDATE_CONT')

        geographical_name = dataset['geographical_name'][1:-1].split(',') if ',' in dataset['geographical_name'] else [dataset['geographical_name']]
        geographical_name.sort()
        geographical_name = '{' + ','.join([str(x) for x in geographical_name]) + '}'
        eq_(geographical_name, '{ITA_BZO}')

        eq_(dataset['publisher_name'], 'bolzano it')
        eq_(dataset['publisher_identifier'], '234234234')
        eq_(dataset['creator_name'], 'test')
        eq_(dataset['creator_identifier'], '412946129')
        eq_(dataset['holder_name'], 'bolzano')
        eq_(dataset['holder_identifier'], '234234234')

        alternate_identifier = set([i['identifier'] for i in json.loads(dataset['alternate_identifier'])])
        eq_(alternate_identifier, set(['ISBN:123', 'TEST']))

        theme = dataset['theme']
        theme = json.loads(dataset['theme'])
        allowed_themes = ('ECON', 'ENVI',)
        assert theme, 'got {}'.format(dataset['theme'])
        for t in theme:
            assert t.get('theme') in allowed_themes, "themes {} not in {}".format(theme, allowed_themes)

        eq_(dataset['geographical_geonames_url'], 'http://www.geonames.org/3181913')

        language = dataset['language'][1:-1].split(',') if ',' in dataset['language'] else [dataset['language']]
        language.sort()
        language = '{' + ','.join([str(x) for x in language]) + '}'
        eq_(language, '{DEU,ENG,ITA}')
        
        eq_(dataset['is_version_of'], 'http://dcat.geo-solutions.it/dataset/energia-da-fonti-rinnovabili2')

        conforms_to = json.loads(dataset['conforms_to'])
        conforms_to_ids = set([c['identifier'] for c in conforms_to])
        eq_(conforms_to_ids, set('CONF1,CONF2,CONF3'.split(',')))

        # Multilang values
        ok_(dataset['DCATAPIT_MULTILANG_BASE'])

        multilang_notes = dataset['DCATAPIT_MULTILANG_BASE'].get('notes', None)
        ok_(multilang_notes)
        eq_(multilang_notes['de'], u'dcatapit test-dataset')
        eq_(multilang_notes['it'], u'dcatapit dataset di test')
        eq_(multilang_notes['en_GB'], u'dcatapit dataset test')

        multilang_holder_name = dataset['DCATAPIT_MULTILANG_BASE'].get('holder_name', None)
        ok_(multilang_holder_name)
        eq_(multilang_holder_name['de'], u'bolzano')
        eq_(multilang_holder_name['it'], u'bolzano')
        eq_(multilang_holder_name['en_GB'], u'bolzano')

        multilang_title = dataset['DCATAPIT_MULTILANG_BASE'].get('title', None)
        ok_(multilang_title)
        eq_(multilang_title['de'], u'Dcatapit Test-Dataset')
        eq_(multilang_title['it'], u'Dataset di test DCAT_AP-IT')
        eq_(multilang_title['en_GB'], u'DCAT_AP-IT test dataset')

        multilang_pub_name = dataset['DCATAPIT_MULTILANG_BASE'].get('publisher_name', None)
        ok_(multilang_pub_name)
        eq_(multilang_pub_name['en_GB'], u'bolzano en')
        eq_(multilang_pub_name['it'], u'bolzano it it')


    def test_groups_to_themes_mapping(self):
        config[DCATAPIT_THEMES_MAP] = os.path.join(os.path.dirname(__file__), 
                                                   '..', 
                                                   '..', 
                                                   '..', 
                                                   'examples', 
                                                   'themes_mapping.json')

        url = 'http://some.test.harvest.url'

        groups_non_mappable = [{'name': 'non-mappable', 'display_name': 'non-mappable'}], []
        groups_mappable = [{'name': 'agriculture', 'display_name': 'agricoltura-e-allevamento'}],\
                           [{'key': 'theme', 'value': 'AGRI'}]


        harvest_obj = self._make_harvest_object(url, groups_non_mappable[0])

        harvester = CKANMappingHarvester()
        
        def get_path(fname):
            return os.path.join(os.path.dirname(__file__),
                                '..', '..', '..', 'examples', fname)

        licenses = get_path('licenses.rdf')
        self.g = _get_graph(path=licenses)

        load_from_graph(path=licenses)
        rev = getattr(Session, 'revision', None)
        Session.flush()
        Session.revision = rev


        # clean, no mapping
        harvester.import_stage(harvest_obj)
        hdata = json.loads(harvest_obj.content)
        eq_([t for t in hdata.get('extras', []) if t['key'] == 'theme'], [])

    
        # test mapping
        hdata = json.loads(harvest_obj.content)
        hdata['groups'] = groups_mappable[0]
        harvest_obj.content = json.dumps(hdata)

        harvester.import_stage(harvest_obj)
        hdata = json.loads(harvest_obj.content)
        eq_([t for t in hdata.get('extras', []) if t['key'] == 'theme'], groups_mappable[1])



    def _make_harvest_object(self, mock_url, groups):
        source_dict = {
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
        Session.revision = repo.new_revision()
        harvest_job = helpers.call_action('harvest_job_create',
                                    default_ctx,
                                    source_id=harvest_source['id'],
                                    )

        hdata = {'groups': groups}
        Session.flush()
        Session.revision = repo.new_revision()

        harvest_object = helpers.call_action('harvest_object_create',
                                    default_ctx,
                                    job_id=harvest_job['id'],
                                    )
        

        Session.flush()
        Session.revision = repo.new_revision()

        hobj = HarvestObject.get(harvest_object['id'])
        hobj.content = json.dumps(hdata)
        return hobj

    def setUp(self):
        helpers.reset_db()

    def tearDown(self):
        Session.rollback()

    def test_mapping(self):

        # multilang requires lang to be set
        from pylons.i18n.translation import set_lang, get_lang
        import pylons
        class dummyreq(object):
            class p(object):
                translator = object()
            environ = {'pylons.pylons': p()}
        pylons.request = dummyreq()
        pylons.translator.pylons_lang = 'en_GB'
        set_lang('en_GB')
        assert get_lang() == 'en_GB'

        assert 'dcatapit_theme_group_mapper' in config['ckan.plugins'], "No dcatapit_theme_group_mapper plugin in config"
        contents = self._get_file_contents('dataset.rdf')

        p = RDFParser(profiles=['it_dcat_ap'])

        p.parse(contents)
        datasets = [d for d in p.datasets()]
        eq_(len(datasets), 1)
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
            org  = call_action('organization_create',
                                context={'user': user_name},
                                name='dummy')
        existing_g = Group.by_name('existing-group')
        if existing_g is None:
            existing_g  = call_action('group_create',
                                      context={'user': user_name},
                                      name='existing-group')

        context = {'user': 'dummy',
                   'ignore_auth': True,
                   'defer_commit': False}
        package_schema = schema.default_create_package_schema()
        context['schema'] = package_schema
        _p = {'frequency': 'manual',
              'publisher_name': 'dummy',
              'extras': [{'key':'theme', 'value':['non-mappable', 'thememap1']}],
              'groups': [],
              'title': 'dummy',
              'holder_name': 'dummy',
              'holder_identifier': 'dummy',
              'name': 'dummy',
              'notes': 'dummy',
              'owner_org': 'dummy',
              'modified': datetime.now(),
              'publisher_identifier': 'dummy',
              'metadata_created' : datetime.now(),
              'metadata_modified': datetime.now(),
              'guid': unicode(uuid.uuid4),
              'identifier': 'dummy'}
        
        package_dict.update(_p)
        config[DCATAPIT_THEME_TO_MAPPING_SOURCE] = ''
        package_data = call_action('package_create', context=context, **package_dict)

        p = Package.get(package_data['id'])

        # no groups should be assigned at this point (no map applied)
        assert {'theme': ['non-mappable', 'thememap1']} == p.extras, '{} vs {}'.format(_p['extras'], p.extras)
        assert [] == p.get_groups(group_type='group'), 'should be {}, got {}'.format([], p.get_groups(group_type='group'))

        package_data = call_action('package_show', context=context, id=package_data['id'])

        # use test mapping, which replaces thememap1 to thememap2 and thememap3
        test_map_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'examples', 'test_map.ini')
        config[DCATAPIT_THEME_TO_MAPPING_SOURCE] = test_map_file

        package_dict['theme'] = ['non-mappable', 'thememap1']

        expected_groups_existing = ['existing-group']
        expected_groups_new = expected_groups_existing + ['somegroup1', 'somegroup2']
        expected_groups_multi = expected_groups_new + ['othergroup']

        package_dict.pop('extras', None)
        p = Package.get(package_data['id'])
        context['package'] = p 

        package_data = call_action('package_update',
                                   context=context,
                                   **package_dict)
        
        #meta.Session.flush()
        #meta.Session.revision = repo.new_revision()

        # check - only existing group should be assigned
        p = Package.get(package_data['id'])
        groups = [g.name for g in p.get_groups(group_type='group')]

        assert expected_groups_existing == groups, (expected_groups_existing, 'vs', groups,)

        config[DCATAPIT_THEME_TO_MAPPING_ADD_NEW_GROUPS] = 'true'


        package_dict['theme'] = ['non-mappable', 'thememap1']
        package_data = call_action('package_update', context=context, **package_dict)


        meta.Session.flush()
        meta.Session.revision = repo.new_revision()

        # recheck - this time, new groups should appear
        p = Package.get(package_data['id'])
        groups = [g.name for g in p.get_groups(group_type='group')]

        assert len(expected_groups_new) == len(groups), (expected_groups_new, 'vs', groups,)
        assert set(expected_groups_new) == set(groups), (expected_groups_new, 'vs', groups,)

        package_dict['theme'] = ['non-mappable', 'thememap1', 'thememap-multi']
        package_data = call_action('package_update', context=context, **package_dict)

        meta.Session.flush()
        meta.Session.revision = repo.new_revision()

        # recheck - there should be no duplicates
        p = Package.get(package_data['id'])
        groups = [g.name for g in p.get_groups(group_type='group')]

        assert len(expected_groups_multi) == len(groups), (expected_groups_multi, 'vs', groups,)
        assert set(expected_groups_multi) == set(groups), (expected_groups_multi, 'vs', groups,)

        package_data = call_action('package_update', context=context, **package_dict)

        meta.Session.flush()
        meta.Session.revision = repo.new_revision()

        # recheck - there still should be no duplicates
        p = Package.get(package_data['id'])
        groups = [g.name for g in p.get_groups(group_type='group')]

        assert len(expected_groups_multi) == len(groups), (expected_groups_multi, 'vs', groups,)
        assert set(expected_groups_multi) == set(groups), (expected_groups_multi, 'vs', groups,)

        meta.Session.rollback()

    def test_license(self):
        
        def get_path(fname):
            return os.path.join(os.path.dirname(__file__),
                        '..', '..', '..', 'examples', fname)
        licenses = get_path('licenses.rdf')
        load_from_graph(path=licenses)
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
                                'license_type': 'http://dati.gov.it/onto/controlledvocabulary/License/A311_GFDL13'
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
            "got license {}, instead of {}".format(license_ref, unknown.license_type)

        gpl = License.get(dataset['resources'][1]['license_type'])
        assert gpl is not None

        license_ref = g.value(r2, DCT.license)
        license_type = g.value(license_ref, DCT.type)
        
        assert license_ref is not None

        assert str(license_ref) == gpl.document_uri
        assert str(license_type) == gpl.license_type

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
            raise ValueError("No resource for {}".format(res_uri))

        new_res_unknown = _find_res(str(r1))
        new_res_gpl = _find_res(str(r2))

        assert new_res_unknown['license_type'] == unknown.uri, (new_res_unknown['license_type'], unknown.uri,)
        assert new_res_gpl['license_type'] == dataset['resources'][1]['license_type']


    def test_conforms_to(self):

        conforms_to_in = [{'identifier': 'CONF1',
                                       'uri': 'http://conf01/abc',
                                 'title': {'en': 'title', 'it': 'title'},
                                 'referenceDocumentation': ['http://abc.efg/'],},
                                {'identifier': 'CONF2',
                                 'title': {'en': 'title', 'it': 'title'},
                                 'description': {'en': 'descen', 'it': 'descit'},
                                 'referenceDocumentation': ['http://abc.efg/'],},
                                 ]
        dataset = {
            'id': '4b6fe9ca-dc77-4cec-92a4-55c6624a5bd6',
            'name': 'test-dataset',
            'title': 'Dataset di test DCAT_AP-IT',
            'notes': 'dcatapit dataset di test',
            'metadata_created': '2015-06-26T15:21:09.034694',
            'metadata_modified': '2015-06-26T15:21:09.075774',
            'tags': [{'name': 'Tag 1'}, {'name': 'Tag 2'}],
            'issued':'2016-11-29',
            'modified':'2016-11-29',
            'identifier':'ISBN',
            'temporal_start':'2016-11-01',
            'temporal_end':'2016-11-30',
            'frequency':'UPDATE_CONT',
            'publisher_name':'bolzano',
            'publisher_identifier':'234234234',
            'creator_name':'test',
            'creator_identifier':'412946129',
            'holder_name':'bolzano',
            'holder_identifier':'234234234',
            'alternate_identifier':'ISBN,TEST',
            'theme':'{ECON,ENVI}',
            'geographical_geonames_url':'http://www.geonames.org/3181913',
            'language':'{DEU,ENG,ITA}',
            'is_version_of':'http://dcat.geo-solutions.it/dataset/energia-da-fonti-rinnovabili2',
            'conforms_to':json.dumps(conforms_to_in)
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

        assert len(dataset_conforms_to) == len(conforms_to_in), "got {}, should be {}".format(len(d['conforms_to']), len(conforms_to_in))
        for conf in dataset_conforms_to:
            check = conforms_to[conf['identifier']]
            for k,v  in check.items():
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

        creators = [{'creator_name': {DEFAULT_LANG: 'abc', 'it': 'abc it'}, 'creator_identifier': "ABC"},
                    {'creator_name': {DEFAULT_LANG: 'cde', 'it': 'cde it'}, 'creator_identifier': "CDE"},
                    ]
        dataset = {
            'id': '4b6fe9ca-dc77-4cec-92a4-55c6624a5bd6',
            'name': 'test-dataset',
            'title': 'Dataset di test DCAT_AP-IT',
            'notes': 'dcatapit dataset di test',
            'metadata_created': '2015-06-26T15:21:09.034694',
            'metadata_modified': '2015-06-26T15:21:09.075774',
            'tags': [{'name': 'Tag 1'}, {'name': 'Tag 2'}],
            'issued':'2016-11-29',
            'modified':'2016-11-29',
            'identifier':'ISBN',
            'temporal_start':'2016-11-01',
            'temporal_end':'2016-11-30',
            'frequency':'UPDATE_CONT',
            'publisher_name':'bolzano',
            'publisher_identifier':'234234234',
            'creator_name':'test',
            'creator_identifier':'412946129',
            'holder_name':'bolzano',
            'holder_identifier':'234234234',
            'alternate_identifier':'ISBN,TEST',
            'theme':'{ECON,ENVI}',
            'geographical_geonames_url':'http://www.geonames.org/3181913',
            'language':'{DEU,ENG,ITA}',
            'is_version_of':'http://dcat.geo-solutions.it/dataset/energia-da-fonti-rinnovabili2',
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
            assert c['creator_identifier'] in creators_dict.keys(), "no {} key in {}".format(c['creator_identifier'],
                                                                                             creators_dict.keys())
            assert c['creator_name'] == creators_dict[c['creator_identifier']]['creator_name'],\
                "{} vs {}".format(c['creator_name'], creators_dict[c['creator_identifier']]['creator_name'])
        for c in creators_dict.keys():
            assert c in [_c['creator_identifier'] for _c in creators_in]
            cdata = creators_dict[c]
            assert cdata in creators_in


    def test_temporal_coverage(self):

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
            'issued':'2016-11-29',
            'modified':'2016-11-29',
            'identifier':'ISBN',
            'temporal_start':'2016-11-01T00:00:00',
            'temporal_end':'2016-11-30T00:00:00',
            'temporal_coverage': json.dumps(temporal_coverage),
            'frequency':'UPDATE_CONT',
            'publisher_name':'bolzano',
            'publisher_identifier':'234234234',
            'creator_name':'test',
            'creator_identifier':'412946129',
            'holder_name':'bolzano',
            'holder_identifier':'234234234',
            'alternate_identifier':'ISBN,TEST',
            'theme':'{ECON,ENVI}',
            'geographical_geonames_url':'http://www.geonames.org/3181913',
            'language':'{DEU,ENG,ITA}',
            'is_version_of':'http://dcat.geo-solutions.it/dataset/energia-da-fonti-rinnovabili2',
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
        except validators.Invalid, err:
            assert False, "Temporal coverage should be valid: {}".format(err)

        temp_cov = json.loads(d['temporal_coverage'])

        assert len(temp_cov) == len(temporal_coverage),\
                "got {} items instead of {}".format(len(temp_cov),
                                                    len(temporal_coverage))

        set1 = set([tuple(d.items()) for d in temp_cov])
        set2 = set([tuple(d.items()) for d in temporal_coverage])

        assert set1 == set2, "Got different temporal coverage sets: \n{}\n vs\n {}".format(set1, set2)



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
            'issued':'2016-11-29',
            'modified':'2016-11-29',
            'frequency':'UPDATE_CONT',
            'publisher_name':'bolzano',
            'publisher_identifier':'234234234',
            'creator_name':'test',
            'creator_identifier':'412946129',
            'holder_name':'bolzano',
            'holder_identifier':'234234234',
            'alternate_identifier':'ISBN,TEST',
            'theme': json.dumps(subthemes),
        }

        s = RDFSerializer()
        p = RDFParser(profiles=['euro_dcat_ap', 'it_dcat_ap'])
        
        serialized = s.serialize_dataset(dataset)

        p.parse(serialized)
        datasets = list(p.datasets())
        
        assert len(datasets) == 1
        d = datasets[0]
        themes = json.loads(dataset['theme'])
        assert(len(themes) == len(subthemes) == 2)
        for t in themes:
            if t['theme'] == 'ENVI':
                assert t['subthemes'] == []
            elif t['theme'] == 'AGRI':
                assert set(t['subthemes']) == set(subthemes[0]['subthemes'])
            else:
                assert False, "Unknown theme: {}".format(t)
