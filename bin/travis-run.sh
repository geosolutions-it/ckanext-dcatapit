#!/bin/sh -e

pytest --ckan-ini=subdir/test.ini --with-coverage --cover-package=ckanext.dcatapit --cover-inclusive --cover-erase --cover-tests ckanext/dcatapit