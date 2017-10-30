import os
import json
import logging

from ConfigParser import SafeConfigParser as ConfigParser
from ckan import model
import ckan.plugins as p
from ckan.model.meta import Session
from ckan.lib.base import config
from paste.deploy.converters import asbool

from ckanext.harvest.queue import get_harvester
from ckanext.dcat.interfaces import IDCATRDFHarvester


log = logging.getLogger(__name__)


DCATAPIT_THEMES_MAP = 'ckanext.dcatapit.nonconformant_themes_mapping.file'
DCATAPIT_THEMES_MAP_SECTION = 'terms_theme_mapping'


def _map_themes_json(fdesc):
    data = json.load(fdesc)
    out = {}
    for map_item in data['data']:
        for syn in map_item['syn']:
            try:
                out[syn].append(map_item['name'])
            except KeyError:
                out[syn] = [map_item['name']]
    return out


def _map_themes_ini(fdesc):
    c = ConfigParser()
    c.readfp(fdesc)
    out = {}
    section_name = 'dcatapit:{}'.format(DCATAPIT_THEMES_MAP_SECTION)
    for theme_in, themes_out in c.items(section_name, raw=True):
        out[theme_in] = [t.strip() for t in themes_out.replace('\n', ',').split(',') if t.strip()]
    return out


def _load_mapping_data():
    """
    Retrives mapping data depending on configuration.

    :returns: dict with from->[to] mapping or None, if no configuration is available
    """
    fpath = config.get(DCATAPIT_THEMES_MAP)
    if not fpath:
        return
    if not os.path.exists(fpath):
        log.warning("Mapping themes in %s doesn't exist", fpath)
        return
    base, ext = os.path.splitext(fpath)
    if ext == '.json':
        handler = _map_themes_json
    else:
        handler = _map_themes_ini

    with open(fpath) as f:
        map_data = handler(f)

        return map_data


def _get_new_themes(themes, map_data, add_existing=True):
    if not themes:
        return

    new_themes = []
    # if theme is not in mapping list, keep it
    # otherwise, replace it with mapped themes
    for theme in themes:
        map_to = map_data.get(theme)
        if map_to:
            new_themes.extend(map_to)
        else:
            if add_existing:
                new_themes.append(theme)
    # do not update if themes are the same
    if set(themes) == set(new_themes):
        return
    return new_themes


def _save_theme_mapping(context, dataset_dict, to_themes):
    dataset_dict['theme'] = to_themes
    dataset_dict['extras'] = [v for v in dataset_dict['extras'] if v['key'] != 'theme']

    p.toolkit.get_action('package_patch')(context, dataset_dict) 


def map_nonconformant_themes(context, dataset_dict):
    """
    Change themes assigned to dataset based on available mapping.
    """

    if not context:
        # really bad default
        user_name = 'harvester'

        context = {
            'model': model,
            'session': Session,
            'user': user_name,
            'ignore_auth': True,
        }

    themes_data = _load_mapping_data()
    if not themes_data:
        return

    # get package with themes
    # dataset_dict = p.toolkit.get_action('package_show')(context, {'id': dataset_dict['id']})

    # collect all themes
    dtheme = dataset_dict.get('theme') or ''
    dthemes = [item for item in dtheme.strip('{}').split(',') if item]
    for e in (dataset_dict.get('extras') or []):
        if e['key'] == 'theme':
            if isinstance(e['value'], list):
                dthemes.extend(e['value'])
            else:
                dthemes.extend([item for item in e['value'].strip('{}').split(',') if item])

    new_themes = _get_new_themes(dthemes, themes_data, add_existing=True)
    if not new_themes:
        return

    # context may come from create call. we'll save it, use default update schema, and restore
    # this one later
    schema = context.pop('schema', None)
    _save_theme_mapping(context, dataset_dict, new_themes)
    context['schema'] = schema

def map_nonconformant_groups(harvest_object):
    """
    Adds themes to fetched data
    """
    themes_data = _load_mapping_data()
    if not themes_data:
        return

    harvester = get_harvester(harvest_object.source.type)
    try:
        user_name = harvester._get_user_name()
    except AttributeError:
        # really bad default
        user_name = 'harvester'

    data = json.loads(harvest_object.content)
    _groups = data.get('groups')
    if not _groups:
        return
    
    groups = [g['name'] for g in _groups]
    groups.extend([g['display_name'] for g in _groups])

    new_themes = _get_new_themes(groups, themes_data, add_existing=False)
    extra = data.get('extras') or []
    for t in new_themes:
        tdata = {'key': 'theme', 'value': t}
        #if extra and not tdata in extra:
        extra.append(tdata)
    data['extras'] = extra
    harvest_object.content = json.dumps(data)
    harvest_object.save()
