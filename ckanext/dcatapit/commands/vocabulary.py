import logging
import re

from rdflib import Graph, Namespace
from rdflib.namespace import DC, SKOS, RDF, RDFS, OWL
from rdflib.term import URIRef

from sqlalchemy.exc import IntegrityError

from ckan.lib.base import config
from ckan.lib.munge import munge_tag
from ckan.model.meta import Session
import ckan.plugins.toolkit as toolkit

from ckanext.dcat.profiles import DCT
from ckanext.dcat.profiles import namespaces as dcat_namespaces

from ckanext.dcatapit import interfaces
from ckanext.dcatapit.model import DCATAPITTagVocabulary, License, ThemeToSubtheme, Subtheme, SubthemeLabel
from ckanext.dcatapit.model.license import clear_licenses
from ckanext.dcatapit.model.subtheme import clear_subthemes

CLVAPIT = Namespace('https://w3id.org/italia/onto/CLV/')
DCATAPIT = Namespace('http://dati.gov.it/onto/dcatapit#')
XKOS = Namespace('http://rdf-vocabulary.ddialliance.org/xkos#')

namespaces = dcat_namespaces.copy()
namespaces.update( {
    'clvapit': CLVAPIT,
    'dcatapit': DCATAPIT,
    'rdf': RDF,
    'rdfs': RDFS,
    'xkos': XKOS,
})


REGION_TYPE = 'https://w3id.org/italia/onto/CLV/Region'
NAME_TYPE = 'https://w3id.org/italia/onto/l0/name'

LANGUAGE_THEME_NAME = 'languages'
EUROPEAN_THEME_NAME = 'eu_themes'
LOCATIONS_THEME_NAME = 'places'
FREQUENCIES_THEME_NAME = 'frequencies'
FILETYPE_THEME_NAME = 'filetype'
LICENSES_NAME = 'licenses'
REGIONS_NAME = 'regions'
SUBTHEME_NAME = 'subthemes'
EUROVOC_NAME = 'eurovoc'

VOC_URI = {
    EUROPEAN_THEME_NAME: 'http://publications.europa.eu/resource/authority/data-theme',
    LOCATIONS_THEME_NAME: 'http://publications.europa.eu/resource/authority/place',
    LANGUAGE_THEME_NAME: 'http://publications.europa.eu/resource/authority/language',
    FREQUENCIES_THEME_NAME: 'http://publications.europa.eu/resource/authority/frequency',
    FILETYPE_THEME_NAME: 'http://publications.europa.eu/resource/authority/file-type',
    REGIONS_NAME: 'https://w3id.org/italia/controlled-vocabulary/territorial-classifications/regions',
    LICENSES_NAME: 'https://w3id.org/italia/controlled-vocabulary/licences',
    SUBTHEME_NAME: 'https://w3id.org/italia/controlled-vocabulary/theme-subtheme-mapping',
    EUROVOC_NAME: "http://eurovoc.europa.eu/100141",
}

DEFAULT_LANG = config.get('ckan.locale_default', 'en')
DATE_FORMAT = '%d-%m-%Y'

log = logging.getLogger(__name__)


class DCATAPITCommands:
    places_theme_regex = '^ITA_.+'

    _locales_ckan_mapping = {
        'it': 'it',
        'de': 'de',
        'en': 'en',
        'fr': 'fr',
        'es': 'es'
    }

    _ckan_language_theme_mapping = {
        'it': 'ITA',
        'de': 'DEU',
        'en_GB': 'ENG',
        'en': 'ENG',
        'fr': 'FRA',
        'es': 'SPA'
    }


def load(filename=None, url=None, format='xml', eurovoc=None, *args, **kwargs):
    # Checking command options
    if (not filename and not url) or (filename and url):
        log.error('ERROR: either URL or FILENAME is required')
        return -1

    g = _get_graph(path=filename, url=url)

    name, uri = detect_rdf_concept_scheme(g)
    log.info(f'Detected vocabulary {name}')

    if name == LICENSES_NAME:
        clear_licenses()
        load_licenses(g)
        Session.commit()
        return

    if name == SUBTHEME_NAME:
        clear_subthemes()
        log.debug(eurovoc)  # path to eurovoc file
        if eurovoc is None:
            log.error('ERROR: Missing eurovoc file')
        else:
            load_subthemes(filename, eurovoc)
            Session.commit()
        return

    created, updated, deleted = do_load(name, g)
    return created, updated, deleted


