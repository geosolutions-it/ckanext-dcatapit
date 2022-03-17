import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import and_

import ckan.plugins.toolkit as toolkit
from ckan.lib.base import config
from ckan.lib.navl.dictization_functions import Invalid
from ckan.logic import ValidationError
from ckan.logic.validators import tag_name_validator
from ckan.model.meta import Session
from ckan.model import (
    Group,
    GroupExtra,
    Package,
    PackageExtra,
    repo,
)

from ckanext.multilang.model import PackageMultilang as ML_PM

from ckanext.dcatapit.schema import FIELD_THEMES_AGGREGATE
from ckanext.dcatapit import validators
import ckanext.dcatapit.interfaces as interfaces

REGION_TYPE = 'https://w3id.org/italia/onto/CLV/Region'
NAME_TYPE = 'https://w3id.org/italia/onto/l0/name'

DEFAULT_LANG = config.get('ckan.locale_default', 'en')
DATE_FORMAT = '%d-%m-%Y'

log = logging.getLogger(__name__)


def do_migrate_data(limit=None, offset=None, skip_orgs=False, pkg_uuid: list = None):
    # Data migrations from 1.0.0 to 1.1.0
    # ref: https://github.com/geosolutions-it/ckanext-dcatapit/issues/188

    from ckanext.dcatapit.plugin import DCATAPITPackagePlugin

    user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name'],
               'ignore_auth': True,
               'use_cache': False}
    pshow = toolkit.get_action('package_show')
    pupdate = toolkit.get_action('package_update')
    pcreate = toolkit.get_action('package_create')
    oshow = toolkit.get_action('organization_show')
    oupdate = toolkit.get_action('organization_patch')
    pupdate_schema = DCATAPITPackagePlugin().update_package_schema()
    pupdate_schema['tags']['name'].remove(tag_name_validator)
    org_list = get_organization_list()
    ocount = org_list.count()
    oidx = 0
    if not skip_orgs:
        log.info(f'processing {ocount} organizations')
        for oidx, oname in enumerate(org_list):
            odata = oshow(context, {'id': oname, 'include_extras': True,
                                    'include_tags': False,
                                    'include_users': False,
                                    })

            oidentifier = odata.get('identifier')
            log.info('processing {}/{} organization: {}'.format(oidx + 1, ocount, odata['name']))
            # we require identifier for org now.
            if not oidentifier:
                odata.pop('identifier', None)
                tmp_identifier = get_temp_org_identifier()
                log.info(
                    f"org: [{odata['name']}] {odata['title']}: "
                    f'setting temporal identifier: {tmp_identifier}'
                )
                ocontext = context.copy()

                ocontext['allow_partial_update'] = True
                # oupdate(ocontext, {'id': odata['id'],
                #                  'identifier': tmp_identifier})
                update_organization_identifier(odata['id'], tmp_identifier)
    else:
        log.info(u'Skipping organizations processing')
    pcontext = context.copy()
    pkg_list = get_package_list(pkg_uuid)
    pcount = pkg_list.count()
    log.info(f'processing {pcount} packages')
    errored = []

    if offset:
        pkg_list = pkg_list.offset(offset)
    if limit:
        pkg_list = pkg_list.limit(limit)

    # pidx may be not initialized for empty slice, need separate counter
    # to count actually processed datasets
    pidx_count = 0
    for pidx, pname in enumerate(pkg_list):
        pcontext['schema'] = pupdate_schema
        pname = pname[0]
        log.info(f'processing {pidx + 1}/{pcount} package: {pname}')
        pdata = pshow(context, {'name_or_id': pname})  # , 'use_default_schema': True})

        # remove empty conforms_to to avoid silly validation errors
        if not pdata.get('conforms_to'):
            pdata.pop('conforms_to', None)
        # ... the same for alternate_identifier
        if not pdata.get('alternate_identifier'):
            pdata.pop('alternate_identifier', None)

        update_creator(pdata)
        update_temporal_coverage(pdata)
        update_theme(pdata)
        update_identifier(pdata)
        update_modified(pdata)
        update_frequency(pdata)
        update_conforms_to(pdata)
        update_holder_info(pdata)
        interfaces.populate_resource_license(pdata)
        pdata['metadata_modified'] = None
        log.info(f"updating {pdata['id']} {pdata['name']}")
        try:
            out = pupdate(pcontext, pdata)
            pidx_count += 1
        except ValidationError as err:
            log.error(
                f"Cannot update due to validation error {pdata['name']}",
                exc_info=True
            )
            errored.append((pidx, pdata['name'], err,))
            continue

        except Exception as err:
            log.error(
                f"Cannot update due to general error {pdata['name']}",
                exc_info=True
            )
            errored.append((pidx, pdata['name'], err,))
            continue
        log.debug('-' * 9)

    if not skip_orgs:
        log.info(f'processed {oidx} out of {ocount} organizations')
    log.info(f'processed {pidx_count} out of {pcount} packages in total')
    if errored:
        log.info(f'Following {len(errored)} datasets failed:')
        for position, ptitile, err in errored:
            err_summary = getattr(err, 'error', None) or err

            # this is a hack on dumb override in __str__() in some exception subclasses
            # stringified exception raises itself otherwise.
            try:
                log.info(
                    f' {ptitile} at position {position}: {err.__class__}{err_summary}'
                )
            except Exception as err:
                err_summary = err
                log.error(
                    f' {ptitile} at position {position}: {err.__class__}{err_summary}'
                )
    return pidx_count


