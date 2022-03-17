#!/usr/bin/env python3
import click
import logging

import ckanext.dcatapit.commands.migrate110 as migrate110
import ckanext.dcatapit.commands.migrate200 as migrate200
from ckanext.dcatapit.commands.vocabulary import load_from_file as load_voc

log = logging.getLogger(__name__)


def get_commands():
    return [dcatapit]


@click.group()
def dcatapit():
    # self._load_config()
    pass


@dcatapit.command()
def initdb():
    from ckanext.dcatapit.model import setup_db
    created = setup_db()
    if created:
        click.secho('DCATAPIT DB tables created', fg=u"green")
    else:
        click.secho('DCATAPIT DB tables not created', fg=u"yellow")


@dcatapit.command(help='Migrate from 1.0.0 version to 1.1.0 (many elements 0..1 now are 0..N)')
@click.option('-o', '--offset', default=None, type=int,
              help='Start from dataset at offset during data migration')
@click.option('-l', '--limit', default=None, type=int,
              help='Limit number of processed datasets during data migration')
@click.option('-s', '--skip-orgs', is_flag=True,
              help='Skip organizations in data migration')
def migrate_110(offset, limit, skip_orgs=False):
    migrate110.do_migrate_data(limit=limit, offset=offset, skip_orgs=skip_orgs)


@dcatapit.command(help='Migrate to 2.0.0 (themes are encoded in a different named field)')
@click.option('-f', '--fix-old', is_flag=True, default=False,
              help='Try and fix datasets in older 1.0.0 format')
def migrate_200(fix_old):
    migrate200.migrate(fix_old)


@dcatapit.command(help='Load an RDF vocabulary into the DB')
@click.option('-f', "--filename", required=False, help='Path to a file', type=str)
@click.option('--url', required=False, help='URL to a resource')
@click.option('--format', default='xml', help='Use specific graph format (xml, turtle..), default: xml')
@click.option('--eurovoc', required=False, help=f'Name of the eurovoc file. Only needed for the subtheme mapping')
@click.option('--name', required=False, help=f'Retained for backward compatibility')
def load(filename, url, format, eurovoc, name):
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
    if name:
        log.warning(f'Option "name" is deprecated and unused.')

    load_voc(filename, url, eurovoc, format=format)
