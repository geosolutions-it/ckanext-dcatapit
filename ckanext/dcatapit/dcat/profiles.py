
import json
import ast
import logging
import datetime

from ckan.lib.base import config

from rdflib.namespace import Namespace, RDF, SKOS
from rdflib import URIRef, BNode, Literal

import ckan.logic as logic

from ckan.lib.i18n import get_locales
from ckanext.dcat.profiles import RDFProfile, DCAT, LOCN, VCARD, DCT, FOAF, ADMS, OWL, SCHEMA
from ckanext.dcat.utils import catalog_uri, dataset_uri, resource_uri

import ckanext.dcatapit.interfaces as interfaces
import ckanext.dcatapit.helpers as helpers
from ckanext.dcatapit.model.subtheme import Subtheme


DCATAPIT = Namespace('http://dati.gov.it/onto/dcatapit#')

it_namespaces = {
    'dcatapit': DCATAPIT,
}

THEME_BASE_URI = 'http://publications.europa.eu/resource/authority/data-theme/'
LANG_BASE_URI = 'http://publications.europa.eu/resource/authority/language/'
FREQ_BASE_URI = 'http://publications.europa.eu/resource/authority/frequency/'
FORMAT_BASE_URI = 'http://publications.europa.eu/resource/authority/file-type/'
GEO_BASE_URI = 'http://publications.europa.eu/resource/authority/place/'

# vocabulary name, base URI
THEME_CONCEPTS = ('eu_themes', THEME_BASE_URI)
LANG_CONCEPTS = ('languages', LANG_BASE_URI)
GEO_CONCEPTS = ('places', GEO_BASE_URI)
FREQ_CONCEPTS = ('frequencies', FREQ_BASE_URI)
FORMAT_CONCEPTS = ('filetype', FORMAT_BASE_URI)

DEFAULT_VOCABULARY_KEY = 'OP_DATPRO'
DEFAULT_THEME_KEY = DEFAULT_VOCABULARY_KEY
DEFAULT_FORMAT_CODE = DEFAULT_VOCABULARY_KEY
DEFAULT_FREQ_CODE = 'UNKNOWN'
DEFAULT_LANG = config.get('ckan.locale_default', 'en')

LOCALISED_DICT_NAME_BASE = 'DCATAPIT_MULTILANG_BASE'
LOCALISED_DICT_NAME_RESOURCES = 'DCATAPIT_MULTILANG_RESOURCES'
OFFERED_LANGS = get_locales()

lang_mapping_ckan_to_voc = {
    'it': 'ITA',
    'de': 'DEU',
    'en': 'ENG',
    'en_GB': 'ENG',
    'fr': 'FRA',
}

lang_mapping_xmllang_to_ckan = {
    'it' : 'it',
    'de' : 'de',
    'en' : 'en_GB' ,
    'fr' : 'fr',
}

lang_mapping_ckan_to_xmllang = {
    'en_GB' : 'en' ,
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
    'ZIP': 'OP_DATPRO', # requires to be more specific, can't infer

}


log = logging.getLogger(__name__)

