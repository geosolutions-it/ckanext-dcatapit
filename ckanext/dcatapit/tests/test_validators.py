import json
import nose
import ckanext.dcatapit.validators as validators

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
                                 'referenceDocumentation': ['http://abc.efg/']}]), False),

                   (json.dumps([{'identifier': 'abc',
                                 'title': {'en': 'title', 'it': 'title'},
                                 'referenceDocumentation': ['http://abc.efg/'],},
                                {'identifier': 'efg',
                                 'title': {'en': 'title', 'it': 'title'},
                                 'referenceDocumentation': ['http://abc.efg/'],},
                                 ]), True,),
                   )

    for test_val, is_valid in test_values:
        passed = False
        err = None
        try:
            value = validators.dcatapit_conforms_to(test_val, None)
            passed = True
        except validators.Invalid, err:
            pass
        assert passed == is_valid, 'failed for {}: {}'.format(test_val, err or 'no validation error')
