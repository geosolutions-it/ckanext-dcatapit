
import os
import nose
import unittest
import ckanext.dcatapit.interfaces as interfaces

from ckanext.dcatapit.commands.dcatapit import DCATAPITCommands
from ckanext.dcatapit.tests.utils import load_themes

eq_ = nose.tools.eq_
ok_ = nose.tools.ok_


class TestDCATAPITCommand(unittest.TestCase):

    def test_vocabulary_command(self):
        load_themes()

        tag_localized = interfaces.get_localized_tag_name('ECON')
        self.assertTrue(tag_localized)
