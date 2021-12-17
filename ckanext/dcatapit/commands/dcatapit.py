#!/usr/bin/env python3

import json
import click
import logging
import re
import traceback
import uuid
from datetime import datetime

from rdflib import Graph
from rdflib.namespace import DC, SKOS
from rdflib.term import URIRef
from sqlalchemy import and_

import ckan.plugins.toolkit as toolkit
from ckan.lib.base import config
from ckan.lib.munge import munge_tag
from ckan.lib.navl.dictization_functions import Invalid
from ckan.logic import ValidationError
from ckan.logic.validators import tag_name_validator
from ckan.model import (
    Group,
    GroupExtra,
    Package,
    PackageExtra,
    repo,
)
from ckan.model.meta import Session

from ckanext.dcat.profiles import namespaces

from ckanext.multilang.model import PackageMultilang as ML_PM

from ckanext.dcatapit import validators
import ckanext.dcatapit.interfaces as interfaces
from ckanext.dcatapit.model.license import clear_licenses
from ckanext.dcatapit.model.license import load_from_graph as load_licenses_from_graph
from ckanext.dcatapit.model.subtheme import clear_subthemes, load_subthemes

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

DEFAULT_LANG = config.get('ckan.locale_default', 'en')
DATE_FORMAT = '%d-%m-%Y'

log = logging.getLogger(__name__)


def get_commands():
    return [dcatapit]


@click.group()
def dcatapit():
    '''
    A command for working with vocabularies
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
    '''
    # self._load_config()


class DCATAPITCommands:
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
        'en': 'ENG',
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


@dcatapit.command()
def initdb():
    from ckanext.dcatapit.model import setup_db
    created = setup_db()
    if created:
        click.secho('DCATAPIT DB tables created', fg=u"green")
    else:
        click.secho('DCATAPIT DB tables not created', fg=u"yellow")


@dcatapit.command()
@click.option('-o', '--offset', default=None, type=int,
              help='Start from dataset at offset during data migration')
@click.option('-l', '--limit', default=None, type=int,
              help='Limit number of processed datasets during data migration')
@click.option('-s', '--skip-orgs', is_flag=True,
              help='Skip organizations in data migration')
def migrate_data(offset, limit, skip_orgs=False):
    do_migrate_data(limit=limit, offset=offset, skip_orgs=skip_orgs)


@dcatapit.command()
@click.option("--filename", required=False, help='Path to a file')
@click.option('--url', required=False, help='URL to a resource')
@click.option('--format', default='xml', help='Use specific graph format (xml, turtle..), default: xml')
@click.option(
    '--name', required=True,
    type=click.Choice(DCATAPITCommands._controlled_vocabularies_allowed),
    help='Name of the vocabulary to work with',
)
@click.option(
    '--eurovoc',
    required=False,
    help=f'Name of the eurovoc file. Allowed',
)
def load(filename, url, format, name, eurovoc, *args, **kwargs):
    # Checking command given options
    if not (url or not filename):
        log.error('ERROR: No URL or FILENAME provided and one is required')

    if name == LICENSES_NAME:
        clear_licenses()
        load_licenses_from_graph(filename, url)
        Session.commit()
        return

    if name == SUBTHEME_NAME:
        clear_subthemes()
        theme_map = filename
        log.debug(eurovoc)  # path to eurovoc file
        if eurovoc is None:
            log.error('ERROR: Missing eurovoc file')
        else:
            load_subthemes(theme_map, eurovoc)
            Session.commit()
        return
    do_load(name, url=url, filename=filename, format=format)


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


def do_load(vocab_name, url=None, filename=None, format=None):
    if vocab_name == LANGUAGE_THEME_NAME:
        ckan_offered_languages = config.get('ckan.locales_offered', 'it').split(' ')
        for offered_language in ckan_offered_languages:
            if offered_language not in DCATAPITCommands._ckan_language_theme_mapping:
                log.info(
                    "INFO: '%s' CKAN locale is not mapped in this plugin and will be skipped during the import stage (vocabulary name '%s')",
                    offered_language,
                    vocab_name
                )

    ##
    # Loading the RDF vocabulary
    ##
    log.debug(f'Loading graph for {vocab_name}')

    g = Graph()
    for prefix, namespace in namespaces.items():
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
    except Exception as err:
        log.error(
            'ERROR: Problem occurred while retrieving the document %r with params %s',
            err,
            fargs,
            exc_info=True
        )
        traceback.print_exc(err)
        return

    if vocab_name == REGIONS_NAME:
        vocab_load = do_load_regions
    else:
        vocab_load = do_load_vocab

    pref_labels, concepts = vocab_load(g, vocab_name)
    ##
    # Creating the Tag Vocabulary using the given name
    ##
    log.info('Creating tag vocabulary %s ...', vocab_name)

    user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name'], 'ignore_auth': True}

    log.debug("Using site user '%s'", user['name'])

    try:
        data = {'id': vocab_name}
        toolkit.get_action('vocabulary_show')(context, data)

        log.info('Vocabulary %s already exists, skipping...', vocab_name)
    except toolkit.ObjectNotFound:
        log.info("Creating vocabulary '%s'", vocab_name)

        data = {'name': vocab_name}
        vocab = toolkit.get_action('vocabulary_create')(context, data)

        for tag in concepts:
            log.info("Adding tag {0} to vocabulary '{1}'".format(tag, vocab_name))
            data = {'name': tag, 'vocabulary_id': vocab['id']}
            toolkit.get_action('tag_create')(context, data)

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

            interfaces.persist_tag_multilang(tag_name, tag_lang, tag_localized_name, vocab_name)

    log.info(f'Vocabulary successfully loaded ({vocab_name})')


