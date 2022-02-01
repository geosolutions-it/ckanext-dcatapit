import logging
import re

from rdflib import Graph, Namespace
from rdflib.namespace import DC, SKOS, RDF, RDFS, OWL
from rdflib.term import URIRef

from sqlalchemy.exc import IntegrityError

from ckan.lib.base import config, model
from ckan.lib.munge import munge_tag
from ckan.model import Vocabulary
from ckan.model.meta import Session
import ckan.plugins.toolkit as toolkit

from ckanext.dcat.profiles import DCT
from ckanext.dcat.profiles import namespaces as dcat_namespaces

from ckanext.dcatapit import interfaces
from ckanext.dcatapit.commands import DataException, ConfigException
from ckanext.dcatapit.interfaces import DBAction
from ckanext.dcatapit.model import License, ThemeToSubtheme, Subtheme, SubthemeLabel
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

LANG_MAPPING_SKOS_TO_CKAN = {
    'it': 'it',
    'de': 'de',
    'en': 'en',
    'fr': 'fr',
    'es': 'es'
}

LANGUAGE_IMPORT_FILTER = {
    'it': 'ITA',
    'de': 'DEU',
    'en_GB': 'ENG',
    'en': 'ENG',
    'fr': 'FRA',
    'es': 'SPA'
}

PLACES_IMPORT_FILTER = '^ITA_.+'


def load_from_file(filename=None, url=None, eurovoc=None, *args, **kwargs):
    try:
        g, name, uri, eurovoc = validate_vocabulary(filename, url, eurovoc)
    except ValueError as e:
        log.error(f'Error in handling vocabulary: {e}')
        return -1

    results = load(g, name, uri, eurovoc)

    log.info(f'Results: {results}' )


def load(g, name, uri, eurovoc):

    if name == LICENSES_NAME:
        ret = {'licenses_deleted': License.count()}
        clear_licenses()
        load_licenses(g)
        ret['licenses_created'] = License.count()
        Session.commit()
        return ret

    if name == SUBTHEME_NAME:
        ret = {'subthemes_deleted': Subtheme.count()}
        clear_subthemes()
        load_subthemes(None, eurovoc, themes_g=g)
        ret['subthemes_created'] = Subtheme.count()
        Session.commit()
        return ret

    return do_load(g, name)


def do_load(g, vocab_name: str):
    def _update_label_counter(cnt, action):
        action_mapping = {
            DBAction.CREATED: 'label_added',
            DBAction.UPDATED: 'label_updated',
            DBAction.NONE: 'label_exists',
            DBAction.ERROR: 'label_skipped',
        }

        try:
            action_mapped = action_mapping[action]
            cnt.incr(action_mapped)
        except KeyError:
            log.error(f'Unknown action {action}')

    if vocab_name == LANGUAGE_THEME_NAME:
        for offered_language in config.get('ckan.locales_offered', 'it').split(' '):
            if offered_language not in LANGUAGE_IMPORT_FILTER:
                log.info(
                    f"'{offered_language}' language is fitlered out in this plugin "
                    f"and will be skipped during the import stage (vocabulary '{vocab_name}')")

    # Loading the RDF vocabulary
    log.debug(f'Loading graph for {vocab_name}')

    if vocab_name == REGIONS_NAME:
        vocab_load = do_load_regions
    else:
        vocab_load = do_load_vocab

    ids = []
    cnt = Counter()

    concepts = vocab_load(g, vocab_name)

    user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name'], 'ignore_auth': True}

    log.debug("Using site user '%s'", user['name'])

    vocab = Vocabulary.get(vocab_name)
    if vocab:
        log.info(f'Vocabulary "{vocab_name}" already exists, skipping...')
    else:
        log.info(f'Creating vocabulary "{vocab_name}"')
        vocab = Vocabulary(vocab_name)
        vocab.save()

    for concept in concepts:
        tag_name = concept['name']
        if len(tag_name) < 2:
            log.error(f"Tag too short: skipping tag '{tag_name}' for vocabulary '{vocab_name}'")
            cnt.incr('tag_skipped')
            continue

        tag = model.Tag.by_name(tag_name, vocab)
        if tag is None:
            log.info(f"Adding tag {vocab_name}::{tag_name}")
            tag = model.Tag(name=tag_name, vocabulary_id=vocab.id)
            tag.save()
            cnt.incr('tag_added')
        else:
            cnt.incr('tag_exists')

        log.debug(f'Creating multilang labels for tag {vocab_name}:{tag_name}')

        for pref_label in concept['labels']:
            if pref_label['lang'] not in LANG_MAPPING_SKOS_TO_CKAN:
                cnt.incr('label_skipped')
                continue
            tag_lang = LANG_MAPPING_SKOS_TO_CKAN[pref_label['lang']]
            tag_text = pref_label['text']

            try:
                log.debug('Storing tag: name[%s] lang[%s] label[%s]', tag_name, tag_lang, tag_text)
            except UnicodeEncodeError:
                log.error(f'Storing tag: name[{tag_name}] lang[{tag_lang}]')

            action, tl_id = interfaces.persist_tag_multilang(tag, tag_lang, tag_text, vocab)

            _update_label_counter(cnt, action)

        ids.append(tag.id)

    # delete from DB old tags not found in input graph
    tag_not_in_voc = model.Session.query(model.Tag)\
        .filter(model.Tag.id.notin_(ids))\
        .filter(model.Tag.vocabulary_id==vocab.id)\
        .all()
    for tag_to_delete in tag_not_in_voc:
        pkg_cnt = len(tag_to_delete.packages)
        if pkg_cnt == 0:
            tag_to_delete.delete()
            Session.commit()
            log.info(f"Deleting tag {tag_to_delete} from vocabulary '{vocab_name}'")
            cnt.incr('tag_deleted')
        else:
            log.info(f"Cannot delete tag {tag_to_delete} from vocabulary '{vocab_name}' used in {pkg_cnt} packages")
            cnt.incr('tag_notdeletable')

    log.info(f'Vocabulary successfully loaded ({vocab_name})')

    return cnt.get()


