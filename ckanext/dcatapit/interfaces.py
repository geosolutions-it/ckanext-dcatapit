import json
import logging
from enum import Enum

import ckan.lib.search as search
from ckantoolkit import config
# from ckan.lib.base import model
import ckan.model as model
from ckan.lib.i18n import get_lang
from ckan.model import Session
from ckan.plugins.interfaces import Interface
from ckanext.dcatapit.model import (
    TagLocalization,
    License,
    Subtheme,
)

log = logging.getLogger(__name__)


class ICustomSchema(Interface):
    """
    Allows extensions to extend DCATAPIT schema
    """

    def get_custom_schema(self):
        """
        Provide the custom fields
        :return: an array of dict representing the new fields, in the same way the fields are defined in schema.py.
                 You may want to specify {'in_tab': True} if the field is handled in an overriding package_basic_field
        """
        return []

    def get_schema_updates(self):
        """
        Provide info to modify default DCATAPIT fields
        :return: a dict {field_schema_name: {map of attribs to be changed}} of the fields to be updates
        """
        return {}


class ICustomOrganizationSchema(Interface):
    """
    Allows extensions to extend DCATAPIT schema for Organizations
    """

    def get_custom_org_schema(self):
        """
        Provide the custom fields for Orgs
        """
        return []

    def get_org_schema_updates(self):
        """
        Provide info to modify default DCATAPIT fields for Orgs
        """
        return {}


def get_language():
    try:
        lang = get_lang()
    except Exception as e:
        lang = config.get(u'ckan.locale_default', u'it')
        # log.debug(f'Exception while retrieving lang. Using [{lang}]', stack_info=True)

    if lang is not None:
        if isinstance(lang, list):
            lang = lang[0]
    return lang


def update_solr_package_indexes(package_dict):
    # Updating Solr Index
    if package_dict:
        log.debug('::: UPDATING SOLR INDEX :::')

        # solr update here
        psi = search.PackageSearchIndex()

        # update the solr index in batches
        BATCH_SIZE = 50

        def process_solr(q):
            # update the solr index for the query
            query = search.PackageSearchQuery()
            q = {
                'q': q,
                'fl': 'data_dict',
                'wt': 'json',
                'fq': 'site_id:"%s"' % config.get('ckan.site_id'),
                'rows': BATCH_SIZE
            }

            for result in query.run(q)['results']:
                data_dict = json.loads(result['data_dict'])
                if data_dict['owner_org'] == package_dict.get('owner_org'):
                    psi.index_package(data_dict, defer_commit=True)

        count = 0
        q = []

        q.append('id:"%s"' % (package_dict.get('id')))
        count += 1
        if count % BATCH_SIZE == 0:
            process_solr(' OR '.join(q))
            q = []

        if len(q):
            process_solr(' OR '.join(q))
        # finally commit the changes
        psi.commit()
    else:
        log.warning('::: package_dict is None: SOLR INDEX CANNOT BE UPDATED! :::')


def save_extra_package_multilang(pkg, lang, field_type):
    try:
        from ckanext.multilang.model import PackageMultilang
    except ImportError:
        log.warning('DCAT-AP_IT: multilang extension not available.')
        return

    log.debug('Creating create_loc_field for package ID: %r', str(pkg.get('id')))
    PackageMultilang.persist(pkg, lang, field_type)
    log.info('Localized field created successfully')


def upsert_package_multilang(pkg_id, field_name, field_type, lang, text):
    try:
        from ckanext.multilang.model import PackageMultilang
    except ImportError:
        log.warning('DCAT-AP_IT: multilang extension not available.')
        return

    pml = PackageMultilang.get(pkg_id, field_name, lang, field_type)
    if not pml and text:
        PackageMultilang.persist({'id': pkg_id, 'field': field_name, 'text': text}, lang, field_type)
    elif pml and not text:
        pml.purge()
    elif pml and not pml.text == text:
        pml.text = text
        pml.save()