def do_migrate_data(limit=None, offset=None, skip_orgs=False):
    from ckanext.dcatapit.plugin import DCATAPITPackagePlugin

    user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name'],
               'ignore_auth': True,
               'use_cache': False}
    pshow = toolkit.get_action('package_show')
    pupdate = toolkit.get_action('package_update')
    pcreate = toolkit.get_action('package_create')
    oshow = toolkit.get_action('organization_show')
    oupdate = toolkit.get_action('organization_patch')
    pupdate_schema = DCATAPITPackagePlugin().update_package_schema()
    pupdate_schema['tags']['name'].remove(tag_name_validator)
    org_list = get_organization_list()
    ocount = org_list.count()
    oidx = 0
    if not skip_orgs:
        log.info(f'processing {ocount} organizations')
        for oidx, oname in enumerate(org_list):
            odata = oshow(context, {'id': oname, 'include_extras': True,
                                    'include_tags': False,
                                    'include_users': False,
                                    })

            oidentifier = odata.get('identifier')
            log.info('processing {}/{} organization: {}'.format(oidx + 1, ocount, odata['name']))
            # we require identifier for org now.
            if not oidentifier:
                odata.pop('identifier', None)
                tmp_identifier = get_temp_org_identifier()
                log.info(
                    f"org: [{odata['name']}] {odata['title']}: "
                    f'setting temporal identifier: {tmp_identifier}'
                )
                ocontext = context.copy()

                ocontext['allow_partial_update'] = True
                # oupdate(ocontext, {'id': odata['id'],
                #                  'identifier': tmp_identifier})
                update_organization_identifier(odata['id'], tmp_identifier)
    else:
        log.info(u'Skipping organizations processing')
    pcontext = context.copy()
    pkg_list = get_package_list()
    pcount = pkg_list.count()
    log.info(f'processing {pcount} packages')
    errored = []

    if offset:
        pkg_list = pkg_list.offset(offset)
    if limit:
        pkg_list = pkg_list.limit(limit)

    # pidx may be not initialized for empty slice, need separate counter
    # to count actually processed datasets
    pidx_count = 0
    for pidx, pname in enumerate(pkg_list):
        pcontext['schema'] = pupdate_schema
        pname = pname[0]
        log.info(f'processing {pidx + 1}/{pcount} package: {pname}')
        pdata = pshow(context, {'name_or_id': pname})  # , 'use_default_schema': True})

        # remove empty conforms_to to avoid silly validation errors
        if not pdata.get('conforms_to'):
            pdata.pop('conforms_to', None)
        # ... the same for alternate_identifier
        if not pdata.get('alternate_identifier'):
            pdata.pop('alternate_identifier', None)

        update_creator(pdata)
        update_temporal_coverage(pdata)
        update_theme(pdata)
        update_identifier(pdata)
        update_modified(pdata)
        update_frequency(pdata)
        update_conforms_to(pdata)
        update_holder_info(pdata)
        interfaces.populate_resource_license(pdata)
        pdata['metadata_modified'] = None
        log.info(f"updating {pdata['id']} {pdata['name']}")
        try:
            out = pupdate(pcontext, pdata)
            pidx_count += 1
        except ValidationError as err:
            log.error(
                f"Cannot update due to validation error {pdata['name']}",
                exc_info=True
            )
            errored.append((pidx, pdata['name'], err,))
            continue

        except Exception as err:
            log.error(
                f"Cannot update due to general error {pdata['name']}",
                exc_info=True
            )
            errored.append((pidx, pdata['name'], err,))
            continue
        log.debug('-' * 9)

    if not skip_orgs:
        log.info(f'processed {oidx} out of {ocount} organizations')
    log.info(f'processed {pidx_count} out of {pcount} packages in total')
    if errored:
        log.info(f'Following {len(errored)} datasets failed:')
        for position, ptitile, err in errored:
            err_summary = getattr(err, 'error', None) or err

            # this is a hack on dumb override in __str__() in some exception subclasses
            # stringified exception raises itself otherwise.
            try:
                log.info(
                    f' {ptitile} at position {position}: {err.__class__}{err_summary}'
                )
            except Exception as err:
                err_summary = err
                log.error(
                    f' {ptitile} at position {position}: {err.__class__}{err_summary}'
                )


def get_package_list():
    return Session.query(Package.name).filter(Package.state == 'active',
                                              Package.type == 'dataset') \
        .order_by(Package.title)


