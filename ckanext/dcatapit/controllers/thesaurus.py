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
    vocabularies_allowed = [dcatapit_command.EUROPEAN_THEME_NAME, dcatapit_command.LOCATIONS_THEME_NAME,
                            dcatapit_command.LANGUAGE_THEME_NAME, dcatapit_command.FREQUENCIES_THEME_NAME,
                            dcatapit_command.FILETYPE_THEME_NAME, dcatapit_command.REGIONS_NAME,
                            dcatapit_command.LICENSES_NAME, dcatapit_command.SUBTHEME_NAME]
    return base.render(
        u'admin/thesaurus.html',
        extra_vars={
            'vocabularies_allowed': vocabularies_allowed,
        }
    )


def load_vocabs(file_name, name, eurovoc):
    if not file_name:
        log.error('ERROR: No FILENAME provided and one is required')

    if name == dcatapit_command.LICENSES_NAME:
        dcatapit_command.clear_licenses()
        dcatapit_command.load_licenses_from_graph(file_name, None)
        Session.commit()
        return 'N/A', 'N/A', 'N/A'

    if name == dcatapit_command.SUBTHEME_NAME:
        dcatapit_command.clear_subthemes()
        theme_map = file_name
        if eurovoc is None:
            log.error('ERROR: Missing eurovoc file')
        dcatapit_command.load_subthemes(theme_map, eurovoc)
        Session.commit()
        return 'N/A', 'N/A', 'N/A'

    created, updated, deleted = dcatapit_command.do_load(name, filename=file_name)
    return created, updated, deleted


def update_vocab_admin():
    ALLOWED_EXTENSIONS = {'rdf'}
    type = None
    file = None

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    if 'vocabulary_type' in request.form:
        type = request.form['vocabulary_type']

    if 'thesaurus_file' in request.files:
        thesaurus_file = request.files['thesaurus_file']
        if thesaurus_file and allowed_file(thesaurus_file.filename):
            storage_path = config.get(u'ckan.storage_path') or tempfile.gettempdir()
            eurovoc_source_path = config.get(u'ckan.dcatapit.eurovoc_location')
            print(eurovoc_source_path)
            filename = secure_filename(thesaurus_file.filename)
            thesaurus_file.save(os.path.join(storage_path, filename))
            print(os.path.join(storage_path, filename))
            filepath = os.path.join(storage_path, filename)
            eurovocpath = os.path.join(storage_path, 'eurovoc.rdf')
            copy2(eurovoc_source_path, eurovocpath)
            print(filepath, type, eurovocpath)
            created, updated, deleted = load_vocabs(file_name=filepath, name=type, eurovoc=eurovocpath)
            return base.render(u'admin/thesaurus_result.html',
                               extra_vars={'created': created, 'updated': updated, 'deleted': deleted})
    else:
        return abort(500, detail=u'File not found')

    return abort(500, detail=u'File not found')


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
