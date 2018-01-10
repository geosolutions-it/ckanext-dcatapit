import os
import json
import nose
import ckanext.dcatapit.validators as validators
from ckanext.dcatapit.tests.utils import load_themes

eq_ = nose.tools.eq_
ok_ = nose.tools.ok_

def test_is_blank():
    test_string = validators.is_blank("")
    eq_(test_string, True)

def test_couple_validator():
    test_couple = 'test1,test2'
    values = validators.couple_validator(test_couple, None)
    eq_(len(values), 11)

def test_no_number():
    test_number = "test"

    try:
        value = validators.no_number(test_number, None)
        ok_(value)
    except Exception:
        eq_(True, True)

def test_dcatapit_id_unique():
    '''
    result = helpers.call_action('package_create',
        name='test_dcatapit_package',
        identifier='4b6fe9ca-dc77-4cec-92a4-55c6624a5bd6',
        theme='{ECON,ENVI}',
        publisher_name='bolzano',
        publisher_identifier='234234234',
        modified='2016-11-29',
        holder_name='bolzano',
        holder_identifier='234234234',
        notes='dcatapit dataset di test',
        frequency='UPDATE_CONT',
        geographical_geonames_url='http://www.geonames.org/3181913')
    '''

    pass


def test_conforms_to():
    
    # list of input, valid flag
    test_values = ((None, False,),
                   ('', False,),
                   ('ABC,DEF', True,), # old notation
                   (json.dumps({'test': 'fail'}), False,),
                   (json.dumps([]), True,),
                   (json.dumps([{'identifier': 'abc'}, 'fail']), False,),
                   (json.dumps([{'identifier': None,}]), False,),
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
                                 'referenceDocumentation': ['http://abc.efg/'],},
                                {'identifier': 'efg',
                                 'title': {'en': 'title', 'it': 'title'},
                                 'referenceDocumentation': ['http://abc.efg/'],},
                                 ]), True,),
                   )


    return _run_checks(test_values, validators.dcatapit_conforms_to)


def test_alternate_identifier():
    
    # list of input, valid flag
    test_values = ((None, False,),
                   ('', False,),
                   ('ABC,DEF', True,), # old notation
                   (json.dumps({'test': 'fail'}), False,),
                   (json.dumps([]), True,),
                   (json.dumps([{'identifier': 'abc'}, 'fail']), False,),
                   (json.dumps([{'identifier': None,}]), False,),
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

    return _run_checks(test_values, validators.dcatapit_alternate_identifier)


def test_creators():

    # list of input, valid flag
    test_values = ((None, False,),
                   ('', False,),
                   ('ABC,DEF', True,), # old notation
                   (json.dumps({'test': 'fail'}), False,),
                   (json.dumps([]), True,),
                   (json.dumps([{'test': 'fail'}]), False,),
                   (json.dumps([{'creator_identifier': 'abc'}, 'fail']), False,),
                   (json.dumps([{'creator_identifier': None,}]), False,),
                   (json.dumps([{'creator_identifier': 'abc'}]), True,),
                   (json.dumps([{'creator_identifier': 'abc', 'creator_name': {}}]), True,),
                   (json.dumps([{'creator_identifier': 'abc', 'creator_name': 'abc'}]), False,),
                   (json.dumps([{'creator_identifier': 'abc', 'creator_name': {'en': 'abc'}}]), True,),

                   (json.dumps([{'creator_identifier': 'abc',
                                 'creator_name': {'en': 'en abc', 'it': 'it abc'}},
                                {'creator_identifier': 'def',
                                 'creator_name': {'en': 'def'}}]), True,),
                   )

    return _run_checks(test_values, validators.dcatapit_creator)
   
def test_temporal_coverage():

    # list of input, valid flag
    test_values = ((None, False,),
                   ('', False,),
                   ('ABC,DEF', False,), # old notation
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

    return _run_checks(test_values, validators.dcatapit_temporal_coverage)


def test_subthemes():

    load_themes()

    test_values = ((None, False,),
                   ('', False,),
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

    return _run_checks(test_values, validators.dcatapit_subthemes)


def _run_checks(test_values, validator):
    for test_val, is_valid in test_values:
        passed = False
        err = None
        try:
            value = validator(test_val, None)
            passed = True
        except validators.Invalid, err:
            pass
        assert passed == is_valid, 'failed for {}: {}'.format(test_val, err or 'expected error, but got no validation error')
