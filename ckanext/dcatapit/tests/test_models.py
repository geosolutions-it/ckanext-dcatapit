import os
import json

import unittest
import nose

from ckan.model import Session
from ckan.plugins import toolkit

try:
    from ckan.tests import helpers
except ImportError:
    from ckan.new_tests import helpers

from ckanext.dcatapit.model.license import (load_from_graph, 
    License, LocalizedLicenseName, _get_graph, SKOS)

def get_path(fname):
    return os.path.join(os.path.dirname(__file__),
                        '..', '..', '..', 'examples', fname)

class LicenseTestCase(unittest.TestCase):
    def setUp(self):

        self.licenses = get_path('licenses.rdf')
        self.g = _get_graph(path=self.licenses)

    def test_licenses(self):

        load_from_graph(path=self.licenses)

        all_licenses = License.q()
        count = all_licenses.count()
        self.assertTrue(count> 0)
        self.assertTrue(count == len(list(self.g.subjects(None, SKOS.Concept))))
        
        all_localized = LocalizedLicenseName.q()
        self.assertTrue(all_localized.count() > 0)

        for_select = License.for_select('it')
        
        # check license type
        self.assertTrue(all([s[0] for s in for_select]))


    def test_tokenizer(self):

        load_from_graph(path=self.licenses)
        tokens = License.get_as_tokens()
        self.assertTrue(len(tokens.keys())>0)

        from_token = License.find_by_token('cc-by-sa')
        self.assertTrue(from_token)
        self.assertTrue(from_token.uri)

    def tearDown(self):
        Session.rollback()


