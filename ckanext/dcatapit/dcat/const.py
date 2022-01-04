from rdflib import Namespace

DCATAPIT = Namespace('http://dati.gov.it/onto/dcatapit#')
it_namespaces = {
    'dcatapit': DCATAPIT,
}
THEME_BASE_URI = 'http://publications.europa.eu/resource/authority/data-theme/'
LANG_BASE_URI = 'http://publications.europa.eu/resource/authority/language/'
FREQ_BASE_URI = 'http://publications.europa.eu/resource/authority/frequency/'
FORMAT_BASE_URI = 'http://publications.europa.eu/resource/authority/file-type/'
GEO_BASE_URI = 'http://publications.europa.eu/resource/authority/place/'

THEME_CONCEPTS = ('eu_themes', THEME_BASE_URI)
LANG_CONCEPTS = ('languages', LANG_BASE_URI)
GEO_CONCEPTS = ('places', GEO_BASE_URI)
FREQ_CONCEPTS = ('frequencies', FREQ_BASE_URI)
FORMAT_CONCEPTS = ('filetype', FORMAT_BASE_URI)

DEFAULT_VOCABULARY_KEY = 'OP_DATPRO'
DEFAULT_THEME_KEY = DEFAULT_VOCABULARY_KEY
DEFAULT_FORMAT_CODE = DEFAULT_VOCABULARY_KEY
DEFAULT_FREQ_CODE = 'UNKNOWN'

LOCALISED_DICT_NAME_BASE = 'DCATAPIT_MULTILANG_BASE'
LOCALISED_DICT_NAME_RESOURCES = 'DCATAPIT_MULTILANG_RESOURCES'

lang_mapping_ckan_to_voc = {
    'it': 'ITA',
    'de': 'DEU',
    'en': 'ENG',
    'en_GB': 'ENG',
    'fr': 'FRA',
}
lang_mapping_xmllang_to_ckan = {
    'it': 'it',
    'de': 'de',
    # 'en': 'en_GB',
    'en': 'en',
    'fr': 'fr',
}
lang_mapping_ckan_to_xmllang = {
    'en_GB': 'en',
    'uk_UA': 'ua',
    'en_AU': 'en',
    'es_AR': 'es',
}
format_mapping = {
    'WMS': 'MAP_SRVC',
    'HTML': 'HTML_SIMPL',
    'CSV': 'CSV',
    'XLS': 'XLS',
    'ODS': 'ODS',
    'ZIP': 'OP_DATPRO',  # requires to be more specific, can't infer
}
