import json
import logging
from datetime import datetime

from ckan.common import _, config
from ckan.lib.i18n import get_locales
from ckan.logic.validators import url_validator
from ckan.plugins.toolkit import Invalid
from sqlalchemy import and_

from ckanext.dcatapit.mapping import themes_to_aggr_json, themes_parse_to_uris
from ckanext.dcatapit.model.subtheme import Subtheme

DEFAULT_LANG = config.get('ckan.locale_default', 'en')
log = logging.getLogger(__file__)
available_locales = get_locales()

def is_blank(string):
    return not (string and string.strip())


def couple_validator(value, context):
    if not is_blank(value):
        couples = value.split(',')

        for c in couples:
            if not c:
                raise Invalid(_('Invalid couple, one value is missing'))

    return value


def no_number(value, context):
    if value and value.isdigit():
        raise Invalid(_('This field cannot be a number'))

    return value


def dcatapit_id_unique(value, context):
    model = context['model']
    session = context['session']

    package = context.get('package', None)
    if package:
        package_id = package.id

        # existing dataset, exclude current one from search
        result = session.query(model.PackageExtra)\
                        .join(model.Package, and_(model.PackageExtra.package_id == model.Package.id,
                                                  model.Package.type == 'dataset',
                                                  model.Package.state == 'active'))\
                        .filter(model.PackageExtra.package_id != package_id,
                                model.PackageExtra.key == 'identifier',
                                model.PackageExtra.value == value)\
                        .first()
    else:
        # no package in context, so this is new dataset, no exclude here
        # just search among live datasets
        result = session.query(model.PackageExtra)\
                        .join(model.Package, and_(model.PackageExtra.package_id == model.Package.id,
                                                  model.Package.type == 'dataset',
                                                  model.Package.state == 'active'))\
                        .filter(model.PackageExtra.key == 'identifier',
                                model.PackageExtra.value == value)\
                        .first()

    if result is not None:
        raise Invalid(_('Another package exists with the same identifier'))

    return value


def _populate_multilang_dict(prop_val):
    """
    This will ensure all handled locales are populated
    Get default lang value,
    populate other languagesif needed
    """
    default_value = prop_val.get(DEFAULT_LANG)
    if default_value is None:
        try:
            default_value = [p for p in prop_val.values() if p][0]
        except IndexError:
            default_value = ''

    for l in available_locales:
        if not prop_val.get(l):
            prop_val[l] = default_value


def dcatapit_conforms_to(value, context):
    """
    Validates conforms to structure
    [ {'identifier': str,
       'title': {lang: str},
       'description': {lang: str},
       'referenceDocumentation: [ str, str],
      },..
    ]

    This should also handle old notation: 'VAL1,VAL2'
    """
    if not value:
        raise Invalid(_('Conforms to value should not be empty'))
    try:
        data = json.loads(value)
    except (TypeError, ValueError):
        try:
            old_data = value.split(',')
            return json.dumps([{'identifier': v,
                                'title': {},
                                'description': {},
                                'referenceDocumentation': []} for v in old_data])
        except (AttributeError, TypeError, ValueError):
            raise Invalid(_('Invalid payload for conforms_to'))
    if not isinstance(data, list):
        raise Invalid(_('List expected for conforms_to values'))

    allowed_keys = ['uri', 'identifier', 'title', 'description', 'referenceDocumentation']

    new_data = []
    for elm in data:
        new_elm = {}
        if not isinstance(elm, dict):
            raise Invalid(_('Each conforms_to element should be a dict'))

        # LEGACY: rewrite _ref to uri for older data
        _ref = elm.pop('_ref', None)
        if _ref and not elm.get('uri'):
            elm['uri'] = _ref

        for k in elm.keys():
            if k not in allowed_keys:
                raise Invalid(_('Unexpected {} key in conforms_to value').format(k))
        if not isinstance(elm.get('identifier'), str):
            raise Invalid(_('conforms_to element should contain identifier'))

        for prop_name, allowed_types in (('uri', str,),
                                         ('identifier', str),
                                         ('title', dict,),
                                         ('description', dict,),
                                         ('referenceDocumentation', list,),
                                         ):
            # those are not obligatory fields
            try:
                prop_val = elm[prop_name]
            except KeyError:
                prop_val = None
            if prop_val is None:
                continue
            if not isinstance(prop_val, allowed_types):
                raise Invalid(_('conforms_to property {} is not valid type').format(prop_name))

            # {lang -> value} mapping
            if allowed_types == dict:
                for k, v in prop_val.items():
                    if not isinstance(k, str):
                        raise Invalid(_('conforms_to property {} should have {} key as string').format(prop_name, k))
                    if not isinstance(v, str):
                        raise Invalid(_('conforms_to property {} should have {} value as string').format(prop_name, k))
                    if v is None:
                        raise Invalid(_('conforms_to property {} for {} lang should not be empty').format(prop_name, k))
                _populate_multilang_dict(prop_val)  # TODO: do we really want to forge entries for all languages?

            if prop_name == 'uri' and prop_val == '':
                continue

            if prop_name == 'referenceDocumentation':
                if prop_val:
                    # keep unique values
                    processed = set([])
                    for ref_doc in prop_val:
                        if not isinstance(ref_doc, str):
                            raise Invalid(_('conforms_to property referenceDocumentation should contain urls'))
                        errors = {'ref_doc': []}

                        url_validator('ref_doc',
                                      {'ref_doc': ref_doc},
                                      errors,
                                      {'model': None, 'session': None})
                        if errors['ref_doc']:
                            raise Invalid(errors['ref_doc'])
                        processed.add(ref_doc)
                    prop_val = list(processed)
            new_elm[prop_name] = prop_val
        new_data.append(new_elm)
    return json.dumps(new_data)


