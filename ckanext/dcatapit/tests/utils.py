
import os
from rdflib import Graph

from ckan.model import meta, Tag, Vocabulary
from ckanext.dcatapit import interfaces
from ckanext.dcatapit.commands.vocabulary import do_load, load_subthemes
from ckanext.dcatapit.model.subtheme import (
    Subtheme,
    clear_subthemes,
)

Session = meta.Session

SKOS_THEME_FILE = 'data-theme-skos.rdf'
MAPPING_FILE = 'theme-subtheme-mapping.rdf'
EUROVOC_FILE = 'eurovoc_filtered.rdf'
LICENSES_FILE = 'licences.rdf'


def _get_base_file(fname, dir_name):
    return os.path.join(os.path.dirname(__file__),
                        '..', '..', '..', dir_name, fname)


def get_example_file(fname):
    return _get_base_file(fname, 'examples')


def get_voc_file(fname):
    return _get_base_file(fname, 'vocabularies')


def get_test_file(fname):
    return os.path.join(os.path.dirname(__file__), 'files', fname)


def load_themes():
    filename = get_test_file(SKOS_THEME_FILE)
    g = load_graph(path=filename)
    do_load(g, 'eu_themes')

    tag_localized = interfaces.get_localized_tag_name('ECON')
    Session.flush()
    assert tag_localized
    q = Session.query(Vocabulary).filter_by(name='eu_themes')
    vocab = q.first()
    assert vocab

    map_f = get_voc_file(MAPPING_FILE)
    voc_f = get_test_file(EUROVOC_FILE)
    clear_subthemes()
    load_subthemes(map_f, voc_f)
    assert Subtheme.q().first()


def load_graph(path=None, url=None):
    if (not path and not url) or (path and url):
        raise ValueError('You should provide either path or url')

    from ckanext.dcat.profiles import namespaces

    g = Graph()
    for prefix, namespace in namespaces.items():
        g.bind(prefix, namespace)

    if url:
        g.parse(location=url)
    else:
        g.parse(source=path)

    return g
