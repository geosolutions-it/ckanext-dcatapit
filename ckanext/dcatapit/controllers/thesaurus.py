import logging
import os
import tempfile

from ckanext.dcatapit.commands import DataException, ConfigException
from ckanext.dcatapit.commands.vocabulary import validate_vocabulary, load
from flask import request
from flask.views import View
from werkzeug.utils import secure_filename

from ckan.common import config
from ckan.lib import base
from ckan.lib.base import abort
from ckan.model import Session
import ckan.plugins.toolkit as tk

import ckanext.dcatapit.commands.vocabulary as voc_logic

log = logging.getLogger(__name__)


def get_thesaurus_admin_page():
    return base.render(
        u'admin/thesaurus.html',
        extra_vars={}
    )


def update_vocab_admin():
    ALLOWED_EXTENSIONS = {'rdf'}
    file = None

    def is_file_allowed(filename):
        return '.' in filename and filename.rsplit('.', 1)[-1].lower() in ALLOWED_EXTENSIONS

    if 'thesaurus_file' not in request.files or not request.files['thesaurus_file']:
        return abort(400, detail='Missing thesaurus file')

    thesaurus_file = request.files['thesaurus_file']
    if not is_file_allowed(thesaurus_file.filename):
        return abort(400, detail='File type not allowed')

    # Store file
    storage_path = config.get(u'ckan.storage_path') or tempfile.gettempdir()
    filename = secure_filename(thesaurus_file.filename)
    upload_dir = os.path.join(storage_path, 'uploaded_vocabularies')
    os.makedirs(upload_dir, exist_ok=True)  # make sure the directory is there
    file_path = os.path.join(upload_dir, filename)
    log.info(f'Storing vocabulary into {file_path}')
    thesaurus_file.save(file_path)

    try:
        g, name, uri, eurovoc = validate_vocabulary(file_path, url=None, eurovoc=None)
    except DataException as e:
        return abort(400, detail=str(e))
    except ConfigException as e:
        return abort(500, detail=str(e) + tk._(' Please contact the administrator.'))
    finally:
        os.remove(file_path)

    results = load(g, name, uri, eurovoc)

    return base.render(u'admin/thesaurus_result.html',
                       extra_vars={'results': results, 'voc_name': name})


class ThesaurusController(View):

    def get(self):
        print('------------------')
        print('thesaurus')
        print('------------------')
        return base.render(
            u'admin/thesaurus.html',
            extra_vars={
                'title': tk._('Thesaurus Data Update')
            }
        )
