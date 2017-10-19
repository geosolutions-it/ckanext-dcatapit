
import os
import logging
from ConfigParser import SafeConfigParser as ConfigParser

from sqlalchemy import types, Column, Table, ForeignKey

from ckan.lib.base import config
from ckan.model import Session
from ckan.model import meta
from ckan.model.domain_object import DomainObject
from ckan.model.group import Group, Member


log = logging.getLogger(__name__)

__all__ = ['DCATAPITTagVocabulary', 'dcatapit_vocabulary_table', 'setup']

dcatapit_vocabulary_table = Table('dcatapit_vocabulary', meta.metadata,
    Column('id', types.Integer, primary_key=True),
    Column('tag_id', types.UnicodeText, ForeignKey("tag.id", ondelete="CASCADE"), nullable=False),
    Column('tag_name', types.UnicodeText, nullable=False, index=True),
    Column('lang', types.UnicodeText, nullable=False, index=True),
    Column('text', types.UnicodeText, nullable=False, index=True))


def setup():
    log.debug('DCAT_AP-IT tables defined in memory')

    #Setting up tag multilang table
    if not dcatapit_vocabulary_table.exists():
        try:
            dcatapit_vocabulary_table.create()
        except Exception, e:
            # Make sure the table does not remain incorrectly created
            if dcatapit_vocabulary_table.exists():
                Session.execute('DROP TABLE dcatapit_vocabulary')
                Session.commit()

            raise e

        log.info('DCATAPIT Tag Vocabulary table created')
    else:
        log.info('DCATAPIT Tag Vocabulary table already exist')


class DCATAPITTagVocabulary(DomainObject):
    def __init__(self, tag_id=None, tag_name=None, lang=None, text=None):
        self.tag_id = tag_id
        self.tag_name = tag_name
        self.lang = lang
        self.text = text

    @classmethod
    def by_name(self, tag_name, tag_lang, autoflush=True):
        query = meta.Session.query(DCATAPITTagVocabulary).filter(DCATAPITTagVocabulary.tag_name==tag_name, DCATAPITTagVocabulary.lang==tag_lang)
        query = query.autoflush(autoflush)
        tag = query.first()
        return tag

    @classmethod
    def all_by_name(self, tag_name, autoflush=True):
        query = meta.Session.query(DCATAPITTagVocabulary).filter(DCATAPITTagVocabulary.tag_name==tag_name)
        query = query.autoflush(autoflush)
        tags = query.all()

        ret = {}
        for record in tags:
            ret[record.lang] = record.text

        return ret

    @classmethod
    def by_tag_id(self, tag_id, tag_lang, autoflush=True):
        query = meta.Session.query(DCATAPITTagVocabulary).filter(DCATAPITTagVocabulary.tag_id==tag_id, DCATAPITTagVocabulary.lang==tag_lang)
        query = query.autoflush(autoflush)
        tag = query.first()
        return tag

    @classmethod
    def persist(self, tag, lang):
        session = meta.Session
        try:
            session.add_all([
                DCATAPITTagVocabulary(tag_id=tag.get('id'), tag_name=tag.get('name'), lang=lang, text=tag.get('text')),
            ])

            session.commit()
        except Exception, e:
            # on rollback, the same closure of state
            # as that of commit proceeds. 
            session.rollback()

            log.error('Exception occurred while persisting DB objects: %s', e)
            raise


meta.mapper(DCATAPITTagVocabulary, dcatapit_vocabulary_table)

MAPPING_SECTION = 'dcatapit:theme_group_mapping'
DCATAPIT_THEME_TO_MAPPING_SOURCE = 'ckanext.dcatapit.theme_group_mapping.file'


def get_theme_to_groups():
    """
    Returns dictionary with groups for themes
    """
    fname = config.get(DCATAPIT_THEME_TO_MAPPING_SOURCE)
    if not fname or not os.path.exists(fname):
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

def populate_theme_groups(instance, clean_existing=False):
    """
    For given instance, it finds groups from mapping corresponding to
    Dataset's themes, and will assign dataset to those groups.

    Existing groups will be removed, if clean_existing is set to True.

    If group doesn't exist, it will be created.
    """
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
        group =  Session.query(Group)\
                        .filter(Group.name==gname)\
                        .first() or _get_group_from_session(gname)
        if group is None:
            group = Group(name=gname)
            Session.add(group)
        groups.append(group)
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
