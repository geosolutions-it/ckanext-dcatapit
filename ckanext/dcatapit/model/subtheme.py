#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from sqlalchemy import types, Column, ForeignKey, Index, Table
from sqlalchemy import orm, and_, or_
from sqlalchemy.exc import SQLAlchemyError as SAError
from sqlalchemy.ext.declarative import declarative_base, declared_attr

from rdflib.namespace import RDF, SKOS, OWL
from rdflib import Graph, URIRef

from ckanext.dcat.profiles import DCT
from ckan.lib.base import config
from ckan.model import Session, Tag, Vocabulary
from ckan.model import meta, repo

from ckanext.dcatapit.model.license import _Base


log = logging.getLogger(__name__)

__all__ = ['Subtheme', 'SubthemeLabel',
           'setup_subtheme_models',
           'load_subthemes', 'clear_subthemes']

DeclarativeBase = declarative_base(metadata=meta.metadata)

CONFIG_THEME_LANGS = 'ckan.dcatapit.subthemes.langs'
THEME_LANGS = (config.get(CONFIG_THEME_LANGS) or '').split(' ')
DEFAULT_LANG = config.get('ckan.locale_default', 'en')


class ThemeToSubtheme(_Base, DeclarativeBase):
    __tablename__ = 'dcatapit_theme_to_subtheme'

    VOCAB_NAME = 'eu_themes'

    id = Column(types.Integer, primary_key=True)
    tag_id = Column(types.Unicode, ForeignKey(Tag.id), nullable=False)
    subtheme_id = Column(types.Integer, ForeignKey('dcatapit_subtheme.id'), nullable=False)

    subtheme = orm.relationship('Subtheme')
    tag = orm.relationship(Tag)

    vocab = None

    @declared_attr
    def __table_args__(cls):
        return (Index('{}_tag_subtheme_idx'.format(cls.__tablename__),
                      'subtheme_id', 'tag_id'),)
    @classmethod
    def get_vocabulary(cls):
        if cls.vocab is None:
            q = Session.query(Vocabulary).filter_by(name=cls.VOCAB_NAME)
            vocab = q.first()
            if not vocab:
                raise ValueError("No vocabulary for {}".format(cls.VOCAB_NAME))

            cls.vocab = vocab
        return cls.vocab

    @classmethod
    def get_tag(cls, name):
        vocab = cls.get_vocabulary()
        tag = Session.query(Tag).filter_by(vocabulary_id=vocab.id, name=name).first()
        if not tag:
            raise ValueError("No tag for {}".format(name))
        return tag

    @classmethod
    def q(cls):
        return Session.query(cls)


