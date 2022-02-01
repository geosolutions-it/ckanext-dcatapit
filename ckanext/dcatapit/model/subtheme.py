#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from ckan.lib.base import config
from ckan.model import Tag, Vocabulary, meta, DomainObject

from sqlalchemy import Column, ForeignKey, Index, and_, or_, orm, types
from sqlalchemy.exc import SQLAlchemyError as SAError, IntegrityError
from sqlalchemy.ext.declarative import declarative_base, declared_attr

from ckanext.dcat.profiles import DCT

log = logging.getLogger(__name__)

__all__ = ['Subtheme', 'SubthemeLabel',
           'clear_subthemes']

DeclarativeBase = declarative_base(metadata=meta.metadata)

CONFIG_THEME_LANGS = 'ckan.dcatapit.subthemes.langs'
THEME_LANGS = (config.get(CONFIG_THEME_LANGS) or '').split(' ')
DEFAULT_LANG = config.get('ckan.locale_default', 'it')


class ThemeToSubtheme(DeclarativeBase, DomainObject):
    __tablename__ = 'dcatapit_theme_to_subtheme'

    VOCAB_NAME = 'eu_themes'

    id = Column(types.Integer, primary_key=True)
    tag_id = Column(types.Unicode, ForeignKey(Tag.id), nullable=False)
    subtheme_id = Column(types.Integer, ForeignKey('dcatapit_subtheme.id'), nullable=False)

    subtheme = orm.relationship('Subtheme')
    tag = orm.relationship(Tag)

    vocab_id = None  # used as a cache in get_vocabulary_id

    @declared_attr
    def __table_args__(cls):
        return (Index(f'{cls.__tablename__}_tag_subtheme_idx',
                      'subtheme_id', 'tag_id'),)

    @classmethod
    def get_vocabulary_id(cls):
        if cls.vocab_id is None:
            q = cls.Session.query(Vocabulary).filter_by(name=cls.VOCAB_NAME)
            vocab = q.first()
            if not vocab:
                raise ValueError(f'No vocabulary for {cls.VOCAB_NAME}')
            cls.vocab_id = vocab.id
        return cls.vocab_id

    @classmethod
    def get_tag(cls, name):
        vid = cls.get_vocabulary_id()
        tag = cls.Session.query(Tag).filter_by(vocabulary_id=vid, name=name).first()
        if not tag:
            raise ValueError(f'No tag for {name}')
        return tag

    @classmethod
    def q(cls):
        return cls.Session.query(cls)


class Subtheme(DeclarativeBase, DomainObject):
    __tablename__ = 'dcatapit_subtheme'

    id = Column(types.Integer, primary_key=True)
    version = Column(types.Unicode, nullable=True)
    identifier = Column(types.Unicode, nullable=False)
    uri = Column(types.Unicode, nullable=False, unique=True)
    default_label = Column(types.Unicode, nullable=False)
    parent_id = Column(types.Integer, ForeignKey('dcatapit_subtheme.id'), nullable=True)
    depth = Column(types.Integer, default=0)
    path = Column(types.Unicode, nullable=False, unique=False)
    themes = orm.relationship(Tag, secondary=ThemeToSubtheme.__table__)
    parent = orm.relationship('Subtheme', lazy=True, uselist=False, remote_side=[id])

    @classmethod
    def q(cls):
        return cls.Session.query(cls)

    @classmethod
    def get(cls, uri):
        try:
            return cls.q().filter_by(uri=uri).one()
        except SAError:
            return

    @classmethod
    def get_any(cls, value):
        q = cls.q()
        try:
            return q.filter(or_(cls.uri == value,
                                cls.identifier == value,
                                cls.default_label == value)).one()
        except SAError:
            return

    def get_names(self):
        return [{'lang': n.lang, 'name': n.label} for n in self.names]

    def get_names_dict(self):
        out = {}
        for n in self.names:
            out[n.lang] = n.label
        return out

    def get_name(self, lang):
        return self.get_names_dict()[lang]

    def get_path(self):
        parent = self
        old_parent = None
        out = []

        while parent and parent != old_parent:
            out.append(parent.default_label)
            old_parent = parent
            parent = parent.parent
        return '/'.join(reversed(out))

    def update_path(self):
        path = self.get_path()
        self.path = path

    def __str__(self):
        return 'Subtheme {} [{}] for {} themes'.format(
            self.uri, self.default_label, ','.join([t.name for t in self.themes])
        )

    @staticmethod
    def normalize_theme(theme_uri):
        return str(theme_uri).split('/')[-1]

    @classmethod
    def for_theme(cls, theme, lang=None):
        tag = ThemeToSubtheme.get_tag(theme)
        if lang:
            q = cls.Session.query(cls, SubthemeLabel.label)\
                       .join(SubthemeLabel,
                             and_(SubthemeLabel.subtheme_id == cls.id,
                                  SubthemeLabel.lang == lang))\
                       .join(ThemeToSubtheme,
                             and_(ThemeToSubtheme.tag_id == tag.id,
                                  ThemeToSubtheme.subtheme_id == cls.id))\
                       .order_by(cls.parent_id, cls.path)

        else:
            q = cls.Session.query(cls).join(ThemeToSubtheme,
                                        and_(ThemeToSubtheme.tag_id == tag.id,
                                             ThemeToSubtheme.subtheme_id == cls.id))\
                .order_by(cls.parent_id, cls.path)
        return q

    @classmethod
    def for_theme_values(cls, theme, lang=None):
        q = cls.for_theme(theme, lang)
        return [i.uri for i in q]

    @classmethod
    def get_theme_names(cls):
        q = cls.Session.query(Tag.name)\
                   .join(ThemeToSubtheme,
                         ThemeToSubtheme.tag_id == Tag.id)\
                   .order_by(Tag.name)
        return [t[0] for t in q]

    @classmethod
    def get_localized(cls, *subthemes):
        q = cls.Session.query(SubthemeLabel.lang, SubthemeLabel.label)\
                   .join(cls, cls.id == SubthemeLabel.subtheme_id)\
                   .filter(or_(cls.uri.in_(subthemes),
                               cls.default_label.in_(subthemes)))
        return q


class SubthemeLabel(DeclarativeBase, DomainObject):
    __tablename__ = 'dcatapit_subtheme_labels'

    id = Column(types.Integer, primary_key=True)
    subtheme_id = Column(types.Integer, ForeignKey(Subtheme.id))
    lang = Column(types.Unicode, nullable=False)
    label = Column(types.Unicode, nullable=False)
    subtheme = orm.relationship(Subtheme, backref='names')

    @classmethod
    def q(cls):
        return cls.Session.query(cls)

    @declared_attr
    def __table_args__(cls):
        return (Index(f'{cls.__tablename__}_label_subtheme_idx',
                      'subtheme_id', 'lang'),)


def clear_subthemes():
    SubthemeLabel.q().delete()
    ThemeToSubtheme.q().delete()
    Subtheme.q().delete()