def do_load_regions(g, vocab_name):
    concepts = []

    for reg in g.subjects(None, URIRef(REGION_TYPE)):
        names = list(g.objects(reg, URIRef(NAME_TYPE)))
        identifier = munge_tag(reg.split('/')[-1])

        labels = [{'lang': n.language, 'text': n.value} for n in names]

        concepts.append({
            'name': identifier,
            'labels': labels
        })

    log.info(f'Loaded {len(concepts)} regions')
    return concepts


def do_load_vocab(g, vocab_name):
    '''
    :param g: The vocabulary Graph
    :param vocab_name: The Vocabulary name
    :return: a list [ {'name': TAG_NAME, 'labels': [{'lang': LANG, 'text': LABEL}, ...]}]
    '''

    concepts = []

    for concept, _pred, _conc in g.triples((None, None, SKOS.Concept)):
        identifier = str(g.value(subject=concept, predicate=DC.identifier))

        # Filtering the ckan locales not mapped in this plugin (subject: language theme)
        if vocab_name == LANGUAGE_THEME_NAME and identifier not in LANGUAGE_IMPORT_FILTER.values():
            continue

        # Filtering the ckan places not in italy according to the regex (subject: places theme)
        if vocab_name == LOCATIONS_THEME_NAME and not re.match(PLACES_IMPORT_FILTER, identifier, flags=0):
            continue

        labels = [{'lang':pl.language, 'text': pl.value} for pl in g.objects(concept, SKOS.prefLabel) if pl.language]

        concepts.append({
            'name': identifier,
            'labels': labels
        })

        log.debug(f'Loaded concept: URI[{str(concept)}] ID[{identifier}] languages[{len(labels)}]')

    return concepts


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


def load_subthemes(t2sub_mapping, eurovoc, themes_g=None):
    if themes_g is None:
        themes_g = Graph()
        themes_g.parse(t2sub_mapping)

    eurovoc_g = Graph()
    eurovoc_g.parse(eurovoc)

    ThemeToSubtheme.vocab_id = None  # reset vocabulary attached to mapping

    for theme in themes_g.subjects(RDF.type, SKOS.Concept):
        sub_themes = themes_g.objects(theme, SKOS.narrowMatch)
        for sub_theme in sub_themes:
            add_subtheme(eurovoc_g, theme, sub_theme)


def add_subtheme(eurovoc, theme_ref, subtheme_ref, parent=None):

    def info(theme, inst):
        return f"T:{theme} id:{inst.id:4} dpth:{inst.depth} par:{inst.parent_id or '':5} P:{inst.path}"

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


def validate_vocabulary(filename=None, url=None, eurovoc=None):
    # Checking command options
    if (not filename and not url) or (filename and url):
        raise DataException('Either URL or FILENAME is required')

    try:
        g = _get_graph(path=filename, url=url)
    except Exception as e:
        raise DataException(f'Could not parse vocabulary file: {e}')

    name, uri = _detect_rdf_concept_scheme(g)
    log.info(f'Detected vocabulary "{name}"')

    if name == SUBTHEME_NAME:
        if not eurovoc:
            eurovoc_config_item = 'ckan.dcatapit.eurovoc_location'
            eurovoc_source_path = config.get(eurovoc_config_item)
            if not eurovoc_source_path:
                raise ConfigException(f'EUROVOC file not configured at {eurovoc_config_item}.')
            else:
                log.info(f'Using configured EUROVOC file at "{eurovoc_source_path}"')
                eurovoc = eurovoc_source_path
        else:
            log.info(f'Using provided EUROVOC file at "{eurovoc}"')

    return g, name, uri, eurovoc


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


def _detect_rdf_concept_scheme(g: Graph) -> (str, str):
    try:
        cs = next(g.subjects(RDF.type, SKOS.ConceptScheme))
    except StopIteration:
        raise DataException("No ConceptScheme found")

    for k in VOC_URI:
        uriref = URIRef(VOC_URI[k])
        try:
            found = next(g.triples((uriref, RDF.type, SKOS.ConceptScheme)))
        except StopIteration:
            continue
        if found:
            return k, VOC_URI[k]

    raise DataException(f"ConceptScheme not handled {str(cs)}")


class Counter:
    def __init__(self):
        self.d = {}

    def incr(self, name):
        self.d[name] = self.d.get(name, 0) + 1

    def get(self):
        return self.d