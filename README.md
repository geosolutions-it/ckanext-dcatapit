# ckanext-dcatapit
CKAN extension for the Italian Open Data Portals (DCAT_AP-IT).

##UNDER DEVELOPMENT

#Requirements

The ckanext-dcatapit extension has been developed for CKAN 2.4 or later.
The ckanext-dcatapit extension requires the [ckanext-multilang plugin](https://github.com/geosolutions-it/ckanext-multilang/tree/ckan-2.5.2) installed on CKAN (see the [WIKI](https://github.com/geosolutions-it/ckanext-multilang/wiki) for more details about that).

#Installation

1. Install the ckanext-multilang extension as described [here](https://github.com/geosolutions-it/ckanext-multilang/blob/ckan-2.5.2/README.rst)

2. Activate your CKAN virtual environment, for example:

     `. /usr/lib/ckan/default/bin/activate`
     
3. Go into your CKAN path for extension (like /usr/lib/ckan/default/src):

    `git clone https://github.com/geosolutions-it/ckanext-dcatapit.git`
    
    `cd ckanext-dcatapit`
    
    `pip install -e .`

4. Add ``dcatapit_pkg`` and ``dcatapit_org`` and ``dcatapit_config`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at ``/etc/ckan/default/production.ini``).
   
5. The EU controlled vocabularies must be populated before start using the dcatapit plugin. Execute in sequence these commands:

    `paster --plugin=ckanext-dcatapit vocabulary load --url http://publications.europa.eu/mdr/resource/authority/language/skos/languages-skos.rdf --name languages --config=/etc/ckan/default/production.ini`
    
    `paster --plugin=ckanext-dcatapit vocabulary load --url http://publications.europa.eu/mdr/resource/authority/data-theme/skos/data-theme-skos.rdf --name eu_themes --config=/etc/ckan/default/production.ini`
    
    `paster --plugin=ckanext-dcatapit vocabulary load --url http://publications.europa.eu/mdr/resource/authority/place/skos/places-skos.rdf --name places --config=/etc/ckan/default/production.ini`
    
    `paster --plugin=ckanext-dcatapit vocabulary load --url http://publications.europa.eu/mdr/resource/authority/frequency/skos/frequencies-skos.rdf --name frequencies --config=/etc/ckan/default/production.ini`
    
    `paster --plugin=ckanext-dcatapit vocabulary load --url http://publications.europa.eu/mdr/resource/authority/file-type/skos/filetypes-skos.rdf  --name filetype --config=/etc/ckan/default/production.ini`

6. Restart CKAN

# Managing translations

The dcatapit extension implements the ITranslation CKAN's interface so the translations procedure of the GUI elements is automatically covered using the translations files provided in the i18n directory. 

## Creating a new translation
To create a new translation proceed as follow:

1.  Create a translation file for your language (a po file) using the existing pot file in this plugin

     `python setup.py init_catalog --locale YOUR_LANGUAGE`

     Replace YOUR_LANGUAGE with the two-letter ISO language code (e.g. es, de).

2. Do the translation into the po file

3. Once the translation files (po) have been updated, either manually or via Transifex, compile them by running:

     `python setup.py compile_catalog --locale YOUR_LANGUAGE`
     
## Updating an existing translation
In order to update the existing translations proceed as follow:

1. Extract new messages from your extension updating the pot file

     `python setup.py extract_messages`
     
2. Update the strings in your po file, while preserving your po edits, by doing:

     `python setup.py update_catalog --locale YOUR-LANGUAGE`

     for a specific language, or for all languages:

     `python setup.py update_catalog`

3. Once the translation files (po) have been updated adding the new translations needed, compile them by running:

     `python setup.py compile_catalog --locale YOUR_LANGUAGE`

     for a specific language, or for all languages:

     `python setup.py compile_catalog`
     
