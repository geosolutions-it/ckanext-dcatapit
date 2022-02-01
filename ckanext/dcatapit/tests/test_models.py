import os
import unittest

from ckan.model.meta import Session
from rdflib import RDF, Graph

from ckanext.dcatapit.tests.utils import (
    EUROVOC_FILE,
    MAPPING_FILE,
    get_example_file,
    get_test_file,
    get_voc_file,
    load_graph, LICENSES_FILE,
)

try:
    from ckan.tests import helpers
except ImportError:
    from ckan.new_tests import helpers

from ckanext.dcatapit.model.license import (
    License,
    LocalizedLicenseName,
)
from ckanext.dcatapit.commands.vocabulary import SKOS, load_licenses as load_license, load_subthemes
from ckanext.dcatapit.model.subtheme import (
    Subtheme,
    clear_subthemes,
)


class LicenseTestCase(unittest.TestCase):

    def setUp(self):

        self.licenses = get_voc_file(LICENSES_FILE)
        self.g = load_graph(path=self.licenses)

    def test_licenses(self):

        load_license(self.g)
        Session.flush()

        all_licenses = License.q()
        count = all_licenses.count()
        self.assertTrue(count > 0)
        self.assertTrue(count == len(list(self.g.subjects(None, SKOS.Concept))))

        all_localized = LocalizedLicenseName.q()
        self.assertTrue(all_localized.count() > 0)

        for_select = License.for_select('it')

        # check license type
        self.assertTrue(all([s[0] for s in for_select]))

    def test_tokenizer(self):

        load_license(self.g)
        Session.flush()
        tokens = License.get_as_tokens()
        self.assertTrue(len(tokens.keys()) > 0)

        from_token, default = License.find_by_token('cc-by-sa')
        self.assertFalse(default)
        self.assertTrue(from_token)
        self.assertTrue('ccbysa' in from_token.uri.lower())

        from_token, default = License.find_by_token('cc-zero')  # http://opendefinition.org/licenses/cc-zero/')
        self.assertFalse(default)
        self.assertTrue(from_token)

        self.assertTrue('PublicDomain' in from_token.license_type)

        from_token, default = License.find_by_token('Creative Commons Attribuzione')  # http://opendefinition.org/licenses/cc-zero/')
        self.assertFalse(default)
        self.assertTrue(from_token)

        self.assertTrue('Attribution' in from_token.license_type)

        odbl = """["Open Data Commons Open Database License / OSM (ODbL/OSM): You are free to copy, distribute, transmit and adapt our data, as long as you credit OpenStreetMap and its contributors\nIf you alter or build upon our data, you may distribute the result only under the same licence. (http://www.openstreetmap.org/copyright)"]"""

        from_token, default = License.find_by_token(odbl, 'other')
        self.assertFalse(default)
        self.assertTrue(from_token)
        self.assertTrue('odbl' in from_token.default_name.lower())

    def tearDown(self):
        Session.rollback()


class SubthemeTestCase(unittest.TestCase):

    EUROVOC_FILE = 'eurovoc.rdf'

    def setUp(self):
        self._load_mapping()

    def _load_mapping(self):
        self.map_f = get_voc_file(MAPPING_FILE)
        self.voc_f = get_test_file(EUROVOC_FILE)

    def test_subthemes(self):
        clear_subthemes()
        g = Graph()
        g.parse(self.map_f)

        refs = list(g.objects(None, SKOS.narrowMatch))
        self.assertTrue(len(refs) > 0)

        load_subthemes(self.map_f, self.voc_f)
        all_subthemes = Subtheme.q()
        self.assertGreater(all_subthemes.count(), 0)
        for ref in refs:
            try:
                subtheme = Subtheme.q().filter_by(uri=str(ref)).one()
                self.assertIsNotNone(subtheme)
            except Exception as err:
                self.fail(f'No results for {ref}: {err}')
        themes = g.subjects(RDF.type, SKOS.Concept)
        for theme in themes:
            theme_len = g.objects(theme, SKOS.narrowMatch)
            theme_name = Subtheme.normalize_theme(theme)
            q = Subtheme.for_theme(theme_name)
            self.assertGreaterEqual(q.count(), len(list(theme_len)))

    def tearDown(self):
        Session.rollback()
