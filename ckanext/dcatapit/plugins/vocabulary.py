from flask import Blueprint
import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as tk

from ckanext.dcatapit.controllers.thesaurus import ThesaurusController, get_thesaurus_admin_page, update_vocab_admin

log = logging.getLogger(__file__)


class DCATAPITVocabularyPlugin(plugins.SingletonPlugin, tk.DefaultDatasetForm):

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
        tk.add_ckan_admin_tab(config_, 'dcatapit_core.thesaurus', 'Thesaurus File Uploader', icon='book')
