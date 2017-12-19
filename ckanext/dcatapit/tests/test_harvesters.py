import os
import json

import unittest
import nose

from ckan.model import Session, Package
from ckan import model
from ckan.plugins import toolkit
from ckan.lib.munge import munge_name

try:
    from ckan.tests import helpers
except ImportError:
    from ckan.new_tests import helpers

from ckanext.harvest.model import HarvestObject
from ckanext.dcatapit.model.license import (load_from_graph, 
    License, LocalizedLicenseName, _get_graph, SKOS)

from ckanext.dcatapit.harvesters.ckanharvester import CKANMappingHarvester
from ckanext.dcatapit.model.license import load_from_graph, License
from ckanext.dcat.harvesters.rdf import DCATRDFHarvester


class HarvestersTestCase(unittest.TestCase):
    
    def _create_harvest_source(self, ctx, mock_url, **kwargs):

        source_dict = {
            'title': 'Test Source',
            'name': 'test-source',
            'url': mock_url,
            'source_type': 'dcat_rdf',
        }
        source_dict.update(**kwargs)
        harvest_source = helpers.call_action('harvest_source_create',
                                       context=ctx, **source_dict)
        return harvest_source

    def _create_harvest_job(self, ctx, harvest_source_id):

        harvest_job = helpers.call_action('harvest_job_create',
                                    context=ctx, source_id=harvest_source_id)
        return harvest_job

    def _create_harvest_obj(self, mock_url, **kwargs):
        ctx = {'session': Session,
               'model': model}
        s = self._create_harvest_source(ctx, mock_url, **kwargs)
        Session.flush()
        j = self._create_harvest_job(ctx, s['id'])
        Session.flush()
        h = helpers.call_action('harvest_object_create',
                                context=ctx, 
                                job_id = j['id'],
                                source_id = s['id'])
        return h


    def test_ckan_harvester_license(self):

        dataset = {'title': 'some title',
                   'id': 'sometitle',
                   'resources': [
                            {
                                'id': 'resource/1111',
                                'url': 'http://resource/1111',
                                'license_type': 'invalid',
                            },
                            {
                                'id': 'resource/2222',
                                'url': 'http://resource/2222',
                                'license_type': 'http://dati.gov.it/onto/controlledvocabulary/License/A311_GFDL13'
                            }
                        ]
                    }
       
        data = json.dumps(dataset)
        harvest_dict = self._create_harvest_obj('http://mock/source/', name='testpkg')
        harvest_obj = HarvestObject.get(harvest_dict['id'])
        harvest_obj.content = data
        h = CKANMappingHarvester()
        h.import_stage(harvest_obj)
        Session.flush()

        pkg_dict = helpers.call_action('package_show', context={}, name_or_id='sometitle')
        self.assertTrue(len(pkg_dict['resources']) == 2)

        resources = pkg_dict['resources']
        r = dataset['resources']
        for res in resources:
            if res['id'] == r[0]['id']:
                self.assertEqual(res['license_type'], License.get(License.DEFAULT_LICENSE).uri)
            else:
                self.assertEqual(res['license_type'], r[1]['license_type'])
    
    
    def test_remote_orgs(self):
        dataset = {'title': 'some title 2',
                   'id': 'sometitle2',
                   'name': 'somename',
                   'holder_name': 'test holder',
                   'holder_identifier': 'abcdef',
                   'notes': 'some notes',
                   'modified': '2000-01-01',
                   'theme': 'AGRI',
                   'frequency': 'UNKNOWN',
                   'publisher_name': 'publisher',
                   'identifier': 'aasdfa',
                   'publisher_identifier': 'publisher',
                    }
       

        # no org creation, holder_identifier should be assigned to dataset
        data = json.dumps(dataset)
        harvest_dict = self._create_harvest_obj('http://mock/source/a',
                                                name='testpkg_2',
                                                config=json.dumps({'remote_orgs': 'no-create'}))
        harvest_obj = HarvestObject.get(harvest_dict['id'])
        harvest_obj.content = data
        
        h = DCATRDFHarvester()
        out = h.import_stage(harvest_obj)

        pkg = helpers.call_action('package_show', context={}, name_or_id=dataset['name'])

        for k in ('holder_name', 'holder_identifier',):
            self.assertEqual(pkg.get(k), dataset[k])

        # check for new org
        dataset.update({'id': 'sometitle3',
                        'name': munge_name('some title 3'),
                        'title': 'some title 3',
                        'holder_name': 'test test holder' ,
                        'holder_identifier': 'abcdefg',
                        })

        harvest_dict = self._create_harvest_obj('http://mock/source/b',
                                                name='testpkg_3',
                                                config=json.dumps({'remote_orgs': 'create'}))
        harvest_obj = HarvestObject.get(harvest_dict['id'])
        harvest_obj.content = json.dumps(dataset)
        
        out = h.import_stage(harvest_obj)
        pkg = helpers.call_action('package_show', context={}, name_or_id='testpkg_3')
        self.assertTrue(out)
        self.assertTrue(isinstance(out, bool))
        pkg = helpers.call_action('package_show', context={}, name_or_id=dataset['name'])

        org_id = pkg['owner_org']

        self.assertIsNotNone(org_id)
        org = helpers.call_action('organization_show', context={}, id=org_id)
        self.assertEqual(org['identifier'], dataset['holder_identifier'])

        # package's holder should be updated with organization's data
        for k in (('holder_name', 'name',), ('holder_identifier','identifier',)):
            self.assertEqual(pkg.get(k[0]), org[k[1]] )

        # check for existing org

        dataset.update({'id': 'sometitle4',
                        'name': munge_name('some title 4'),
                        'title': 'some title 4',
                        })

        harvest_dict = self._create_harvest_obj('http://mock/source/c',
                                                name='testpkg_4',
                                                config=json.dumps({'remote_orgs': 'create'}))
        harvest_obj = HarvestObject.get(harvest_dict['id'])
        harvest_obj.content = json.dumps(dataset)
        
        out = h.import_stage(harvest_obj)
        pkg = helpers.call_action('package_show', context={}, name_or_id='testpkg_4')
        self.assertTrue(out)
        self.assertTrue(isinstance(out, bool))
        pkg = helpers.call_action('package_show', context={}, name_or_id=dataset['name'])

        org_id = pkg['owner_org']

        self.assertIsNotNone(org_id)
        org = helpers.call_action('organization_show', context={}, id=org_id)
        self.assertEqual(org['identifier'], dataset['holder_identifier'])


    def setUp(self):
        def get_path(fname):
            return os.path.join(os.path.dirname(__file__),
                        '..', '..', '..', 'examples', fname)
        licenses = get_path('licenses.rdf')
        load_from_graph(path=licenses)
        Session.flush()