def dcatapit_alternate_identifier(value, context):
    """
    Validates alternate identifier structure (as json string):

    [ {'identifier': str,
       'agent': {'agent_name': {lang: str},
                 'agent_identifier': str},},


    ]

    This should also handle old
    """
    if not value:
        raise Invalid(_('Alternate Identifier value should not be empty'))
    try:
        data = json.loads(value)
    except (TypeError, ValueError):
        try:
            old_data = value.split(',')
            return json.dumps([{'identifier': v, 'agent': {}} for v in old_data])
        except (AttributeError, TypeError, ValueError):
            raise Invalid(_('Invalid payload for alternate_identifier'))
    if not isinstance(data, list):
        raise Invalid(_('Invalid payload type {} for alternate_identifier').format(type(data)))

    allowed_keys = ['identifier', 'agent']
    agent_allowed_keys = ['agent_identifier', 'agent_name']
    for elm in data:
        if not isinstance(elm, dict):
            raise Invalid(_('Each alternate_identifier element should be a dict'))
        for k in elm.keys():
            if k not in allowed_keys:
                raise Invalid(_('Unexpected {} key in alternate_identifier value').format(k))

        if not isinstance(elm.get('identifier'), str):
            raise Invalid(_('alternate_identifier element should contain identifier'))

        if not isinstance(elm.get('agent'), dict):
            raise Invalid(_('alternate_identifier element should contain agent'))

        for k, v in elm['agent'].items():
            if k not in agent_allowed_keys:
                raise Invalid(_('alternate_identifier agent dict contains disallowed: {}').format(k))
            if k == 'agent_name':
                if not isinstance(v, dict):
                    raise Invalid(_('alternate_identifier agent name should be a dict'))
                _populate_multilang_dict(v)

            else:
                if not isinstance(v, str):
                    raise Invalid(_('alternate_identifier agent {} key should be string').format(k))

    return json.dumps(data)


