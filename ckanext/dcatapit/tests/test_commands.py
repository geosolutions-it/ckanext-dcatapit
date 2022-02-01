import os
import pytest
import unittest

import ckanext.dcatapit.interfaces as interfaces
from ckanext.dcatapit.tests.utils import get_test_file, SKOS_THEME_FILE


class BaseCommandTest(unittest.TestCase):
    pass


class TestDCATAPITCommand(BaseCommandTest):

    @pytest.mark.usefixtures('with_request_context', 'clean_dcatapit_db')
    def test_vocabulary_command(self):
        from ckanext.dcatapit.commands.vocabulary import load_from_file

        vocab_file_path = get_test_file(SKOS_THEME_FILE)
        load_from_file(filename=vocab_file_path, format='xml')

        tag_localized = interfaces.get_localized_tag_name('ECON')
        self.assertTrue(tag_localized)
