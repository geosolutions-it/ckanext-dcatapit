import json

import nose

from pylons import config

from dateutil.parser import parse as parse_date
from rdflib import URIRef, BNode, Literal
from rdflib.namespace import RDF

from geomet import wkt

try:
    from ckan.tests import helpers, factories
except ImportError:
    from ckan.new_tests import helpers, factories

from ckan.plugins import toolkit
from ckan.model import Session, repo
from ckanext.dcat import utils
from ckanext.dcat.processors import RDFSerializer
from ckanext.dcat.profiles import (DCAT, DCT, ADMS, XSD, VCARD, FOAF, SCHEMA,
                                   SKOS, LOCN, GSP, OWL, SPDX, GEOJSON_IMT)
from ckanext.dcatapit.dcat.profiles import (DCATAPIT)
from ckanext.dcatapit.validators import parse_date as pdate
from ckanext.dcatapit import interfaces

eq_ = nose.tools.eq_
assert_true = nose.tools.assert_true

DEFAULT_LANG = config.get('ckan.locale_default', 'en')

class BaseSerializeTest(object):

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


class TestDCATAPITProfileSerializeDataset(BaseSerializeTest):

    def _get_user(self):
        user = toolkit.get_action('get_site_user')(
            {'ignore_auth': True, 'defer_commit': True},
            {})
        return user

    def test_graph_from_dataset(self):

        conforms_to_in = [{'identifier': 'CONF1',
                                       'uri': 'conf01',
                                 'title': {'en': 'title', 'it': 'title'},
                                 'referenceDocumentation': ['http://abc.efg/'],},
                                {'identifier': 'CONF2',
                                 'title': {'en': 'title', 'it': 'title'},
                                 'description': {'en': 'descen', 'it': 'descit'},
                                 'referenceDocumentation': ['http://abc.efg/'],},
                                 ]

        alternate_identifiers = [{'identifier': 'aaaabc',
                                 'agent': {'agent_identifier': 'agent01',
                                           'agent_name': {'en': 'Agent en 01', 'it': 'Agent it 01'}},
                                 },
                                 {'identifier': 'other identifier', 'agent': {}}]
        creators = [{'creator_name': {'en': 'abc'}, 'creator_identifier': "ABC"},
                    {'creator_name': {'en': 'cde'}, 'creator_identifier': "CDE"},
                    ]

        temporal_coverage = [{'temporal_start': '2001-01-01', 'temporal_end': '2001-02-01 10:11:12'},
                             {'temporal_start': '2001-01-01', 'temporal_end': '2001-02-01 11:12:13'},
                            ]

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
            'alternate_identifier':json.dumps(alternate_identifiers),
            'temporal_coverage': json.dumps(temporal_coverage),
            #'theme':'ECON',
            'geographical_geonames_url':'http://www.geonames.org/3181913',
            'language':'{DEU,ENG,ITA}',
            'is_version_of':'http://dcat.geo-solutions.it/dataset/energia-da-fonti-rinnovabili2',
            'conforms_to':json.dumps(conforms_to_in),
            'creator': json.dumps(creators),
            'theme': json.dumps(subthemes),


        }
        
        pkg_id = dataset['id']
        
        pub_names = {'it': 'IT publisher',
                     'es': 'EN publisher'}
        holder_names = {'it': 'IT holder name',
                        'es': 'EN holder name'}

        multilang_fields = [('publisher_name', 'package', k, v) for k, v in pub_names.items()] +\
                           [('holder_name', 'package', k, v) for k, v in holder_names.items()]
        
        pkg = helpers.call_action('package_create', {'defer_commit': True}, **dataset)
        rev = getattr(Session,  'revision', repo.new_revision())
        Session.flush()
        Session.revision = rev
        pkg_id = pkg['id']

        for field_name, field_type, lang, text in multilang_fields:
            interfaces.upsert_package_multilang(pkg_id, field_name, field_type, lang, text)

        loc_dict = interfaces.get_for_package(pkg_id)
        #assert loc_dict['publisher_name'] == pub_names
        #assert loc_dict['holder_name'] == holder_names


        # temporary bug for comaptibility with interfaces.get_language(),
        # which will return lang[0]
        pub_names.update({DEFAULT_LANG: dataset['publisher_name']})
        # pub_names.update({DEFAULT_LANG[0]: dataset['publisher_name']})
        holder_names.update({DEFAULT_LANG: dataset['holder_name']})
        # holder_names.update({DEFAULT_LANG[0]: dataset['holder_name']})
        
        s = RDFSerializer()
        g = s.g

        dataset_ref = s.graph_from_dataset(dataset)

        eq_(unicode(dataset_ref), utils.dataset_uri(dataset))

        # Basic fields
        assert self._triple(g, dataset_ref, RDF.type, DCATAPIT.Dataset)
        assert self._triple(g, dataset_ref, DCT.title, dataset['title'])
        assert self._triple(g, dataset_ref, DCT.description, dataset['notes'])

        assert self._triple(g, dataset_ref, DCT.identifier, dataset['identifier'])

        # Tags
        eq_(len([t for t in g.triples((dataset_ref, DCAT.keyword, None))]), 2)
        for tag in dataset['tags']:
            assert self._triple(g, dataset_ref, DCAT.keyword, tag['name'])
        
        # conformsTo
        conforms_to = list(g.triples((None, DCT.conformsTo, None)))
        assert conforms_to

        conforms_to_dict = dict((d['identifier'], d) for d in conforms_to_in)
        for conf in conforms_to:
            conf_id = conf[-1]

            identifier = g.value(conf_id, DCT.identifier)
            titles = list(g.objects(conf_id, DCT.title))
            descs = list(g.objects(conf_id, DCT.description))
            references = list(g.objects(conf_id, DCATAPIT.referenceDocumentation))
            
            check = conforms_to_dict.get(str(identifier))
            
            assert isinstance(check, dict)

            if check.get('uri'):
                assert check['uri'] == str(conf_id)
            assert len(titles), "missing titles"
            
            assert (len(descs)> 0) == bool(check.get('description')), "missing descriptions"

            for title in titles:
                tlang = title.language
                tval = str(title)
                assert tval == check['title'][tlang], (tlang, tval, check['title'])

            for desc in descs:
                tlang = desc.language
                tval = str(desc)
                assert tval == check['description'][tlang], (tlang, str(tval), check['description'])
            
            ref_docs = check.get('referenceDocumentation')
            assert len(references) == len(ref_docs), "missing reference documentation"
            
            for dref in references:
                assert str(dref) in ref_docs, "{} not in {}".format(dref, ref_docs)
                                                                
            for ref in ref_docs:
                assert URIRef(ref) in references

        # alternate identifiers
        alt_ids = [a[-1] for a in g.triples((None, ADMS.identifier, None))]
        alt_ids_dict = dict((a['identifier'], a) for a in alternate_identifiers)

        for alt_id in alt_ids:
            identifier = g.value(alt_id, SKOS.notation)
            check = alt_ids_dict[str(identifier)]
            assert str(identifier) == check['identifier']
            if check.get('agent'):
                agent_ref = g.value(alt_id, DCT.creator)
                assert agent_ref is not None

                agent_identifier = g.value(agent_ref, DCT.identifier)

                agent_name = dict((v.language, str(v)) for v in g.objects(agent_ref, FOAF.name))
                
                assert set(agent_name.items()) == set(check['agent']['agent_name'].items()),\
                    "expected {}, got {} for {}".format(check['agent']['agent_name'], agent_name, agent_ref)

                assert str(agent_identifier) == check['agent']['agent_identifier'],\
                    "expected {}, got {}".format(check['agent']['agent_identifier'], agent_identifier)
        # creators
        creators.append({'creator_name':{'en': 'test'},
                         'creator_identifier':'412946129'})
        creators_in = list(g.objects(dataset_ref, DCT.creator))
        assert len(creators) == len(creators_in)

        for cref in creators_in:
            cnames = dict((str(c.language) if c.language else DEFAULT_LANG, str(c)) for c in g.objects(cref, FOAF.name))
            c_identifier = g.value(cref, DCT.identifier)
            c_dict = {'creator_name': cnames,
                      'creator_identifier': str(c_identifier)}
            assert c_dict in creators, "no {} in {}".format(c_dict, creators)

        # temporal coverage
        temporal_coverage.append({'temporal_start': dataset['temporal_start'],
                                  'temporal_end': dataset['temporal_end']})
        temp_exts = list(g.triples((dataset_ref, DCT.temporal, None)))
        assert len(temp_exts) == len(temporal_coverage)
        
        # normalize values
        for item in temporal_coverage:
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
        set2 = set([tuple(d.items()) for d in temporal_coverage])
        assert set1 == set2, "Got different temporal coverage sets: \n{}\n vs\n {}".format(set1, set2)

        for pub_ref in g.objects(dataset_ref, DCT.publisher):
            _pub_names = list(g.objects(pub_ref, FOAF.name))

            assert len(_pub_names) 

            for pub_name in _pub_names:
                if pub_name.language:
                    assert str(pub_name.language) in pub_names, "no {} in {}".format(pub_name.language, pub_names)
                    assert pub_names[str(pub_name.language)] == str(pub_name), "{} vs {}".format(pub_name, pub_names)

        for holder_ref in g.objects(dataset_ref, DCT.rightsHolder):
            _holder_names = list(g.objects(holder_ref, FOAF.name))

            assert len(_holder_names) 

            for holder_name in _holder_names:
                if holder_name.language:
                    assert str(holder_name.language) in holder_names, "no {} in {}".format(holder_name.language, holder_names)
                    assert holder_names[str(holder_name.language)] == str(holder_name), "{} vs {}".format(holder_name, holder_names)


    def test_holder(self):
        org = {'name': 'org-test',
               'title': 'Test org',
               'identifier': "abc"}
        
        pkg1 = {
            'id': '2b6fe9ca-dc77-4cec-92a4-55c6624a5bd6',
            'name': 'test-dataset-1',
            'title': 'Dataset di test DCAT_AP-IT',
            'notes': 'dcatapit dataset di test',
            'metadata_created': '2015-06-26T15:21:09.034694',
            'metadata_modified': '2015-06-26T15:21:09.075774',
            'modified':'2016-11-29',
            'identifier':'ISBNabc',
            'frequency':'UPDATE_CONT',
            'publisher_name':'bolzano',
            'publisher_identifier':'234234234',
            'creator_name':'test',
            'creator_identifier':'412946129',
            'holder_name':'bolzano',
            'holder_identifier':'234234234',
            'theme':'{ECON,ENVI}',
            'language':'{DEU,ENG,ITA}',
        }
        
        pkg2 = {
            'id': 'eb6fe9ca-dc77-4cec-92a4-55c6624a5b00',
            'name': 'test-dataset-2',
            'title': 'Dataset di test DCAT_AP-IT 2',
            'notes': 'dcatapit dataset di test',
            'metadata_created': '2015-06-26T15:21:09.034694',
            'metadata_modified': '2015-06-26T15:21:09.075774',
            'modified':'2016-11-29',
            'identifier':'ISBNcde',
            'frequency':'UPDATE_CONT',
            'publisher_name':'bolzano',
            'publisher_identifier':'234234234',
            'creator_name':'test',
            'creator_identifier':'412946129',
            'theme':'{ECON,ENVI}',
            'language':'{DEU,ENG,ITA}',
            'owner_org': org['name'],
        }

        packages = [pkg1, pkg2]
        ctx = {'ignore_auth': True,
               'user': self._get_user()['name']}

        org_dict = helpers.call_action('organization_create', context=ctx, **org)
        for pkg in packages:
            helpers.call_action('package_create', context=ctx, **pkg)

        for pkg in packages:
            s = RDFSerializer()
            g = s.g
            dataset_ref = s.graph_from_dataset(pkg)
            has_identifier = False
            rights_holders = list(g.objects(dataset_ref, DCT.rightsHolder))

            assert len(rights_holders), "There should be one rights holder for\n {}:\n {}".format(pkg, 
                                                                                                  s.serialize_dataset(pkg))
            for holder_ref in rights_holders:
                _holder_names = list(g.objects(holder_ref, FOAF.name))
                _holder_ids = list((str(ob) for ob in g.objects(holder_ref, DCT.identifier)))

                assert len(_holder_names) == 1
                assert len(_holder_ids) == 1
                
                test_id = pkg.get('holder_identifier') or org_dict['identifier']
                has_identifier = _holder_ids[0] == test_id
                assert has_identifier, "No identifier in {} (expected {}) for\n {}\n{}".format(_holder_ids,
                                                                                           test_id,
                                                                                           pkg,
                                                                                           s.serialize_dataset(pkg))