def do_load_regions(g, vocab_name):
    concepts = []
    pref_labels = []
    for reg in g.subjects(None, URIRef(REGION_TYPE)):
        names = list(g.objects(reg, URIRef(NAME_TYPE)))
        identifier = munge_tag(reg.split('/')[-1])

        concepts.append(identifier)
        for n in names:
            label = {'name': identifier,
                     'lang': n.language,
                     'localized_text': n.value}
            pref_labels.append(label)

    log.info('Loaded %d regions', len(concepts))
    return pref_labels, concepts


def do_load_vocab(g, vocab_name):
    concepts = []
    pref_labels = []

    for concept, _pred, _conc in g.triples((None, None, SKOS.Concept)):
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

        concepts.append(identifier)

        langs = set()

        for pref_label in g.objects(concept, SKOS.prefLabel):
            lang = pref_label.language
            label = pref_label.value

            langs.add(lang)

            log.debug(f'Concept {about} ({identifier}).  {lang}:{label}')
            pref_labels.append({
                'name': identifier,
                'lang': lang,
                'localized_text': label
            })
        log.info(
            f'Loaded concept: URI[{about}] ID[{identifier}] languages[{len(langs)}]'
        )
    return pref_labels, concepts


def do_load(vocab_name, g):
    if vocab_name == LANGUAGE_THEME_NAME:
        ckan_offered_languages = config.get('ckan.locales_offered', 'it').split(' ')
        for offered_language in ckan_offered_languages:
            if offered_language not in DCATAPITCommands._ckan_language_theme_mapping:
                log.info(
                    f"'{offered_language}' CKAN locale is not mapped in this plugin "
                    f"and will be skipped during the import stage (vocabulary '{vocab_name}')")

    ##
    # Loading the RDF vocabulary
    ##
    log.debug(f'Loading graph for {vocab_name}')

    if vocab_name == REGIONS_NAME:
        vocab_load = do_load_regions
    else:
        vocab_load = do_load_vocab

    ids = []
    created_count = 0
    updated = 0
    deleted_count = 0
    pref_labels, concepts = vocab_load(g, vocab_name)
    ##
    # Creating the Tag Vocabulary using the given name
    ##
    log.info('Creating tag vocabulary %s ...', vocab_name)

    user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name'], 'ignore_auth': True}

    log.debug("Using site user '%s'", user['name'])

    try:
        toolkit.get_action('vocabulary_show')(context, {'id': vocab_name})

        log.info('Vocabulary %s already exists, skipping...', vocab_name)
    except toolkit.ObjectNotFound:
        log.info("Creating vocabulary '%s'", vocab_name)

        vocab = toolkit.get_action('vocabulary_create')(context, {'name': vocab_name})

        for tag in concepts:
            if len(tag) > 1:
                log.info(f"Adding tag {tag} to vocabulary '{vocab_name}'")
                data = {'name': tag, 'vocabulary_id': vocab['id']}
                toolkit.get_action('tag_create')(context, data)
            else:
                log.error(f"Tag too short: skipping tag '{tag}' for vocabulary '{vocab_name}'")

    ##
    # Persisting Multilag Tags or updating existing
    ##
    log.info('Creating the corresponding multilang tags for vocab: {0} ...'.format(vocab_name))

    for pref_label in pref_labels:
        if pref_label['lang'] in DCATAPITCommands._locales_ckan_mapping:
            tag_name = pref_label['name']
            tag_lang = DCATAPITCommands._locales_ckan_mapping[pref_label['lang']]
            tag_localized_name = pref_label['localized_text']

            try:
                log.info('Storing tag: name[%s] lang[%s] label[%s]', tag_name,
                         tag_lang, tag_localized_name)
            except UnicodeEncodeError:
                log.error(f'Storing tag: name[{tag_name}] lang[{tag_lang}]')

            created, id = interfaces.persist_tag_multilang(tag_name, tag_lang, tag_localized_name, vocab_name)
            if created:
                created_count += 1
            else:
                updated += 1
            ids.append(id)

            tags = DCATAPITTagVocabulary.nin_tags_ids(ids)
            deleted_count = len(tags)
            for tag in tags:
                tag.delete()
    log.info(f'Vocabulary successfully loaded ({vocab_name})')

    return created_count, updated, deleted_count


def _get_graph(path=None, url=None):
    if (not path and not url) or (path and url):
        raise ValueError('You should provide either path or url')
    g = Graph()
    for prefix, namespace in namespaces.items():
        g.bind(prefix, namespace)

    if url:
        g.parse(location=url)
    else:
        g.parse(source=path)

    return g


