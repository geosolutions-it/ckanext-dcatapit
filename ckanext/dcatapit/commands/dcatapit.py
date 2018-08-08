#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import traceback
import json
import uuid
from datetime import datetime
from pprint import pprint

import ckan.plugins.toolkit as toolkit
from ckan.lib.munge import munge_tag
import ckanext.dcatapit.interfaces as interfaces
from ckanext.dcatapit.model.license import (
    load_from_graph as load_licenses_from_graph,
    clear_licenses)

from ckanext.dcatapit.model.subtheme import (
    load_subthemes, clear_subthemes)
from ckan.model.meta import Session
from ckan.model import Package, Group, GroupExtra, Tag, PackageExtra
from ckan.logic import ValidationError
from ckan.lib.navl.dictization_functions import Invalid

from sqlalchemy import and_
from ckan.lib.base import config
from ckan.lib.cli import CkanCommand

from rdflib import Graph
from rdflib.term import URIRef
from rdflib.namespace import SKOS, DC
from ckanext.dcat.profiles import namespaces
from ckanext.dcatapit import validators
from ckanext.multilang.model import PackageMultilang as ML_PM

LANGUAGE_THEME_NAME = 'languages'
EUROPEAN_THEME_NAME = 'eu_themes'
LOCATIONS_THEME_NAME = 'places'
FREQUENCIES_THEME_NAME = 'frequencies'
FILETYPE_THEME_NAME = 'filetype'
LICENSES_NAME = 'licenses'
REGIONS_NAME = 'regions'
SUBTHEME_NAME = 'subthemes'
DEFAULT_LANG = config.get('ckan.locale_default', 'en')
DATE_FORMAT = '%d-%m-%Y'

log = logging.getLogger(__name__)


