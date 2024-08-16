
import logging
import urllib

import ckan.logic as logic
import ckan.model as model
from ckan.common import c, request
from ckan.views.api import _finish
from flask.views import MethodView
from flask import Blueprint

log = logging.getLogger(__file__)

# shortcuts
get_action = logic.get_action

dcatapit_blp = Blueprint('apicontroller', __name__)


@dcatapit_blp.route("/apicontroller", methods=['GET'])
def get():
    q = request.args.get('incomplete', '')
    q = urllib.parse.unquote(q)

    vocab = request.args.get('vocabulary_id', None)

    vocab = str(vocab)

    log.debug('Looking for Vocab %r', vocab)

    limit = request.args.get('limit', 10)

    tag_names = []
    if q:
        context = {'model': model, 'session': model.Session, 'user': c.user, 'auth_user_obj': c.userobj}
        data_dict = {'q': q, 'limit': limit, 'vocabulary_id': vocab}
        tag_names = get_action('tag_autocomplete')(context, data_dict)

    resultSet = {
        'ResultSet': {
            'Result': [{'Name': tag} for tag in tag_names]
        }
    }
    print(_finish(200, resultSet, 'json'))
    return _finish(200, resultSet, 'json')

def get_blueprints():
    return [dcatapit_blp]

'''
class DCATAPITApiController(MethodView):
    methods = ['GET', ]

    def get(self):
        q = request.str_params.get('incomplete', '')
        q = urllib.unquote(q)

        vocab = request.params.get('vocabulary_id', None)

        vocab = str(vocab)

        log.debug('Looking for Vocab %r', vocab)

        limit = request.params.get('limit', 10)

        tag_names = []
        if q:
            context = {'model': model, 'session': model.Session, 'user': c.user, 'auth_user_obj': c.userobj}
            data_dict = {'q': q, 'limit': limit, 'vocabulary_id': vocab}
            tag_names = get_action('tag_autocomplete')(context, data_dict)

        resultSet = {
            'ResultSet': {
                'Result': [{'Name': tag} for tag in tag_names]
            }
        }

        return _finish(200, resultSet, 'json')
'''