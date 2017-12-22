import logging

import urllib
import ckan.model as model
import ckan.logic as logic
from ckan import plugins as p

from ckan.controllers.api import ApiController

from ckan.lib.base import BaseController, c, \
                          request, response, render, abort
log = logging.getLogger(__file__)

# shortcuts
get_action = logic.get_action

class HarvesterController(BaseController):

    def list(self):
        try:
            context = {'model':model,
                       'user':c.user}
            harvest_sources = p.toolkit.get_action('harvest_source_list')(context, {})
            c.harvest_sources = harvest_sources

            return render('harvest/sources_list.html')

        except p.toolkit.ObjectNotFound:
            abort(404,_('Harvest source not found'))
        except p.toolkit.NotAuthorized, e:
            abort(401,self.not_auth_message)
        except Exception, e:
            msg = 'An error occurred: [%s]' % str(e)
            import traceback
            traceback.print_exc(e)

            abort(500, msg)