def get_package_list(pkg_uuid=None):
    query = Session.query(Package.name)\
                .filter(Package.state.in_(['active', 'draft']),
                        Package.type == 'dataset')

    if pkg_uuid:
        query = query.filter(Package.id.in_(pkg_uuid))

    return query.order_by(Package.title)


def get_organization_list():
    return Session.query(Group.name).filter(Group.state == 'active',
                                            Group.type == 'organization') \
        .order_by(Group.title)


def update_holder_info(pdata):
    if pdata.get('holder_name') and not pdata.get('holder_identifier'):
        pdata['holder_identifier'] = get_temp_holder_identifier()
        log.info(
            'dataset %s: holder_name present: %s, but no holder_identifier in data. using generated one: %s',
            pdata['name'], pdata['holder_name'], pdata['holder_identifier']
        )


def update_conforms_to(pdata):
    cname = pdata.pop('conforms_to', None)
    to_delete = []
    if not cname:
        for idx, ex in enumerate(pdata.get('extras') or []):
            if ex['key'] == 'conforms_to':
                to_delete.append(idx)
                cname = ex['value']
        if to_delete:
            for idx in reversed(to_delete):
                pdata['extras'].pop(idx)

    ml_pkg = interfaces.get_for_package(pdata['id'])
    if ml_pkg:
        try:
            ml_conforms_to = ml_pkg['conforms_to']
        except KeyError:
            ml_conforms_to = {}
    if cname:
        validator = toolkit.get_validator('dcatapit_conforms_to')
        try:
            # do not update conforms_to if it's already present
            conforms_to = json.loads(cname)
            if isinstance(conforms_to, list) and len(conforms_to):
                pdata['conforms_to'] = validator(cname, {})
                return
        except (ValueError, TypeError, Invalid) as err:
            log.error(
                f"dataset {pdata['name']}: conforms_to present, but invalid: {err}",
                exec_info=True
            )

        standard = {'identifier': None, 'description': {}}
        if not ml_conforms_to:
            standard['identifier'] = cname
        else:
            standard['identifier'] = ml_conforms_to.get('it') or ml_conforms_to.get(DEFAULT_LANG) or cname
            for lang, val in ml_conforms_to.items():
                standard['description'][lang] = val

        Session.query(ML_PM).filter(ML_PM.package_id == pdata['id'],
                                    ML_PM.field == 'conforms_to').delete()
        pdata['conforms_to'] = json.dumps([standard])


def update_creator(pdata):
    # move "creator_name" and "creator_identifier" into a json struct in field "creator"
    # old format foresaw a single creator, new struct allows N creators
    if pdata.get('creator'):
        return
    cname = pdata.pop('creator_name', None)
    cident = pdata.pop('creator_identifier', None)

    to_delete = []
    if not (cname and cident):
        for idx, ex in enumerate(pdata.get('extras') or []):
            if ex['key'] == 'creator_name':
                to_delete.append(idx)
                cname = ex['value']
            elif ex['key'] == 'creator_identifier':
                to_delete.append(idx)
                cident = ex['value']
        if to_delete:
            for idx in reversed(to_delete):
                pdata['extras'].pop(idx)

    if (cname or cident):
        lang = interfaces.get_language()
        pdata['creator'] = json.dumps([{'creator_identifier': cident,
                                        'creator_name': {lang: cname}}])


DEFAULT_THEME = json.dumps([{'theme': 'OP_DATPRO', 'subthemes': []}])


def update_theme(pdata):
    if FIELD_THEMES_AGGREGATE in pdata:
        return

    theme = pdata.pop('theme', None)
    if not theme:
        to_delete = []
        for idx, ex in enumerate(pdata.get('extras') or []):
            if ex['key'] == 'theme':
                to_delete.append(idx)
                theme = ex['value']
        if to_delete:
            for idx in reversed(to_delete):
                pdata['extras'].pop(idx)

    # default theme if nothing available
    if not theme:
        theme = DEFAULT_THEME
    validator = toolkit.get_validator('dcatapit_subthemes')

    try:
        theme = validator(theme, {})
    except Invalid as err:
        log.error(
            f"dataset {pdata['name']}: cannot use theme {theme}:",
            exec_info=True
        )
        theme = DEFAULT_THEME
    pdata['theme'] = theme


