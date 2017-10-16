
import os
import sys
import logging
from ConfigParser import SafeConfigParser as ConfigParser

from sqlalchemy import types, Column, Table, ForeignKey
from sqlalchemy import orm

from ckan.lib.base import config
from ckan import model
from ckan.model import Session
from ckan.model import meta
from ckan.model.domain_object import DomainObject
from ckan.model.group import Group, Member
from ckan.model.package import Package


log = logging.getLogger(__name__)

__all__ = ['DCATAPITTagVocabulary', 'dcatapit_vocabulary_table', 'setup']

dcatapit_vocabulary_table = Table('dcatapit_vocabulary', meta.metadata,
    Column('id', types.Integer, primary_key=True),
    Column('tag_id', types.UnicodeText, ForeignKey("tag.id", ondelete="CASCADE"), nullable=False),
    Column('tag_name', types.UnicodeText, nullable=False, index=True),
    Column('lang', types.UnicodeText, nullable=False, index=True),
    Column('text', types.UnicodeText, nullable=False, index=True))


dcatapit_theme_map_from = Table('dcatapit_theme_from', meta.metadata,
    Column('id', types.Integer, primary_key=True),
    Column('name', types.UnicodeText, nullable=False, index=False))

dcatapit_group_map_to = Table('dcatapit_group_to', meta.metadata,
    Column('id', types.Integer, primary_key=True),
    Column('theme_id', types.Integer, ForeignKey('dcatapit_theme_from.id')),
    Column('name', types.UnicodeText, nullable=False, index=False))
    

def setup():
    log.debug('DCAT_AP-IT tables defined in memory')

    #Setting up tag multilang table
    if not dcatapit_vocabulary_table.exists():
        try:
            dcatapit_vocabulary_table.create()
        except Exception,e:
            # Make sure the table does not remain incorrectly created
            if dcatapit_vocabulary_table.exists():
                Session.execute('DROP TABLE dcatapit_vocabulary')
                Session.commit()

            raise e

        log.info('DCATAPIT Tag Vocabulary table created')
    else:
        log.info('DCATAPIT Tag Vocabulary table already exist')

    for t in (dcatapit_theme_map_from, dcatapit_group_map_to,):
        if not t.exists():
            t.create()


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

class _Queryable(object):

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def create(cls, **kwargs):
        inst = cls(**kwargs)
        meta.Session.add(inst)
        meta.Session.commit()
        return inst

    @classmethod
    def query(cls):
        return meta.Session.query(cls)


class DCATAPITThemeMapFrom(_Queryable):
    pass

class DCATAPITTGroupMapTo(_Queryable):
    pass


meta.mapper(DCATAPITTagVocabulary, dcatapit_vocabulary_table)
meta.mapper(DCATAPITThemeMapFrom, dcatapit_theme_map_from)
meta.mapper(DCATAPITTGroupMapTo, dcatapit_group_map_to,
        properties={
            'theme': orm.relation(
                DCATAPITThemeMapFrom,
                lazy=True,
                backref=u'groups',
            )}
        )


def get_theme_to_groups():
    """
    Returns dictionary with groups for themes
    """
    q = DCATAPITThemeMapFrom.query().all()
    out = {}
    for theme in q:
        groups = [g.name for g in theme.groups]
        out[theme.name] = groups
    return out

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

MAPPING_SECTION = 'dcatapit:theme_group_mapping'


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
    log.info("Read theme to groups mapping definition from %s. Replacing configuration", fpath)
    DCATAPITTGroupMapTo.query().delete()
    for theme_name, groups in conf.items(MAPPING_SECTION, raw=True):
        _groups = groups.replace('\n', ',').split(',')
        theme = DCATAPITThemeMapFrom.create(name=theme_name)
        for g in _groups:
            if g.strip():
                DCATAPITTGroupMapTo.create(theme_id=theme.id, name=g.strip())

