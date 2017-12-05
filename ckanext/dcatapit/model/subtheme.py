#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import logging
from urlparse import urlparse

from sqlalchemy import types, Column, Table, ForeignKey, Index
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base, declared_attr

from rdflib.namespace import Namespace, RDF, XSD, SKOS, RDFS
from rdflib import Graph, URIRef

from ckan.lib.base import config
from ckan import model
from ckan.model import Session
from ckan.model import meta

from ckan import model
from ckanext.dcatapit.model.license import _Base


log = logging.getLogger(__name__)

__all__ = ['Subtheme', 'SubthemeLabel', 'setup_subtheme_models', 'load_subthemes', 'clear_subthemes']

DeclarativeBase = declarative_base(metadata=meta.metadata)
CONFIG_THEME_LANGS = 'ckan.dcatapit.subthemes.langs'
THEME_LANGS = (config.get(CONFIG_THEME_LANGS) or '').split(' ')

DEFAULT_LANG = config.get('ckan.locale_default', 'en')


class Subtheme(_Base, DeclarativeBase):
    __tablename__ = 'dcatapit_subtheme'

    id = Column(types.Integer, primary_key=True)
    version = Column(types.Unicode, nullable=True)
    identifier = Column(types.Unicode, nullable=False)
    uri = Column(types.Unicode, nullable=False, unique=True)
    default_label = Column(types.Unicode, nullable=False)
    theme = Column(types.Unicode, nullable=False, unique=False)
    
    @classmethod
    def q(cls):
        return Session.query(cls)

    @declared_attr
    def __table_args__(cls):
        return (Index('{}_theme_idx'.format(cls.__tablename__), 'theme',),)

    def get_names(self):
        return [{'lang': n.lang, 'name': n.label} for n in self.names]

    def get_names_dict(self):
        out = {}
        for n in self.names:
            out[n.lang] = n.label
        return out

    def get_name(self, lang):
        return self.get_names_dict()[lang]        
    
    @classmethod
    def add_for_theme(cls, g, theme_ref, subtheme_ref):
        labels = {}
        for l in g.objects(theme_ref, SKOS.prefLabel):
            labels[l.language] = str(l)

        version = g.value(subtheme_ref, OWL.versionInfo) or ''
        identifier = g.value(subtheme_ref, DCT.identifier) or ''
        default_label = labels[DEFAULT_LANG]
        inst = cls(version=version,
                   identifier=identifier,
                   uri=str(subtheme_ref),
                   default_label=default_label,
                   theme=cls.normalize_theme(theme_ref))
        Session.add(inst)

        revision = getattr(Session, 'revision', None) or repo.new_revision()
        Session.flush()
        Session.revision = revision
        for lang, label in labels.items():
            l = SubthemeLabel(subtheme_id=inst.id,
                              lang=lang,
                              label=label)
            Session.add(l)
        Session.flush()
        Session.revision = revision
        return inst
            
    @staticmethod
    def normalize_theme(theme_uri):
        s = str(theme_uri)
        return s.split('/')[-1]

    @classmethod
    def map_themes(cls, themes_g, eurovoc_g):
        for theme in themes_g.subjects(RDF.type, URIRef('http://www.w3.org/2004/02/skos/core#Concept')):
            sub_themes = themes_g.objects(theme, SKOS.narrowMatch)
            for sub_theme in sub_themes:
                cls.add_for_theme(eurovoc_g, theme, sub_theme)


class SubthemeLabel(_Base, DeclarativeBase):
    __tablename__ = 'dcatapit_subtheme_labels'

    id = Column(types.Integer, primary_key=True)
    subtheme_id = Column(types.Integer, ForeignKey(Subtheme.id))
    lang = Column(types.Unicode, nullable=False)
    label = Column(types.Unicode, nullable=False)

    subtheme = orm.relationship(Subtheme, backref="names")


def clear_subthemes():
    Subtheme.q().delete()
    SubthemeLabel.q().delete()


def load_subthemes(themes, eurovoc):
    themes_g = Graph()
    eurovoc_g = Graph()

    themes_g.parse(themes)
    eurovoc_g.parse(eurovoc)
    Subtheme.map_themes(themes_g, eurovoc_g)


def setup_subtheme_models():
    for t in (Subtheme.__table__, SubthemeLabel.__table__,):
        if not t.exists():
            t.create()
