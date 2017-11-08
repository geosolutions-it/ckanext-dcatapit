import sys
import re
import logging

from sqlalchemy import types, Column, Table, ForeignKey
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

from rdflib.namespace import Namespace, RDF, XSD, SKOS, RDFS
from rdflib import Graph

from ckan.lib.base import config
from ckan import model
from ckan.model import Session
from ckan.model import meta
from ckan.model.domain_object import DomainObject

from ckan import model

log = logging.getLogger(__name__)

__all__ = ['License', 'LocalizedLicenseName', 'setup_license_models']

DeclarativeBase = declarative_base(metadata=meta.metadata)

NO_DIGITS = re.compile(r'\d+')

class _Base(object):

    @classmethod
    def q(cls):
        """
        Query object for current class
        """
        return Session.query(cls)

class License(_Base, DeclarativeBase):
    __tablename__ = 'dcatapit_license'
    id = Column(types.Integer, primary_key=True)
    license_type = Column(types.Unicode, nullable=True, unique=False)
    version = Column(types.Unicode, nullable=True)
    uri = Column(types.Unicode, nullable=False)
    document_uri = Column(types.Unicode, nullable=True)
    rank_order = Column(types.Integer, nullable=False)
    default_name = Column(types.Unicode, nullable=False)
    parent_id = Column(types.Integer, ForeignKey('dcatapit_license.id'), nullable=True)
    parent = orm.relationship('License',
                              backref=orm.backref("children",
                                                  remote_side=[id]),
                              lazy=True)
    
    DEFAULT_LICENSE = "http://dati.gov.it/onto/controlledvocabulary/License/C1_Unknown"

    @classmethod
    def get(cls, id_or_uri):
        """
        Get License based on first match from:
            * id
            * license uri (dcatapit vocabulary)
            * document uri (dcatapit reference to normative doc)
            * license_type (dcat uri)
        """
        inst = None
        try:
            inst = cls.q().filter_by(id=int(id_or_uri)).first()
        except ValueError:
            pass
        if inst:
            return inst
        inst = cls.q().filter_by(uri=id_or_uri).order_by(License.rank_order).first()
        if inst:
            return inst
        inst = cls.q().filter_by(document_uri=id_or_uri).first()
        if inst:
            return inst
        return cls.q().filter_by(license_type=id_or_uri).first()

    def __str__(self):
        return "License({}/{}: {})".format(self.license_type, self.version, self.default_name)

    def generate_tokens(self):
        """
        return list of tokens which may be matching to current license
        for example, CC-BY-SA may generate list of ['ccbysa', 'cc-by-sa', 'CCBYSA', 'CCBY', 'A35', ..]
        """
        out = []
        if self.license_type:
            license_type = self.license_type.lower().split('/')[-1]
            # <skos:exactMatch rdf:resource="http://purl.org/adms/licencetype/NonCommercialUseOnly"/>
            out.extend([self.license_type, self.license_type.lower(), license_type, license_type.lower()])
    
        if self.uri:
            # <rdf:Description rdf:about="http://dati.gov.it/onto/controlledvocabulary/License/B1_NonCommercial">
            uri = self.uri.lower().split('/')[-1]
            usplit = uri.split('_')
            out.extend([self.uri, self.uri.lower(), uri.lower(), uri] + usplit)
            noversion = NO_DIGITS.split(usplit[-1])[0]
            if noversion != usplit[-1]:
                out.append(noversion)
        if self.document_uri:
            # <dcatapit:referenceDoc rdf:datatype="http://www.w3.org/2001/XMLSchema#anyURI">http://creativecommons.org/licenses/by-nc/4.0/</dcatapit:referenceDoc>
            out.append(self.document_uri.lower())
        return out

    def set_parent(self, parent_uri):
        """
        Set parent for given license
        """
        parent = License.get(parent_uri)
        if not parent:
            raise ValueError("No parent %s object" % parent_uri)
        self.parent_id = parent.id
        Session.add(self)
        try:
            rev = Session.revision
        except AttributeError:
            rev = None
        Session.flush()

    def set_names(self, langs):
        """
        Set translated license names
        """

        self.names = []
        for lang_name, label in langs.items():
            localized = LocalizedLicenseName(license_id=self.id,
                                             lang = lang_name,
                                             label = label)
            Session.add(localized)

    def get_name(self, lang):
        for localized in self.names:
            if localized.lang == lang:
                return localized.label
        return self.default_name

    @classmethod
    def clear(cls):
        Session.query(LocalizedLicenseName).delete()
        Session.query(cls).delete()
        
        try:
            rev = Session.revision
        except AttributeError:
            rev = None
        Session.flush()
        Session.revision = rev


    @classmethod
    def for_license_uri(cls, uri, lang):
        inst = cls.get(uri)
        return inst.get_name(lang)

    @classmethod
    def for_dataset_license(cls, ds_license):
        license = cls.get(ds_license.url)

        tokens = cls.get_tokenized()
        if license:
            return license
        return cls.get(cls.DEFAULT_LICENSE)
    
    @classmethod
    def get_as_tokens(cls):
        out = {}
        for l in cls.q():
            tokens = l.generate_tokens()
            for t in tokens:
                try:
                    out[t].append(l)
                except KeyError:
                    out[t] = [l]
        return out

    @classmethod
    def find_by_token(cls, token):
        tokenized = cls.get_as_tokens()
        token_normalized = token.replace(' ', '').replace('-', '').lower()
        try:
            from_tokenized = tokenized[token_normalized]
            from_tokenized.sort(key=lambda t: t.version)
            # return latest version
            return from_tokenized[-1]
                
        except KeyError:
            return cls.get(cls.DEFAULT_LICENSE)

    @classmethod
    def from_data(cls,
                  license_type,
                  version,
                  uri,
                  document_uri,
                  rank_order,
                  names,
                  default_lang=None,
                  parent=None):

        if default_lang is None:
            default_lang = 'it'
        default_name = names[default_lang]

        if parent is not None:
            parent_inst = Session.query(License).filter_by(uri=str(parent)).first()
            if parent_inst:
                parent = parent_inst.id

        inst = cls(license_type=license_type,
                   version=version,
                   uri=uri,
                   document_uri=document_uri,
                   rank_order=rank_order,
                   parent_id=parent,
                   default_name=default_name)
        Session.add(inst)
        try:
            rev = Session.revision
        except AttributeError:
            rev = None
        Session.flush()
        Session.revision = rev
        inst.set_names(names)
        Session.flush()
        Session.revision = rev
        return inst

    @classmethod
    def for_select(cls, lang):
        q = Session.query(cls.license_type, cls.uri, LocalizedLicenseName.label)\
                   .join(LocalizedLicenseName)\
                   .filter(LocalizedLicenseName.lang==lang,
                           cls.rank_order > 1)\
                   .order_by(cls.rank_order,
                             cls.parent_id,
                             cls.default_name)
        return list(q)


