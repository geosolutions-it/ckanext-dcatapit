import json
import logging

from ckan.common import _, ungettext

from ckan.logic.validators import url_validator
from ckan.plugins.toolkit import Invalid
from datetime import datetime

log = logging.getLogger(__file__)


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

def dcatapit_conforms_to(value, context):
    """
    Validates conforms to structure
    [ {'identifier': str,
       'title': {lang: str},
       'description': {lang: str},
       'referenceDocumentation: [ str, str],
      },..
    ]

    """
    try:
        data = json.loads(value)
    except (TypeError, ValueError,):
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
                    if not v:
                        raise Invalid(_("conforms_to property {} for {} lang should not be empty").format(prop_name, k))

        if prop_name == 'referenceDocumentation':
            if prop_val:
                for ref_doc in prop_val:
                    if not isinstance(ref_doc, (str, unicode,)):
                        raise Invalid(_("conforms_to property referenceDocumentation should contain urls"))
                    errors = {'ref_doc': []}

                    url_validator('ref_doc', {'ref_doc': ref_doc}, errors, {'model': None, 'session': None} )
                    if errors['ref_doc']:
                        raise Invalid(errors['ref_doc'])
    return value


def dcatapit_alternate_identifier(value, context):
    """
    Validates alternate identifier structure (as json string):

    [ {'identifier': str,
       'agent': {'agent_name': {lang: str},
                 'agent_identifier': str},},


    ]
    """
    try:
        data = json.loads(value)
    except (TypeError, ValueError,):
        raise Invalid(_("Invalid payload for alternate_identifier"))
    if not isinstance(data, list):
        raise Invalid(_("List expected for alternate_identifier values"))

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
                raise Invalid(_("alternate_identifier agent dict contains disallowedelement should contain agent"))
            if k == 'agent_name':
                if not isinstance(v, dict):
                    raise Invalid(_("alternate_identifier agent name should be a dict"))
            else:
                if not isinstance(v, (str,unicode,)):
                    raise Invalid(_("alternate_identifier agent {} key should be string").format(k))

    return value