def upsert_resource_multilang(res_id, field_name, lang, text):
    try:
        from ckanext.multilang.model import ResourceMultilang
    except ImportError:
        log.warning('DCAT-AP_IT: multilang extension not available.')
        return

    ml = ResourceMultilang.get_for_pk(res_id, field_name, lang)
    if not ml and text:
        ResourceMultilang.persist_resources([ResourceMultilang(res_id, field_name, lang, text)])
    elif ml and not text:
        ml.purge()
    elif ml and not ml.text == text:
        ml.text = text
        ml.save()


def update_extra_package_multilang(extra, pkg_id, field, lang, field_type='extra'):
    try:
        from ckanext.multilang.model import PackageMultilang
    except ImportError:
        log.warning('DCAT-AP_IT: multilang extension not available.')
        return

    if extra.get('key') == field.get('name', None) and field.get('localized', False) == True:
        log.debug(':::::::::::::::Localizing schema field: %r', field['name'])

        f = PackageMultilang.get(pkg_id, field['name'], lang, field_type)
        if f:
            if extra.get('value') == '':
                f.purge()
            elif f.text != extra.get('value'):
                # Update the localized field value for the current language
                f.text = extra.get('value')
                f.save()

                log.info('Localized field updated successfully')

        elif extra.get('value') != '':
            # Create the localized field record
            save_extra_package_multilang({'id': pkg_id, 'text': extra.get('value'), 'field': extra.get('key')}, lang, 'extra')


def get_localized_field_value(field=None, pkg_id=None, field_type='extra'):
    try:
        from ckanext.multilang.model import PackageMultilang
    except ImportError:
        log.warning('DCAT-AP_IT: multilang extension not available.')
        return

    if field and pkg_id:
        lang = get_language()
        if lang:
            localized_value = PackageMultilang.get(pkg_id, field, lang, field_type)
            if localized_value:
                return localized_value.text
            else:
                return None
        else:
            return None
    else:
        return None


def get_for_package(pkg_id):
    '''
    Returns all the localized fields of a dataset, in a dict of dicts, i.e.:
        {FIELDNAME:{LANG:label,...},...}

    Returns None if multilang extension not loaded.
    '''

    try:
        from ckanext.multilang.model import PackageMultilang
    except ImportError:
        log.warning('DCAT-AP_IT: multilang extension not available.')

        # TODO: if no multilang, return the dataset in a single language in the same format of the multilang data
        return None

    records = PackageMultilang.get_for_package(pkg_id)
    return _multilang_to_dict(records)


def get_for_group_or_organization(pkg_id):
    '''
    Returns all the localized fields of group (or organization), in a dict of dicts, i.e.:
        {FIELDNAME:{LANG:label,...},...}

    Returns None if multilang extension not loaded.
    '''

    try:
        from ckanext.multilang.model import GroupMultilang
    except ImportError:
        log.warning('DCAT-AP_IT: multilang extension not available.')

        # TODO: if no multilang, return the dataset in a single language in the same format of the multilang data
        return None
    records = GroupMultilang.get_for_group_id(pkg_id)
    return _multilang_to_dict(records)


def get_for_resource(res_id):
    '''
    Returns all the localized fields of a dataset's resources, in a dict of dicts, i.e.:
         {FIELDNAME:{LANG:label, ...}, ...}

    Returns None if multilang extension not loaded.
    '''

    try:
        from ckanext.multilang.model import ResourceMultilang
    except ImportError:
        log.warning('DCAT-AP_IT: multilang extension not available.')

        return None

    records = ResourceMultilang.get_for_resource_id(res_id)
    return _multilang_to_dict(records)


def _multilang_to_dict(records):
    fields_dict = {}

    for r in records:
        fieldname = r.field
        lang = r.lang
        value = r.text

        lang_dict = fields_dict.get(fieldname, {})
        if len(lang_dict) == 0:
            fields_dict[fieldname] = lang_dict

        lang_dict[lang] = value

    return fields_dict


class DBAction(Enum):
    ERROR = -1
    NONE = 0
    CREATED = 1
    UPDATED = 2