class LocalizedLicenseName(_Base, DeclarativeBase):
    __tablename__ = 'dcatapit_localized_license_name'
    id = Column(types.Integer, primary_key=True)
    license_id = Column(types.Integer, ForeignKey(License.id))
    lang = Column(types.Unicode, nullable=False)
    label = Column(types.Unicode, nullable=False)

    license = orm.relationship(License, backref="names")


def setup_license_models():
    for t in (License.__table__, LocalizedLicenseName.__table__,):
        if not t.exists():
            t.create()


ADMS=Namespace("http://www.w3.org/ns/adms#")
CLVAPIT=Namespace("http://dati.gov.it/onto/clvapit#")
DCATAPIT=Namespace("http://dati.gov.it/onto/dcatapit#")
DCT=Namespace("http://purl.org/dc/terms/")
FOAF=Namespace("http://xmlns.com/foaf/0.1/")
OWL=Namespace("http://www.w3.org/2002/07/owl#")
RDF=Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
RDFS=Namespace("http://www.w3.org/2000/01/rdf-schema#")
SKOS=Namespace("http://www.w3.org/2004/02/skos/core#")
XKOS=Namespace("http://rdf-vocabulary.ddialliance.org/xkos#")

namespaces = {
    'adms': ADMS,
    'clvapit': CLVAPIT,
    'dcatapit': DCATAPIT,
    'dct': DCT,
    'foaf': FOAF,
    'owl': OWL,
    'rdf': RDF,
    'rdfs': RDFS,
    'skos': SKOS,
    'xkos': XKOS,
}


def _get_graph(path=None, url=None):
    if (not path and not url) or (path and url):
        raise ValueError("You should provide either path or url")
    g = Graph()
    for prefix, namespace in namespaces.iteritems():
        g.bind(prefix, namespace)

    if url:
        g.parse(location=url)
    else:
        g.parse(source=path)

    return g

def load_from_graph(path=None, url=None):
    """
    Loads license tree into db from provided path or url

    """
    g = _get_graph(path=path, url=url)
    License.clear()

    for license in g.subjects(None, SKOS.Concept):
        rank_order = g.value(license, CLVAPIT.hasRankOrder)
        # 2nd level, we have exactMatch
        license_type = g.value(license, SKOS.exactMatch)
        if not license_type:
            # 3rd level, need to go up
            parent = g.value(license, SKOS.broader)
            license_type = g.value(parent, SKOS.exactMatch)

        version = g.value(license, OWL.versionInfo)
        _labels = g.objects(license, SKOS.prefLabel)
        labels = dict((l.language, unicode(l),) for l in _labels)
        parent = None
        document_uri = g.value(license, DCATAPIT.referenceDoc)
        l = License.from_data(unicode(license_type or ''),
                              str(version),
                              uri=str(license),
                              document_uri=str(document_uri),
                              rank_order=int(str(rank_order)),
                              names=labels,
                              parent=parent)

    for license in g.subjects(None, SKOS.Concept):
        parent = None
        parents = list(g.objects(license, SKOS.broader))
        if parents:
            parent = parents[0]
            License.get(license).set_parent(parent)

