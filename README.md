# ckanext-dcatapit
CKAN extension for the Italian Open Data Portals (DCAT_AP-IT).

##UNDER DEVELOPMENT

------------
Requirements
------------

The ckanext-dcatapit extension has been developed for CKAN 2.4 or later.
The ckanext-dcatapit extension requires the [ckanext-multilang plugin](https://github.com/geosolutions-it/ckanext-multilang/tree/ckan-2.5.2) installed on CKAN (see the [WIKI](https://github.com/geosolutions-it/ckanext-multilang/wiki) for more details about that).

------------
Installation
------------

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
