import re
import logging
from urlparse import urlparse

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

DIGITS = re.compile(r'\d+')

DIGITS_AND_COMMAS = re.compile(r'[\d\.]+')

# https://creativecommons.org/publicdomain/zero/1.0
# but also
# http://creativecommons.org/licenses/by-nd/1.0/
CC_LICENSE = re.compile(r'https{0,1}://creativecommons.org/(licenses|publicdomain)/(?P<license>[\w\-\.]+)/')
CC_LICENSE_NAME = re.compile(r'creative commons \w ', re.I)

# http://www.dati.gov.it/iodl/2.0
DATI_LICENSE = re.compile(r'https{0,1}://www.dati.gov.it/(?P<license>[\w\-\.]+)/')

# https://opendatacommons.org/licenses/odbl/summary/
# but also
# https://opendatacommons.org/category/odc-by/
OPENDATA_LICENSE = re.compile(r'https{0,1}://opendatacommons.org/(licenses|category)/(?P<license>[\w\-\.]+)/')

# http://www.formez.it/iodl/
FORMEZ_LICENSE = re.compile(r'https{0,1}://www.formez.it/(?P<license>[\w\-\.]+)/')

# https://www.gnu.org/licenses/fdl.html
GNU_LICENSE = re.compile(r'https{0,1}://www.gnu.org/licenses/(?P<license>[\w\-\.]+).html/')

LICENSES = (CC_LICENSE, OPENDATA_LICENSE, DATI_LICENSE, FORMEZ_LICENSE, GNU_LICENSE,)


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
    uri = Column(types.Unicode, nullable=False, unique=True)
    path = Column(types.Unicode, nullable=False, unique=True)
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
            * license name (dcatapit refererence from foaf:name)
            * license_type (dcat uri)
        """
        inst = None
        try:
            inst = cls.q().filter_by(id=int(id_or_uri)).first()
        except ValueError:
            pass
        if not inst:
            inst = cls.q().filter_by(uri=id_or_uri).order_by(License.rank_order).first()
        if not inst:
            inst = cls.q().filter_by(document_uri=id_or_uri).first()
        if not inst:
            inst = cls.q().filter_by(default_name=id_or_uri).first()
        if not inst:
            inst = cls.q().filter_by(license_type=id_or_uri).first()
        
        return inst

    def __str__(self):
        return "License({}/version {}: {}{})".format(self.license_type, self.version, self.default_name, ' [doc: {}]'.format(self.document_uri) if self.document_uri else '')

    def generate_tokens(self):
        """
        return list of tokens which may be matching to current license
        for example, CC-BY-SA may generate list of ['ccbysa', 'cc-by-sa', 'CCBYSA', 'CCBY', 'A35', ..]
        """
        out = []
        if self.license_type:
            license_type = self.license_type.lower().split('/')[-1]
            # <skos:exactMatch rdf:resource="http://purl.org/adms/licencetype/NonCommercialUseOnly"/>
            # -> NonCommercialUseOnly
            out.extend([self.license_type, self.license_type.lower(), license_type, license_type.lower()])
    
        if self.uri:
            # <rdf:Description rdf:about="http://dati.gov.it/onto/controlledvocabulary/License/B1_NonCommercial">
            # B1_NonCommercial
            uri = self.uri.lower().split('/')[-1]
            usplit = uri.split('_')
            out.extend([self.uri, self.uri.lower(), uri.lower(), uri] + usplit)
            noversion = DIGITS.split(usplit[-1])[0]
            if noversion != usplit[-1]:
                out.append(noversion)
        if self.document_uri:
            # <dcatapit:referenceDoc rdf:datatype="http://www.w3.org/2001/XMLSchema#anyURI">http://creativecommons.org/licenses/by-nc/4.0/</dcatapit:referenceDoc>
            # -> by-nc
            uri = self.document_uri.lower()
            out.append(uri)
            for lre in LICENSES:
                m = lre.search(uri)
                if m:
                    lname = m.groupdict()['license']
                    out.extend([lname, lname.replace('-', '')])
        if self.default_name:
            dn = self.default_name.lower()
            out.append(dn)
            s = CC_LICENSE_NAME.search(dn)
            if s:
                out.append(s.groups()[0])
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

    def get_names(self):
        return [{'lang': l.lang, 'name': l.label} for l in self.names]

    @classmethod
    def get_by_lang(cls, lang, label):
        q = cls.q().join(LocalizedLicenseName,
                         LocalizedLicenseName.license_id == cls.id)\
                   .where(LocalizedLicenseName.lang == lang,
                          LocalizedLicenseName.label == label)
        return q.first()

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
    def find_by_token(cls, *search_for):
        """
        Try to find license based on token provided. If no license can match,
        return default license defined in License.DEFAULT_LICENSE (unknown license)
        When multiple licenses are found for given token, they are sorted by version,
        and License with newest version will be returned.

        :param *search_for: List of strings to be searched for. This list will be tokenized
            and used in order provided
        :type *search_for: list of str

        :return: Returns tuple of License and fallback marker as boolean. 
            Fallback set to True means that no license could be found for 
            given token, and license returned is a default one.

        :rtype: (License, bool,)
        """
        # get list of token-> license mapping
        tokenized = cls.get_as_tokens()

        # generate tokens from input
        normalized_tokens = cls.generate_tokens_from_str(*search_for)
        for token in normalized_tokens:
            try:
                from_tokenized = tokenized[token]
                from_tokenized.sort(key=lambda t: t.version)
                # return latest version
                license = from_tokenized[-1]
                return license, False
            except KeyError, err:
                pass
        # return default if nothing was found
        license = cls.get(cls.DEFAULT_LICENSE)
        assert license is not None
        return license, True

    @classmethod
    def generate_tokens_from_str(cls, *strings):
        for s in strings:
            if not s:
                continue
            s = s.lower()
            if s.startswith('http'):
                yield s.split('/')[-1]

            else:
                # CC SOMETHING
                subs = s.split(' ')[-1]
                # cc-zero
                yield subs
                if subs.startswith('cc') and len(subs)> 2:
                    yield subs[2:]
                yield s.split('-')[-1]
            if 'odbl' in s:
                yield 'odbl'

            yield s.replace(' ', '')
            yield s.replace('-', '')
            yield s.replace(' ', '').replace('-', '')


    @classmethod
    def from_data(cls,
                  license_type,
                  version,
                  uri,
                  path,
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
                   path=path,
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
        q = Session.query(cls, LocalizedLicenseName.label)\
                   .join(LocalizedLicenseName)\
                   .filter(LocalizedLicenseName.lang==lang,
                           cls.rank_order>1)\
                   .order_by(cls.path)
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
        license_path=str(license).split('/')[-1].split('_')[0]
        document_uri = g.value(license, DCATAPIT.referenceDoc)
        l = License.from_data(unicode(license_type or ''),
                              str(version) if version else None,
                              uri=str(license),
                              path=license_path,
                              document_uri=str(document_uri) if document_uri else None,
                              rank_order=int(str(rank_order)),
                              names=labels,
                              parent=parent)

    for license in g.subjects(None, SKOS.Concept):
        parent = None
        parents = list(g.objects(license, SKOS.broader))
        if parents:
            parent = parents[0]
            License.get(license).set_parent(parent)


def clear_licenses():
    LocalizedLicenseName.q().delete()
    License.q().delete()
