
import os
from ckanext.dcatapit.commands.dcatapit import DCATAPITCommands
from ckanext.dcatapit.model.subtheme import clear_subthemes, load_subthemes


MAPPING_FILE = 'eurovoc_mapping.rdf'
EUROVOC_FILE = 'eurovoc.rdf'

def _get_path(fname, dir_name='examples'):
    return os.path.join(os.path.dirname(__file__),
                        '..', '..', '..', dir_name, fname)
themes_loader = DCATAPITCommands('eu_themes')

def load_themes():
    vocab_file_path = _get_path('data-theme-skos.rdf', 'vocabularies')
    class Opts(object):
        def __init__(self, filename, name):
            self.filename = filename
            self.url = filename
            self.name = name

    themes_loader.options = Opts(vocab_file_path, 'eu_themes')
    themes_loader.initdb()
    themes_loader.load()

    map_f = _get_path(MAPPING_FILE)
    voc_f = _get_path(EUROVOC_FILE)
    clear_subthemes()
    load_subthemes(map_f, voc_f)