class ItalianDCATAPProfile(RDFProfile):
    '''
    An RDF profile for the Italian DCAT-AP recommendation for data portals
    It requires the European DCAT-AP profile (`euro_dcat_ap`)
    '''

    def parse_dataset(self, dataset_dict, dataset_ref):

        # check the dataset type
        if (dataset_ref, RDF.type, DCATAPIT.Dataset) not in self.g:
            # not a DCATAPIT dataset
            return dataset_dict

        # date info
        for predicate, key, logf in (
                (DCT.issued, 'issued', log.debug),
                (DCT.modified, 'modified', log.warn),
                ):
            value = self._object_value(dataset_ref, predicate)
            if value:
                self._remove_from_extra(dataset_dict, key)

                value = helpers.format(value, '%Y-%m-%d', 'date')
                dataset_dict[key] = value
            else:
                logf('No %s found for dataset "%s"', predicate, dataset_dict.get('title', '---'))

        # 0..1 predicates
        for predicate, key, logf in (
                (DCT.identifier, 'identifier', log.warn),
                ):
            value = self._object_value(dataset_ref, predicate)
            if value:
                self._remove_from_extra(dataset_dict, key)
                dataset_dict[key] = value
            else:
                logf('No %s found for dataset "%s"', predicate, dataset_dict.get('title', '---'))

        # 0..n predicates list
        for predicate, key, logf in (
                (DCT.isVersionOf, 'is_version_of', log.debug),
                ):
            valueList = self._object_value_list(dataset_ref, predicate)
            if valueList:
                self._remove_from_extra(dataset_dict, key)
                value = ','.join(valueList)
                dataset_dict[key] = value
            else:
                logf('No %s found for dataset "%s"', predicate, dataset_dict.get('title', '---'))

        alternate_identifiers = self.g.objects(dataset_ref, ADMS.identifier)
        alt_ids = []
        for alt_id in alternate_identifiers:
            alternate_id = self._alternate_id(dataset_ref, alt_id)
            if alternate_id:
                alt_ids.append(alternate_id)
        dataset_dict['alternate_identifier'] = json.dumps(alt_ids)


        # conformsTo
        self._remove_from_extra(dataset_dict, 'conforms_to')
        conform_list = []
        for conforms_to in self.g.objects(dataset_ref, DCT.conformsTo):
            conform_list.append(self._conforms_to(conforms_to))
        if conform_list:
            dataset_dict['conforms_to'] = json.dumps(conform_list)
        else:
            log.debug('No DCT.conformsTo found for dataset "%s"', dataset_dict.get('title', '---'))

        # Temporal
        temporal_coverage = self._get_temporal_coverage(dataset_ref)
        if temporal_coverage:
            dataset_dict['temporal_coverage'] = json.dumps(temporal_coverage)
        
        #start, end = self._time_interval(dataset_ref, DCT.temporal)

        # URI 0..1
        for predicate, key, base_uri in (
                (DCT.accrualPeriodicity, 'frequency', FREQ_BASE_URI),
                ):
            valueRef = self._object_value(dataset_ref, predicate)
            if valueRef:
                self._remove_from_extra(dataset_dict, key)
                value = self._strip_uri(valueRef, base_uri)
                dataset_dict[key] = value
            else:
                log.warn('No %s found for dataset "%s"', predicate, dataset_dict.get('title', '---'))

        # URI lists
        for predicate, key, base_uri in (
                (DCT.language, 'language', LANG_BASE_URI),
                ):
            self._remove_from_extra(dataset_dict, key)
            valueRefList = self._object_value_list(dataset_ref, predicate)
            valueList = [self._strip_uri(valueRef, base_uri) for valueRef in valueRefList]
            value = ','.join(valueList)
            if len(valueList) > 1:
                value = '{'+value+'}'
            dataset_dict[key] = value

        self._parse_themes(dataset_dict, dataset_ref)

        # Spatial
        spatial_tags = []
        geonames_url = None

        for spatial in self.g.objects(dataset_ref, DCT.spatial):
           for spatial_literal in self.g.objects(spatial, DCATAPIT.geographicalIdentifier):
               spatial_value = spatial_literal.value
               if GEO_BASE_URI in spatial_value:
                   spatial_tags.append(self._strip_uri(spatial_value, GEO_BASE_URI))
               else:
                   if geonames_url:
                       log.warn("GeoName URL is already set to %s, value %s will not be imported", geonames_url, spatial_value)
                   else:
                       geonames_url = spatial_value

        if len(spatial_tags) > 0:
            value = ','.join(spatial_tags)
            if len(spatial_tags) > 1:
                value = '{'+value+'}'
            dataset_dict['geographical_name'] = value

        if geonames_url:
            dataset_dict['geographical_geonames_url'] = geonames_url

        ### Collect strings from multilang fields

        # { 'field_name': {'it': 'italian loc', 'de': 'german loc', ...}, ...}
        localized_dict = {}

        for key, predicate in (
                ('title', DCT.title),
                ('notes', DCT.description),
                ):
            self._collect_multilang_strings(dataset_dict, key, dataset_ref, predicate, localized_dict)

        # Agents
        for predicate, basekey in (
                (DCT.publisher, 'publisher'),
                (DCT.rightsHolder, 'holder'),
                # for backward compatibility only,
                # new format is handled with self._parse_creators() below
                (DCT.creator, 'creator'),
                ):
            agent_dict, agent_loc_dict = self._parse_agent(dataset_ref, predicate, basekey)
            for key,v in agent_dict.iteritems():
                self._remove_from_extra(dataset_dict, key)
                dataset_dict[key] = v
            localized_dict.update(agent_loc_dict)

        creators = self._parse_creators(dataset_ref)

        # use data from old method to populate new format
        from_old = {}
        if dataset_dict.get('creator_name'):
            from_old['creator_name'] = {DEFAULT_LANG: dataset_dict['creator_name']}
        if dataset_dict.get('creator_identifier'):
            from_old['creator_identifier'] = dataset_dict['creator_identifier']
    
        # do not add old format if the same identifier is in new data
        # this will avoid duplicates in re-harvesting
        from_old_add = False
        if from_old:
            from_old_add = True
            if from_old.get('creator_identifier'):
                for cr in creators:
                    cid = cr.get('creator_identifier')
                    if cid is None:
                        continue
                    if cid == from_old['creator_identifier']:
                        from_old_add = False
                        break
        if from_old_add:
            creators.append(from_old)
        dataset_dict['creator'] = json.dumps(creators)

        # when all localized data have been parsed, check if there really any and add it to the dict
        if len(localized_dict) > 0:
            log.debug('Found multilang metadata')
            dataset_dict[LOCALISED_DICT_NAME_BASE] = localized_dict

        ### Resources

        resources_loc_dict = {}

        # In ckan, the license is a dataset property, not resource's
        # We'll collect all of the resources' licenses, then we will postprocess them
        licenses = [] #  contains tuples (url, name)

        for resource_dict in dataset_dict.get('resources', []):
            resource_uri = resource_dict['uri']
            if not resource_uri:
                log.warn("URI not defined for resource %s", resource_dict['name'])
                continue

            distribution = URIRef(resource_uri)
            if not (dataset_ref, DCAT.distribution, distribution) in self.g:
                log.warn("Distribution not found in dataset %s", resource_uri)
                continue

            # fix the CKAN resource's url set by the dcat extension
            resource_dict['url'] = (self._object_value(distribution, DCAT.downloadURL) or
                                    self._object_value(distribution, DCAT.accessURL))

            # URI 0..1
            for predicate, key, base_uri in (
                    (DCT['format'], 'format', FORMAT_BASE_URI), # Format
                    ):
                valueRef = self._object_value(distribution, predicate)
                if valueRef:
                    value = self._strip_uri(valueRef, base_uri)
                    resource_dict[key] = value
                else:
                    log.warn('No %s found for resource "%s"::"%s"',
                             predicate,
                             dataset_dict.get('title', '---'),
                             resource_dict.get('name', '---'))

            # License
            license = self._object(distribution, DCT.license)
            if license:

                license_uri = unicode(license)
                license_dct = self._object_value(license, DCT.type)
                license_names = self.g.objects(license, FOAF.name) # may be either the title or the id
                license_version = self._object_value(license, FOAF.versionInfo)

                names = {}
                prefname = None
                for l in license_names:
                    if l.language:
                        names[l.language] = unicode(l)
                    else:
                        prefname = unicode(l)
                
                license_type = interfaces.get_license_from_dcat(license_uri,
                                                                license_dct,
                                                                prefname,
                                                                **names)
                if license_version and unicode(license_version) != license_type.version:
                    log.warn("License version mismatch between %s and %s", license_versions, license_type.version)
                    
                resource_dict['license_type'] = license_type.uri
                try:
                    license_name = names['it']
                except KeyError:
                    try:
                        license_name = names['en']
                    except KeyError:
                        license_name = names.values()[0] if names else license_type.default_name
                    
                log.info("Setting lincense %s %s %s", license_type.uri, license_name, license_type.document_uri)
                    
                licenses.append((license_type.uri, license_name, license_type.document_uri))
            else:
                log.warn('No license found for resource "%s"::"%s"',
                         dataset_dict.get('title', '---'),
                         resource_dict.get('name', '---'))

            # Multilang
            loc_dict = {}

            for key, predicate in (
                    ('name', DCT.title),
                    ('description', DCT.description),
                    ):
                self._collect_multilang_strings(resource_dict, key, distribution, predicate, loc_dict)

            if len(loc_dict) > 0:
                log.debug('Found multilang metadata in resource %s', resource_dict['name'])
                resources_loc_dict[resource_uri] = loc_dict

        if len(resources_loc_dict) > 0:
            log.debug('Found multilang metadata in resources')
            dataset_dict[LOCALISED_DICT_NAME_RESOURCES] = resources_loc_dict

        # postprocess licenses
        # license_ids = {id for url,id in licenses}  # does not work in python 2.6
        license_ids = set()
        for lic_uri, id, doc_uri in licenses:
           license_ids.add(id)

        if len(license_ids) == 1:
            dataset_dict['license_id'] = license_ids.pop()
            # TODO Map to internally defined licenses
        else:            
            log.warn('%d licenses found for dataset "%s"', len(license_ids), dataset_dict.get('title', '---'))
            dataset_dict['license_id'] = 'notspecified'

        return dataset_dict

    def _collect_multilang_strings(self, base_dict, key, subj, pred, loc_dict):
        '''
        Search for multilang Literals matching (subj, pred).
        - Literals not localized will be stored as source_dict[key] -- possibly replacing the value set by the EURO parser
        - Localized literals will be stored into target_dict[key][lang]
        '''

        for obj in self.g.objects(subj, pred):
            value = obj.value
            lang = obj.language
            if not lang:
                # force default value in dataset
                base_dict[key] = value
            else:
                # add localized string
                lang_dict = loc_dict.setdefault(key, {})
                lang_dict[lang_mapping_xmllang_to_ckan.get(lang)] = value

    def _parse_themes(self, dataset, ref):
        self._remove_from_extra(dataset, 'theme')
        themes = list(self.g.objects(ref, DCAT.theme))
        subthemes = list(self.g.objects(ref, DCT.subject))
        out = []
        for t in themes:
            theme_name = str(t).split('/')[-1]
            try:
                subthemes_for_theme = Subtheme.for_theme_values(theme_name)
            except ValueError, err:
                subthemes_for_theme = []

            row = {'theme': theme_name,
                   'subthemes': []}
            for subtheme in subthemes:
                s = str(subtheme)
                if s in subthemes_for_theme:
                    row['subthemes'].append(s)
            out.append(row)

        dataset['theme'] = json.dumps(out)


    def _remove_from_extra(self, dataset_dict, key):

        #  search and replace
        for extra in dataset_dict.get('extras', []):
            if extra['key'] == key:
                dataset_dict['extras'].pop(dataset_dict['extras'].index(extra))
                return

    def _add_or_replace_extra(self, dataset_dict, key, value):

        #  search and replace
        for extra in dataset_dict.get('extras', []):
            if extra['key'] == key:
                extra['value'] = value
                return

        # add if not found
        dataset_dict['extras'].append({'key': key, 'value': value})

    def _set_temporal_coverage(self, graph, dataset_dict, dataset_ref):
        g = graph
        d = dataset_dict
        
        # clean from dcat's data, to avoid duplicates
        for obj in g.objects(dataset_ref, DCT.temporal):
            g.remove((dataset_ref, DCT.temporal, obj,))

        temp_cov = dataset_dict.get('temporal_coverage')

        if temp_cov:
            temp_cov = json.loads(temp_cov)
        else:
            temp_cov = []
        
        if d.get('temporal_start') or d.get('temporal_end'):
            temp_cov.append({'temporal_start': d['temporal_start'],
                             'temporal_end': d['temporal_end']})
        if not temp_cov:
            return

        for tc in temp_cov:
            start = tc['temporal_start']
            end = tc['temporal_end']
            temporal_extent = BNode()
            g.add((temporal_extent, RDF.type, DCT.PeriodOfTime))
            _added = False
            if start:
                _added = True
                self._add_date_triple(temporal_extent, SCHEMA.startDate, start)
            if end:
                _added = True
                self._add_date_triple(temporal_extent, SCHEMA.endDate, end)
            if _added:
                g.add((dataset_ref, DCT.temporal, temporal_extent))

    def _get_temporal_coverage(self, dataset_ref):
        pred = DCT.temporal
        out = []
        
        for interval in self.g.objects(dataset_ref, pred):
            # Fist try the schema.org way
            start = self._object_value(interval, SCHEMA.startDate)
            end = self._object_value(interval, SCHEMA.endDate)
            if start or end:
                out.append({'temporal_start': start,
                            'temporal_end': end})
                continue
            start_nodes = [t for t in self.g.objects(interval,
                                                     TIME.hasBeginning)]
            end_nodes = [t for t in self.g.objects(interval,
                                                   TIME.hasEnd)]
            if start_nodes:
                start = self._object_value(start_nodes[0],
                                                TIME.inXSDDateTime)
            if end_nodes:
                end = self._object_value(end_nodes[0],
                                              TIME.inXSDDateTime)

            if start or end:
                out.append({'temporal_start': start,
                            'temporal_end': end})

        return out

    def _conforms_to(self, conforms_id):
        ref_docs = [ unicode(val) for val in self.g.objects(conforms_id, DCATAPIT.referenceDocumentation)]

        out = {'identifier': unicode(self.g.value(conforms_id, DCT.identifier)),
               'title': {},
               'description': {},
               'referenceDocumentation': ref_docs}
        if isinstance(conforms_id, (URIRef, Literal,)):
            out['uri'] = unicode(conforms_id)

        for t in self.g.objects(conforms_id, DCT.title):
            out['title'][t.language] = unicode(t)

        for t in self.g.objects(conforms_id, DCT.description):
            out['description'][t.language] = unicode(t)

        return out

    def _alternate_id(self, dataset_ref, alt_id):
        out = {}
        identifier = self.g.value(alt_id, SKOS.notation)

        if not identifier:
            return out

        out['identifier'] = unicode(identifier)

        predicate, basekey = DCT.creator, 'creator'
        agent_dict, agent_loc_dict = self._parse_agent(alt_id, predicate, basekey)
        agent = {}
        for k, v in agent_dict.items():
            new_k = 'agent_{}'.format(k[len(basekey)+1:])
            agent[new_k] = v
        
        out['agent'] = agent
        if agent_loc_dict.get('creator_name'):
            out['agent']['agent_name'] = agent_loc_dict['creator_name']
        
        return out
    def _parse_creators(self, dataset_ref):
        out = []
        for cref in self.g.objects(dataset_ref, DCT.creator):
            creator = {}
            creator['creator_identifier'] = self._object_value(cref, DCT.identifier)
            creator_name = {}
            for obj in self.g.objects(cref, FOAF.name):
                if obj.language:
                    creator_name[unicode(obj.language)] = unicode(obj)
                else:
                    creator_name[DEFAULT_LANG] = unicode(obj)
            creator['creator_name'] = creator_name
            out.append(creator) 
        return out

    def _parse_agent(self, subject, predicate, base_name):

        agent_dict = {}
        loc_dict= {}

        for agent in self.g.objects(subject, predicate):
            agent_dict[base_name + '_identifier'] = self._object_value(agent, DCT.identifier)
            self._collect_multilang_strings(agent_dict, base_name + '_name', agent, FOAF.name, loc_dict)

        return agent_dict, loc_dict

    def _strip_uri(self, value, base_uri):
        return value.replace(base_uri, '')

    def graph_from_dataset(self, dataset_dict, dataset_ref):

        title = dataset_dict.get('title')
        
        g = self.g

        for prefix, namespace in it_namespaces.iteritems():
            g.bind(prefix, namespace)

        ### add a further type for the Dataset node
        g.add((dataset_ref, RDF.type, DCATAPIT.Dataset))

        ### replace themes
        value = self._get_dict_value(dataset_dict, 'theme')
        self._add_themes(dataset_ref, value)

        ### replace languages
        value = self._get_dict_value(dataset_dict, 'language')
        if value:
            for lang in value.split(','):
                self.g.remove((dataset_ref, DCT.language, Literal(lang)))
                lang = lang.replace('{','').replace('}','')
                self.g.add((dataset_ref, DCT.language, URIRef(LANG_BASE_URI + lang)))
                # self._add_concept(LANG_CONCEPTS, lang)

        ### add spatial (EU URI)
        value = self._get_dict_value(dataset_dict, 'geographical_name')
        if value:
            for gname in value.split(','):
                gname = gname.replace('{','').replace('}','')

                dct_location = BNode()
                self.g.add((dataset_ref, DCT.spatial, dct_location))

                self.g.add((dct_location, RDF['type'], DCT.Location))

                # Try and add a Concept from the spatial vocabulary
                if self._add_concept(GEO_CONCEPTS, gname):
                    self.g.add((dct_location, DCATAPIT.geographicalIdentifier, Literal(GEO_BASE_URI + gname)))

                    # geo concept is not really required, but may be a useful adding
                    self.g.add((dct_location, LOCN.geographicalName, URIRef(GEO_BASE_URI + gname)))
                else:
                    # The dataset field is not a controlled tag, let's create a Concept out of the label we have
                    concept = BNode()
                    self.g.add((concept, RDF['type'], SKOS.Concept))
                    self.g.add((concept, SKOS.prefLabel, Literal(gname)))
                    self.g.add((dct_location, LOCN.geographicalName, concept))

        ### add spatial (GeoNames)
        value = self._get_dict_value(dataset_dict, 'geographical_geonames_url')
        if value:
            dct_location = BNode()
            self.g.add((dataset_ref, DCT.spatial, dct_location))

            self.g.add((dct_location, RDF['type'], DCT.Location))
            self.g.add((dct_location, DCATAPIT.geographicalIdentifier, Literal(value)))

        ### replace periodicity
        self._remove_node(dataset_dict, dataset_ref,  ('frequency', DCT.accrualPeriodicity, None, Literal))
        self._add_uri_node(dataset_dict, dataset_ref, ('frequency', DCT.accrualPeriodicity, DEFAULT_FREQ_CODE, URIRef), FREQ_BASE_URI)
        # self._add_concept(FREQ_CONCEPTS, dataset_dict.get('frequency', DEFAULT_VOCABULARY_KEY))

        ### replace landing page
        self._remove_node(dataset_dict, dataset_ref,  ('url', DCAT.landingPage, None, URIRef))
        landing_page_uri = None
        if dataset_dict.get('name'):
            landing_page_uri = '{0}/dataset/{1}'.format(catalog_uri().rstrip('/'), dataset_dict['name'])
        else:
            landing_page_uri = dataset_uri(dataset_dict)  # TODO: preserve original URI if harvested

        self.g.add((dataset_ref, DCAT.landingPage, URIRef(landing_page_uri)))

        ### conformsTo
        self.g.remove((dataset_ref, DCT.conformsTo, None))
        value = self._get_dict_value(dataset_dict, 'conforms_to')
        if value:
            try:
                conforms_to = json.loads(value)
            except (TypeError, ValueError,):
                log.warn("Cannot deserialize DCATAPIT:conformsTo value: %s", value)
                conforms_to = []

            for item in conforms_to:
                standard = URIRef(item['uri']) if item.get('uri') else BNode()
                
                self.g.add((dataset_ref, DCT.conformsTo, standard))
                self.g.add((standard, RDF['type'], DCT.Standard))
                self.g.add((standard, RDF['type'], DCATAPIT.Standard))

                self.g.add((standard, DCT.identifier, Literal(item['identifier'])))

                for lang, val in (item.get('title') or {}).items():
                    if lang in OFFERED_LANGS:
                        self.g.add((standard, DCT.title, Literal(val, lang=lang_mapping_ckan_to_xmllang.get(lang, lang))))

                for lang, val in (item.get('description') or {}).items():
                    if lang in OFFERED_LANGS:
                        self.g.add((standard, DCT.description, Literal(val, lang=lang_mapping_ckan_to_xmllang.get(lang, lang))))

                for reference_document in (item.get('referenceDocumentation') or []):
                    self.g.add((standard, DCATAPIT.referenceDocumentation, URIRef(reference_document)))

        ### ADMS:identifier alternative identifiers
        self.g.remove((dataset_ref, ADMS.identifier, None,))
        try:
            alt_ids = json.loads(dataset_dict['alternate_identifier'])
        except (KeyError, TypeError, ValueError,):
            alt_ids = []

        for alt_identifier in alt_ids:
            node = BNode()
            self.g.add((dataset_ref, ADMS.identifier, node))

            identifier = Literal(alt_identifier['identifier'])
            self.g.add((node, SKOS.notation, identifier))

            if alt_identifier.get('agent'):
                adata = alt_identifier['agent']
                agent = BNode()

                self.g.add((agent, RDF['type'], DCATAPIT.Agent))
                self.g.add((agent, RDF['type'], FOAF.Agent))
                self.g.add((node, DCT.creator, agent))
                if adata.get('agent_name'):
                    for alang, aname in adata['agent_name'].items():
                        self.g.add((agent, FOAF.name, Literal(aname, lang=alang)))

                if adata.get('agent_identifier'):
                    self.g.add((agent, DCT.identifier, Literal(adata['agent_identifier'])))

        self._set_temporal_coverage(self.g, dataset_dict, dataset_ref)

        ### publisher

        # DCAT by default creates this node
        # <dct:publisher>
        #   <foaf:Organization rdf:about="http://10.10.100.75/organization/55535226-f82a-4cf7-903a-3e10afeaa79a">
        #     <foaf:name>orga2_test</foaf:name>
        #   </foaf:Organization>
        # </dct:publisher>

        for s,p,o in g.triples( (dataset_ref, DCT.publisher, None) ):
            #log.info("Removing publisher %r", o)
            g.remove((s, p, o))

        publisher_ref = self._add_agent(dataset_dict, dataset_ref, 'publisher', DCT.publisher, use_default_lang=True)


        ### Autore : Agent
        self._add_creators(dataset_dict, dataset_ref)


        ### Point of Contact

        # <dcat:contactPoint rdf:resource="http://dati.gov.it/resource/PuntoContatto/contactPointRegione_r_liguri"/>

        # <!-- http://dati.gov.it/resource/PuntoContatto/contactPointRegione_r_liguri -->
        # <dcatapit:Organization rdf:about="http://dati.gov.it/resource/PuntoContatto/contactPointRegione_r_liguri">
        #    <rdf:type rdf:resource="&vcard;Kind"/>
        #    <rdf:type rdf:resource="&vcard;Organization"/>
        #    <vcard:hasEmail rdf:resource="mailto:infoter@regione.liguria.it"/>
        #    <vcard:fn>Regione Liguria - Sportello Cartografico</vcard:fn>
        # </dcatapit:Organization>


        # TODO: preserve original info if harvested

        # retrieve the contactPoint added by the euro serializer
        euro_poc = g.value(subject=dataset_ref, predicate=DCAT.contactPoint, object=None, any=False)

        # euro poc has this format:
        # <dcat:contactPoint>
        #    <vcard:Organization rdf:nodeID="Nfcd06f452bcd41f48f33c45b0c95979e">
        #       <vcard:fn>THE ORGANIZATION NAME</vcard:fn>
        #       <vcard:hasEmail>THE ORGANIZATION EMAIL</vcard:hasEmail>
        #    </vcard:Organization>
        # </dcat:contactPoint>

        if euro_poc:
            g.remove((dataset_ref, DCAT.contactPoint, euro_poc))

        org_id = dataset_dict.get('owner_org')

        # get orga info
        org_show = logic.get_action('organization_show')

        org_dict = {}
        if org_id:
            try:
                org_dict = org_show({'ignore_auth': True},
                                    {'id': org_id,
                                     'include_datasets': False,
                                     'include_tags': False,
                                     'include_users': False,
                                     'include_groups': False,
                                     'include_extras': True,
                                     'include_followers': False}
                                    )
            except Exception, err:
                log.warning("Cannot get org for %s: %s", org_id, err, exc_info=err)

        org_uri = organization_uri(org_dict)

        poc = URIRef(org_uri)
        g.add((dataset_ref, DCAT.contactPoint, poc))
        g.add((poc, RDF.type, DCATAPIT.Organization))
        g.add((poc, RDF.type, VCARD.Kind))
        g.add((poc, RDF.type, VCARD.Organization))

        g.add((poc, VCARD.fn, Literal(org_dict.get('name'))))

        if 'email' in org_dict.keys():  # this element is mandatory for dcatapit, but it may not have been filled for imported datasets
            g.add((poc, VCARD.hasEmail, URIRef(org_dict.get('email'))))
        if 'telephone' in org_dict.keys():
            g.add((poc, VCARD.hasTelephone, Literal(org_dict.get('telephone'))))
        if 'site' in org_dict.keys():
            g.add((poc, VCARD.hasURL, Literal(org_dict.get('site'))))


        ### Rights holder : Agent,
        ### holder_ref keeps graph reference to holder subject
        ### holder_use_dataset is a flag if holder info is taken from dataset (or organization)
        holder_ref, holder_use_dataset = self._add_right_holder(dataset_dict, org_dict, dataset_ref)

        ### Multilingual
        # Add localized entries in dataset
        # TODO: should we remove the non-localized nodes?

        loc_dict = interfaces.get_for_package(dataset_dict['id'])
        #  The multilang fields
        loc_package_mapping = {
            'title': (dataset_ref, DCT.title),
            'notes': (dataset_ref, DCT.description),
            'publisher_name': (publisher_ref, FOAF.name),
        }
        if holder_use_dataset and holder_ref:
            loc_package_mapping['holder_name'] = (holder_ref, FOAF.name)

        self._add_multilang_values(loc_dict, loc_package_mapping)
        if not holder_use_dataset and holder_ref:
            loc_dict = interfaces.get_for_group_or_organization(org_dict['id'])
            loc_package_mapping = {'name': (holder_ref, FOAF.name)}
            self._add_multilang_values(loc_dict, loc_package_mapping)

        ### Resources
        for resource_dict in dataset_dict.get('resources', []):

            distribution = URIRef(resource_uri(resource_dict))  # TODO: preserve original info if harvested

            # Add the DCATAPIT type
            g.add((distribution, RDF.type, DCATAPIT.Distribution))

            ### format
            self._remove_node(resource_dict, distribution,  ('format', DCT['format'], None, Literal))
            if not self._add_uri_node(resource_dict, distribution, ('distribution_format', DCT['format'], None, URIRef), FORMAT_BASE_URI):
                guessed_format = guess_format(resource_dict)
                if guessed_format:
                    self.g.add((distribution, DCT['format'], URIRef(FORMAT_BASE_URI + guessed_format)))
                else:
                    log.warn('No format for resource: %s / %s', dataset_dict.get('title', 'N/A'), resource_dict.get('description', 'N/A') )
                    self.g.add((distribution, DCT['format'], URIRef(FORMAT_BASE_URI + DEFAULT_FORMAT_CODE)))


            
            ### license
            # <dct:license rdf:resource="http://creativecommons.org/licenses/by/3.0/it/"/>
            #
            # <dcatapit:LicenseDocument rdf:about="http://creativecommons.org/licenses/by/3.0/it/">
            #    <rdf:type rdf:resource="&dct;LicenseDocument"/>
            #    <owl:versionInfo>3.0 ITA</owl:versionInfo>
            #    <foaf:name>CC BY</foaf:name>
            #    <dct:type rdf:resource="http://purl.org/adms/licencetype/Attribution"/>
            # </dcatapit:LicenseDocument>

            # "license_id" : "cc-zero"
            # "license_title" : "Creative Commons CCZero",
            # "license_url" : "http://www.opendefinition.org/licenses/cc-zero",

            license_info = interfaces.get_license_for_dcat(resource_dict.get('license_type'))
            dcat_license, license_title, license_url, license_version, dcatapit_license, names = license_info

            license = URIRef(license_url or dcatapit_license)

            g.add((license, RDF.type, DCATAPIT.LicenseDocument))
            g.add((license, RDF.type, DCT.LicenseDocument))
            g.add((license, DCT.type, URIRef(dcat_license)))
            if license_version:
                g.add((license, OWL.versionInfo, Literal(license_version)))
            for n in names:
                g.add((license, FOAF.name, Literal(n['name'], lang=n['lang'])))
            
            g.add((distribution, DCT.license, license))

            ### Multilingual
            # Add localized entries in resource
            # TODO: should we remove the not-localized nodes?

            loc_dict = interfaces.get_for_resource(resource_dict['id'])

            #  The multilang fields
            loc_resource_mapping = {
                'name': (distribution, DCT.title),
                'description': (distribution, DCT.description),
            }
            self._add_multilang_values(loc_dict, loc_resource_mapping)

    def _add_multilang_values(self, loc_dict, loc_mapping):
        if loc_dict:
            for field_name, lang_dict in loc_dict.iteritems():
                ref, pred = loc_mapping.get(field_name, (None, None))
                if not pred:
                    log.warn('Multilang field not mapped "%s"', field_name)
                    continue
                for lang, value in lang_dict.iteritems():
                   lang = lang.split('_')[0]  # rdflib is quite picky in lang names
                   self.g.add((ref, pred, Literal(value, lang=lang)))
        else:
            log.warn("No mulitlang source data")

    def _add_right_holder(self, dataset_dict, org_dict, ref):
        basekey = 'holder'
        agent_name = self._get_dict_value(dataset_dict, basekey + '_name', None)
        agent_id = self._get_dict_value(dataset_dict, basekey + '_identifier', None)
        holder_ref = None
        if agent_id and agent_name:
            use_dataset = True
            holder_ref = self._add_agent(dataset_dict,
                                         ref,
                                         'holder',
                                         DCT.rightsHolder,
                                         use_default_lang=True)
        else:
            use_dataset = False
            agent_name = org_dict.get('name')
            agent_id = org_dict.get('identifier')

            if agent_id and agent_name:
                agent_data = (agent_name, agent_id,)
                holder_ref = self._add_agent(org_dict,
                                             ref,
                                             'organization',
                                             DCT.rightsHolder,
                                             use_default_lang=True,
                                             agent_data=agent_data)
        return holder_ref, use_dataset

    def _add_themes(self, dataset_ref, raw_value):
        """
        Create theme/subtheme
        """
        try:
            themes = json.loads(raw_value)
        except (TypeError, ValueError,):
            if isinstance(raw_value, (str, unicode,)):
                themes = [{'theme': r, 'subthemes': []} for r in raw_value.strip('{}').split(',')]
            elif isinstance(raw_value, (list, tuple,)):
                themes = raw_value
            else:
                themes = []

        # ckanext-dcat will leave bad values from serialized themes
        self.g.remove((dataset_ref, DCAT.theme, None))
        if themes:
            for theme in themes:
                theme_name = theme['theme']
                subthemes = theme['subthemes']
                theme_ref = URIRef(theme_name)
                               
                self.g.remove((dataset_ref, DCAT.theme, theme_ref))

                self.g.add((dataset_ref, DCAT.theme, URIRef(THEME_BASE_URI + theme_name)))
                self._add_concept(THEME_CONCEPTS, theme_name)
                self._add_subthemes(dataset_ref, subthemes)
        else:
                self.g.add((dataset_ref, DCAT.theme, URIRef(THEME_BASE_URI + DEFAULT_THEME_KEY)))
                self._add_concept(THEME_CONCEPTS, DEFAULT_THEME_KEY)


    def _add_subthemes(self, ref, subthemes):
        """
        subthemes is a list of eurovoc hrefs.

        """
        for subtheme in subthemes:
            sref = URIRef(subtheme)
            sthm = Subtheme.get(subtheme)
            if not sthm:
                print("No subtheme for {}".format(subtheme))
                continue

            labels = sthm.get_names_dict()
            self.g.add((sref, RDF.type, SKOS.Concept))
            for lang, label in labels.items():
                if lang in OFFERED_LANGS:
                    self.g.add((sref, SKOS.prefLabel, Literal(label, lang=lang)))
            self.g.add((ref, DCT.subject, sref))

    def _add_creators(self, dataset_dict, ref):
        """
        new style creators. creator field is serialized json, with pairs of name/identifier
        """
        # clear any previous data
        self.g.remove((ref, DCT.creator, None))
        creators_data = dataset_dict.get('creator')
        if not creators_data:
            for extra in (dataset_dict.get('extras') or []):
                if extra['key'] == 'creator':
                    creators_data = extra['value']

        try:
            creators = json.loads(creators_data)
        except (TypeError, ValueError,), err:
            creators = []
        if dataset_dict.get('creator_identifier') or dataset_dict.get('creator_name'):
            old_creator = {}
            if dataset_dict.get('creator_identifier'):
                old_creator['creator_identifier'] = dataset_dict['creator_identifier']
            if dataset_dict.get('creator_name'):
                old_creator['creator_name'] = {DEFAULT_LANG: dataset_dict['creator_name']}
            old_to_add = bool(old_creator)
            if old_creator.get('creator_identifier'):
                for cr in creators:
                    if cr.get('creator_identifier') and cr['creator_identifier'] == old_creator['creator_identifier']:
                        old_to_add = False
                        break
            if old_to_add:
                creators.append(old_creator)

        for creator in creators:
            self._add_agent(creator, ref, 'creator', DCT.creator)

    def _add_agent(self, _dict, ref, basekey, _type, use_default_lang=False, agent_data=None):
        ''' Stores the Agent in this format:
                <dct:publisher rdf:resource="http://dati.gov.it/resource/Amministrazione/r_liguri"/>
                    <dcatapit:Agent rdf:about="http://dati.gov.it/resource/Amministrazione/r_liguri">
                        <rdf:type rdf:resource="&foaf;Agent"/>
                        <dct:identifier>r_liguri</dct:identifier>
                        <foaf:name>Regione Liguria</foaf:name>
                    </dcatapit:Agent>

            Returns the ref to the agent node
        '''

        try:
            agent_name, agent_id = agent_data
        except (TypeError, ValueError, IndexError,):
            agent_name = self._get_dict_value(_dict, basekey + '_name', 'N/A')
            agent_id = self._get_dict_value(_dict, basekey + '_identifier','N/A')

        agent = BNode()

        self.g.add((agent, RDF['type'], DCATAPIT.Agent))
        self.g.add((agent, RDF['type'], FOAF.Agent))
        self.g.add((ref, _type, agent))

        if isinstance(agent_name, dict):
            for lang, aname in agent_name.items():
                if lang in OFFERED_LANGS:
                    self.g.add((agent, FOAF.name, Literal(aname, lang=lang_mapping_ckan_to_xmllang.get(lang, lang))))
        else:
            if use_default_lang:
                self.g.add((agent, FOAF.name, Literal(agent_name, lang=DEFAULT_LANG)))
            else:
                self.g.add((agent, FOAF.name, Literal(agent_name)))
        self.g.add((agent, DCT.identifier, Literal(agent_id)))

        return agent

    def _add_uri_node(self, _dict, ref, item, base_uri=''):

        key, pred, fallback, _type = item

        value = self._get_dict_value(_dict, key)
        if value:
            self.g.add((ref, pred, _type(base_uri + value)))
            return True
        elif fallback:
            self.g.add((ref, pred, _type(base_uri + fallback)))
            return False
        else:
            return False

    def _remove_node(self, _dict, ref, item):

        key, pred, fallback, _type = item

        value = self._get_dict_value(_dict, key)
        if value:
            self.g.remove((ref, pred, _type(value)))

    def _add_concept(self, concepts, tag):

        # Localized concepts should be serialized as:
        #
        # <dcat:theme rdf:resource="http://publications.europa.eu/resource/authority/data-theme/ENVI"/>
        #
        # <skos:Concept rdf:about="http://publications.europa.eu/resource/authority/data-theme/ENVI">
        #     <skos:prefLabel xml:lang="it">Ambiente</skos:prefLabel>
        # </skos:Concept>
        #
        # Return true if Concept has been added

        voc, base_uri = concepts

        loc_dict = interfaces.get_all_localized_tag_labels(tag)

        if loc_dict and len(loc_dict) > 0:

            concept = URIRef(base_uri + tag)
            self.g.add((concept, RDF['type'], SKOS.Concept))

            for lang, label in loc_dict.iteritems():
                lang = lang.split('_')[0]  # rdflib is quite picky in lang names
                self.g.add((concept, SKOS.prefLabel, Literal(label, lang=lang)))

            return True

        return False

    def graph_from_catalog(self, catalog_dict, catalog_ref):

        g = self.g

        for prefix, namespace in it_namespaces.iteritems():
            g.bind(prefix, namespace)

        ### Add a further type for the Catalog node
        g.add((catalog_ref, RDF.type, DCATAPIT.Catalog))

        ### Replace homepage
        # Try to avoid to have the Catalog URIRef identical to the homepage URI
        g.remove((catalog_ref, FOAF.homepage, URIRef(config.get('ckan.site_url'))))
        g.add((catalog_ref, FOAF.homepage, URIRef(catalog_uri() + '/#')))

        ### publisher
        pub_agent_name = config.get('ckanext.dcatapit_configpublisher_name', 'unknown')
        pub_agent_id = config.get('ckanext.dcatapit_configpublisher_code_identifier', 'unknown')

        agent = BNode()
        self.g.add((agent, RDF['type'], DCATAPIT.Agent))
        self.g.add((agent, RDF['type'], FOAF.Agent))
        self.g.add((catalog_ref, DCT.publisher, agent))
        self.g.add((agent, FOAF.name, Literal(pub_agent_name)))
        self.g.add((agent, DCT.identifier, Literal(pub_agent_id)))

        ### issued date
        issued = config.get('ckanext.dcatapit_config.catalog_issued', '1900-01-01')
        if issued:
            self._add_date_triple(catalog_ref, DCT.issued, issued)

        ### theme taxonomy

        # <dcat:themeTaxonomy rdf:resource="http://publications.europa.eu/resource/authority/data-theme"/>

        # <skos:ConceptScheme rdf:about="http://publications.europa.eu/resource/authority/data-theme">
        #    <dct:title xml:lang="it">Il Vocabolario Data Theme</dct:title>
        # </skos:ConceptScheme>

        taxonomy = URIRef(THEME_BASE_URI.rstrip('/'))
        self.g.add((catalog_ref, DCAT.themeTaxonomy, taxonomy))
        self.g.add((taxonomy, RDF.type, SKOS.ConceptScheme))
        self.g.add((taxonomy, DCT.title, Literal('Il Vocabolario Data Theme', lang='it')))

        ### language
        langs = config.get('ckan.locales_offered', 'it')

        for lang_offered in langs.split():
            lang_code = lang_mapping_ckan_to_voc.get(lang_offered)
            if lang_code:
                self.g.add((catalog_ref, DCT.language, URIRef(LANG_BASE_URI + lang_code)))

        self.g.remove((catalog_ref, DCT.language, Literal(config.get(DEFAULT_LANG))))


def organization_uri(orga_dict):
    '''
    Returns an URI for the organization

    This will be used to uniquely reference the organization on the RDF serializations.

    The value will be

        `catalog_uri()` + '/organization/' + `orga_id`

    Check the documentation for `catalog_uri()` for the recommended ways of
    setting it.

    Returns a string with the resource URI.
    '''

    uri = '{0}/organization/{1}'.format(catalog_uri().rstrip('/'), orga_dict.get('id', None))

    return uri


def guess_format(resource_dict):
    f = resource_dict.get('format')

    if not f:
        log.info('No format found')
        return None

    ret = format_mapping.get(f, None)

    if not ret:
       log.info('Mapping not found for format %s', f)

    return ret
