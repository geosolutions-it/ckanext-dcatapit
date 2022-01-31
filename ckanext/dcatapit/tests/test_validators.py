import json
from builtins import Exception

import nose
import pytest
from unittest import TestCase

import ckanext.dcatapit.validators as validators

eq_ = nose.tools.eq_
ok_ = nose.tools.ok_


def test_is_blank():
    test_string = validators.is_blank('')
    eq_(test_string, True)


def test_couple_validator():
    test_couple = 'test1,test2'
    values = validators.couple_validator(test_couple, None)
    eq_(len(values), 11)


def test_no_number():
    test_number = 'test'

    try:
        value = validators.no_number(test_number, None)
        ok_(value)
    except Exception:
        eq_(True, True)

class ValidationTests(TestCase):

    def test_conforms_to(self):
        # list of input, valid flag
        test_values = ((None, False,),
                       ('', False,),
                       ('ABC,DEF', True,),  # old notation
                       (json.dumps({'test': 'fail'}), False,),
                       (json.dumps([]), True,),
                       (json.dumps([{'identifier': 'abc'}, 'fail']), False,),
                       (json.dumps([{'identifier': None, }]), False,),
                       (json.dumps([{'identifier': 'abc'}]), True,),
                       (json.dumps([{'identifier': 'abc', 'title': ['some', 'description']}]), False),
                       (json.dumps([{'identifier': 'abc', 'title': 'title', 'referenceDocumentation': 'abc'}]), False,),
                       (json.dumps([{'identifier': 'abc', 'title': 'title', 'referenceDocumentation': ['abc erwer ew']}]), False,),
                       (json.dumps([{'identifier': 'abc', 'title': 'title', 'referenceDocumentation': ['abc']}]), False,),
                       (json.dumps([{'identifier': 'abc',
                                     'title': {'en': 'title'},
                                     'referenceDocumentation': ['http://abc.efg/']}]), True),
                       (json.dumps([{'identifier': 'abc',
                                     'title': {'en': ''},
                                     'referenceDocumentation': ['http://abc.efg/']}]), True),

                       (json.dumps([{'identifier': 'abc',
                                     'title': {'en': 'title', 'it': 'title'},
                                     'referenceDocumentation': ['http://abc.efg/'], },
                                    {'identifier': 'efg',
                                     'title': {'en': 'title', 'it': 'title'},
                                     'referenceDocumentation': ['http://abc.efg/'], },
                                    ]), True,),
                       )

        self._run_checks(test_values, validators.dcatapit_conforms_to, 'ConformsTo')

    def test_alternate_identifier(self):

        # list of input, valid flag
        test_values = ((None, False,),
                       ('', False,),
                       ('ABC,DEF', True,),  # old notation
                       (json.dumps({'test': 'fail'}), False,),
                       (json.dumps([]), True,),
                       (json.dumps([{'identifier': 'abc'}, 'fail']), False,),
                       (json.dumps([{'identifier': None, }]), False,),
                       (json.dumps([{'identifier': 'abc'}]), False,),
                       (json.dumps([{'identifier': 'abc', 'agent': {}}]), True,),
                       (json.dumps([{'identifier': 'abc', 'agent': {'agent_name': 'abc'}}]), False,),
                       (json.dumps([{'identifier': 'abc', 'title': ['some', 'description']}]), False),

                       (json.dumps([{'identifier': 'abc',
                                     'agent': {
                                         'agent_name': {'en': 'title', 'it': 'title'},
                                         'agent_identifier': 'abc'},
                                     },
                                    {'identifier': 'efg',
                                     'agent': {}}
                                    ]), True,),
                       )

        self._run_checks(test_values, validators.dcatapit_alternate_identifier, 'Alternate identifier')

    def test_creators(self):
        # list of input, valid flag
        test_values = ((None, False,),
                       ('', False,),
                       ('ABC,DEF', True,),  # old notation
                       (json.dumps({'test': 'fail'}), False,),
                       (json.dumps([]), True,),
                       (json.dumps([{'test': 'fail'}]), False,),
                       (json.dumps([{'creator_identifier': 'abc'}, 'fail']), False,),
                       (json.dumps([{'creator_identifier': None, }]), False,),
                       (json.dumps([{'creator_identifier': 'abc'}]), True,),
                       (json.dumps([{'creator_identifier': 'abc', 'creator_name': {}}]), True,),
                       (json.dumps([{'creator_identifier': 'abc', 'creator_name': 'abc'}]), False,),
                       (json.dumps([{'creator_identifier': 'abc', 'creator_name': {'en': 'abc'}}]), True,),

                       (json.dumps([{'creator_identifier': 'abc',
                                     'creator_name': {'en': 'en abc', 'it': 'it abc'}},
                                    {'creator_identifier': 'def',
                                     'creator_name': {'en': 'def'}}]), True,),
                       )

        self._run_checks(test_values, validators.dcatapit_creator, 'Creator')

    def test_temporal_coverage(self):

        # list of input, valid flag
        test_values = ((None, False,),
                       ('', False,),
                       ('ABC,DEF', False,),  # old notation
                       (json.dumps({'test': 'fail'}), False,),
                       (json.dumps([]), True,),
                       (json.dumps([{'temporal_start': None, 'temporal_end': None}]), False,),
                       (json.dumps([{'temporal_start': 'abc', 'temporal_end': ''}]), False,),
                       (json.dumps([{'temporal_start': None}, 'fail']), False,),
                       (json.dumps([{'temporal_start': '2001-01-01', 'temporal_end': '2001-01-02'}]), True,),
                       (json.dumps([{'temporal_start': '2001-01-01'}]), True,),
                       (json.dumps([{'temporal_start': '2001-01-01 00:00:01', 'temporal_end': '2001-01-02 00:01:02'}]), True,),
                       (json.dumps([{'temporal_start': '2001-01-01', 'temporal_end': '2001-01-02'},
                                    {'temporal_start': '2001-01-02', 'temporal_end': '2001-01-03'}]), True,),
                       (json.dumps([{'temporal_start': '2001-01-02', 'temporal_end': '2001-01-01'}]), False,),
                       )

        self._run_checks(test_values, validators.dcatapit_temporal_coverage, 'Temporal coverage')

    @pytest.mark.usefixtures("with_request_context")
    def test_subthemes(self):
        from ckanext.dcatapit.tests.utils import load_themes
        load_themes()

        test_values = (
            # (None, False,), # old values, aggr is now not mandatory,and OP_DATPRO is inserted if no aggr is given
            (None, True,),
            # ('', False,), # old values, aggr is now not mandatory,and OP_DATPRO is inserted if no aggr is given
            ('', True,),
            ('{AGRI}', True,),
            ('{AGRI,INVALID}', False,),
            ('SOME,INVALID,THEME', False,),
            (json.dumps({}), False,),
            (json.dumps([]), True,),
            (json.dumps([{'theme': 'AGRI'}]), True,),
            (json.dumps([{'theme': 'AGRI'},
                         {'theme': 'AGRI'}]), False,),
            (json.dumps([{'theme': 'AGRI', 'subthemes': ['test', 'invalid']}]), False),
            (json.dumps([{'theme': 'AGRI', 'subthemes': ['http://eurovoc.europa.eu/100253',
                                                         'http://eurovoc.europa.eu/100258']}]), True,)
                       )

        self._run_checks(test_values, validators.dcatapit_subthemes, 'Theme aggregate', params=4)

    def _run_checks(self, test_values, validator, name = 'Unknown', params=2):
        for test_val, should_pass in test_values:
            err = None

            try:
                if params == 2:
                    value = validator(test_val, None)
                    passed = True
                elif params == 4:
                    flattened = {'key': test_val}
                    value = validator('key', flattened, [], None)
                    passed = True
                else:
                    raise Exception('Bad param number')

            except validators.Invalid as err:
                passed = False
                value = err

            if passed != should_pass:
                self.fail(f'{name} validation failed for value IN::{test_val}:: OUT::{value} : '
                          f'{"expected error, but got no validation error" if passed else ""}')