def dcatapit_creator(value, context):
    """
    Validates creator list

    """
    if not value:
        raise Invalid(_('Creator value should not be empty'))
    try:
        data = json.loads(value)
    except (TypeError, ValueError):
        try:
            old_data = value.split(',')
            return json.dumps([{'creator_name': old_data[0], 'creator_identifier': old_data[1]}])
        except (AttributeError, TypeError, ValueError):
            raise Invalid(_('Invalid creator payload'))
    if not isinstance(data, list):
        raise Invalid(_('Invalid payload type {} for creator').format(type(data)))

    allowed_keys = ['creator_name', 'creator_identifier']
    localized_keys = ['creator_name']
    for elm in data:
        if not isinstance(elm, dict):
            raise Invalid(_('Each creator element should be a dict'))
        for k in elm.keys():
            if k not in allowed_keys:
                raise Invalid(_('Unexpected {} key in creator value').format(k))
        for k, val in elm.items():
            if k in localized_keys:
                if not isinstance(val, dict):
                    raise Invalid(_('Creator {} value should be dict, got {} instead').format(k, type(val)))
                _populate_multilang_dict(val)
            else:
                if not isinstance(val, str):
                    raise Invalid(_('Creator {} value should be string, got {} instead').format(k, type(val)))
    return json.dumps(data)


DATE_FORMATS = ['%Y-%m-%d',
                '%d-%m-%Y',
                '%Y%m%d',
                '%y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S %z',
                '%Y-%m-%dT%H:%M:%S %Z',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                # faulty ones, but still can be used
                '%Y',
                'N/A%Y',
                'N/A %Y',
                '%b. %Y',
                '%b.%Y',
                '%B %Y',
                '%m/%Y',
                '%d.%m.%Y',
                '%d/%m/%Y',
                # american notation is disabled, it can be bogus with one above
                # '%m/%d/%Y',
                # some timestamps have invalid tz offset (without a sign)
                '%Y-%m-%dT%H:%M:%S 0100',
                '%Y-%m-%dT%H:%M:%S 01:00',
                ]


def parse_date(val, default=None):
    for format in DATE_FORMATS:
        try:
            return datetime.strptime(val, format).date()
        except (ValueError, TypeError,):
            pass
    if default is not None:
        return default
    raise Invalid(_(u'Invalid date input: {}').format(val))


def serialize_date(val):
    if not val:
        return
    return val.strftime(DATE_FORMATS[0])


def parse_nullable_date(val):
    return parse_date(val) if val else None


def dcatapit_temporal_coverage(value, context):
    """
    Validates temporal coverage data
    """
    if not value:
        raise Invalid(_('Temporal coverage value should not be empty'))
    try:
        data = json.loads(value)
    except (TypeError, ValueError):
        raise Invalid(_('Temporal coverage value is not valid'))

    if not isinstance(data, list):
        raise Invalid(_('Temporal coverage values should be in a list, got {}').format(type(data)))

    allowed_keys = {'temporal_start': parse_nullable_date,
                    'temporal_end': parse_nullable_date}
    allowed_keys_set = set(allowed_keys.keys())
    new_data = []
    for elm in data:
        if not isinstance(elm, dict):
            raise Invalid(_('Invalid temporal coverage item, should be a dict, got {}').format(type(elm)))
        keys_set = set(elm.keys())

        if not (keys_set.issubset(allowed_keys_set) and allowed_keys_set.issuperset(keys_set)):
            raise Invalid(_('Temporal coverage item contains invalid keys: {}').format(keys_set - allowed_keys_set))

        tmp = {}
        for k, v in elm.items():
            parsed = allowed_keys[k](v)
            if parsed:
                tmp[k] = parsed

        if not tmp.get('temporal_start'):
            raise Invalid(_('Temporal coverage should contain start element'))

        if tmp.get('temporal_start') and tmp.get('temporal_end') and tmp['temporal_start'] > tmp['temporal_end']:
            raise Invalid(_('Temporal coverage start {} is after end {}').format(tmp['temporal_start'], tmp['temporal_end']))
        new_data.append(dict((k, serialize_date(v)) for k, v in tmp.items()))
    return json.dumps(new_data)


def dcatapit_copy_to_context(key, flattened_data, errors, context):
    value = flattened_data.get(key)
    basekey = key[-1]
    context[f'dcatapit_{basekey}'] = value


def dcatapit_remove_theme(key, flattened_data, errors, context):
    for tkey in flattened_data:
        if len(tkey) == 3:
            x, idx, k = tkey
            if x == 'extras' and k == 'key' and flattened_data[tkey] == 'theme':
                flattened_data.pop(tkey)
                flattened_data.pop(('extras', idx, 'value'))
                return