class Subtheme(_Base, DeclarativeBase):
    __tablename__ = 'dcatapit_subtheme'

    id = Column(types.Integer, primary_key=True)
    version = Column(types.Unicode, nullable=True)
    identifier = Column(types.Unicode, nullable=False)
    uri = Column(types.Unicode, nullable=False, unique=True)
    default_label = Column(types.Unicode, nullable=False)
    parent_id = Column(types.Integer, ForeignKey('dcatapit_subtheme.id'), nullable=True)
    depth = Column(types.Integer, default=0)
    path = Column(types.Unicode, nullable=False, unique=True)
    themes = orm.relationship(Tag, secondary=ThemeToSubtheme.__table__)
    parent = orm.relationship('Subtheme', lazy=True, uselist=False, remote_side=[id])

    @classmethod
    def q(cls):
        return Session.query(cls)
    
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
            return q.filter(or_(cls.uri==value,
                                cls.identifier==value,
                                cls.default_label==value)).one()
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
        return "Subtheme {} [{}] for {} themes".format(self.uri, self.default_label, ','.join([t.name for t in self.themes]))

    @classmethod
    def add_for_theme(cls, g, theme_ref, subtheme_ref, parent=None):
        theme = cls.normalize_theme(theme_ref)
        existing = cls.q().filter_by(uri=str(subtheme_ref)).first()
        theme_tag = ThemeToSubtheme.get_tag(theme)
        
        revision = getattr(Session, 'revision', None) or repo.new_revision()

        # several themes may refer to this subtheme, so we'll just return
        # exising instance
        if existing:
            if not theme_tag in existing.themes:
                existing.themes.append(theme_tag)
            Session.flush()
            Session.revision = revision
            log.error("Subtheme %s already exists. Skipping", subtheme_ref)
            return existing

        labels = {}
        for l in g.objects(subtheme_ref, SKOS.prefLabel):
            labels[l.language] = unicode(l)
        if not labels:
            log.error("NO labels for %s. Skipping", subtheme_ref)
            return
        version = g.value(subtheme_ref, OWL.versionInfo) or ''
        identifier = g.value(subtheme_ref, DCT.identifier) or ''
        default_label = labels[DEFAULT_LANG]
        inst = cls(version=str(version),
                   identifier=str(identifier),
                   uri=str(subtheme_ref),
                   default_label=default_label,
                   parent_id=parent.id if parent else None,
                   depth=parent.depth + 1 if parent else 0)
        inst.update_path()
        Session.add(inst)
        Session.flush()
        Session.revision = revision

        if parent is None:
            inst.parent_id = inst.id

        theme_m = ThemeToSubtheme(tag_id=theme_tag.id, subtheme_id=inst.id)
        Session.add(theme_m)

        for lang, label in labels.items():
            l = SubthemeLabel(subtheme_id=inst.id,
                              lang=lang,
                              label=label)
            Session.add(l)
        Session.flush()
        Session.revision = revision
        # handle children

        for child in g.objects(subtheme_ref, SKOS.hasTopConcept):
            cls.add_for_theme(g, theme_ref, child, inst)

        return inst

    @staticmethod
    def normalize_theme(theme_uri):
        s = str(theme_uri)
        return s.split('/')[-1]

    @classmethod
    def map_themes(cls, themes_g, eurovoc_g):
        concept = SKOS.Concept
        for theme in themes_g.subjects(RDF.type, concept):
            sub_themes = themes_g.objects(theme, SKOS.narrowMatch)
            for sub_theme in sub_themes:
                cls.add_for_theme(eurovoc_g, theme, sub_theme)

    @classmethod
    def for_theme(cls, theme, lang=None):
        tag = ThemeToSubtheme.get_tag(theme)
        if lang:
            q = Session.query(cls, SubthemeLabel.label)\
                       .join(SubthemeLabel,
                             and_(SubthemeLabel.subtheme_id == cls.id,
                                 SubthemeLabel.lang == lang))\
                       .join(ThemeToSubtheme, 
                            and_(ThemeToSubtheme.tag_id == tag.id,
                                 ThemeToSubtheme.subtheme_id == cls.id))\
                       .order_by(cls.parent_id, cls.path)

        else:
            q = Session.query(cls).join(ThemeToSubtheme, 
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
        q = Session.query(Tag.name)\
                   .join(ThemeToSubtheme,
                         ThemeToSubtheme.tag_id == Tag.id)\
                   .order_by(Tag.name)
        return [t[0] for t in q]

    @classmethod
    def get_localized(cls, *subthemes):
        q = Session.query(SubthemeLabel.lang, SubthemeLabel.label)\
                   .join(cls, cls.id == SubthemeLabel.subtheme_id)\
                   .filter(or_(cls.uri.in_(subthemes),
                               cls.default_label.in_(subthemes)))
        return q

class SubthemeLabel(_Base, DeclarativeBase):
    __tablename__ = 'dcatapit_subtheme_labels'

    id = Column(types.Integer, primary_key=True)
    subtheme_id = Column(types.Integer, ForeignKey(Subtheme.id))
    lang = Column(types.Unicode, nullable=False)
    label = Column(types.Unicode, nullable=False)
    subtheme = orm.relationship(Subtheme, backref="names")

    @declared_attr
    def __table_args__(cls):
        return (Index('{}_label_subtheme_idx'.format(cls.__tablename__),
                      'subtheme_id', 'lang'),)


def clear_subthemes():
    SubthemeLabel.q().delete()
    ThemeToSubtheme.q().delete()
    Subtheme.q().delete()


def load_subthemes(themes, eurovoc):
    themes_g = Graph()
    eurovoc_g = Graph()
    # reset vocabulary attached to mapping
    ThemeToSubtheme.vocab = None
    themes_g.parse(themes)
    eurovoc_g.parse(eurovoc)
    Subtheme.map_themes(themes_g, eurovoc_g)


def setup_subtheme_models():
    for t in (Subtheme.__table__, SubthemeLabel.__table__, ThemeToSubtheme.__table__):
        if not t.exists():
            t.create()