class DCATAPITCommands(CkanCommand):
    '''  A command for working with vocabularies
    Usage::
     # Loading a vocabulary
     paster --plugin=ckanext-dcatapit vocabulary load --url URL --name NAME --config=PATH_TO_INI_FILE [--format=FORMAT]
     paster --plugin=ckanext-dcatapit vocabulary load --filename FILE --name NAME --config=PATH_TO_INI_FILE [--format=FORMAT]
     Where:
       URL  is the url to a SKOS document
       FILE is the local path to a SKOS document
       FORMAT is rdflib format name (xml, turtle etc)
       NAME is the short-name of the vocabulary (only allowed languages, eu_themes, places, frequencies, regions, licenses, subthemes)
       Where the corresponding rdf are:
          languages   -> http://publications.europa.eu/mdr/resource/authority/language/skos/languages-skos.rdf
          eu_themes   -> http://publications.europa.eu/mdr/resource/authority/data-theme/skos/data-theme-skos.rdf
          places      -> http://publications.europa.eu/mdr/resource/authority/place/skos/places-skos.rdf
          frequencies -> http://publications.europa.eu/mdr/resource/authority/frequency/skos/frequencies-skos.rdf
          regions     -> https://raw.githubusercontent.com/italia/daf-ontologie-vocabolari-controllati/master/VocabolariControllati/territorial-classifications/regions/regions.rdf

          filetype -> http://publications.europa.eu/mdr/resource/authority/file-type/skos/filetypes-skos.rdf
       PATH_TO_INI_FILE is the path to the Ckan configuration file

     If you use subthemes, additional argument is required, path to EUROVOC rdf file:

     paster --plugin=ckanext-dcatapit vocabulary load --filename EUROVOC_TO_THEMES_MAPPING_FILE --name subthemes --config=PATH_TO_INI_FILE  PATH_TO_EUROVOC
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__

    places_theme_regex = '^ITA_.+'

    _locales_ckan_mapping = {
        'it': 'it',
        'de': 'de',
        'en': 'en_GB',
        'fr': 'fr',
        'es': 'es'
    }

    _ckan_language_theme_mapping = {
        'it': 'ITA',
        'de': 'DEU',
        'en_GB': 'ENG',
        'fr': 'FRA',
        'es': 'SPA'
    }

    _controlled_vocabularies_allowed = (EUROPEAN_THEME_NAME,
                                        LOCATIONS_THEME_NAME,
                                        LANGUAGE_THEME_NAME,
                                        FREQUENCIES_THEME_NAME,
                                        FILETYPE_THEME_NAME,
                                        REGIONS_NAME,
                                        LICENSES_NAME,
                                        SUBTHEME_NAME)

    def __init__(self, name):
        super(DCATAPITCommands, self).__init__(name)

        self.parser.add_option('--filename', dest='filename', default=None,
                               help='Path to a file')
        self.parser.add_option('--url', dest='url', default=None,
                               help='URL to a resource')
        self.parser.add_option('--format', dest='format', default='xml',
                                help="Use specific graph format (xml, turtle..), default: xml")
        self.parser.add_option('--name', dest='name', default=None,
                               help='Name of the vocabulary to work with')

    def command(self):
        '''
        Parse command line arguments and call appropriate method.
        '''
        try:
            cmd = self.args[0]
        except IndexError:
            print "ERROR: missing command"
            print self.usage
            return
        self._load_config()

        if cmd == 'load':
            self.load()
        elif cmd == 'initdb':
            self.initdb()
        elif cmd == 'migrate_data':
            self.migrate_data()
        else:
            print self.usage
            log.error('ERROR: Command "%s" not recognized' % (cmd,))
            return

    def initdb(self):
        from ckanext.dcatapit.model import setup as db_setup, setup_license_models, setup_subtheme_models

        db_setup()
        setup_license_models()
        setup_subtheme_models()

    def migrate_data(self):
        do_migrate_data()

    def load(self):
        ##
        # Checking command given options
        ##

        url = self.options.url
        filename = self.options.filename
        format = self.options.format

        if not url and not filename:
            print "ERROR: No URL or FILENAME provided and one is required"
            print self.usage
            return

        vocab_name = self.options.name

        if not vocab_name:
            print "ERROR: No vocabulary name provided and is required"
            print self.usage
            return

        if vocab_name not in self._controlled_vocabularies_allowed:
            print "ERROR: Incorrect vocabulary name, only one of these values are allowed: {0}".format(self._controlled_vocabularies_allowed)
            print self.usage
            return
        
        if vocab_name == LICENSES_NAME:
            clear_licenses()
            load_licenses_from_graph(filename, url)
            Session.commit()
            return

        if vocab_name == SUBTHEME_NAME:
            clear_subthemes()
            theme_map = self.options.filename
            try:
                eurovoc = self.args[-1]
            except IndexError:
                print "ERROR: Missing eurovoc file"
                print self.usage
                return
            load_subthemes(theme_map, eurovoc)
            Session.commit()
            return
            
        do_load(vocab_name, url=url, filename=filename, format=format)

REGION_TYPE = 'https://w3id.org/italia/onto/CLV/Region'
NAME_TYPE = 'https://w3id.org/italia/onto/l0/name'

def do_load_regions(g, vocab_name):
    concepts = []
    pref_labels = []
    for reg in g.subjects(None, URIRef(REGION_TYPE)):
        names = list(g.objects(reg, URIRef(NAME_TYPE)))
        identifier = munge_tag(unicode(reg).split('/')[-1])

        concepts.append(identifier)
        for n in names:
            label = {'name': identifier,
                     'lang': n.language,
                     'localized_text': n.value}
            pref_labels.append(label)

    log.info('Loaded %d regions', len(concepts))
    print('Loaded %d regions' % len(concepts))
    return pref_labels, concepts


def do_load_vocab(g, vocab_name):
    concepts = []
    pref_labels = []

    for concept,_pred,_conc in g.triples((None, None, SKOS.Concept)):
        about = str(concept)
        identifier = str(g.value(subject=concept, predicate=DC.identifier))

        #
        # Skipping the ckan locales not mapped in this plugin (subject: language theme)
        #
        if vocab_name == 'languages' and identifier not in DCATAPITCommands._ckan_language_theme_mapping.values():
            continue

        #
        # Skipping the ckan places not in italy according to the regex (subject: places theme)
        #
        if vocab_name == 'places' and not re.match(DCATAPITCommands.places_theme_regex, identifier, flags=0):
            continue

        # print 'Concept {0} ({1})'.format(about, identifier)
        concepts.append(identifier)

        langs = set()

        for pref_label in g.objects(concept, SKOS.prefLabel):
            lang = pref_label.language
            label = pref_label.value

            langs.add(lang)

            # print u'    Label {0}: {1}'.format(lang, label)
            pref_labels.append({
                'name': identifier,
                'lang': lang,
                'localized_text': label
            })

        print 'Loaded concept: URI[{0}] ID[{1}] languages[{2}]'.format(about, identifier, len(langs))

    return pref_labels, concepts


def do_load(vocab_name, url=None, filename=None, format=None):

    if vocab_name == LANGUAGE_THEME_NAME:
        ckan_offered_languages = config.get('ckan.locales_offered', 'it').split(' ')
        for offered_language in ckan_offered_languages:
            if offered_language not in DCATAPITCommands._ckan_language_theme_mapping:
                print "INFO: '{0}' CKAN locale is not mapped in this plugin and will be skipped during the import stage (vocabulary name '{1}')".format(offered_language, vocab_name)

    ##
    # Loading the RDF vocabulary
    ##
    print "Loading graph for", vocab_name

    g = Graph()
    for prefix, namespace in namespaces.iteritems():
        g.bind(prefix, namespace)
    fargs = {}
    if url:
        fargs['location'] = url
    elif filename:
        fargs['source'] = filename
    if format:
        fargs['format'] = format
    try:
        g.parse(**fargs)
    except Exception,e:
        log.error("ERROR: Problem occurred while retrieving the document %r with params %s", e, fargs)
        print("ERROR: Problem occurred while retrieving the document %r with params %s", fargs)
        traceback.print_exc(e)
        return

    if vocab_name == REGIONS_NAME:
        vocab_load = do_load_regions
    else:
        vocab_load = do_load_vocab

    pref_labels, concepts = vocab_load(g, vocab_name)
    ##
    # Creating the Tag Vocabulary using the given name
    ##
    log.info('Creating tag vocabulary {0} ...'.format(vocab_name))

    user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name'], 'ignore_auth': True}

    print "Using site user '{0}'".format(user['name'])

    try:
        data = {'id': vocab_name}
        toolkit.get_action('vocabulary_show')(context, data)

        log.info("Vocabulary {0} already exists, skipping...".format(vocab_name))
    except toolkit.ObjectNotFound:
        log.info("Creating vocabulary '{0}'".format(vocab_name))

        data = {'name': vocab_name}
        vocab = toolkit.get_action('vocabulary_create')(context, data)

        for tag in concepts:
            log.info(u"Adding tag {0} to vocabulary '{1}'".format(tag, vocab_name))
            print(u"Adding tag {0} to vocabulary '{1}'".format(tag, vocab_name))
            data = {'name': tag, 'vocabulary_id': vocab['id']}
            toolkit.get_action('tag_create')(context, data)

    ##
    # Persisting Multilag Tags or updating existing
    ##
    log.info('Creating the corresponding multilang tags for vocab: {0} ...'.format(vocab_name))
    print('Creating the corresponding multilang tags for vocab: {0} ...'.format(vocab_name))

    for pref_label in pref_labels:
        if pref_label['lang'] in DCATAPITCommands._locales_ckan_mapping:
            tag_name = pref_label['name']
            tag_lang = DCATAPITCommands._locales_ckan_mapping[pref_label['lang']]
            tag_localized_name = pref_label['localized_text']

            try:
               print(u"Storing tag: name[{}] lang[{}] label[{}]".format(tag_name, tag_lang, tag_localized_name))
            except UnicodeEncodeError:
               print(u"Storing tag: name[{}] lang[{}]".format(tag_name, tag_lang))

            interfaces.persist_tag_multilang(tag_name, tag_lang, tag_localized_name, vocab_name)

    print 'Vocabulary successfully loaded ({0})'.format(vocab_name)

def do_migrate_data():

    user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name'],
               'ignore_auth': True,
               'use_cache': False}
    pshow = toolkit.get_action('package_show')
    pupdate = toolkit.get_action('package_update')
    pcreate = toolkit.get_action('package_create')
    oshow = toolkit.get_action('organization_show')
    oupdate = toolkit.get_action('organization_patch')

    for oname in get_organization_list():
        odata = oshow(context, {'id': oname, 'include_extras': True,
                                             'include_tags': True,
                                             'include_users': False,
                                             })
        
        oidentifier = odata.get('identifier')

        # we require identifier for org now.
        if not oidentifier:
            odata.pop('identifier', None)
            tmp_identifier = get_temp_org_identifier()
            print (u"org: [{}] {} : setting temporal identifier: {}".format(odata['name'],
                                                                           odata['title'],
                                                                           tmp_identifier)).encode('utf-8')
            context['allow_partial_update'] = True
            oupdate(context, {'id': odata['id'],
                              'identifier': tmp_identifier})

            out = oshow(context, {'id': oname,
                                  'include_extras': True,
                                  'include_tags': True,
                                  'include_users': True})

    for pname in get_package_list():
        pname = pname[0]
        
        pdata = pshow(context, {'name_or_id': pname}) #, 'use_default_schema': True})

        if pdata['type'] != 'dataset':
            continue

        # remove empty conforms_to to avoid silly validation errors
        if not pdata.get('conforms_to'):
            pdata.pop('conforms_to', None)
        # ... the same for alternate_identifier
        if not pdata.get('alternate_identifier'):
            pdata.pop('alternate_identifier', None)

        # tags can be multilang, but they won't pass validation
        # we can munge name to pass validation
        # better way to handle this is welcomed
        for t in pdata['tags']:
            t['name'] = munge_tag(t['name'])
        
        update_creator(pdata)
        update_temporal_coverage(pdata)
        update_theme(pdata)
        update_identifier(pdata)
        update_modified(pdata)
        update_frequency(pdata)
        update_conforms_to(pdata)
        update_holder_info(pdata)

        pdata['metadata_modified'] = None
        print 'updating', pdata['id'], pdata['name']
        try:
           out = pupdate(context, pdata)
        except ValidationError, err:
            print (u'Cannot update due to validation error {}'.format(pdata['name'])).encode('utf-8')
            print err
            print (pdata)
            print
            continue

        except Exception, err:
            print (u'Cannot update due to general error {}'.format(pdata['name'])).encode('utf-8')
            print err
            print (pdata)
            print
            continue
        print '---' * 3

def get_package_list():
    return Session.query(Package.name).filter(Package.state=='active',
                                              Package.type=='dataset')\
                                      .order_by(Package.title)


def get_organization_list():
    return Session.query(Group.name).filter(Group.state=='active',
                                            Group.type=='organization')\
                                    .order_by(Group.title)


def update_holder_info(pdata):
    if pdata.get('holder_name') and not pdata.get('holder_identifier'):
        pdata['holder_identifier'] = get_temp_holder_identifier()
        print (u'dataset {}: holder_name present: {}, but no holder_identifier in data. using generated one: {}'
               .format(pdata['name'], pdata['holder_name'],pdata['holder_identifier']))


def update_conforms_to(pdata):
    cname = pdata.pop('conforms_to', None)

    to_delete = []
    if not cname:
        for idx, ex in enumerate(pdata.get('extras') or []):
            if ex['key'] == 'conforms_to':
                to_delete.append(idx)
                cname = ex['value']
        if to_delete:
            for idx in reversed(to_delete):
                pdata['extras'].pop(idx)
    
    ml_pkg = interfaces.get_for_package(pdata['id'])
    if ml_pkg:
        try:
            ml_conforms_to = ml_pkg['conforms_to']
        except KeyError:
            ml_conforms_to = {}
    if cname:
        standard = {'identifier': None, 'description': {}}
        if not ml_conforms_to:
            standard['identifier'] = cname
        else:
            standard['identifier'] = ml_conforms_to.get('it') or ml_conforms_to.get(DEFAULT_LANG) or cname
            for lang, val in ml_conforms_to.items():
                standard['description'][lang] = val

        Session.query(ML_PM).filter(ML_PM.package_id==pdata['id'],
                                    ML_PM.field=='conforms_to').delete()
        pdata['conforms_to'] = json.dumps([standard])


def update_creator(pdata):
    cname = pdata.pop('creator_name', None)
    cident = pdata.pop('creator_identifier', None)

    to_delete = []
    if not (cname and cident):
        for idx, ex in enumerate(pdata.get('extras') or []):
            if ex['key'] == 'creator_name':
                to_delete.append(idx)
                cname = ex['value']
            elif ex['key'] == 'creator_identifier':
                to_delete.append(idx)
                cident = ex['value']
        if to_delete:
            for idx in reversed(to_delete):
                pdata['extras'].pop(idx)

    if (cname or cident):
        lang = interfaces.get_language()
        pdata['creator'] = json.dumps([{'creator_identifier': cident,
                                        'creator_name': {lang: cname}}])


DEFAULT_THEME = json.dumps([{'theme': 'OP_DATPRO', 'subthemes': []}])

def update_theme(pdata):
    theme = pdata.pop('theme', None)
    if not theme:
        to_delete = []
        for idx, ex in enumerate(pdata.get('extras') or []):
            if ex['key'] == 'theme':
                to_delete.append(idx)
                theme = ex['value']
        if to_delete:
            for idx in reversed(to_delete):
                pdata['extras'].pop(idx)
    
    # default theme if nothing available
    if not theme:
        theme = DEFAULT_THEME
    validator = toolkit.get_validator('dcatapit_subthemes')

    try:
        theme = validator(theme, {})
    except Invalid, err:
        print (u'dataset {}: cannot use theme {}: {}. Using default theme'.format(pdata['name'], theme, err)).encode('utf-8')
        theme = DEFAULT_THEME
    pdata['theme'] = theme

def update_temporal_coverage(pdata):
    tstart = pdata.pop('temporal_start', None)
    tend = pdata.pop('temporal_end', None)

    if not (tstart and tend):
        to_delete = []
        for idx, ex in enumerate(pdata.get('extras') or []):
            if ex['key'] == 'temporal_start':
                to_delete.append(idx)
                tstart = ex['value']
            if ex['key'] == 'temporal_end':
                to_delete.append(idx)
                tend = ex['value']
        if to_delete:
            for idx in reversed(to_delete):
                pdata['extras'].pop(idx)

    try:
        tstart = validators.parse_date(tstart).strftime(DATE_FORMAT)
    except Invalid:
        tstart = None
    try:
        tend = validators.parse_date(tend).strftime(DATE_FORMAT)
    except Invalid:
        tend = None
    ## handle 2010-01-01 to 2010-01-01 case, use whole year 
    # if tstart == tend and tstart.day == 1 and tstart.month == 1:
    #     tend = tend.replace(day=31, month=12)

    if (tstart):

        validator = toolkit.get_validator('dcatapit_temporal_coverage')
        if (tstart == tend):
            print (u'dataset {} has the same temporal coverage start/end: {}/{}, using start only'.format(pdata['name'], tstart,tend)).encode('utf-8')
            tend = None
        temp_cov = json.dumps([{'temporal_start': tstart,
                                'temporal_end': tend}])
        try:
            temp_cov = validator(temp_cov, {})
            pdata['temporal_coverage'] = temp_cov
        except Invalid, err:
            print (u'dataset {}: cannot use temporal coverage {}: {}'.format(pdata['name'], (tstart,tend,), err)).encode('utf-8')

def update_frequency(pdata):
    frequency = pdata.pop('frequency', None)
    if not frequency:
        to_delete = []
        for idx, ex in enumerate(pdata.get('extras') or []):
            if ex['key'] == 'frequency':
                to_delete.append(idx)
                frequency = ex['value']
        if to_delete:
            for idx in reversed(to_delete):
                pdata['extras'].pop(idx)
    
    # default frequency
    if not frequency:
        print (u'dataset {}: no frequency. Using default, UNKNOWN.'.format(pdata['name'])).encode('utf-8')
        frequency = 'UNKNOWN'
    pdata['frequency'] = frequency



def update_identifier(pdata):
    identifier = pdata.pop('identifier', None)
    if not identifier:
        to_delete = []
        for idx, ex in enumerate(pdata.get('extras') or []):
            if ex['key'] == 'identifier':
                to_delete.append(idx)
                identifier = ex['value']
        if to_delete:
            for idx in reversed(to_delete):
                pdata['extras'].pop(idx)
    
    # default theme if nothing available
    if not identifier:
        print (u'dataset {}: no identifier. generating new one'.format(pdata['name'])).encode('utf-8')
        identifier = str(uuid.uuid4())
    pdata['identifier'] = identifier

def update_modified(pdata):
    try:
        data = validators.parse_date(pdata['modified'])
    except (KeyError, Invalid,):
        val = pdata.get('modified') or None
        print (u"dataset {}: invalid modified date {}. Using now timestamp"
                .format(pdata['name'], val)).encode('utf-8')
        data = datetime.now()
    pdata['modified'] = datetime.now().strftime("%Y-%m-%d")


TEMP_IPA_CODE = 'tmp_ipa_code'
TEMP_HOLDER_CODE = 'tmp_holder_code'

def get_temp_holder_identifier():
    c = package_temp_code_count(TEMP_HOLDER_CODE)
    return '{}_{}'.format(TEMP_HOLDER_CODE, c + 1)

def get_temp_org_identifier():
    c = group_temp_code_count(TEMP_IPA_CODE)
    return '{}_{}'.format(TEMP_IPA_CODE, c + 1)


def package_temp_code_count(BASE_CODE):
    s = Session
    q = s.query(PackageExtra.value).join(Package, and_(Package.id==PackageExtra.package_id,
                                                   PackageExtra.state=='active'))\
                                 .filter(Package.type == 'organization',
                                         Package.state == 'active',
                                         PackageExtra.key == 'identifier',
                                         PackageExtra.value.startswith(BASE_CODE))\
                                 .group_by(PackageExtra.value)\
                                 .count()
    return q

def group_temp_code_count(BASE_CODE):
    s = Session
    q = s.query(GroupExtra.value).join(Group, and_(Group.id==GroupExtra.group_id,
                                                   GroupExtra.state=='active'))\
                                 .filter(Group.type == 'organization',
                                         Group.state == 'active',
                                         GroupExtra.key == 'identifier',
                                         GroupExtra.value.startswith(BASE_CODE))\
                                 .group_by(GroupExtra.value)\
                                 .count()
    return q
