import json
import logging

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from ckan.model import GroupExtra, Session
import ckan.lib.helpers as h
import ckan.plugins.toolkit as toolkit
import ckanext.dcatapit.schema as dcatapit_schema

import ckanext.dcatapit.interfaces as interfaces
from ckanext.dcatapit.model.license import License
from ckan.lib.base import config
from ckanext.dcatapit.model.subtheme import Subtheme

import datetime
from webhelpers.html import escape, HTML, literal, url_escape

log = logging.getLogger(__file__)

dateformats = [
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%d-%m-%y",
    "%Y-%m-%d %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S"
]

# config param names
GEONAMES_USERNAME = 'geonames.username'
GEONAMES_LIMIT_TO = 'geonames.limits.countries'
DEFAULT_CTX = {'ignore_auth': True}
DEFAULT_ORG_CTX = DEFAULT_CTX.copy()
DEFAULT_ORG_CTX.update(dict((k, False) for k in ('include_tags',
                                                 'include_users',
                                                 'include_groups',
                                                 'include_extras',
                                                 'include_followers',)))

def get_dcatapit_package_schema():
    log.debug('Retrieving DCAT-AP_IT package schema fields...')
    return dcatapit_schema.get_custom_package_schema()

def get_dcatapit_organization_schema():
    log.debug('Retrieving DCAT-AP_IT organization schema fields...')
    return dcatapit_schema.get_custom_organization_schema()

def get_dcatapit_configuration_schema():
    log.debug('Retrieving DCAT-AP_IT configuration schema fields...')
    return dcatapit_schema.get_custom_config_schema()

def get_dcatapit_resource_schema():
    log.debug('Retrieving DCAT-AP_IT resource schema fields...')
    return dcatapit_schema.get_custom_resource_schema()

def get_vocabulary_items(vocabulary_name, keys=None):
    try:
        tag_list = toolkit.get_action('tag_list')
        items = tag_list(data_dict={'vocabulary_id': vocabulary_name})

        tag_list = []
        for item in items:
            if keys:
                for key in keys:
                    if key == item:
                        localized_tag_name = interfaces.get_localized_tag_name(item)
                        tag_list.append(localized_tag_name)
            else:
                localized_tag_name = interfaces.get_localized_tag_name(item)
                tag_list.append({'text': localized_tag_name, 'value': item})

        return tag_list
    except toolkit.ObjectNotFound:
        return []

def get_vocabulary_item(vocabulary_name, key):
    return interfaces.get_localized_tag_name(key)

def get_dcatapit_license(license_type):
    return interfaces.get_license_for_dcat(license_type)

def get_package_resource_dcatapit_format_list(pkg_resources, fallback_lang=None):
    resources = []
    if pkg_resources:
        resources = h.dict_list_reduce(pkg_resources, 'format')

    package_res = []
    for resource in resources:
        localized_resource_name = interfaces.get_localized_tag_name(resource, fallback_lang)
        package_res.append(localized_resource_name)

    resources = package_res
    return resources

def get_localized_field_value(field=None, pkg_id=None, field_type='extra'):
    log.debug('Retrieving localized package field...')
    return interfaces.get_localized_field_value(field, pkg_id, field_type)

def get_resource_licenses_tree(value=None, lang=None):
    return interfaces.get_resource_licenses_tree(value, lang)


def list_to_string(_list, _format=None):
    if _list:
        _string = ''

        first_item = True
        for item in _list:
            if first_item:
                first_item = False
                element = item

                if _format:
                    element = format(element, _format)

                _string = _string + element
            else:
                element = item

                if _format:
                    element = format(element, _format)

                _string = _string + ', ' + item

        return _string

def couple_to_string(field_couples, pkg_dict):
    if field_couples and pkg_dict:
        _string = ''
        for couple in field_couples:
            if couple['name'] in pkg_dict:
                field_value = pkg_dict[couple['name']]
                if field_value and couple['label']:
                    _string = _string + ' ' + couple['label'] + ': ' + field_value

        return _string
    return None

def couple_to_html(field_couples, pkg_dict):
    if field_couples and pkg_dict:
        html_elements = []
        for couple in field_couples:
            couple_name = couple.get('name', None)

            if couple_name in pkg_dict:
                field_value = pkg_dict[couple_name]

                couple_format = couple.get('format', None)
                if couple_format:
                    couple_type = couple.get('type', None)
                    field_value = format(field_value, couple_format, couple_type)

                couple_label = couple.get('label', None)
                if field_value and couple_label:
                    html_elements.append(literal(('<span style="font-weight:bold">%s: </span><span>%s</span>') % (couple_label, field_value)))

        return html_elements if len(html_elements) > 0 else []
    return []


