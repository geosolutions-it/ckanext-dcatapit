import logging

from ckan.lib.base import model
from ckan.model import Session
from ckanext.multilang.model import TagMultilang
from pylons.i18n.translation import get_lang

def get_language():
    lang = get_lang()
    
    if lang is not None:
        lang = unicode(lang[0])        
    
    return lang

def persist_tag_multilang(name, lang, localized_text, vocab_name):
    logging.info('DCAT-AP_IT: persisting tag multilang for tag %r ...', name)
    
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

                logging.error('Exception occurred while persisting DB objects: %s', e)
                raise
    else:
        # Create a new localized record
        vocab = model.Vocabulary.get(vocab_name)        
        existing_tag = model.Tag.by_name(name, vocab)

        if existing_tag:
            TagMultilang.persist({'id': existing_tag.id, 'name': name, 'text': localized_text}, lang)
            logging.info('::::::::: OBJECT TAG PERSISTED SUCCESSFULLY :::::::::')

def get_localized_tag_name(tag_name=None):
    if tag_name:
        lang = get_language()
        localized_tag_name = TagMultilang.by_name(tag_name, lang)
        if localized_tag_name:
            return localized_tag_name.text
        else:
            return tag_name
    else:
        return None