#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import traceback

import ckan.plugins.toolkit as toolkit
from ckan.lib.munge import munge_tag
import ckanext.dcatapit.interfaces as interfaces
from ckanext.dcatapit.model.license import (
    load_from_graph as load_licenses_from_graph,
    clear_licenses)

from ckanext.dcatapit.model.subtheme import (
    load_subthemes, clear_subthemes)
from ckan.model.meta import Session

from pylons import config
from ckan.lib.cli import CkanCommand

from rdflib import Graph
from rdflib.term import URIRef
from rdflib.namespace import SKOS, DC
from ckanext.dcat.profiles import namespaces

LANGUAGE_THEME_NAME = 'languages'
EUROPEAN_THEME_NAME = 'eu_themes'
LOCATIONS_THEME_NAME = 'places'
FREQUENCIES_THEME_NAME = 'frequencies'
FILETYPE_THEME_NAME = 'filetype'
LICENSES_NAME = 'licenses'
REGIONS_NAME = 'regions'
SUBTHEME_NAME = 'subthemes'

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
          regions     -> https://github.com/italia/daf-ontologie-vocabolari-controllati/blob/master/VocabolariControllati/ClassificazioneTerritorio/Istat-Classificazione-08-Territorio.rdf?raw=true
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
        else:
            print self.usage
            log.error('ERROR: Command "%s" not recognized' % (cmd,))
            return

    def initdb(self):
        from ckanext.dcatapit.model import setup as db_setup, setup_license_models, setup_subtheme_models

        db_setup()
        setup_license_models()
        setup_subtheme_models()

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


def do_load_regions(g, vocab_name):
    concepts = []
    pref_labels = []
    for reg in g.subjects(None, URIRef('http://dati.gov.it/onto/clvapit#Region')):
        names = list(g.objects(reg, URIRef('http://dati.gov.it/onto/clvapit#name')))
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
