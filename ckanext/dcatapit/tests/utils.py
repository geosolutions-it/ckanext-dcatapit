
import os
from ckanext.dcatapit import interfaces
from ckanext.dcatapit.commands.dcatapit import DCATAPITCommands
from ckanext.dcatapit.model.subtheme import clear_subthemes, load_subthemes, Subtheme

from ckan.model import Session, Tag, Vocabulary

MAPPING_FILE = 'eurovoc_mapping.rdf'
EUROVOC_FILE = 'eurovoc.rdf'

def _get_path(fname, dir_name='examples'):
    return os.path.join(os.path.dirname(__file__),
                        '..', '..', '..', dir_name, fname)
themes_loader = DCATAPITCommands('eu_themes')

def load_themes():
    vocab_file_path = _get_path('data-theme-skos.rdf', 'vocabularies')

    class Opts(object):
        def __init__(self, filename, name, format):
            self.filename = filename
            self.url = None #filename
            self.name = name
            self.format = format
    

    themes_loader.options = Opts(vocab_file_path, 'eu_themes', None)
    themes_loader.load()
    
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
