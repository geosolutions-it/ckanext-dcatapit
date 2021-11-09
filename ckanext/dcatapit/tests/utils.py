
import os

from ckan.model import Session, Tag, Vocabulary
from ckanext.dcatapit import interfaces
from ckanext.dcatapit.commands.dcatapit import DCATAPITCommands, do_load
from ckanext.dcatapit.model.subtheme import (
    Subtheme,
    clear_subthemes,
    load_subthemes,
)

MAPPING_FILE = 'eurovoc_mapping.rdf'
EUROVOC_FILE = 'eurovoc.rdf'


def _get_path(fname, dir_name='examples'):
    return os.path.join(os.path.dirname(__file__),
                        '..', '..', '..', dir_name, fname)

def load_themes():
    filename = _get_path('data-theme-skos.rdf', 'vocabularies')
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

    map_f = _get_path(MAPPING_FILE)
    voc_f = _get_path(EUROVOC_FILE)
    clear_subthemes()
    load_subthemes(map_f, voc_f)
    assert Subtheme.q().first()