def update_temporal_coverage(pdata):
    # do not process if tempcov is already present
    if pdata.get('temporal_coverage'):
        return

    tstart = pdata.pop('temporal_start', None)
    tend = pdata.pop('temporal_end', None)

    if not (tstart and tend):
        to_delete = []
        for idx, ex in enumerate(pdata.get('extras') or []):
            if ex['key'] == 'temporal_start':
                to_delete.append(idx)
                tstart = ex['value']
            if ex['key'] == 'temporal_end':
                to_delete.append(idx)
                tend = ex['value']
        if to_delete:
            for idx in reversed(to_delete):
                pdata['extras'].pop(idx)

    try:
        tstart = validators.parse_date(tstart).strftime(DATE_FORMAT)
    except (Invalid, ValueError, TypeError) as err:
        if tstart is not None:
            log.error(
                f"dataset {pdata['name']}: can't use {tstart} as temporal coverage start:",
                exc_info=True
            )
        tstart = None
    try:
        tend = validators.parse_date(tend).strftime(DATE_FORMAT)
    except (Invalid, ValueError, TypeError) as err:
        if tend is not None:
            log.error(
                f"dataset {pdata['name']}: can't use {tend} as temporal coverage end:",
                exc_info=True
            )
        tend = None
    # handle 2010-01-01 to 2010-01-01 case, use whole year
    # if tstart == tend and tstart.day == 1 and tstart.month == 1:
    #     tend = tend.replace(day=31, month=12)

    if (tstart):

        validator = toolkit.get_validator('dcatapit_temporal_coverage')
        if (tstart == tend):
            log.info(
                f"dataset {pdata['name']}: "
                f'the same temporal coverage start/end: {tstart}/{tend}, '
                f'using start only',
            )
            tend = None
        temp_cov = json.dumps([{'temporal_start': tstart,
                                'temporal_end': tend}])
        try:
            temp_cov = validator(temp_cov, {})
            pdata['temporal_coverage'] = temp_cov
        except Invalid as err:
            log.error(
                f"dataset {pdata['name']}: cannot use temporal coverage {(tstart, tend)}:",
                exec_info=True
            )


def update_frequency(pdata):
    frequency = pdata.pop('frequency', None)
    if not frequency:
        to_delete = []
        for idx, ex in enumerate(pdata.get('extras') or []):
            if ex['key'] == 'frequency':
                to_delete.append(idx)
                frequency = ex['value']
        if to_delete:
            for idx in reversed(to_delete):
                pdata['extras'].pop(idx)

    # default frequency
    if not frequency:
        log.info(
            f"dataset {pdata['name']}: no frequency. Using default, UNKNOWN."
        )
        frequency = 'UNKNOWN'
    pdata['frequency'] = frequency


def update_identifier(pdata):
    identifier = pdata.pop('identifier', None)
    if not identifier:
        to_delete = []
        for idx, ex in enumerate(pdata.get('extras') or []):
            if ex['key'] == 'identifier':
                to_delete.append(idx)
                identifier = ex['value']
        if to_delete:
            for idx in reversed(to_delete):
                pdata['extras'].pop(idx)

    # default theme if nothing available
    if not identifier:
        log.warning(
            f"dataset {pdata['name']}: no identifier. generating new one"
        )
        identifier = str(uuid.uuid4())
    pdata['identifier'] = identifier


def update_modified(pdata):
    try:
        data = validators.parse_date(pdata['modified'])
    except (KeyError, Invalid):
        val = pdata.get('modified') or None
        log.info(
            f"dataset {pdata['name']}: invalid modified date {val}. "
            f'Using now timestamp'
        )
        data = datetime.now()
    pdata['modified'] = datetime.now().strftime('%Y-%m-%d')


TEMP_IPA_CODE = 'tmp_ipa_code'
TEMP_HOLDER_CODE = 'tmp_holder_code'


def get_temp_holder_identifier():
    c = package_temp_code_count(TEMP_HOLDER_CODE)
    return '{}_{}'.format(TEMP_HOLDER_CODE, c + 1)


def get_temp_org_identifier():
    c = group_temp_code_count(TEMP_IPA_CODE)
    return '{}_{}'.format(TEMP_IPA_CODE, c + 1)


def package_temp_code_count(BASE_CODE):
    s = Session
    q = s.query(PackageExtra.value).join(Package, and_(Package.id == PackageExtra.package_id,
                                                       PackageExtra.state == 'active')) \
        .filter(Package.type == 'organization',
                Package.state == 'active',
                PackageExtra.key == 'identifier',
                PackageExtra.value.startswith(BASE_CODE)) \
        .group_by(PackageExtra.value) \
        .count()
    return q


def group_temp_code_count(BASE_CODE):
    s = Session
    q = s.query(GroupExtra.value).join(Group, and_(Group.id == GroupExtra.group_id,
                                                   GroupExtra.state == 'active')) \
        .filter(Group.type == 'organization',
                Group.state == 'active',
                GroupExtra.key == 'identifier',
                GroupExtra.value.startswith(BASE_CODE)) \
        .group_by(GroupExtra.value) \
        .count()
    return q


def update_organization_identifier(org_id, org_identifier):
    s = Session
    s.revision = getattr(s, 'revision', None) or repo.new_revision()
    g = s.query(Group).filter(Group.id == org_id).one()
    g.extras['identifier'] = org_identifier
    s.add(g)
    s.flush()
