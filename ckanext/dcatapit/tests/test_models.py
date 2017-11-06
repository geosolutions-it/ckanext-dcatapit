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

    def test_licenses(self):
        licenses = get_path('licenses.rdf')
        g = _get_graph(path=licenses)

        load_from_graph(path=licenses)

        all_licenses = License.q()
        count = all_licenses.count()
        self.assertTrue(count> 0)
        self.assertTrue(count == len(list(g.subjects(None, SKOS.Concept))))
        
        all_localized = LocalizedLicenseName.q()
        self.assertTrue(all_localized.count() > 0)

        for_select = License.for_select('it')
        
        # check license type
        self.assertTrue(all([s[0] for s in for_select]))