def get_organization_list():
    return Session.query(Group.name).filter(Group.state == 'active',
                                            Group.type == 'organization') \
        .order_by(Group.title)


def update_holder_info(pdata):
    if pdata.get('holder_name') and not pdata.get('holder_identifier'):
        pdata['holder_identifier'] = get_temp_holder_identifier()
        log.info(
            'dataset %s: holder_name present: %s, but no holder_identifier in data. using generated one: %s',
            pdata['name'], pdata['holder_name'], pdata['holder_identifier']
        )


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
        validator = toolkit.get_validator('dcatapit_conforms_to')
        try:
            # do not update conforms_to if it's already present
            conforms_to = json.loads(cname)
            if isinstance(conforms_to, list) and len(conforms_to):
                pdata['conforms_to'] = validator(cname, {})
                return
        except (ValueError, TypeError, Invalid) as err:
            log.error(
                f"dataset {pdata['name']}: conforms_to present, but invalid: {err}",
                exec_info=True
            )

        standard = {'identifier': None, 'description': {}}
        if not ml_conforms_to:
            standard['identifier'] = cname
        else:
            standard['identifier'] = ml_conforms_to.get('it') or ml_conforms_to.get(DEFAULT_LANG) or cname
            for lang, val in ml_conforms_to.items():
                standard['description'][lang] = val

        Session.query(ML_PM).filter(ML_PM.package_id == pdata['id'],
                                    ML_PM.field == 'conforms_to').delete()
        pdata['conforms_to'] = json.dumps([standard])


def update_creator(pdata):
    if pdata.get('creator'):
        return
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
    except Invalid as err:
        log.error(
            f"dataset {pdata['name']}: cannot use theme {theme}:",
            exec_info=True
        )
        theme = DEFAULT_THEME
    pdata['theme'] = theme


def update_temporal_coverage(pdata):
    # do not process if tempcov is already present
    if pdata.get('temporal_coverage'):
        return

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
    except (Invalid, ValueError, TypeError) as err:
        if tstart is not None:
            log.error(
                f"dataset {pdata['name']}: can't use {tstart} as temporal coverage start:",
                exc_info=True
            )
        tstart = None
    try:
        tend = validators.parse_date(tend).strftime(DATE_FORMAT)
    except (Invalid, ValueError, TypeError) as err:
        if tend is not None:
            log.error(
                f"dataset {pdata['name']}: can't use {tend} as temporal coverage end:",
                exc_info=True
            )
        tend = None
    # handle 2010-01-01 to 2010-01-01 case, use whole year
    # if tstart == tend and tstart.day == 1 and tstart.month == 1:
    #     tend = tend.replace(day=31, month=12)

    if (tstart):

        validator = toolkit.get_validator('dcatapit_temporal_coverage')
        if (tstart == tend):
            log.info(
                f"dataset {pdata['name']}: "
                f'the same temporal coverage start/end: {tstart}/{tend}, '
                f'using start only',
            )
            tend = None
        temp_cov = json.dumps([{'temporal_start': tstart,
                                'temporal_end': tend}])
        try:
            temp_cov = validator(temp_cov, {})
            pdata['temporal_coverage'] = temp_cov
        except Invalid as err:
            log.error(
                f"dataset {pdata['name']}: cannot use temporal coverage {(tstart, tend)}:",
                exec_info=True
            )


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
        log.info(
            f"dataset {pdata['name']}: no frequency. Using default, UNKNOWN."
        )
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
        log.warning(
            f"dataset {pdata['name']}: no identifier. generating new one"
        )
        identifier = str(uuid.uuid4())
    pdata['identifier'] = identifier


def update_modified(pdata):
    try:
        data = validators.parse_date(pdata['modified'])
    except (KeyError, Invalid):
        val = pdata.get('modified') or None
        log.info(
            f"dataset {pdata['name']}: invalid modified date {val}. "
            f'Using now timestamp'
        )
        data = datetime.now()
    pdata['modified'] = datetime.now().strftime('%Y-%m-%d')


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
    q = s.query(PackageExtra.value).join(Package, and_(Package.id == PackageExtra.package_id,
                                                       PackageExtra.state == 'active')) \
        .filter(Package.type == 'organization',
                Package.state == 'active',
                PackageExtra.key == 'identifier',
                PackageExtra.value.startswith(BASE_CODE)) \
        .group_by(PackageExtra.value) \
        .count()
    return q


def group_temp_code_count(BASE_CODE):
    s = Session
    q = s.query(GroupExtra.value).join(Group, and_(Group.id == GroupExtra.group_id,
                                                   GroupExtra.state == 'active')) \
        .filter(Group.type == 'organization',
                Group.state == 'active',
                GroupExtra.key == 'identifier',
                GroupExtra.value.startswith(BASE_CODE)) \
        .group_by(GroupExtra.value) \
        .count()
    return q


def update_organization_identifier(org_id, org_identifier):
    s = Session
    s.revision = getattr(s, 'revision', None) or repo.new_revision()
    g = s.query(Group).filter(Group.id == org_id).one()
    g.extras['identifier'] = org_identifier
    s.add(g)
    s.flush()
