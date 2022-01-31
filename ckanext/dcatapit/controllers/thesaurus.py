import logging
import os
import tempfile
from shutil import copy2

from ckan.common import config
from ckan.lib import base
from ckan.lib.base import abort
from ckan.model import Session
from flask.views import View
from werkzeug.utils import secure_filename
from flask import request

import ckanext.dcatapit.commands.dcatapit as dcatapit_command

log = logging.getLogger(__name__)


def get_thesaurus_admin_page():
    vocabularies_allowed = (dcatapit_command.EUROPEAN_THEME_NAME,
                            dcatapit_command.LOCATIONS_THEME_NAME,
                            dcatapit_command.LANGUAGE_THEME_NAME,
                            dcatapit_command.FREQUENCIES_THEME_NAME,
                            dcatapit_command.FILETYPE_THEME_NAME,
                            dcatapit_command.REGIONS_NAME,
                            dcatapit_command.LICENSES_NAME,
                            dcatapit_command.SUBTHEME_NAME,)
    return base.render(
        u'admin/thesaurus.html',
        extra_vars={
            'vocabularies_allowed': vocabularies_allowed,
        }
    )


def load_vocabs(file_name, name, eurovoc):
    if not file_name or not name:
        raise ValueError('Missing argument')

    if name == dcatapit_command.LICENSES_NAME:
        dcatapit_command.clear_licenses()
        dcatapit_command.load_licenses_from_graph(path=file_name)
        Session.commit()
        return 'N/A', 'N/A', 'N/A'

    if name == dcatapit_command.SUBTHEME_NAME:
        if eurovoc is None:
            raise ValueError('Missing EUROVOC file')
        dcatapit_command.clear_subthemes()
        dcatapit_command.load_subthemes(file_name, eurovoc)
        Session.commit()
        return 'N/A', 'N/A', 'N/A'

    created, updated, deleted = dcatapit_command.do_load(name, filename=file_name)
    return created, updated, deleted


def update_vocab_admin():
    ALLOWED_EXTENSIONS = {'rdf'}
    file = None

    def is_file_allowed(filename):
        return '.' in filename and filename.rsplit('.', 1)[-1].lower() in ALLOWED_EXTENSIONS

    if 'vocabulary_type' not in request.form:
        return abort(400, detail='Missing vocabulary_type')

    type = request.form['vocabulary_type']

    if 'thesaurus_file' not in request.files or not request.files['thesaurus_file']:
        return abort(400, detail='Missing thesaurus file')

    thesaurus_file = request.files['thesaurus_file']

    if not is_file_allowed(thesaurus_file.filename):
        return abort(400, detail='File type not allowed')

    eurovoc_source_path = config.get(u'ckan.dcatapit.eurovoc_location')
    if type == dcatapit_command.SUBTHEME_NAME and not eurovoc_source_path:
        return abort(500, detail=u'EuroVoc file not configured. Please contact the administrator.')

    storage_path = config.get(u'ckan.storage_path') or tempfile.gettempdir()
    filename = secure_filename(thesaurus_file.filename)
    upload_dir = os.path.join(storage_path, 'uploaded_vocabularies')
    os.makedirs(upload_dir, exist_ok=True)  # make sure the directory is there
    file_path = os.path.join(upload_dir, filename)
    log.info(f'Storing vocabulary {type} into {file_path}')
    thesaurus_file.save(file_path)
    created, updated, deleted = load_vocabs(file_name=file_path, name=type, eurovoc=eurovoc_source_path)

    return base.render(u'admin/thesaurus_result.html',
                       extra_vars={'created': created, 'updated': updated, 'deleted': deleted})


class ThesaurusController(View):

    def get(self):
        print('------------------')
        print('thesaurus')
        print('------------------')
        return base.render(
            u'admin/thesaurus.html',
            extra_vars={
                'title': u'Thesaurus Data Update'
            }
        )
