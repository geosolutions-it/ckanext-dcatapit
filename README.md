<!-- [![Build status](https://github.com/geosolutions-it/ckanext-dcatapit/actions/workflows/test.yml/badge.svg)](https://github.com/geosolutions-it/ckanext-dcatapit/actions/workflows/test.yml) -->
[![Code Coverage](https://codecov.io/github/geosolutions-it/ckanext-dcatapit/coverage.svg?branch=master)](https://codecov.io/github/geosolutions-it/ckanext-dcatapit?branch=master)

# ckanext-dcatapit
CKAN extension for the Italian Open Data Portals (DCAT_AP-IT).

## Contents

- [Overview](#overview)
- [License](#license)
- [Demo Instance](#demo-instance)
- [Requirements](#requirements)
- [Installation](#installation)
- [Development Installation](#development-installation)
- [Running the Tests](#running-the-tests)
- [DCAT_AP-IT CSW Harvester](#dcat_ap-it-csw-harvester)
    - [CSW Metadata Guidelines](#csw-metadata-guidelines)
- [Test Instance and Validation](#test-instance-and-validation)
- [Extending the package schema in your own extension](#extending-the-package-schema-in-your-own-extension)
- [Managing translations](#managing-translations)
    - [Creating a new translation](#creating-a-new-translation)
    - [Updating an existing translation](#updating-an-existing-translation)
- [Updating an old installation](#updating-an-old-installation)
- [Contributing](#contributing)
- [Support, Communication and Credits](#support-communication-and-credits)

## License

**ckanext-dcatapit** is Free and Open Source software and is licensed under the [GNU Affero General Public License (AGPL) v3.0](http://www.fsf.org/licensing/licenses/agpl-3.0.html).


## Demo Instance

A demo instance can be found [here](http://dcatapit.geo-solutions.it/).

## Overview 

This extension provides plugins that allow CKAN to expose and consume metadata from other catalogs using RDF documents serialized according to the [Italian DCAT Application Profile](https://www.dati.gov.it/content/dcat-ap-it-v10-profilo-italiano-dcat-ap-0). The Data Catalog Vocabulary (DCAT) is "an RDF vocabulary designed to facilitate interoperability between data catalogs published on the Web".

Also, if enabled, this extension improves dataset form look'n'feel. See [Dataset form](#dataset-form)

## Requirements

The ckanext-dcatapit extension is compatible with CKAN 2.9 and Python 3.7 (master branch).  
Previous version ([tagged `dcatapit-1.0.0`](https://github.com/geosolutions-it/ckanext-dcatapit/tree/dcatapit-1.0.0) has been developed for CKAN 2.4 and should be compatible with CKAN upto 2.8.

The dcatap-it plugins extend the functionalities of the [ckanext-dcat plugins](https://github.com/ckan/ckanext-dcat).

In order to use the dcatapit CSW harvester functionalities, you need to install also the [ckanext-spatial](https://github.com/ckan/ckanext-spatial) extension.

If you want to manage localized fields, the ckanext-dcatapit extension requires also the [ckanext-multilang plugin](https://github.com/geosolutions-it/ckanext-multilang) installed (see the [WIKI](https://github.com/geosolutions-it/ckanext-multilang/wiki) for more details about that).

## Installation

1. (**Optional**) Install the **ckanext-spatial** extension as described [here](https://github.com/ckan/ckanext-spatial). Install this extension only if you need to use the dcatapit CSW harvester (see below).

2. The ckanext-dcatapit extension allows to localize the package fields (eg. title, description etc.) according to the schema definition; in order to be able to do it, you need the **ckanext-multilang** extension installed.
   
   If you also need to use the localized resources feature provided by the
   [multilang_resources](https://github.com/geosolutions-it/ckanext-multilang/wiki/Plugin-multilang_resources) plugin in the `ckanext-multilang` extension,
   you'll have to define:
   
        ckanext.dcatapit.localized_resources = True
        
   Also make sure NOT to have the `multilang_resources` directly listed in your `ckan.plugins` line, or it will conflict with the
   internal mechanism of plugin handling.

3. Install the **ckanext-dcat** extension as described [here](https://github.com/ckan/ckanext-dcat/blob/master/README.md#installation).

4. Activate your CKAN virtual environment, for example:

        . /usr/lib/ckan/default/bin/activate
     
5. Go into your CKAN path for extension (like /usr/lib/ckan/default/src):

        git clone https://github.com/geosolutions-it/ckanext-dcatapit.git    
        cd ckanext-dcatapit    
        pip install -e .

6. Add the required plugins to the ``ckan.plugins`` setting in your CKAN config file 
  (by default the config file is located at ``/etc/ckan/default/production.ini``).

   * `dcatapit_pkg`: extends the package schema allowing to edit and visualize extra fields according to 
     the DCAT_AP-IT specs.
   * `dcatapit_org`: extends the organization schema allowing to edit and visualize extra fields according to 
     the DCAT_AP-IT specs.
   * `dcatapit_config`: extends the admin configuration schema allowing to edit and visualize extra fields according to 
     the DCAT_AP-IT specs.
   * `dcatapit_subcatalog_facets`: (deprecated) adds a facet containing the harvested subcatalogs. It needs the property
     `ckanext.dcat.expose_subcatalogs` to be set to `True` (see [*transitive harvesting*](https://github.com/geosolutions-it/ckanext-dcat/blob/d0b4373282cac7dd519c702b15c1aaf1c013e03a/README.md#transitive-harvesting) in ckanext-dcat).
   * `dcatapit_theme_group_mapper`: binds automatically a dataset to groups according to the themes in the dataset. 
     In the configuration file you'll need to specify a file containing the mapping between the themes and the groups:
      
         ckanext.dcatapit.theme_group_mapping.file=/path/to/your/file.ini
      
     The mapping ini file should have a section named `dcatapit:theme_group_mapping` and shall contain lines in the form:
      
         theme_key = group1 [, group2 ...]
	 
     a [sample file](https://github.com/geosolutions-it/ckanext-dcatapit/blob/master/examples/theme_to_group.ini) in examples directory of this project

   * `dcatapit_ckan_harvester`: a CKAN harvester that binds remote CKAN groups into local themes; that is, given a local
      group/themes mapping, if an harvested dataset belongs to a given remote group, the mapped themes will locally be added
      to the harvested dataset. You'll have to define the property:
      
         ckanext.dcatapit.nonconformant_themes_mapping.file = /path/to/your/group_to_theme_file
	 
      The plugin will accept both json and ini file. The use of the file at
          https://www.dati.gov.it/datigov/taxonomy/synonyms/topics.json
      is strongly recommended.

   * `dcatapit_harvest_list`: adds the page `/harvest/list`, which provides a summary of the status of all the catalog harvesters.
 
   * `dcatapit_harvester`: enables the RDF harvester.
     The `ckanext-dcatapit` RDF harvester also harvests localized fields in multiple languages, but to do that requires the ckanext-multilang installed.

   * `dcatapit_csw_harvester`: enhances the CSW harvester to be able to import some more fields related to DCAT.

   * `dcatapit_vocabulary`: allows to upload vocabularies from the admin pages.    
     You'll also need to define the property `ckan.dcatapit.eurovoc_location` to point to a local eurovoc file if you 
     want to load subtheme mappings.  

7. Enable the dcatapit profile adding the following configuration property in the ``production.ini`` file:

       ckanext.dcat.rdf.profiles = euro_dcat_ap it_dcat_ap

8. Configure the CKAN base URI as reported in the [dcat documentation](https://github.com/ckan/ckanext-dcat/blob/master/README.md#uris):

        ckanext.dcat.base_uri = YOUR_BASE_URI

9. Configure the geonames integration:
    
    * Create a geonames account (if you don't have one) at http://www.geonames.org/login ;
    * Enable the web services at http://www.geonames.org/manageaccount ;
    * Edit your CKAN config file (e.g. at ``/etc/ckan/default/production.ini``) and add the properties:

      * `geonames.username`: (mandatory) the username you registered in geonames;
      * `geonames.limits.countries`: (optional) limits the results to the requested country; use the ISO-3166 code (e.g. "IT" for Italy).

    By default the HTTP APIs service of geonames is configured (``http://api.geonames.org``). In order to set it to HTTPS the related [javascript configuration](https://github.com/geosolutions-it/ckanext-dcatapit/blob/4c8ec92baf1d8051c9e03f03c522b11026a09724/ckanext/dcatapit/fanstatic/jeoquery.js#L18) needs to be changed with the following:
    
        my.geoNamesApiServer = 'secure.geonames.org';
        my.geoNamesProtocol = 'https';
    
10. Initialize the CKAN DB with the mandatory table needed for localized vocabulary voices:

         ckan --config=/etc/ckan/default/production.ini dcatapit initdb

11. Update the Solr schema.xml file used by CKAN introducing the following element:

         <field name="dcat_theme" type="string" indexed="true" stored="false" multiValued="true"/>
         <field name="dcat_subtheme" type="string" indexed="true" stored="false" multiValued="true"/>
         <dynamicField name="dcat_subtheme_*" type="string" indexed="true" stored="false" multiValued="true"/>
         <dynamicField name="organization_region_*" type="string" indexed="true" stored="false" multiValued="true"/>
         <dynamicField name="resource_license_*" type="string" indexed="true" stored="false" multiValued="true"/>
         <field name="resource_license" type="string" indexed="true" stored="false" multiValued="true"/>
        
12. Restart Solr.

13. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

      `sudo service apache2 reload`
     
14. The controlled vocabularies (by EU and AgID) must be populated before start using the dcatapit plugin.    
    The files in the repository are processed versions of the official files.    
    Please refer to the [`README.files.md`](README.files.md) file for info about how these files 
    have been processed and how to regenerate them if needed.  

    Execute in sequence these commands:

         export CKAN_CONFIG=/etc/ckan/default/production.ini

         ckan -c /etc/ckan/default/ckan.ini dcatapit load --filename=vocabularies/languages-filtered.rdf

         ckan -c /etc/ckan/default/ckan.ini dcatapit load --filename=vocabularies/data-theme-filtered.rdf

         ckan -c /etc/ckan/default/ckan.ini dcatapit load --filename=vocabularies/places-filtered.rdf

         ckan -c /etc/ckan/default/ckan.ini dcatapit load --filename=vocabularies/frequencies-filtered.rdf

         ckan -c /etc/ckan/default/ckan.ini dcatapit load --filename=vocabularies/filetypes-filtered.rdf

         # curl https://raw.githubusercontent.com/italia/daf-ontologie-vocabolari-controllati/master/VocabolariControllati/territorial-classifications/regions/regions.rdf > regions.rdf
         # paster --plugin=ckanext-dcatapit vocabulary load --filename regions.rdf --name regions --config=/etc/ckan/default/production.ini

         ckan -c /etc/ckan/default/ckan.ini dcatapit load --filename vocabularies/theme-subtheme-mapping.rdf --eurovoc vocabularies/eurovoc-filtered.rdf
     
         ckan -c /etc/ckan/default/ckan.ini dcatapit load --filename vocabularies/licences.rdf


### Dataset reindexing after Organization change

Due to use of Organization's *region* field in dataset search facet, the catalogue should be reindexed in Solr if a *region* field value is changed for an organization (this is only needed if the `dcatapit_subcatalog_facets` plugin is enabled in order to have the Region facet updated and aligned to the Organization's setting in *region* fields)

        ckan --config=PATH_TO_INI_FILE search-index rebuild

### Dataset form

This extension improves look'n'feel of dataset edit form. Form inputs will be grouped into logical sets, and access is handled through tabs. 
    
<p align="center">
    <img src="docs/images/edit_form.png" alt="Dataset Form" title="Dataset Form" align="center">
</p>

By default, this improvement is enabled. You can disable it by setting `ckanext.dcatapit.form_tabs` config variable to `false`.

## Development Installation

To install `ckanext-dcatapit` for development, activate your CKAN virtualenv and do:

    git clone https://github.com/geosolutions-it/ckanext-dcatapit.git
    cd ckanext-dcatapit
    pip install -e .
    pip install -r dev-requirements.txt
    
## Running the Tests

To prepare the environment for running tests, follow instructions reported [here](http://docs.ckan.org/en/latest/contributing/test.html)
Then initialize the test database:

    cd /usr/lib/ckan/default/src/ckan
    ckan -c test-core.ini db init && ckan -c test.ini multilang initdb && ckan -c test.ini dcatapit initdb

Finally to run tests, do:

    cd /usr/lib/ckan/default/src/ckanext-dcatapit
    . /usr/lib/ckan/default/bin/activate
    
    pytest --ckan-ini=test.ini --cov=ckanext.dcatapit --cov-report=xml --cov-append --disable-warnings ckanext/dcatapit/tests

## DCAT_AP-IT CSW Harvester

The ckanext-dcatapit extension provides also a CSW harvester built on the **ckanext-spatial** extension, and inherits all of its functionalities. With this harvester you can harvest dcatapit dataset fields from the ISO metadata. The CSW harvester uses a default configuration usefull for populating mandatory fields into the source metadata, this json configuration can be customized into the harvest source form (please see the default one [here](https://github.com/geosolutions-it/ckanext-dcatapit/blob/master/ckanext/dcatapit/harvesters/csw_harvester.py#L54)). Below an example of the available configuration properties (for any configuration property not specified, the default one will be used):

    {
       "dcatapit_config":{
          "dataset_themes":[{"theme": "OP_DATPRO", "subthemes": []}],
          "dataset_places":"ITA_BZO",
          "dataset_languages":"{ITA,DEU}",
          "frequency":"UNKNOWN",
          "agents":{
             "publisher":{
                "code":"p_bz",
                "role":"publisher",
                "code_regex":{
                   "regex":"\\(([^)]+)\\:([^)]+)\\)",
                   "groups":[2]
                },
                "name_regex":{
                   "regex":"([^(]*)(\\(IPa[^)]*\\))(.+)",
                   "groups":[1, 3]
                }
             },
             "owner":{
                "code":"p_bz",
                "role":"owner",
                "code_regex":{
                   "regex":"\\(([^)]+)\\:([^)]+)\\)",
                   "groups":[2]
                },
                "name_regex":{
                   "regex":"([^(]*)(\\(IPa[^)]*\\))(.+)",
                   "groups":[1, 3]
                }
             },
             "author":{
                "code":"p_bz",
                "role":"author",
                "code_regex":{
                   "regex":"\\(([^)]+)\\:([^)]+)\\)",
                   "groups":[2]
                },
                "name_regex":{
                   "regex":"([^(]*)(\\(IPa[^)]*\\))(.+)",
                   "groups":[1, 3]
                }
             }
          },
          "controlled_vocabularies":{
             "dcatapit_skos_theme_id":"theme.data-theme-skos",
             "dcatapit_skos_places_id":"theme.places-skos"
          }
       }
    }

* ``dataset_themes``: default value to use for the dataset themes field if the thesaurus keywords are missing in the ISO metadata. The source metadata should have thesaurus keywords from the EU controlled vocabulary (data-theme-skos.rdf). Multiple values must be set between braces and comma separated values.

* ``dataset_places``: default value to use for the dataset geographical name field if the thesaurus keywords are missing in the ISO metadata. The source metadata should have thesaurus keywords from the EU controlled vocabulary (places-skos.rdf). Multiple values must be set between braces and comma separated values.

* ``dataset_languages``: default value to use for the dataset languages field. Metadata languages are harvested by the che ckanext-spatial extension (see the 'dataset-language' in iso_values). Internally the harvester map the ISO languages to the mdr vocabulary languages. The default configuration for that can be overridden in harvest source configuration by using an additional configuration property, like:

        "mapping_languages_to_mdr_vocabulary": {
            "ita': "ITA",
            "ger': "DEU",
            "eng': "ENG"
        }
        
* ``frequency``: default value to use for the dataset frequency field. Metadata frequencies are harvested by the che ckanext-spatial extension (see the 'frequency-of-update' in iso_values). Internally the harvester automatically map the ISO frequencies to the mdr vocabulary frequencies.

* ``agents``: Configuration for harvesting the dcatapit dataset agents from the responsible party metadata element. Below more details on the agent configuration:

         "publisher":{
            "code":"p_bz",      --> the IPA/IVA code to use as default for the agent identifier
            "role":"publisher", --> the responsible party role to harvest for this agent
            "code_regex":{      --> a regular expression to extrapolate a substring from the responsible party organization name
               "regex":"\\(([^)]+)\\:([^)]+)\\)",
               "groups":[2]     --> optional, dependes by the regular expression
            },
            "name_regex":{      --> a regular expression to extrapolate the IPA/IVA code from the responsible party organization name
               "regex":"([^(]*)(\\(IPA[^)]*\\))(.+)",
               "groups":[1, 3]  --> optional, dependes by the regular expression
            }
         }
     
* ``controlled_vocabularies``: To harvest 'dataset_themes' and 'dataset_places' the harvester needs to know the thesaurus ID or TITLE as specified into the source metadata.

**NOTES**: The default IPA code to use is extrapolated by the metadata identifier in respect to the RNDT specifications (ipa_code:UUID).
This represents a last fallback if the agent regex does not match any code and if the agent code has not been specified in configuration.

#### Harvest source configuration
In order to set the dcatapit CSW harvester:

1. Specify a valid csw endpoint in the URL field 
2. Specify a title and a description for the harvest source
3. Select 'DCAT_AP-IT CSW Harvester' as source type
4. Provide your own configuration to override the default one

### CSW Metadata Guidelines

* The dataset unique identifier will be harvested from the metadata fileIdentifier (see the above paragraph for additional notes about the IPA code).

* In order to harvest dcatapit dataset themes, the source metadata should have thesaurus keywords from the EU controlled vocabulary (data-theme-skos.rdf). Then the thesaurus identifier or title must be specified into the controlled_vocabularies->dcatapit_skos_theme_id configuration property

* In order to harvest dcatapit dataset geographical names, the source metadata should have thesaurus keywords from the EU controlled vocabulary (places-skos.rdf). Then the thesaurus identifier or title must be specified into the controlled_vocabularies->dcatapit_skos_places_id configuration property

* The dcatapit agents (publisher, holder, creator) will be harvested from the responsible party with the role specified in configuration (see 'agents' configuration property explained above)

* The dataset languages are harvested using the xpaths reported [here](https://github.com/ckan/ckanext-spatial/blob/master/ckanext/spatial/model/harvested_metadata.py#L723)

* The dataset frequency of update is harvested using the xpath reported [here](https://github.com/ckan/ckanext-spatial/blob/master/ckanext/spatial/model/harvested_metadata.py#L597)

## Test Instance and Validation

We have a test instance available at [this link](http://dcatapit.geo-solutions.it/) with a few sample datasets; a specific test dataset is available [here](http://dcatapit.geo-solutions.it/dataset/dcatapit-test-dataset).

If you want to test validation please use the online validator available [here](http://52.50.205.146:3031/dcat-ap_validator.html). To get no errors you should validate the entire catalog (e.g. [this link](http://dcatapit.geo-solutions.it/catalog.rdf)) if you validate a single dataset (e.g. using [this link](http://dcatapit.geo-solutions.it/dataset/dcatapit-test-dataset.rdf)) you will always get an error for "...missing catalog...".

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

Through this an additional schema field named `custom_text` will be added to the package schema and automatically managed by the dcatapit extension. Below a brief description of the fields properties that can be used:

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

### Creating a new translation

To create a new translation proceed as follow:

1. Extract new messages from your extension updating the pot file

       python setup.py extract_messages
     
2.  Create a translation file for your language (a po file) using the existing pot file in this plugin

        python setup.py init_catalog --locale YOUR_LANGUAGE

     Replace YOUR_LANGUAGE with the two-letter ISO language code (e.g. es, de).
     
3. Do the translation into the po file

4. Once the translation files (po) have been updated, either manually or via Transifex, compile them by running:

       python setup.py compile_catalog --locale YOUR_LANGUAGE
     
### Updating an existing translation

In order to update the existing translations proceed as follow:

1. Extract new messages from your extension updating the pot file

       python setup.py extract_messages
     
2. Update the strings in your po file, while preserving your po edits, by doing:

       python setup.py update_catalog --locale YOUR-LANGUAGE

3. Once the translation files (po) have been updated adding the new translations needed, compile them by running:

       python setup.py compile_catalog --locale YOUR_LANGUAGE


## Updating an existing installation

### Migration from 1.1.0 to 2.0.0

1. Dump of ckan and datastore databases (this is a safety measure)

2. Run the migration script:

       ckan -c $CONFIG_FILE dcatapit migrate-200

3. Update the DB:

       ckan -c $CONFIG_FILE db upgrade -p dcatapit_pkg
 
4. Reindex the datasets 

#### Migration details

The `theme` extra field is now required by the `ckanext-dcat` extension, and it's required to be a valid URI.

The `ckanext-dcatapit` extension used the `theme` field as a dict for holding information about multiple themes and
subthemes, and this content would conflict with the dcat one.

The migration will move the content from the `theme` extra field to the `themes_aggregate` field,
while the logic will provide on-the-fly valid content for the `theme` field so that `ckanext-dcat` will not complain.

The `db upgrade` will remove some harmful constraints in the vocabulary model.

### Migration from 1.0.0 to 1.1.0

In order to update an old installation (from 1.0.0 to 1.1.0 version):

1. Dump of ckan and datastore databases (this is a safety measure):

        su postgres
        pg_dump -U postgres -i ckan > ckan.dump
        pg_dump -U postgres -i datastore > datastore.dump

2. Update extension code:

        git pull

3. Update the Solr schema as reported in the installation steps and then restart Solr. In particular ensure that following fields are present in schema.xml:

        <field name="dcat_theme" type="string" indexed="true" stored="false" multiValued="true"/>
        <field name="dcat_subtheme" type="string" indexed="true" stored="false" multiValued="true"/>
        <dynamicField name="dcat_subtheme_*" type="string" indexed="true" stored="false" multiValued="true"/>
        <dynamicField name="organization_region_*" type="string" indexed="true" stored="false" multiValued="true"/>
        <dynamicField name="resource_license_*" type="string" indexed="true" stored="false" multiValued="true"/>
        <field name="resource_license" type="string" indexed="true" stored="false" multiValued="true"/>

4. Ensure that all the configuration properties required by the new version have been properly provided in .ini file (see [Installation](#installation) paragraph)

5. Activate the virtual environment:

        . /usr/lib/ckan/default/bin/activate
6. Run model update

        paster --plugin=ckanext-dcatapit vocabulary initdb --config=/etc/ckan/default/production.ini

7. Run vocabulary load commands (regions, licenses and sub-themes):

        wget "https://raw.githubusercontent.com/italia/daf-ontologie-vocabolari-controllati/master/VocabolariControllati/territorial-classifications/regions/regions.rdf" -O "/tmp/regions.rdf"
	
        paster --plugin=ckanext-dcatapit vocabulary load --filename "/tmp/regions.rdf" --name regions --config "/etc/ckan/default/production.ini"

        wget "https://raw.githubusercontent.com/italia/daf-ontologie-vocabolari-controllati/master/VocabolariControllati/licences/licences.rdf" -O "/tmp/licenses.rdf"
	
        paster --plugin=ckanext-dcatapit vocabulary load --filename "/tmp/licenses.rdf" --name licenses --config "/etc/ckan/default/production.ini"
        paster --plugin=ckanext-dcatapit vocabulary load --filename "ckanext-dcatapit/examples/eurovoc_mapping.rdf" --name subthemes --config "/etc/ckan/default/production.ini" "ckanext-dcatapit/examples/eurovoc.rdf"

8. Run data migration command:

        ckan -c CONFIG_FILE dcatapit migrate-110

You can review migration results by viewing `migration.log` file. It will contain list of messages generated during migration. 
There are additional command switches that can be used to optimize processing:

* `-l`/`--limit` - limit processing packages to given count of packages
* `-o`/`--offset` - start processing packages from given count offset
* `-s`/`--skip-orgs` - do not process organizations


Migration script will:
 * update all organizations and assign temporary identifier in form of `tmp_ipa_code_X` (where `X` is a number in sequence). Organization identifier is required field now, and thus temporary value is created to avoid errors in validation. Script will report each organization which have updated identifier in log with message similar to following: `org: [pab-foreste] PAB: Foreste : setting temporal identifier: tmp_ipa_code_1`

 * update all packages and migrate DCAT AP_IT fields. Where possible, it will try to transform those fields into new notation/format. Successful package data migration will be marked with message like this:

        ---------
        updating ortofoto-di-merano-2005
        ---------

  If migration is not possible for some reason, there will be a message like this:
  
	dataset test-dataset: the same temporal coverage start/end: 01-01-2014/01-01-2014, using start only
	dataset test-dataset: no identifier. generating new one
	dataset test-dataset: invalid modified date Manuelle. Using now timestamp
	updating b36e6f42-d0eb-4b53-8e41-170c50a2384c occupati-e-disoccupati
	---------
	
9. Rebuild Solr indexes:

		paster --plugin=ckan search-index rebuild -c /etc/ckan/default/production.ini
		
10. Restart Ckan

### Field conversion notes

- **conforms_to** is more complex structure now. It contains identifier, title and description. Converter will use old string value as an identifier of standard, and if multilang values are present, they will populate description subfield of standard. In case of multilang values present, Italian translation will be used as identifier.
- **creator** is a list of entities. It’s composed of *creator_name* and *creator_identifier*, and converter will use existing values (including multilang name)
- **temporal_coverage** is a list of entries, where each entry is constructed from two old fields: *temporal_start* and *temporal_end*. If both values are equal, only *temporal_start* will be used. Some values may not be parseable, and should be adjusted manually in dataset.
- **theme** is required now, so if dataset lacks theme(s), default one (*OP_DATPRO*) will be assigned. Subthemes will be empty.
- **identifier** is required now. If it’s missing, new one (*UUID*) will be generated.
- **modified** is required now. If it’s missing or invalid, current date will be used.
- **frequency** is required now. If it’s missing or invalid *UNKNOWN* value will be used.
- **holder_name** and **holder_identifier** behaves differently in new DCAT_AP-IT version. When dataset is created locally (wasn’t harvested), rights holder information is gathered directly from organization to which dataset belongs. Organization is the source of *holder_name* and *holder_identifier* fields (including multilang name). However, harvested datasets will preserve original holder information that is attached to dataset.
			
## Contributing

We welcome contributions in any form:

* pull requests for new features
* pull requests for bug fixes
* pull requests for documentation
* funding for any combination of the above

## Support, Communication and Credits
This work has been performed by [GeoSolutions](http://www.geo-solutions.it) with funding provided by Provincia Autonoma di Trento and Provincia Autonoma di Bolzano in a joint effort.

The work is provided as is and no warranty whatsoever is provided. There is a public Google Group for support questions available [here](https://groups.google.com/d/forum/ckanext-dcatapit) but beware that support through this channel will be given on a best effort basis.

Professional Support is available through our [Enterprise Support Services](http://www.geo-solutions.it/enterprise-support-services) offer. 