def detect_rdf_concept_scheme(g: Graph) -> (str, str):
    try:
        cs = next(g.subjects(RDF.type, SKOS.ConceptScheme))
    except StopIteration:
        raise ValueError("No ConceptScheme found")

    try:
        return next(iter([(k, VOC_URI[k]) for k in VOC_URI if VOC_URI[k] == str(cs)]))
    except StopIteration:
        raise ValueError(f"ConceptScheme not handled {str(cs)}")


def load_licenses(g: Graph):
    """
    Loads license tree into db from provided graph
    """
    License.delete_all()

    for license in g.subjects(None, SKOS.Concept):
        rank_order = g.value(license, CLVAPIT.hasRankOrder)
        version = g.value(license, OWL.versionInfo)
        doc_uri = g.value(license, DCATAPIT.referenceDoc)

        # exactMatch exists only in 2nd level
        license_type = g.value(license, SKOS.exactMatch)
        if not license_type:
            # 3rd level, need to go up
            parent = g.value(license, SKOS.broader)
            license_type = g.value(parent, SKOS.exactMatch)

        _labels = g.objects(license, SKOS.prefLabel)
        labels = dict([(l.language, l) for l in _labels])
        license_path = str(license).split('/')[-1].split('_')[0]
        log.debug('Adding license [%r] [%s]', license, labels.get('it', None))
        l = License.from_data(license_type or '',
                              str(version) if version else None,
                              uri=str(license),
                              path=license_path,
                              document_uri=str(doc_uri) if doc_uri else None,
                              rank_order=int(str(rank_order)),
                              names=labels,
                              parent=None)  # parent will be set later

    for license in g.subjects(None, SKOS.Concept):
        parents = list(g.objects(license, SKOS.broader))
        if parents:
            parent = parents[0]
            License.get(license).set_parent(parent)


def load_subthemes(themes, eurovoc):
    themes_g = Graph()
    eurovoc_g = Graph()

    ThemeToSubtheme.vocab_id = None  # reset vocabulary attached to mapping
    themes_g.parse(themes)
    eurovoc_g.parse(eurovoc)

    for theme in themes_g.subjects(RDF.type, SKOS.Concept):
        sub_themes = themes_g.objects(theme, SKOS.narrowMatch)
        for sub_theme in sub_themes:
            add_subtheme(eurovoc_g, theme, sub_theme)


def add_subtheme(eurovoc, theme_ref, subtheme_ref, parent=None):

    def info(theme, inst):
        return f"T:{theme} id:{inst.id:4} dpth:{inst.depth} par:{inst.parent_id} P:{inst.path}"

    theme = Subtheme.normalize_theme(theme_ref)
    existing = Subtheme.q().filter_by(uri=str(subtheme_ref)).first()
    theme_tag = ThemeToSubtheme.get_tag(theme)

    # several themes may refer to this subtheme, so we'll just return
    # exising instance
    if existing:
        if not theme_tag in existing.themes:
            existing.themes.append(theme_tag)
        Subtheme.Session.flush()
        log.error(f'Subtheme {subtheme_ref} already exists - {info(theme, existing)}. Skipping')
        return existing

    labels = {}
    for pref_label in eurovoc.objects(subtheme_ref, SKOS.prefLabel):
        labels[pref_label.language] = str(pref_label)
    if not labels:
        log.error(f'No labels found in EUROVOC for subtheme {subtheme_ref}. Skipping')
        return
    version = eurovoc.value(subtheme_ref, OWL.versionInfo) or ''
    identifier = eurovoc.value(subtheme_ref, DCT.identifier) or ''
    default_label = labels[DEFAULT_LANG]
    inst = Subtheme(version=str(version),
               identifier=str(identifier),
               uri=str(subtheme_ref),
               default_label=default_label,
               parent_id=parent.id if parent else None,
               depth=parent.depth + 1 if parent else 0)
    inst.update_path()

    inst.add()
    Subtheme.Session.flush()

    log.info(f"Added sub {info(theme, inst)}")

    if parent is None:
        inst.parent_id = inst.id

    theme_m = ThemeToSubtheme(tag_id=theme_tag.id, subtheme_id=inst.id)
    theme_m.add()

    for lang, label in labels.items():
        l = SubthemeLabel(subtheme_id=inst.id,
                          lang=lang,
                          label=label)
        l.add()
    Subtheme.Session.flush()
    # handle children

    # make sure that we have all the intermediate items from the subtheme upto the main theme
    for child in eurovoc.objects(subtheme_ref, SKOS.hasTopConcept):
        try:
            add_subtheme(eurovoc, theme_ref, child, inst)
        except IntegrityError as e:
            # same parent may have already been added
            log.error(f'Not adding subtheme parent "{child}" for "{theme_ref}" and sub "{subtheme_ref}"')

    return inst