def persist_tag_multilang(tag: model.Tag, lang, label, vocab):
    log.debug('DCAT-AP_IT: persisting tag multilang for tag %r ...', tag.name)

    tag_loc = TagLocalization.by_tag_id(tag.id, lang)

    if tag_loc:
        # Update the existing record
        if label:
            if label != tag_loc.text:
                try:
                    tag_loc.text = label
                    tag_loc.save()
                    return DBAction.UPDATED, tag_loc.id
                except Exception as err:
                    # on rollback, the same closure of state
                    # as that of commit proceeds.
                    Session.rollback()

                    log.error('Exception occurred while persisting DB objects: %s', err)
                    raise
            else:
                return DBAction.NONE, tag_loc.id
        else:
            log.warning(f'Skipping empty label V:{vocab.name} T:{tag.name} L:{lang}')
            return DBAction.ERROR, tag_loc.id
    else:
        # Create a new localized record
        tag_loc = TagLocalization.persist(tag, label, lang)
        return DBAction.CREATED, tag_loc.id


def get_localized_tag_name(tag_name=None, fallback_lang=None, lang=None):
    if tag_name:
        if lang is None:
            lang = get_language()

        localized_tag_name = TagLocalization.by_name(tag_name, lang)

        if localized_tag_name:
            return localized_tag_name.text
        else:
            if fallback_lang:
                fallback_name = TagLocalization.by_name(tag_name, fallback_lang)

                if fallback_name:
                    fallback_name = fallback_name.text
                    return fallback_name
                else:
                    return tag_name
            else:
                return tag_name
    else:
        return None


def get_localized_tag_by_id(tag_id, lang=None):
    if lang is None:
        lang = get_language()

    localized_tag_name = TagLocalization.by_tag_id(tag_id, lang)
    return localized_tag_name.text if localized_tag_name else None


def get_all_localized_tag_labels(tag_name):
    return TagLocalization.all_by_name(tag_name)


def get_resource_licenses_tree(value, lang):
    options = License.for_select(lang)

    out = []
    for license, label in options:
        out.append({'selected': license.uri == value,
                    'value': license.uri,
                    # let's do indentation
                    'text': label,
                    'depth': license.rank_order - 1,
                    'depth_str': '&nbsp;&nbsp;' * (license.rank_order - 1) or '',
                    'level': license.rank_order})
    return out


def get_license_for_dcat(license_type):
    l = License.get(license_type or License.DEFAULT_LICENSE)
    if not l or not l.license_type:
        l = License.get(License.DEFAULT_LICENSE)
    if not l:
        log.error('*** Licenses vocabulary has not been loaded ***')
        return None, '-', None, None, None, None
    names = dict((k['lang'], k['name']) for k in l.get_names())
    return l.license_type, l.default_name, l.document_uri, l.version, l.uri, names


def get_license_from_dcat(license_uri, license_dct, prefname, **license_names):
    # First try dcatapit info
    l = License.get(license_uri)

    if not l and prefname:
        l = License.get(prefname)

    if not l:
        for lang, name in license_names.items():
            l = License.get_by_lang(lang, name)
            if l:
                break
    if not l and license_dct:
        # try and use DCT licence URI (usually level 2 in DCATAPIT voc)
        l = License.get(license_dct)

    return l or License.get(License.DEFAULT_LICENSE)


def get_localized_subtheme(subtheme, lang):
    localized = Subtheme.get_any(subtheme)
    if not localized:
        return
    return localized.get_name(lang)


def get_localized_subthemes(subthemes):

    q = Subtheme.get_localized(*subthemes)
    out = {}
    for item in q:
        lang, label = item  # .lang, item.label
        try:
            out[lang].append(label)
        except KeyError:
            out[lang] = [label]
    return out


def populate_resource_license(package_dict):
    license_id = package_dict.get('license_id')
    license_url = None
    license = None
    access_constraints = None
    for ex in package_dict.get('extras') or []:
        if ex['key'] in ('license_url', 'licence_url',):
            license_url = ex['value']
        elif ex['key'] in ('license', 'licence',):
            license = ex['value']
        elif ex['key'] == 'access_constraints':
            access_constraints = ex['value']

    if not (access_constraints or license_id or license or license_url):
        l = License.get(License.DEFAULT_LICENSE)

    else:
        l, default = License.find_by_token(access_constraints, license, license_id, license_url)

    for res in package_dict['resources']:
        res['license_type'] = l.uri
    return package_dict
