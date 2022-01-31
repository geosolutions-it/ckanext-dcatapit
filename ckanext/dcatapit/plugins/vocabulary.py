import datetime
import json
import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.plugins.toolkit import _
from ckan import lib, logic
from ckan.common import config
from flask import Blueprint
from routes.mapper import SubMapper

import ckanext.dcatapit.helpers as helpers
import ckanext.dcatapit.interfaces as interfaces
import ckanext.dcatapit.schema as dcatapit_schema
import ckanext.dcatapit.validators as validators
from ckanext.dcatapit.commands import dcatapit as dcatapit_cli
from ckanext.dcatapit.controllers.harvest import HarvesterController
from ckanext.dcatapit.dcat.const import THEME_BASE_URI
from ckanext.dcatapit.helpers import get_org_context
from ckanext.dcatapit.mapping import populate_theme_groups, theme_name_to_uri
from ckanext.dcatapit.mapping import populate_theme_groups
from ckanext.dcatapit.controllers.thesaurus import ThesaurusController, get_thesaurus_admin_page, update_vocab_admin
from ckanext.dcatapit.model.license import License
from ckanext.dcatapit.schema import FIELD_THEMES_AGGREGATE

log = logging.getLogger(__file__)


class DCATAPITVocabularyPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):

    # plugins.implements(plugins.ITranslation, inherit=True)
    plugins.implements(plugins.IBlueprint, inherit=True)
    plugins.implements(plugins.IConfigurer)

    def get_blueprint(self):
        blueprint = Blueprint('dcatapit_core', self.__module__)

        blueprint.add_url_rule(
            rule='/ckan-admin/thesaurus',
            endpoint='thesaurus',
            view_func=get_thesaurus_admin_page,
        )
        blueprint.add_url_rule(
            rule='/ckan-admin/thesaurus/save',
            endpoint='thesaurus_save',
            view_func=update_vocab_admin,
            methods=[u'POST']
        )

        return blueprint

    def update_config(self, config_):
        toolkit.add_ckan_admin_tab(config_, 'dcatapit_core.thesaurus', 'Thesaurus File Uploader', icon='book')
