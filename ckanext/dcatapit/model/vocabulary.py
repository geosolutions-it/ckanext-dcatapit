import logging

from sqlalchemy import Column, ForeignKey, Table, types

from ckan.model import Session, meta
from ckan.model.domain_object import DomainObject

log = logging.getLogger(__name__)

__all__ = ['TagLocalization', 'dcatapit_vocabulary_table', ]

dcatapit_vocabulary_table = Table(
    'dcatapit_vocabulary', meta.metadata,
    Column('id', types.Integer, primary_key=True),
    Column('tag_id', types.UnicodeText, ForeignKey('tag.id', ondelete='CASCADE'), nullable=False),
    Column('tag_name', types.UnicodeText, nullable=False, index=True),
    Column('lang', types.UnicodeText, nullable=False, index=True),
    Column('text', types.UnicodeText, nullable=False, index=False)
)


class TagLocalization(DomainObject):
    def __init__(self, tag_id=None, tag_name=None, lang=None, text=None):
        self.tag_id = tag_id
        self.tag_name = tag_name
        self.lang = lang
        self.text = text

    @classmethod
    def by_name(cls, tag_name, tag_lang, autoflush=True):
        # !!! TODO: deprecate this method: name is not unique, since different vocs may have the same names
        log.warning(f'Deprecated TagLocalization.by_name call for "{tag_name}"')
        query = meta.Session.query(TagLocalization)\
            .filter(TagLocalization.tag_name == tag_name,
                    TagLocalization.lang == tag_lang)\
            .autoflush(autoflush)

        return query.first()

    @classmethod
    def all_by_name(cls, tag_name, autoflush=True):
        # !!! TODO: deprecate this method: name is not unique, since different vocs may have the same names
        log.warning('Deprecated TagLocalization.all_by_name call')
        query = meta.Session.query(TagLocalization)\
            .filter(TagLocalization.tag_name == tag_name)\
            .autoflush(autoflush)

        return {record.lang: record.text for record in query.all()}

    @classmethod
    def by_tag_id(cls, tag_id, tag_lang, autoflush=True):
        query = meta.Session.query(TagLocalization)\
            .filter(TagLocalization.tag_id == tag_id,
                    TagLocalization.lang == tag_lang)\
            .autoflush(autoflush)

        return query.first()

    @classmethod
    def persist(cls, tag, label, lang):
        session = meta.Session
        try:
            tl = TagLocalization(tag_id=tag.id, tag_name=tag.name, lang=lang, text=label)
            tl.save()
            session.commit()
            return tl
        except Exception as err:
            # on rollback, the same closure of state
            # as that of commit proceeds.
            session.rollback()

            log.error('Exception occurred while persisting DB objects: %s', err)
            raise

    @classmethod
    def id_not_in(cls, ids, autoflush=True):
        query = meta.Session.query(TagLocalization).filter(TagLocalization.tag_id.notin_(ids))
        query = query.autoflush(autoflush)
        tags = query.all()
        return tags


meta.mapper(TagLocalization, dcatapit_vocabulary_table)
