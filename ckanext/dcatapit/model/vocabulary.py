import logging

from sqlalchemy import Column, ForeignKey, Table, types

from ckan.model import Session, meta
from ckan.model.domain_object import DomainObject

log = logging.getLogger(__name__)

__all__ = ['DCATAPITTagVocabulary', 'dcatapit_vocabulary_table', ]

dcatapit_vocabulary_table = Table(
    'dcatapit_vocabulary', meta.metadata,
    Column('id', types.Integer, primary_key=True),
    Column('tag_id', types.UnicodeText, ForeignKey('tag.id', ondelete='CASCADE'), nullable=False),
    Column('tag_name', types.UnicodeText, nullable=False, index=True),
    Column('lang', types.UnicodeText, nullable=False, index=True),
    Column('text', types.UnicodeText, nullable=False, index=False)
)


class DCATAPITTagVocabulary(DomainObject):
    def __init__(self, tag_id=None, tag_name=None, lang=None, text=None):
        self.tag_id = tag_id
        self.tag_name = tag_name
        self.lang = lang
        self.text = text

    @classmethod
    def by_name(self, tag_name, tag_lang, autoflush=True):
        query = meta.Session.query(DCATAPITTagVocabulary)\
            .filter(DCATAPITTagVocabulary.tag_name == tag_name,
                    DCATAPITTagVocabulary.lang == tag_lang)\
            .autoflush(autoflush)

        return query.first()

    @classmethod
    def all_by_name(self, tag_name, autoflush=True):
        query = meta.Session.query(DCATAPITTagVocabulary)\
            .filter(DCATAPITTagVocabulary.tag_name == tag_name)\
            .autoflush(autoflush)

        return {record.lang: record.text for record in query.all()}

    @classmethod
    def by_tag_id(self, tag_id, tag_lang, autoflush=True):
        query = meta.Session.query(DCATAPITTagVocabulary)\
            .filter(DCATAPITTagVocabulary.tag_id == tag_id,
                    DCATAPITTagVocabulary.lang == tag_lang)\
            .autoflush(autoflush)

        return query.first()

    @classmethod
    def persist(self, tag, lang):
        session = meta.Session
        try:
            session.add_all([
                DCATAPITTagVocabulary(tag_id=tag.get('id'), tag_name=tag.get('name'), lang=lang, text=tag.get('text')),
            ])

            session.commit()
        except Exception as err:
            # on rollback, the same closure of state
            # as that of commit proceeds.
            session.rollback()

            log.error('Exception occurred while persisting DB objects: %s', err)
            raise

    @classmethod
    def nin_tags_ids(self, ids, autoflush=True):
        query = meta.Session.query(DCATAPITTagVocabulary).filter(DCATAPITTagVocabulary.tag_id.notin_(ids))
        query = query.autoflush(autoflush)
        tags = query.all()
        return tags


meta.mapper(DCATAPITTagVocabulary, dcatapit_vocabulary_table)
