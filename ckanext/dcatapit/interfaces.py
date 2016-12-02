import logging

from ckan.lib.base import model
from ckan.model import Session
from pylons.i18n.translation import get_lang

from ckan.plugins.interfaces import Interface

log = logging.getLogger(__name__)


class ICustomSchema(Interface):
    '''
    Allows extensions to provide their own schema fields.
    '''
    def get_custom_schema(self):
        '''gets the array containing the custom schema fields'''
        return []


def get_language():
    lang = get_lang()

    if lang is not None:
        lang = unicode(lang[0])

    return lang

def save_extra_package_multilang(pkg, lang, field_type):
    try:
        from ckanext.multilang.model import PackageMultilang
    except ImportError:
        log.warn('DCAT-AP_IT: multilang extension not available.')
        return

    log.debug('Creating create_loc_field for package ID: %r', str(pkg.get('id')))
    PackageMultilang.persist(pkg, lang, field_type)
    log.info('Localized field created successfully')

def update_extra_package_multilang(extra, pkg_id, field, lang, field_type='extra'):
    try:
        from ckanext.multilang.model import PackageMultilang
    except ImportError:
        log.warn('DCAT-AP_IT: multilang extension not available.')
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
        log.warn('DCAT-AP_IT: multilang extension not available.')
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

def persist_tag_multilang(name, lang, localized_text, vocab_name):
    try:
        from ckanext.multilang.model import TagMultilang
    except ImportError:
        log.warn('DCAT-AP_IT: multilang extension not available. Will not persist name:%r for lang:%s', name, lang)
        return

    log.info('DCAT-AP_IT: persisting tag multilang for tag %r ...', name)

    tag = TagMultilang.by_name(name, lang)

    if tag:
        # Update the existing record
        if localized_text and localized_text != tag.text:
            tag.text = localized_text

            try:
                tag.save()
                logging.info('::::::::: OBJECT TAG UPDATED SUCCESSFULLY :::::::::') 
                pass
            except Exception, e:
                # on rollback, the same closure of state
                # as that of commit proceeds. 
                Session.rollback()

                log.error('Exception occurred while persisting DB objects: %s', e)
                raise
    else:
        # Create a new localized record
        vocab = model.Vocabulary.get(vocab_name)
        existing_tag = model.Tag.by_name(name, vocab)

        if existing_tag:
            TagMultilang.persist({'id': existing_tag.id, 'name': name, 'text': localized_text}, lang)
            logging.info('::::::::: OBJECT TAG PERSISTED SUCCESSFULLY :::::::::')


def get_localized_tag_name(tag_name=None):
    try:
        from ckanext.multilang.model import TagMultilang
    except ImportError:
        log.warn('DCAT-AP_IT: multilang extension not available. Tag %s will not be localized', tag_name)
        return tag_name

    if tag_name:
        lang = get_language()
        localized_tag_name = TagMultilang.by_name(tag_name, lang)
        if localized_tag_name:
            return localized_tag_name.text
        else:
            return tag_name
    else:
        return None