def couple_to_dict(field_couples, pkg_dict):
    ret = []
    if field_couples and pkg_dict:
        for couple in field_couples:
            couple_name = couple.get('name', None)

            if couple_name in pkg_dict:
                field_value = pkg_dict[couple_name]

                couple_format = couple.get('format', None)
                if couple_format:
                    couple_type = couple.get('type', None)
                    field_value = format(field_value, couple_format, couple_type)

                couple_label = couple.get('label', None)
                if field_value and couple_label:
                    c = {'label': couple_label, 'value': field_value}
                    ret.append(c)
 
    return ret


def format(value, _format='%d-%m-%Y', _type=None):
    # #################################################
    # TODO: manage here other formats if needed
    #      (ie. for type text, other date formats etc)
    # #################################################
    if _format and _type:
        if _type == 'date':
            date = None
            for dateformat in dateformats:
                date = validate_dateformat(value, dateformat)

                if date and isinstance(date, datetime.date):
                    date = date.strftime(_format)
                    return date
        if _type == 'text':
            return value

    return value

def validate_dateformat(date_string, date_format):
    try:
        date = datetime.datetime.strptime(date_string, date_format)
        return date
    except ValueError:
        log.debug(u'Incorrect date format {0} for date string {1}'.format(date_format, date_string))
        return None

def json_load(val):
    try:
        return json.loads(val)
    except (TypeError, ValueError,):
        pass

def json_dump(val):
    try:
        return json.dumps(val)
    except (TypeError, ValueError,), err:
        pass

def load_json_or_list(val):
    try:
        return json.loads(val)
    except (TypeError, ValueError,):
        if val:
            return [{'identifier': v} for v in val.split(',')]


def get_geonames_config():
    out = {}
    uname = config.get(GEONAMES_USERNAME)
    limit_to = config.get(GEONAMES_LIMIT_TO)
    if uname:
        out['username'] = uname
    if limit_to:
        out['limit_to'] = limit_to
    return out

  
def get_localized_subtheme(subtheme_id, lang):
    return interfaces.get_localized_subtheme(subtheme_id, lang) or subtheme_id


def get_dcatapit_subthemes(lang):
    """
    Dump subthemes tree with localized lables for all themes 
    """
    out = {}
    def _get_name(opt_val, depth):
        return u'{} {}'.format('-'*depth, opt_val)
      
    for theme in Subtheme.get_theme_names():
        out[theme] = theme_l = []
        for opt, label in Subtheme.for_theme(theme, lang):
            theme_l.append({'name': _get_name(label, opt.depth),
                            'value': opt.uri})
    return out


def dump_dcatapit_subthemes(value):
    """
    Dump subthemes from dataset dict, handle old format as well
    """
    out = []
    data = []
    try:
        data = json.loads(value)
    except (ValueError, TypeError):
        if isinstance(value, (str, unicode,)):
            data = [{'theme': s, 'subthemes': []} for s in value.strip('{}').split(',')]
    out.extend(data)
    return out

def load_dcatapit_subthemes(value, lang):
    """
    Load json with subthemes and get localized subtheme names. Used in template
    """
    data = dump_dcatapit_subthemes(value)
    out = []
    
    for item in data:
        localized_theme = interfaces.get_localized_tag_name(item['theme'], lang=lang)
        outitem = {'theme': localized_theme,
                   'subthemes': []}
        from_model = Subtheme.for_theme(item['theme'], lang)
        for st, label in from_model:
            if st.uri in item['subthemes']:
                outitem['subthemes'].append(label)
        out.append(outitem)
    return out

def get_organization_by_identifier(context, identifier):
    """
    quick'n'dirty way to get organization by rights holder's identifer
    from dcat rdf.
    """
    try:
        ge = Session.query(GroupExtra).filter_by(key='identifier',
                                            value=identifier,
                                            state='active')\
                                 .one()
    except MultipleResultsFound:
        raise
    except NoResultFound:
        ge = None
    if ge:
        # safety check
        assert ge.group_id is not None
        ctx = context.copy()
        ctx.update(DEFAULT_ORG_CTX)

        return toolkit.get_action('organization_show')(context=ctx, data_dict={'id': ge.group_id})
