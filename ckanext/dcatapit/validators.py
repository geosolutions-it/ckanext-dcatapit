import json
import logging

from ckan.common import _, ungettext

from ckan.logic.validators import url_validator
from ckan.plugins.toolkit import Invalid
import ckan.plugins.toolkit as toolkit
from datetime import datetime
from ckan.lib.i18n import get_locales

log = logging.getLogger(__file__)

try:
    from ckan.common import config
except ImportError:
    from pylons import config

DEFAULT_LANG = config.get('ckan.locale_default', 'en')
available_locales = get_locales()

def is_blank (string):
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

        result = session.query(model.PackageExtra).filter(model.PackageExtra.package_id != package_id, model.PackageExtra.key == 'identifier', model.PackageExtra.value == value).first()

        if result:
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
        raise Invalid(_("Conforms to value should not be empty"))
    try:
        data = json.loads(value)
    except (TypeError, ValueError,):
        try:
            old_data = value.split(',')
            return json.dumps([{'identifier': v, 'title': {}, 'description': {}, 'referenceDocumentation': []} for v in old_data])
        except (AttributeError, TypeError, ValueError,):
            raise Invalid(_("Invalid payload for conforms_to"))
    if not isinstance(data, list):
        raise Invalid(_("List expected for conforms_to values"))

    allowed_keys = ['_ref', 'identifier', 'title', 'description', 'referenceDocumentation']

    for elm in data:
        if not isinstance(elm, dict):
            raise Invalid(_("Each conforms_to element should be a dict"))
        for k in elm.keys():
            if k not in allowed_keys:
                raise Invalid(_("Unexpected {} key in conforms_to value").format(k))
        if not isinstance(elm.get('identifier'), (str, unicode,)):
            raise Invalid(_("conforms_to element should contain identifier"))

        for prop_name, allowed_types in (('_ref', (str, unicode,),),
                                         ('title', dict,),
                                         ('description', dict,),
                                         ('referenceDocumentation', list,),
                                         ):
            # those are not obligatory
            try:
                prop_val = elm[prop_name]
            except KeyError:
                prop_val = None
            if prop_val is None:
                continue
            if not isinstance(prop_val, allowed_types):
                raise Invalid(_("conforms_to property {} is not valid type").format(prop_name))
           
            # {lang -> value} mapping
            if allowed_types == dict:
                for k, v in prop_val.items():
                    if not isinstance(k, (str, unicode,)):
                        raise Invalid(_("conforms_to property {} should have {} key as string").format(prop_name, k))
                    if not isinstance(v, (str, unicode,)):
                        raise Invalid(_("conforms_to property {} should have {} value as string").format(prop_name, k))
                    if v is None:
                        raise Invalid(_("conforms_to property {} for {} lang should not be empty").format(prop_name, k))
                _populate_multilang_dict(prop_val)

        if prop_name == 'referenceDocumentation':
            if prop_val:
                for ref_doc in prop_val:
                    if not isinstance(ref_doc, (str, unicode,)):
                        raise Invalid(_("conforms_to property referenceDocumentation should contain urls"))
                    errors = {'ref_doc': []}

                    url_validator('ref_doc', {'ref_doc': ref_doc}, errors, {'model': None, 'session': None} )
                    if errors['ref_doc']:
                        raise Invalid(errors['ref_doc'])
    return json.dumps(data)


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
        raise Invalid(_("Alternate Identifier value should not be empty"))
    try:
        data = json.loads(value)
    except (TypeError, ValueError,):
        try:
            old_data = value.split(',')
            return json.dumps([{'identifier': v, 'agent': {}} for v in old_data])
        except (AttributeError, TypeError, ValueError,):
            raise Invalid(_("Invalid payload for alternate_identifier"))
    if not isinstance(data, list):
        raise Invalid(_("Invalid payload type {} for alternate_identifier").format(type(data)))

    allowed_keys = ['identifier', 'agent']
    agent_allowed_keys = ['agent_identifier', 'agent_name']

    for elm in data:
        if not isinstance(elm, dict):
            raise Invalid(_("Each alternate_identifier element should be a dict"))
        for k in elm.keys():
            if k not in allowed_keys:
                raise Invalid(_("Unexpected {} key in alternate_identifier value").format(k))

        if not isinstance(elm.get('identifier'), (str, unicode,)):
            raise Invalid(_("alternate_identifier element should contain identifier"))

        if not isinstance(elm.get('agent'), dict):
            raise Invalid(_("alternate_identifier element should contain agent"))

        for k, v in elm['agent'].items():
            if k not in agent_allowed_keys:
                raise Invalid(_("alternate_identifier agent dict contains disallowed: {}").format(k))
            if k == 'agent_name':
                if not isinstance(v, dict):
                    raise Invalid(_("alternate_identifier agent name should be a dict"))
                _populate_multilang_dict(v)

            else:
                if not isinstance(v, (str,unicode,)):
                    raise Invalid(_("alternate_identifier agent {} key should be string").format(k))

    return json.dumps(data)


