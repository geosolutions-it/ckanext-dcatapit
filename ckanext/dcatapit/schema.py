#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ckanext.dcatapit.interfaces as interfaces

from ckan.common import _, ungettext
from ckan.plugins import PluginImplementations


def get_custom_config_schema(show=True):
    if show:
        return [
            {
                'name': 'ckanext.dcatapit_configpublisher_name',
                'validator': ['not_empty'],
                'element': 'input',
                'type': 'text',
                'label': _('Dataset Editor'),
                'placeholder': _('dataset editor'),
                'description': _('The responsible organization of the catalog'),
                'is_required': True
            },
            {
                'name': 'ckanext.dcatapit_configpublisher_code_identifier',
                'validator': ['not_empty'],
                'element': 'input',
                'type': 'text',
                'label': _('Catalog Organization Code'),
                'placeholder': _('IPA/IVA'),
                'description': _('The IVA/IPA code of the catalog organization'),
                'is_required': True
            },
            {
                'name': 'ckanext.dcatapit_config.catalog_issued',
                'validator': ['ignore_missing'],
                'element': 'input',
                'type': 'date',
                'label': _('Catalog Release Date'),
                'format': '%d-%m-%Y',
                'placeholder': _('catalog release date'),
                'description': _('The creation date of the catalog'),
                'is_required': False
            }
        ]
    else:
        return [
            {
                'name': 'ckanext.dcatapit_configpublisher_name',
                'validator': ['not_empty']
            },
            {
                'name': 'ckanext.dcatapit_configpublisher_code_identifier',
                'validator': ['not_empty']
            },
            {
                'name': 'ckanext.dcatapit_config.catalog_issued',
                'validator': ['ignore_missing']
            }
        ]


def get_custom_organization_schema():
    return [
        {
            'name': 'email',
            'validator': ['ignore_missing'],
            'element': 'input',
            'type': 'email',
            'label': _('EMail'),
            'placeholder': _('organization email'),
            'is_required': True
        },
        {
            'name': 'telephone',
            'validator': ['ignore_missing'],
            'element': 'input',
            'type': 'text',
            'label': _('Telephone'),
            'placeholder': _('organization telephone'),
            'is_required': False
        },
        {
            'name': 'site',
            'validator': ['ignore_missing'],
            'element': 'input',
            'type': 'url',
            'label': _('Site URL'),
            'placeholder': _('organization site url'),
            'is_required': False
        },
        {
            'name': 'identifier',
            'label': _('IPA/IVA'),
            'validator': ['ignore_missing'],
            'element': 'input',
            'type': 'text',
            'is_required': False,
            'placeholder': _('organization IPA/IVA code')
        }
    ]


