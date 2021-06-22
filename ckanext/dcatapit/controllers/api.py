
import logging
import urllib

import ckan.logic as logic
import ckan.model as model
from ckan.common import c, request
from ckan.views.api import _finish
from flask.views import MethodView

log = logging.getLogger(__file__)

# shortcuts
get_action = logic.get_action


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