def dcatapit_creator(value, context):
    """
    Validates creator list

    """
    if not value:
        raise Invalid(_("Creator value should not be empty"))
    try:
        data = json.loads(value)
    except (TypeError, ValueError,):
        try:
            old_data = value.split(',')
            return json.dumps([{'creator_name': old_data[0], 'creator_identifier': old_data[1]}])
        except (AttributeError, TypeError, ValueError,):
            raise Invalid(_("Invalid creator payload"))
    if not isinstance(data, list):
        raise Invalid(_("Invalid payload type {} for creator").format(type(data)))

    allowed_keys = ['creator_name', 'creator_identifier']
    localized_keys  = ['creator_name']
    for elm in data:
        if not isinstance(elm, dict):
            raise Invalid(_("Each creator element should be a dict"))
        for k in elm.keys():
            if k not in allowed_keys:
                raise Invalid(_("Unexpected {} key in creator value").format(k))
        for k, val in elm.items():
            if k in localized_keys:
                if not isinstance(val, dict):
                    raise Invalid(_("Creator {} value should be dict, got {} instead").format(k, type(val)))
                _populate_multilang_dict(val)
            else:
                if not isinstance(val, (str, unicode,)):
                    raise Invalid(_("Creator {} value should be string, got {} instead").format(k, type(val)))
    return json.dumps(data)


DATE_FORMATS = ['%Y-%m-%d',
                '%Y%m%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M']

def parse_date(val):
    for format in DATE_FORMATS:
        try:
            return datetime.strptime(val, format).date()
        except (ValueError, TypeError,):
            pass

    raise Invalid(_("Invalid date input: {}").format(val))


def parse_nullable_date(val):
    return parse_date(val) if val else None


def dcatapit_temporal_coverage(value, context):
    """
    Validates temporal coverage data
    """
    if not value:
        raise Invalid(_("Temporal coverage value should not be empty"))
    try:
        data = json.loads(value)
    except (TypeError, ValueError,):
        raise Invalid(_("Temporal coverage value is not valid"))

    if not isinstance(data, list):
        raise Invalid(_("Temporal coverage values should be in a list, got {}").format(type(data)))

    allowed_keys = {'temporal_start': parse_date,
                    'temporal_end': parse_nullable_date}
    allowed_keys_set = set(allowed_keys.keys())

    for elm in data:
        if not isinstance(elm, dict):
            raise Invalid(_("Invalid temporal coverage item, should be a dict, got {}").format(type(elm)))
        keys_set = set(elm.keys())
        if not (keys_set.issubset(allowed_keys_set) and allowed_keys_set.issuperset(keys_set)):
            raise Invalid(_("Temporal coverage item contains invalid keys: {}").format(keys_set - allowed_keys_set))

        tmp = {}
        for k, v in elm.items():
            parsed = allowed_keys[k](v)
            if parsed:
               tmp[k] = parsed
        
        if tmp.get('temporal_end') and tmp['temporal_start'] > tmp['temporal_end']:
            raise Invalid(_("Temporal coverage start {} is after end {}").format(tmp['temporal_start'], tmp['temporal_end']))

    return json.dumps(data)
