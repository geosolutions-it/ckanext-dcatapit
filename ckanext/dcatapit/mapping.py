import os
import logging
from ConfigParser import SafeConfigParser as ConfigParser
from paste.deploy.converters import asbool

from ckan.lib.base import config
from ckan.model import Session, repo
from ckan.model.group import Group, Member


log = logging.getLogger(__name__)


MAPPING_SECTION = 'dcatapit:theme_group_mapping'
DCATAPIT_THEME_TO_MAPPING_SOURCE = 'ckanext.dcatapit.theme_group_mapping.file'
DCATAPIT_THEME_TO_MAPPING_ADD_NEW_GROUPS = 'ckanext.dcatapit.theme_group_mapping.add_new_groups'


def get_theme_to_groups():
    """
    Returns dictionary with groups for themes
    """
    fname = config.get(DCATAPIT_THEME_TO_MAPPING_SOURCE)
    if not fname:
        return
    if not os.path.exists(fname):
        log.warning("Cannot parse theme mapping, no such file: %s", fname)
        return
    return import_theme_to_group(fname)


def _clean_groups(package):
    """
    Clears package's groups
    """
    Session.query(Member).filter(Member.table_name == 'package',
                                 Member.table_id == package.id,
                                 Member.capacity != 'admin')\
                         .update({'state':'deleted'})


def _add_groups(package, groups):
    """
    Adds groups to package
    """
    for g in groups:
        if g.id is None:
            raise ValueError("No id in group %s" % g)
        member = Member(state='active',
                        table_id=package.id,
                        group_id=g.id,
                        table_name='package')
        Session.add(member)


def _get_group_from_session(gname):
    """
    If Group was created within current session, get
    it from cache instead of db.

    This exists because new, uncommited/unflushed objects are 
    not accessible by Session.query.
    """
    for obj in Session.new:
        if isinstance(obj, Group):
            if obj.name == gname:
                return obj


def populate_theme_groups(instance, clean_existing=False, add_new=False):
    """
    For given instance, it finds groups from mapping corresponding to
    Dataset's themes, and will assign dataset to those groups.

    Existing groups will be removed, if clean_existing is set to True.

    This utilizes `ckanext.dcatapit.theme_group_mapping.add_new_groups`
    configuration option. If it's set to true, and mapped group doesn't exist,
    new group will be created.
    """
    add_new = asbool(config.get(DCATAPIT_THEME_TO_MAPPING_ADD_NEW_GROUPS))
    themes = instance.extras.get('theme')
    if not themes:
        log.debug("no theme from %s", instance)
        return
    theme_map = get_theme_to_groups()
    if not theme_map:
        log.warning("Theme to group map is empty")
        return
    if not isinstance(themes, list):
        themes = [themes]
    all_groups = set()
    for theme in themes:
        _groups = theme_map.get(theme)
        if not _groups:
            continue
        all_groups = all_groups.union(set(_groups))

    if clean_existing:
        _clean_groups(instance)
    groups = []
    for gname in all_groups:
        group =  Group.get(gname) or _get_group_from_session(gname)
        if add_new and group is None:
            group = Group(name=gname)
            Session.add(group)
        if group:
            groups.append(group)
    if Session.new:
        # flush to db, refresh with ids
        Session.flush()
        Session.revision = repo.new_revision()
        groups = [(Group.get(g.name) if g.id is None else g) for g in groups]
    _add_groups(instance, groups)

    return groups


def import_theme_to_group(fname):
    """
    Import theme to group mapping configuration from path

    Function will parse .ini file and populate mapping tables. 

    This function will make commits internally, so caller should create fresh revision before commiting later.

    Sample configuration file:

[dcatapit:theme_group_mapping]

# can be one line of values separated by coma
Economy = economy01, economy02, test01, test02

# can be per-line list
Society = society
    economy01
    other02

# or mixed
OP_DATPRO = test01
    test02, test03, dupatest

    """
    fpath = os.path.abspath(fname)
    conf = ConfigParser()
    # otherwise theme names will be lower-cased
    conf.optionxform = str
    conf.read([fpath])
    if not conf.has_section(MAPPING_SECTION):
        log.warning("Theme to groups mapping config: cannot find %s section in %s",
                    MAPPING_SECTION, fpath)
        return
    out = {}
    for theme_name, groups in conf.items(MAPPING_SECTION, raw=True):
        out[theme_name] = groups.replace('\n', ',').split(',')
    log.info("Read theme to groups mapping definition from %s. %s themes to map.", fpath, len(out.keys()))
    return out
