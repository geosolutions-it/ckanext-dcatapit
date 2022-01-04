import json
import unittest
import uuid
from functools import reduce
from uuid import UUID

import pytest
from rdflib import BNode, Literal, URIRef
from rdflib.namespace import RDF

try:
    from ckan.tests import factories, helpers
except ImportError:
    from ckan.new_tests import helpers, factories

from ckan.common import config
from ckan.model import Group, repo, meta
from ckan.plugins import toolkit
import ckan.tests.factories as factories

from ckanext.dcat import utils
from ckanext.dcat.processors import RDFSerializer
from ckanext.dcat.profiles import (
    ADMS,
    DCAT,
    DCT,
    FOAF,
    SCHEMA,
    SKOS,
)
from ckanext.dcatapit import interfaces
from ckanext.dcatapit.dcat.const import DCATAPIT
from ckanext.dcatapit.mapping import theme_aggr_to_theme_uris, theme_name_to_uri, themes_to_aggr_json
from ckanext.dcatapit.schema import FIELD_THEMES_AGGREGATE
from ckanext.dcatapit.validators import parse_date as pdate


DEFAULT_LANG = config.get('ckan.locale_default', 'it')
Session = meta.Session


class BaseSerializeTest(unittest.TestCase):

    def _triples(self, graph, subject, predicate, _object, data_type=None):
        if not (isinstance(_object, URIRef) or isinstance(_object, BNode) or _object is None):
            if data_type:
                _object = Literal(_object, datatype=data_type)
            else:
                _object = Literal(_object)
        triples = [t for t in graph.triples((subject, predicate, _object))]
        return triples

    def _triple(self, graph, subject, predicate, _object, data_type=None):
        triples = self._triples(graph, subject, predicate, _object, data_type)
        return triples[0] if triples else None