def get_custom_package_schema():
    package_schema = [
        {
            'name': 'identifier',
            'validator': ['not_empty', 'dcatapit_id_unique'],
            'element': 'input',
            'type': 'text',
            'label': _('Dataset Identifier'),
            'placeholder': _('dataset identifier'),
            'is_required': True,
            'help': _(u"""E’ un codice identificativo univoco che si deve assegnare al dataset."""
                      u"""Si genera associando il codice IPA dell’organizzazione ad un codice """
                      u"""identificativo unico (UUID) generato sul sito https://www.uuidgenerator.net/ . """
                      u"""Questo sito genera, ogni volta che viene aperto, un codice alfanumerico unico """
                      u"""e irripetibile. E’ pertanto sufficiente aprire il sito e copiare il codice """
                      u"""che compare in alto. Riportare il codice ottenuto nella forma IPA:UUID.""")
        },
        {
            'name': 'alternate_identifier',
            'validator': ['ignore_missing', 'no_number', 'dcatapit_alternate_identifier'],
            'element': 'alternate_identifier',
            'type': 'text',
            'label': _('Other Identifier'),
            'placeholder': _('other identifier'),
            'is_required': False,
            'help': _(u"""Specificare, se utile, uno o più identificativi """
                      u"""secondari per il dataset. Per esempio, un identificativo """
                      u"""disponibile nel sistema da cui il dato è estratto."""),
        },
        {
            'name': 'theme',
            'validator': ['not_empty'],
            'element': 'theme',
            'type': 'vocabulary',
            'vocabulary_name': 'eu_themes',
            'label': _('Dataset Themes'),
            'placeholder': _('eg. education, agriculture, energy'),
            'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=eu_themes&incomplete=?',
            'is_required': True,
            'help': _(u"""Assegnare al dataset uno o più temi che descrivano l'ambito in cui si colloca, """
                      u"""scegliendo tra quelli proposti nel menù a tendina. I temi proposti sono quelli """
                      u"""definiti nel vocabolario Europeo sui Temi per i cataloghi che contengono dataset.""")
        },
        {
            'name': 'publisher',
            'element': 'couple',
            'label': _('Dataset Editor'),
            'is_required': True,
            'couples': [
                {
                    'name': 'publisher_name',
                    'validator': ['not_empty'],
                    'label': _('Name'),
                    'type': 'text',
                    'placeholder': _('publisher name'),
                    'localized': True
                },
                {
                    'name': 'publisher_identifier',
                    'validator': ['not_empty'],
                    'label': _('IPA/IVA'),
                    'type': 'text',
                    'placeholder': _('publisher identifier')
                }
            ],
            'help': _(u"""L’organizzazione (o pubblica amministrazione) che rende disponibile il dataset, """
                      u"""pubblicandolo. Vanno indicati sia il nome che il codice identificativo """
                      u"""dell'organizzazione. Non inserire nomi di singole persone. Nel caso della Provincia """
                      u"""autonoma di Trento andrà indicato il codice IPA della PAT associato al codice """
                      u"""dell’ufficio/servizio/dipartimento che rende disponibile il dataset.""")
        },
        {
            'name': 'issued',
            'validator': ['ignore_missing'],
            'element': 'input',
            'type': 'date',
            'label': _('Release Date'),
            'format': '%d-%m-%Y',
            'placeholder': _('release date'),
            'is_required': False,
            'help': _(u"""E' la data in cui il dataset è reso disponibile la prima volta. """
                      u"""Si sceglie dal calendario che viene proposto.""")
        },
        {
            'name': 'modified',
            'validator': ['not_empty'],
            'element': 'input',
            'type': 'date',
            'label': _('Modification Date'),
            'format': '%d-%m-%Y',
            'placeholder': _('modification date'),
            'is_required': True,
            'help': _(u"""E' la data dell'ultima modifica o dell'ultimo aggiornamento del dataset. """
                      u"""Si sceglie dal calendario che viene proposto. In caso di aggiornamento """
                      u"""continuo/quotidiano o comunque molto frequente inserire la data di ultima """
                      u"""modifica sostanziale del dataset.""")
        },
        {
            'name': 'geographical_name',
            'validator': ['ignore_missing'],
            'element': 'theme',
            'type': 'vocabulary',
            'vocabulary_name': 'places',
            'label': _('Geographical Name'),
            'placeholder': _('geographical name'),
            'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=places&incomplete=?',
            'is_required': False,
            'default': _('Organizational Unit Responsible Competence Area'),
            'help': _(u"""E' l'area geografica coperta dal dataset; scegliere tra quelle proposte, """
                      u"""che fanno riferimento al "tabella europea dei luoghi" (table of places)""")
        },
        {
            'name': 'geographical_geonames_url',
            'validator': ['ignore_missing'],
            'element': 'input',
            'type': 'url',
            'label': _('GeoNames URL'),
            'placeholder': _('http://www.geonames.org/3175395'),
            'is_required': False,
            'help': _(u"""Questa proprietà si riferisce ai riferimenti spaziali dell’area geografica """
                      u"""di pertinenza del dataset ed utilizza una URI (Uniform Resource Identifier). """
                      u"""L’URI da inserire si ottiene sul sito http://www.geonames.org/"""
                      u"""Nel caso di dataset che interessano contemporaneamente più comuni, utilizzare """
                      u"""l'area ""Provincia di Trento"".""")
        },
        {
            'name': 'language',
            'validator': ['ignore_missing'],
            'element': 'theme',
            'type': 'vocabulary',
            'vocabulary_name': 'languages',
            'label': _('Dataset Languages'),
            'placeholder': _('eg. italian, german, english'),
            'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=languages&incomplete=?',
            'is_required': False,
            'help': _(u"""Indicare una o più lingue utilizzate nel dataset, scegliendo tra quelle proposte """
                      u"""nel menù a tendina (italiano, tedesco, inglese).""")
        },
        {
            'name': 'temporal_coverage',
            'element': 'temporal_coverage',
            'label': _('Temporal Coverage'),
            'validator': ['ignore_missing', 'dcatapit_temporal_coverage'],
            'is_required': False,
            '_couples': [
                {
                    'name': 'temporal_start',
                    'label': _('Start Date'),
                    'validator': ['ignore_missing'],
                    'type': 'date',
                    'format': '%d-%m-%Y',
                    'placeholder': _('temporal coverage')
                },
                {
                    'name': 'temporal_end',
                    'label': _('End Date'),
                    'validator': ['ignore_missing'],
                    'type': 'date',
                    'format': '%d-%m-%Y',
                    'placeholder': _('temporal coverage')
                }
            ],

            'help': _(u"""Inserire, se pertinente, la data di inizio e di fine del periodo """
                      u"""a cui si riferiscono i dati del dataset.""")
        },

        {
            'name': 'rights_holder',
            'element': 'couple',
            'label': _('Rights Holder'),
            'is_required': False,
            'read_only': True,
            'couples': [
                {
                    'name': 'holder_name',
                    'label': _('Name'),
                    'validator': ['ignore_missing'],
                    'type': 'text',
                    'placeholder': _('rights holder of the dataset'),
                    'localized': True

                },
                {
                    'name': 'holder_identifier',
                    'label': _('IPA/IVA'),
                    'validator': ['ignore_missing'],
                    'type': 'text',
                    'placeholder': _('rights holder of the dataset')
                }
            ],
            'help': _(u"""E' l’organizzazione (o pubblica amministrazione) che detiene la titolarità dei dati ed """
                      u"""è quindi responsabile della gestione complessiva del dataset. Si raccomanda di evitare """
                      u"""l’inserimento di nomi di singole persone. Vanno inseriti il nome e il codice """
                      u"""identificativo dell’organizzazione.""")
        },
        {
            'name': 'frequency',
            'validator': ['not_empty'],
            'element': 'select',
            'type': 'vocabulary',
            'vocabulary_name': 'frequencies',
            'label': _('Frequency'),
            'placeholder': _('accrual periodicity'),
            'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=frequencies&incomplete=?',
            'is_required': True,
            'help': _(u"""Frequenza temporale con cui il dataset viene aggiornato; scegliere tra quelle proposte """
                      u"""che fanno riferimento al vocabolario Europeo sulle frequenze""")
        },
        {
            'name': 'is_version_of',
            'validator': ['ignore_missing'],
            'element': 'input',
            'type': 'url',
            'label': _('Version Of'),
            'placeholder': _('is version of a related dataset URI'),
            'is_required': False,
            'help': _(u"""Questa proprietà si può utilizzare se il dataset è un adattamento o una nuova versione """
                      u"""di un dataset già pubblicato e descritto. Per esempio, se si vuole inserire una nuova """
                      u"""versione 2.0 di un dataset già presente nel catalogo (con versione 1.0) si richiede """
                      u"""di indicare il riferimento al dataset già incluso nel catalogo. Generalmente, si """
                      u"""sconsiglia fortemente di creare nuovi dataset per piccoli cambiamenti. E’ invece """
                      u"""consigliato definire nuovi dataset solo in presenza di cambiamenti significativi """
                      u"""rispetto a precedenti versioni (e.g., nuovi elementi inclusi, adattamenti significativi """
                      u"""di alcuni elementi, ecc). Perr fare riferimento al dataset di riferimento, inserire """
                      u"""l'identificativo del dataset stesso.""")
        },
        {
            'name': 'conforms_to',
            'validator': ['ignore_missing', 'dcatapit_conforms_to'],
            'element': 'conforms_to',
            'type': 'conforms_to',
            'label': _('Conforms To'),
            'placeholder': _('conforms to'),
            'is_required': False,
            'help': _(u"""Questa proprietà si riferisce a una regola implementativa o altra specifica """
                      u"""a cui il dataset è conforme. Si possono specificare uno o più standard, sia tecnici """
                      u"""(anche de-facto) come per esempio DCAT, ISO/IEC 25012, CSW, ecc., sia riferimenti """
                      u"""normativi (e.g., Decreto legislativo n.82/2005 - Codice dell’Amministrazione Digitale).""")
        },

	    {
		    'name': 'creator',
		    'element': 'creator',
		    'label': _('Creator'),
            'type': 'creator',
            'placeholder': '-',
            'validator': ['ignore_missing', 'dcatapit_creator'],
            'is_required': False,
            '_couples': [
                {
                    'name': 'creator_name',
                    'label': _('Name'),
                    'validator': ['ignore_missing'],
                    'type': 'text',
                    'placeholder': _('creator of the dataset'),
                    'localized': True
                },
                {
                    'name': 'creator_identifier',
                    'label': _('IPA/IVA'),
                    'validator': ['ignore_missing'],
                    'type': 'text',
                    'placeholder': _('creator of the dataset')
                }
            ],
            'help': _(u"""Questa proprietà si riferisce a una o più entità (organizzazione) """
                      u"""che hanno materialmente creato il dataset. Se l'editore non l’ha prodotto, """
                      u"""si può indicare l’organizzazione (o pubblica amministrazione) che ha materialmente """
                      u"""prodotto il dataset come creatore. Si raccomanda di evitare l’inserimento di nomi di """
                      u"""singole persone."""
                      u"""Nel caso in cui editore e creatore del dataset coincidano, allora si può omettere questa """
                      u""" proprietà. Vanno inseriti il nome dell'organizzazione e il suo codice identificativo.""")
        }
    ]


    for plugin in PluginImplementations(interfaces.ICustomSchema):
        extra_schema = plugin.get_custom_schema()

        for extra in extra_schema:
            extra['external'] = True

        package_schema = package_schema + extra_schema

    return package_schema

def get_custom_resource_schema():
    return [
         {
            'name': 'distribution_format',
            'validator': ['ignore_missing'],
            'element': 'select',
            'type': 'vocabulary',
            'vocabulary_name': 'filetype',
            'label': _('Distribution Format'),
            'placeholder': _('distribution format'),
            'data_module_source': '/api/2/util/vocabulary/autocomplete?vocabulary_id=filetype&incomplete=?',
            'is_required': False
        },
        {
            'name': 'license_type',
            'validator': ['ignore_missing'],
            'element': 'licenses_tree',
            'label': _('License'),
            'placeholder': _('license type'),
            'is_required': True,
            'help': _(u"""Questa proprietà si riferisce alla licenza con cui viene """
                      u"""pubblicato il dataset. Scegliere una delle due licenze """
                      u"""Creative Commons proposte.""")
        }
    ]