def dcatapit_subthemes(key, flattened_data, errors, context):
    """
    Validate aggregate_theme; expected format is
    [
      {
        'theme': THEME_CODE,
        'subthemes': ['subtheme uri', 'subtheme uri']
      }, ...
    ]

    If the aggregate theme does not exist, try and parse the extra theme value.
    """
    def _get_flattened_theme():
        for tkey in flattened_data:
            if len(tkey) == 3:
                x, idx, k = tkey
                if x == 'extras' and k == 'key' and flattened_data[tkey] == 'theme':
                    return flattened_data[('extras', idx, 'value')]

        # Not found in expected fields, Look into the discarded fields
        __extras = flattened_data.get(('__extras',), None)
        if __extras and 'theme' in __extras:
            return __extras['theme']

        return None

    def _do_return(value):
        flattened_data[key] = value

    value = flattened_data.get(key)

    if not value or value == '[]':  # a little shortcut here
        theme = _get_flattened_theme()
        if theme and theme != '[]':  # other shortcut
            log.warning('Aggregate theme is missing, trying setting values from extra theme key')
            theme_list = themes_parse_to_uris(theme)
            _do_return(themes_to_aggr_json(theme_list))
        else:
            log.warning('Aggregate theme is missing, setting undefined value')
            _do_return(themes_to_aggr_json(['OP_DATPRO']))
        return
        # raise Invalid(_('Theme data should not be empty'))

    try:
        aggr_list = json.loads(value)
    except (TypeError, ValueError):
        # handle old '{THEME1,THEME2}' notation
        if isinstance(value, str):
            _v = value.rstrip('}').lstrip('{').split(',')
            aggr_list = [{'theme': v, 'subthemes': []} for v in _v]
        elif isinstance(value, (list, tuple,)):
            aggr_list = [{'theme': v, 'subthemes': []} for v in value]
        else:
            raise Invalid(_('Theme data is not valid, expected json, got {}'.format(type(value))))
    if not isinstance(aggr_list, list):
        raise Invalid(_('Theme data should be a list, got {}'.format(type(aggr_list))))

    allowed_keys = {'theme': str,
                    'subthemes': list}

    allowed_keys_set = set(allowed_keys.keys())
    check_with_db = context.get('dcatapit_subthemes_check_in_db') if context else True

    if not aggr_list:
        raise Invalid(_('Theme data should not be empty'))

    for aggr in aggr_list:
        if not isinstance(aggr, dict):
            raise Invalid(_('Invalid theme aggr item, should be a dict, got {}'.format(type(aggr))))
        keys_set = set(aggr.keys())
        if keys_set - allowed_keys_set:
            raise Invalid(_('Theme aggr contains invalid keys: {}'.format(keys_set - allowed_keys_set)))
        if not aggr.get('theme'):
            raise Invalid(_('Theme data should not be empty'))

        for k, v in aggr.items():
            allowed_type = allowed_keys[k]
            if (k == 'theme' and not isinstance(v, str)) or \
                    (k == 'subthemes' and not isinstance(v, list)):
                raise Invalid(_('Theme item {} value: {} should be {}, got {}'.format(k, v, allowed_type, type(v))))
            if k == 'subthemes':
                for subtheme in v:
                    if not isinstance(subtheme, str):
                        raise Invalid(_('Subtheme {} value should be string'.format(subtheme)))
        if not check_with_db:
            continue
        theme_name = aggr['theme']
        subthemes = aggr.get('subthemes') or []
        try:
            slist = [s.uri for s in Subtheme.for_theme(theme_name)]
        except ValueError:
            raise Invalid(_('Invalid theme {}'.format(theme_name)))

        for s in subthemes:
            if s not in slist:
                raise Invalid(_('Invalid subtheme: {}'.format(s)))

    reduced_themes = set([s.get('theme') for s in aggr_list if s.get('theme')])
    if len(aggr_list) != len(reduced_themes):
        raise Invalid(_('There are duplicate themes. Expected {} items, got {}'.format(len(aggr_list), len(reduced_themes))))

    _do_return(json.dumps(aggr_list))
    # return json.dumps(data)