@pytest.mark.usefixtures("with_request_context")
class TestDCATAPITProfileSerializeDataset(BaseSerializeTest):

    def _get_user(self):
        user = toolkit.get_action('get_site_user')(
            {'ignore_auth': True, 'defer_commit': True},
            {})
        return user

    def test_graph_from_dataset(self):

        src_conforms_to = [{'identifier': 'CONF1',
                           'uri': 'conf01',
                           'title': {'en': 'title1EN', 'it': 'title1IT'},
                           'referenceDocumentation': ['http://abc.efg/'], },
                          {'identifier': 'CONF2',
                           'title': {'en': 'title2EN', 'it': 'title2IT'},
                           'description': {'en': 'desc2EN', 'it': 'desc2IT'},
                           'referenceDocumentation': ['http://abc.efg/'], },
                          ]

        src_alt_identifiers = [{'identifier': 'aaaabc',
                                'agent': {'agent_identifier': 'agent01',
                                          'agent_name': {'en': 'Agent en 01', 'it': 'Agent it 01'}},
                                },
                               {'identifier': 'other identifier', 'agent': {}}]
        src_creators = [{'creator_name': {'en': 'abcEN', 'it': 'abcIT'}, 'creator_identifier': 'ABC'},
                        {'creator_name': {'en': 'cde'}, 'creator_identifier': 'CDE'},
                        ]

        src_temporal_coverage = [{'temporal_start': '2001-01-01', 'temporal_end': '2001-02-01 10:11:12'},
                                 {'temporal_start': '2001-01-01', 'temporal_end': '2001-02-01 11:12:13'},
                                 ]

        subthemes = [{'theme': 'AGRI', 'subthemes': ['http://eurovoc.europa.eu/100253',
                                                     'http://eurovoc.europa.eu/100258']},
                     {'theme': 'ENVI', 'subthemes': []}]

        pub_it = 'IT publisher'
        holder_it = 'IT holder'

        org = factories.Organization(identifier=uuid.uuid4(), is_org=True, name=uuid.uuid4())
        src_dataset = {
            # 'id': '4b6fe9ca-dc77-4cec-92a4-55c6624a5bd6',
            'owner_org': org['id'],
            'name': str(uuid.uuid4()),
            'title': 'Dataset di test DCAT_AP-IT',
            'notes': 'dcatapit dataset di test',
            'metadata_created': '2015-06-26T15:21:09.034694',
            'metadata_modified': '2015-06-26T15:21:09.075774',
            'tags': [{'name': 'Tag 1'}, {'name': 'Tag 2'}],
            'issued': '2016-11-29',
            'modified': '2016-11-29',
            'identifier': str(uuid.uuid4()),
            'temporal_start': '2016-11-01',
            'temporal_end': '2016-11-30',
            'frequency': 'UPDATE_CONT',
            'publisher_name': pub_it,
            'publisher_identifier': '234234234',
            'creator_name': 'test',
            'creator_identifier': '412946129',
            'holder_name': holder_it,
            'holder_identifier': '234234234',
            'alternate_identifier': json.dumps(src_alt_identifiers),
            'temporal_coverage': json.dumps(src_temporal_coverage),
            # 'theme':'ECON',
            'geographical_geonames_url': 'http://www.geonames.org/3181913',
            'language': '{DEU,ENG,ITA}',
            'is_version_of': 'http://dcat.geo-solutions.it/dataset/energia-da-fonti-rinnovabili2',
            'conforms_to': json.dumps(src_conforms_to),
            'creator': json.dumps(src_creators),
            FIELD_THEMES_AGGREGATE: json.dumps(subthemes),
            'theme': theme_aggr_to_theme_uris(subthemes),
        }

        src_pub_names = {'it': pub_it,
                         'en': 'EN publisher'}
        src_holder_names = {'it': holder_it,
                            'en': 'EN holder name'}

        multilang_fields = [('publisher_name', 'package', k, v) for k, v in src_pub_names.items()] +\
                           [('holder_name', 'package', k, v) for k, v in src_holder_names.items()]

        pkg = helpers.call_action('package_create', {'defer_commit': True}, **src_dataset)
        Session.flush()
        pkg_id = pkg['id']
        src_dataset['id'] = pkg_id

        for field_name, field_type, lang, text in multilang_fields:
            interfaces.upsert_package_multilang(pkg_id, field_name, field_type, lang, text)

        # loc_dict = interfaces.get_for_package(pkg_id)
        #assert loc_dict['publisher_name'] == pub_names
        #assert loc_dict['holder_name'] == holder_names

        # LEGACY: temporary bug for comaptibility with interfaces.get_language(),
        # which will return lang[0]
        # pub_names.update({DEFAULT_LANG: src_dataset['publisher_name']})
        # pub_names.update({DEFAULT_LANG[0]: dataset['publisher_name']})
        # holder_names.update({DEFAULT_LANG: src_dataset['holder_name']})
        # holder_names.update({DEFAULT_LANG[0]: dataset['holder_name']})

        s = RDFSerializer()
        g = s.g

        dataset_graph = s.graph_from_dataset(pkg)

        self.assertEqual(str(dataset_graph), str(utils.dataset_uri(src_dataset)), 'Dataset URI changes')

        # Basic fields
        self.assertIsNotNone(self._triple(g, dataset_graph, RDF.type, DCATAPIT.Dataset))
        self.assertIsNotNone(self._triple(g, dataset_graph, DCT.title, src_dataset['title']))
        self.assertIsNotNone(self._triple(g, dataset_graph, DCT.description, src_dataset['notes']))

        self.assertIsNotNone(self._triple(g, dataset_graph, DCT.identifier, src_dataset['identifier']))

        # Tags
        self.assertEqual(2, len([t for t in g.triples((dataset_graph, DCAT.keyword, None))]))
        for tag in src_dataset['tags']:
            self.assertIsNotNone(self._triple(g, dataset_graph, DCAT.keyword, tag['name']))

        # conformsTo
        conforms_to_nodes = list(g.objects(dataset_graph, DCT.conformsTo))
        self.assertEqual(2, len(conforms_to_nodes))

        src_conforms_dict = {d['identifier']: d for d in src_conforms_to}
        for conf_node in conforms_to_nodes:
            conf_id = str(conf_node)

            identifier = g.value(conf_node, DCT.identifier)
            titles = list(g.objects(conf_node, DCT.title))
            descs = list(g.objects(conf_node, DCT.description))
            references = list(g.objects(conf_node, DCATAPIT.referenceDocumentation))

            src_conforms = src_conforms_dict.get(str(identifier))

            assert isinstance(src_conforms, dict)

            if src_conforms.get('uri'):
                assert src_conforms['uri'] == str(conf_node)
            assert len(titles), 'missing titles'

            assert (len(descs) > 0) == bool(src_conforms.get('description')), 'missing descriptions'

            titles_dict = {title.language: str(title) for title in titles}
            for lang, src_value in src_conforms['title'].items():  # looping on the source items bc graph info may have been augmented
                self.assertEqual(src_value, titles_dict[lang], f'Titles do not match for lang:{lang}')

            descr_dict = {descr.language: str(descr) for descr in descs}
            for lang, src_value in src_conforms.get('description', {}).items():  # looping on the source items bc graph info may have been augmented
                self.assertEqual(src_value, descr_dict[lang], f'descriptions do not match for lang:{lang}')

            ref_docs = src_conforms.get('referenceDocumentation')
            assert len(references) == len(ref_docs), 'missing reference documentation'

            for dref in references:
                assert str(dref) in ref_docs, '{} not in {}'.format(dref, ref_docs)

            for ref in ref_docs:
                assert URIRef(ref) in references

        # alternate identifiers
        alt_ids = [a[-1] for a in g.triples((None, ADMS.identifier, None))]
        alt_ids_dict = dict((a['identifier'], a) for a in src_alt_identifiers)

        for alt_id in alt_ids:
            identifier = g.value(alt_id, SKOS.notation)
            src_conforms = alt_ids_dict[str(identifier)]
            assert str(identifier) == src_conforms['identifier']
            if src_conforms.get('agent'):
                agent_ref = g.value(alt_id, DCT.creator)
                assert agent_ref is not None

                # agent_identifier = g.value(agent_ref, DCT.identifier)
                agent_name = {v.language: str(v) for v in g.objects(agent_ref, FOAF.name)}

                for a in set(src_conforms['agent']['agent_name'].items()):
                    self.assertIn(a, set(agent_name.items()), "Agents name not found")

                self.assertEqual(src_conforms['agent']['agent_identifier'],
                                 str(g.value(agent_ref, DCT.identifier)),
                                 "Agents identifier mismatch")
        # creators
        creators_in = list(g.objects(dataset_graph, DCT.creator))
        assert len(src_creators) == len(creators_in)

        for cref in creators_in:
            c_identifier = str(g.value(cref, DCT.identifier))
            cnames = dict((str(c.language) if c.language else DEFAULT_LANG, str(c)) for c in g.objects(cref, FOAF.name))
            src_creator = [x for x in src_creators if x['creator_identifier']==c_identifier]
            self.assertEqual(1, len(src_creator))
            for lang, name in src_creator[0]['creator_name'].items():
                self.assertEqual(name, cnames[lang])

            # c_dict = {'creator_name': cnames,
            #           'creator_identifier': str(c_identifier)}
            # assert c_dict in src_creators, 'no {} in {}'.format(c_dict, src_creators)

        # temporal coverage
        temp_exts = list(g.triples((dataset_graph, DCT.temporal, None)))
        assert len(temp_exts) == len(src_temporal_coverage)

        # normalize values
        for item in src_temporal_coverage:
            for k, v in item.items():
                item[k] = pdate(v)

        temp_ext = []
        for interval_t in temp_exts:
            interval = interval_t[-1]
            start = g.value(interval, SCHEMA.startDate)
            end = g.value(interval, SCHEMA.endDate)
            assert start is not None
            assert end is not None
            temp_ext.append({'temporal_start': pdate(str(start)),
                             'temporal_end': pdate(str(end))})

        set1 = set([tuple(d.items()) for d in temp_ext])
        set2 = set([tuple(d.items()) for d in src_temporal_coverage])
        assert set1 == set2, 'Got different temporal coverage sets: \n{}\n vs\n {}'.format(set1, set2)

        for pub_ref in g.objects(dataset_graph, DCT.publisher):
            _pub_names = list(g.objects(pub_ref, FOAF.name))

            assert len(_pub_names)

            for pub_name in _pub_names:
                if pub_name.language:
                    self.assertIn(str(pub_name.language), src_pub_names.keys(),
                                  f'Missing publisher lang:{pub_name.language}')
                    self.assertEqual(src_pub_names[str(pub_name.language)], str(pub_name),
                                     f'Mismatching publisger name lang:{pub_name.language} ')

        # skipping holder checks: local dataset imports holder from owner org
        # for holder_ref in g.objects(dataset_graph, DCT.rightsHolder):
        #     _holder_names = list(g.objects(holder_ref, FOAF.name))
        #
        #     assert len(_holder_names)
        #
        #     for holder_name in _holder_names:
        #         if holder_name.language:
        #             self.assertIn(str(holder_name.language), src_holder_names,
        #                           f'Missing holder lang:{holder_name.language}')
        #             assert src_holder_names[str(holder_name.language)] == str(holder_name), '{} vs {}'.format(holder_name, src_holder_names)

    def test_holder(self):
        org = {'name': 'org-test',
               'title': 'Test org',
               'identifier': 'abc'}

        pkg1 = {
            # 'id': '2b6fe9ca-dc77-4cec-92a4-55c6624a5bd6',
            'name': 'test-dataset-1',
            'title': 'Dataset di test DCAT_AP-IT',
            'notes': 'dcatapit dataset di test',
            'metadata_created': '2015-06-26T15:21:09.034694',
            'metadata_modified': '2015-06-26T15:21:09.075774',
            'modified': '2016-11-29',
            'identifier': str(uuid.uuid4()),
            'frequency': 'UPDATE_CONT',
            'publisher_name': 'bolzano',
            'publisher_identifier': '234234234',
            'creator_name': 'test',
            'creator_identifier': '789789789',
            'holder_name': 'bolzano',
            'holder_identifier': '234234234',
            FIELD_THEMES_AGGREGATE: themes_to_aggr_json(('ECON',)),
            'theme': json.dumps([theme_name_to_uri(name) for name in ('ECON',)]),
            'dataset_is_local': False,
            'language': '{DEU,ENG,ITA}',
        }

        pkg2 = {
            # 'id': 'eb6fe9ca-dc77-4cec-92a4-55c6624a5b00',
            'name': 'test-dataset-2',
            'title': 'Dataset di test DCAT_AP-IT 2',
            'notes': 'dcatapit dataset di test',
            'metadata_created': '2015-06-26T15:21:09.034694',
            'metadata_modified': '2015-06-26T15:21:09.075774',
            'modified': '2016-11-29',
            'identifier': str(uuid.uuid4()),
            'frequency': 'UPDATE_CONT',
            'publisher_name': 'bolzano',
            'publisher_identifier': '234234234',
            'creator_name': 'test',
            'creator_identifier': '123123123123',
            FIELD_THEMES_AGGREGATE: themes_to_aggr_json(('ENVI',)),
            'theme': json.dumps([theme_name_to_uri(name) for name in ('ENVI',)]),
            'dataset_is_local': True,
            'language': '{DEU,ENG,ITA}',
            'owner_org': org['name'],
        }

        src_packages = [pkg1, pkg2]
        ctx = {'ignore_auth': True,
               'user': self._get_user()['name']}

        org_loaded = Group.by_name(org['name'])
        if org_loaded:
            org_dict = org_loaded.__dict__
        else:
            org_dict = helpers.call_action('organization_create', context=ctx, **org)
        pkg1['owner_org'] = org_dict['id']
        pkg2['owner_org'] = org_dict['id']

        created_packages = [helpers.call_action('package_create', context=ctx, **pkg) for pkg in src_packages]

        for pkg in created_packages:
            s = RDFSerializer()
            g = s.g
            dataset_ref = s.graph_from_dataset(pkg)
            has_identifier = False
            rights_holders = list(g.objects(dataset_ref, DCT.rightsHolder))

            assert len(rights_holders), 'There should be one rights holder for\n {}:\n {}'.\
                format(pkg, s.serialize_dataset(pkg))

            for holder_ref in rights_holders:
                _holder_names = list(g.objects(holder_ref, FOAF.name))
                _holder_ids = list((str(ob) for ob in g.objects(holder_ref, DCT.identifier)))

                # local dataset will use organization name only
                # while remote will have at least two names - one with lang, one default without lang
                if pkg['dataset_is_local']:
                    num_holder_names = 1
                else:
                    num_holder_names = 2
                assert len(_holder_names) == num_holder_names, _holder_names
                assert len(_holder_ids) == 1

                test_id = pkg.get('holder_identifier') or org_dict['identifier']
                has_identifier = _holder_ids[0] == test_id
                assert has_identifier, \
                    f'No identifier in {_holder_ids} (expected {test_id}) for\n {pkg}\n{s.serialize_dataset(pkg)}'
