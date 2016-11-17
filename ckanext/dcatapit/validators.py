import logging

from ckan.plugins.toolkit import Invalid
from datetime import datetime

log = logging.getLogger(__file__)


def isBlank (string):
    return not (string and string.strip())

def couple_validator(value, context):
	if not isBlank(value):
		couples = value.split(',')

		for c in couples:
			if not c:
				raise Invalid('Invalid couple, one value is missing')

	return value