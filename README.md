# UNDER DEVELOPMENT

# ckanext-dcatapit
CKAN extension for the Italian Open Data Portals (DCAT_AP-IT).

## Contents

- [Overview](#overview)
- [Requirements](#requirements)
- [Installation](#installation)
- [Development Installation](#development-installation)
- [Extending the package schema in your own extension](#extending-the-package-schema-in-your-own-extension)
- [Managing translations](#managing-translations)
    - [Creating a new translation](#creating-a-new-translation)
    - [Updating an existing translation](#updating-an-existing-translation)

## Overview 

This extension provides plugins that allow CKAN to expose and consume metadata from other catalogs using RDF documents serialized according to the [Italian DCAT Application Profile](http://www.dati.gov.it/content/dcat-ap_it_v10). The Data Catalog Vocabulary (DCAT) is "an RDF vocabulary designed to facilitate interoperability between data catalogs published on the Web".

## Requirements

The ckanext-dcatapit extension has been developed for CKAN 2.4 or later and is based on [ckanext-dcat plugin](https://github.com/ckan/ckanext-dcat) 
The ckanext-dcatapit extension requires also the [ckanext-multilang plugin](https://github.com/geosolutions-it/ckanext-multilang/tree/ckan-2.5.2) installed on CKAN in order to manage localized fields (see the [WIKI](https://github.com/geosolutions-it/ckanext-multilang/wiki) for more details about that). 

If the ckanext-multilang extension is missing you can use the dcatapit extension without the multilingual management. This means that all the multilingual aspects will be ignored (ie. for vocabularies, the package editing and also during the RDF harvesting and the serialization procedures).

## Installation

1. Install the **ckanext-multilang** extension as described [here](https://github.com/geosolutions-it/ckanext-multilang/blob/ckan-2.5.2/README.rst) and **ckanext-dcat** [here](https://github.com/ckan/ckanext-dcat/blob/master/README.md).

2. Activate your CKAN virtual environment, for example:

     `. /usr/lib/ckan/default/bin/activate`
     
3. Go into your CKAN path for extension (like /usr/lib/ckan/default/src):

    `git clone https://github.com/geosolutions-it/ckanext-dcatapit.git`
    
    `cd ckanext-dcatapit`
    
    `pip install -e .`

4. Add ``dcatapit_pkg`` and ``dcatapit_org`` and ``dcatapit_config`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at ``/etc/ckan/default/production.ini``).

   * **dcatapit_pkg**: extends the package schema allowing to edit and visualize extra fields according to the DCAT_AP-IT specs.
   * **dcatapit_org**: extends the organization schema allowing to edit and visualize extra fields according to the DCAT_AP-IT specs.
   * **dcatapit_config**: extends the admin configuration schema allowing to edit and visualize extra fields according to the DCAT_AP-IT specs.

The ckanext-dcatapit allows to localize the package fields (eg. title, description etc.) according to the schema definition, but to do that requires the ckanext-multilang installed.

5. In order to enable also the RDF harvester add ``dcatapit_harvester`` to the ``ckan.plugins`` setting in your CKAN. 
The ckanext-dcatapit RDF harvester also harvests localized fields, but to do that requires the ckanext-multilang installed.

6. Enable the dcatapit profile adding the following configuration property in the ``production.ini`` file:

    `ckanext.dcat.rdf.profiles = euro_dcat_ap it_dcat_ap`

7. Configure the CKAN base URI as reported in the [dcat documentation](https://github.com/ckan/ckanext-dcat/blob/master/README.md#uris):
    `ckanext.dcat.base_uri = YOUR_BASE_URI`
   
8. The EU controlled vocabularies must be populated before start using the dcatapit plugin. Execute in sequence these commands:

    `paster --plugin=ckanext-dcatapit vocabulary load --url http://publications.europa.eu/mdr/resource/authority/language/skos/languages-skos.rdf --name languages --config=/etc/ckan/default/production.ini`
    
    `paster --plugin=ckanext-dcatapit vocabulary load --url http://publications.europa.eu/mdr/resource/authority/data-theme/skos/data-theme-skos.rdf --name eu_themes --config=/etc/ckan/default/production.ini`
    
    `paster --plugin=ckanext-dcatapit vocabulary load --url http://publications.europa.eu/mdr/resource/authority/place/skos/places-skos.rdf --name places --config=/etc/ckan/default/production.ini`
    
    `paster --plugin=ckanext-dcatapit vocabulary load --url http://publications.europa.eu/mdr/resource/authority/frequency/skos/frequencies-skos.rdf --name frequencies --config=/etc/ckan/default/production.ini`
    
    `paster --plugin=ckanext-dcatapit vocabulary load --url http://publications.europa.eu/mdr/resource/authority/file-type/skos/filetypes-skos.rdf  --name filetype --config=/etc/ckan/default/production.ini`

9. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

     `sudo service apache2 reload`


## Development Installation

To install `ckanext-dcatapit` for development, activate your CKAN virtualenv and
do::

    git clone https://github.com/geosolutions-it/ckanext-dcatapit.git
    
    cd ckanext-dcatapit
    
    python setup.py develop

    pip install -r dev-requirements.txt

## Extending the package schema in your own extension

The dcatapit extension allows to define additional custom fields to the package schema by implementing the `ICustomSchema` interface 
in you CKAN extension. Below a sample:

    class ExamplePlugin(plugins.SingletonPlugin):

        # ICustomSchema
        plugins.implements(interfaces.ICustomSchema)

        def get_custom_schema(self):
            return [
                {
                    'name': 'custom_text',
                    'validator': ['ignore_missing'],
                    'element': 'input',
                    'type': 'text',
                    'label': _('Custom Text'),
                    'placeholder': _('custom texte here'),
                    'is_required': False,
                    'localized': False
                }
            ]

Through this an additional schema field named `custom_text` will be added to the package schema and automatically managed by the dcatapit extension. Below a brief description of the 
fields properties that can be used:

* ``name``: the name of the field
* ``validator``: array of validators to use for the field
* ``element``: the element type to use into the package edit form (ie. see the available ckan macros or macros defined into the dcatapit extension [here](https://github.com/geosolutions-it/ckanext-dcatapit/blob/master/ckanext/dcatapit/templates/macros/dcatapit_form_macros.html)
* ``type``: the type of input eg. email, url, date (default: text)
* ``label``: the human readable label
* ``placeholder``: some placeholder text
* ``is_required``: boolean of whether this input is requred for the form to validate
* ``localized``: True to enable the field localization by the dcatapit extension (default False). This need the ckanext-multilang installed.

## Managing translations

The dcatapit extension implements the ITranslation CKAN's interface so the translations procedure of the GUI elements is automatically covered using the translations files provided in the i18n directory.

    Pay attention that the usage of the ITranslation interface can work only in CKAN 2.5 
    or later, if you are using a minor version of CKAN the ITranslation's implementation 
    will be ignored.

### Creating a new translation

To create a new translation proceed as follow:

1. Extract new messages from your extension updating the pot file

     `python setup.py extract_messages`
     
2.  Create a translation file for your language (a po file) using the existing pot file in this plugin

     `python setup.py init_catalog --locale YOUR_LANGUAGE`

     Replace YOUR_LANGUAGE with the two-letter ISO language code (e.g. es, de).
     
3. Do the translation into the po file

4. Once the translation files (po) have been updated, either manually or via Transifex, compile them by running:

     `python setup.py compile_catalog --locale YOUR_LANGUAGE`
     
### Updating an existing translation

In order to update the existing translations proceed as follow:

1. Extract new messages from your extension updating the pot file

     `python setup.py extract_messages`
     
2. Update the strings in your po file, while preserving your po edits, by doing:

     `python setup.py update_catalog --locale YOUR-LANGUAGE`

3. Once the translation files (po) have been updated adding the new translations needed, compile them by running:

     `python setup.py compile_catalog --locale YOUR_LANGUAGE`
     
