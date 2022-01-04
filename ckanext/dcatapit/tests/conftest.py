# -*- coding: utf-8 -*-

import pytest

from ckan.model import Package, Group, PackageExtra, meta, GroupExtra, Member, PackageTag
from ckanext.harvest.model import HarvestObject, HarvestSource, HarvestJob, HarvestObjectError

from ckan.tests.pytest_ckan.fixtures import clean_db
from ckanext.harvest.tests.fixtures import harvest_setup
from ckanext.spatial.tests.conftest import clean_postgis, spatial_setup
from ckanext.multilang.tests.conftest import multilang_setup

from ckanext.dcatapit.model import setup_db as dcatapit_setup_db


@pytest.fixture
def dcatapit_setup():
    dcatapit_setup_db()


@pytest.fixture
def clean_dcatapit_db(clean_postgis, clean_db, harvest_setup, spatial_setup, multilang_setup, dcatapit_setup):
    return [
        clean_postgis,
        clean_db,
        # clean_index()
        harvest_setup,
        spatial_setup,
        multilang_setup,
        dcatapit_setup,
        ]


@pytest.fixture
def remove_dataset_groups():
    for cls in (
        HarvestObjectError,
        HarvestObject,

        PackageTag,
        PackageExtra, Package,
        Member,
        GroupExtra, Group
    ):
        meta.Session.query(cls).delete()

    meta.Session.commit()


@pytest.fixture
def remove_harvest_stuff():
    for cls in (
        HarvestObjectError,
        HarvestObject,
        HarvestJob,
        HarvestSource,
    ):
        meta.Session.query(cls).delete()

    meta.Session.commit()