import os
import pytest
import unittest

import ckanext.dcatapit.interfaces as interfaces
from ckanext.dcatapit.tests.utils import get_test_file, SKOS_THEME_FILE


class BaseCommandTest(unittest.TestCase):

    def _get_file_contents(self, file_name):
        path = os.path.join(os.path.dirname(__file__),
                            '..', '..', '..', 'vocabularies',
                            file_name)
        return path


class TestDCATAPITCommand(BaseCommandTest):

    @pytest.mark.usefixtures('with_request_context', 'clean_dcatapit_db')
    def test_vocabulary_command(self):
        from ckanext.dcatapit.commands.vocabulary import load

        vocab_file_path = get_test_file(SKOS_THEME_FILE)
        load(filename=vocab_file_path, format='xml')

        tag_localized = interfaces.get_localized_tag_name('ECON')
        self.assertTrue(tag_localized)
