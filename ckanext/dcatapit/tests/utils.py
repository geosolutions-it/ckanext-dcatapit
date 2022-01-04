
import os

from ckan.model import meta, Tag, Vocabulary
from ckanext.dcatapit import interfaces
from ckanext.dcatapit.commands.dcatapit import DCATAPITCommands, do_load
from ckanext.dcatapit.model.subtheme import (
    Subtheme,
    clear_subthemes,
    load_subthemes,
)

Session = meta.Session

SKOS_THEME_FILE = 'data-theme-skos.rdf'
MAPPING_FILE = 'theme-subtheme-mapping.rdf'
EUROVOC_FILE = 'eurovoc_filtered.rdf'


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
    # load_subthemes(filename, 'eu_themes')
    do_load(
        vocab_name='eu_themes',
        url=None,
        filename=filename,
        format='xml'
    )
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
