
import logging

from pylons import config

from rdflib.namespace import Namespace, RDF
from rdflib import URIRef, BNode, Literal

import ckan.logic as logic

from ckanext.dcat.profiles import RDFProfile, DCAT
from ckanext.dcat.utils import catalog_uri, dataset_uri, resource_uri


DCT = Namespace("http://purl.org/dc/terms/")
DCATAPIT = Namespace('http://dati.gov.it/onto/dcatapit#')
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SCHEMA = Namespace('http://schema.org/')
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")


THEME_BASE_URI = 'http://publications.europa.eu/resource/authority/data-theme/'
LANG_BASE_URI = 'http://publications.europa.eu/resource/authority/language/'
FREQ_BASE_URI = 'http://publications.europa.eu/resource/authority/frequency/'
FORMAT_BASE_URI = 'http://publications.europa.eu/resource/authority/file-type/'

it_namespaces = {
    'dcatapit': DCATAPIT,
}

languages_mapping = {
    'it': 'ITA',
    'en': 'ENG',
}

log = logging.getLogger(__name__)

class ItalianDCATAPProfile(RDFProfile):
    '''
    An RDF profile for the Italian DCAT-AP recommendation for data portals
    It requires the European DCAT-AP profile (`euro_dcat_ap`)
    '''

    def parse_dataset(self, dataset_dict, dataset_ref):
        return dataset_dict

    def graph_from_dataset(self, dataset_dict, dataset_ref):

        logging.info(":::::: graph_from_dataset")

        title = dataset_dict.get('title')

        g = self.g

        for prefix, namespace in it_namespaces.iteritems():
            g.bind(prefix, namespace)

        ### replace Dataset node
        g.add((dataset_ref, RDF.type, DCATAPIT.Dataset))
        g.remove((dataset_ref, RDF.type, DCAT.Dataset))

        ### replace theme
        self._remove_node(dataset_dict, dataset_ref, ('theme', DCAT.theme, None, URIRef))
        self._add_uri_node(dataset_dict, dataset_ref, ('theme', DCAT.theme, None, URIRef), THEME_BASE_URI)

        ### replace language
        self._remove_node(dataset_dict, dataset_ref,  ('language', DCT.language, None, Literal))
        self._add_uri_node(dataset_dict, dataset_ref, ('language', DCT.language, None, URIRef), LANG_BASE_URI)

        ### replace periodicity
        self._remove_node(dataset_dict, dataset_ref,  ('frequency', DCT.accrualPeriodicity, None, Literal))
        self._add_uri_node(dataset_dict, dataset_ref, ('accrual_periodicity', DCT.accrualPeriodicity, None, URIRef), FREQ_BASE_URI)

        ### replace landing page
        self._remove_node(dataset_dict, dataset_ref,  ('url', DCAT.landingPage, None, URIRef))
        landing_page = dataset_uri(dataset_dict)
        self.g.add((dataset_ref, DCAT.landingPage, URIRef(landing_page)))

        ### temporal extension
        value = self._get_dict_value(dataset_dict, 'temporal_coverage')  # "temporal_coverage" : "2016-11-01,2016-11-06",
        if value:
            start, end = value.split(',')

            if start or end:
                temporal_extent = BNode()

                g.add((temporal_extent, RDF.type, DCT.PeriodOfTime))
                if start:
                    self._add_date_triple(temporal_extent, SCHEMA.startDate, start)
                if end:
                    self._add_date_triple(temporal_extent, SCHEMA.endDate, end)
                g.add((dataset_ref, DCT.temporal, temporal_extent))


        ### publisher

        # DCAT by default creates this node
        # <dct:publisher>
        #   <foaf:Organization rdf:about="http://10.10.100.75/organization/55535226-f82a-4cf7-903a-3e10afeaa79a">
        #     <foaf:name>orga2_test</foaf:name>
        #   </foaf:Organization>
        # </dct:publisher>

        for s,p,o in g.triples( (dataset_ref, DCT.publisher, None) ):
            log.info("Removing publisher %r", o)
            g.remove((s, p, o))

        # This is what we have in the dataset info
        #"publisher" : "dataset_editor_test,dataset_editor_ipa_test"

        self._add_agent(dataset_dict, dataset_ref, 'publisher', DCT.publisher)

        ### Rights holder : Agent
        self._add_agent(dataset_dict, dataset_ref, 'rights_holder', DCT.rightsHolder)

        ### Autore : Agent
        self._add_agent(dataset_dict, dataset_ref, 'creator', DCT.creator)

        ### Point of Contact

        org_id = dataset_dict.get('organization',{}).get('id')

        # get orga info
        org_show = logic.get_action('organization_show')
        org_dict = org_show({}, {'id': org_id})
        org_uri = organization_uri(org_dict)

        poc = URIRef(org_uri)
        g.add((poc, RDF.type, DCATAPIT.Organization))
        g.add((dataset_ref, DCAT.contactPoint, poc))

        g.add((poc, VCARD.fn, Literal(org_dict.get('name'))))
        g.add((poc, VCARD.hasEmail, Literal(org_dict.get('email'))))
        if 'telephone' in org_dict.keys():
            g.add((poc, VCARD.hasTelephone, Literal(org_dict.get('telephone'))))
        if 'site' in org_dict.keys():
            g.add((poc, VCARD.hasURL, Literal(org_dict.get('site'))))

        ### Resources
        for resource_dict in dataset_dict.get('resources', []):

            distribution = URIRef(resource_uri(resource_dict))

            ### format
            self._remove_node(resource_dict, distribution,  ('format', DCT['format'], None, Literal))
            self._add_uri_node(resource_dict, distribution, ('distribution_format', DCT['format'], None, URIRef), FORMAT_BASE_URI)

            ### license
#            <dct:license rdf:resource="http://creativecommons.org/licenses/by/3.0/it/"/>
#
#            <!-- http://creativecommons.org/licenses/by/3.0/it/ -->
#            <dcatapit:LicenseDocument rdf:about="http://creativecommons.org/licenses/by/3.0/it/">
#                <rdf:type rdf:resource="&dct;LicenseDocument"/>
#                <owl:versionInfo>3.0 ITA</owl:versionInfo>
#                <foaf:name>CC BY</foaf:name>
#                <dct:type rdf:resource="http://purl.org/adms/licencetype/Attribution"/>
#            </dcatapit:LicenseDocument>

            # "license_id" : "cc-zero"
            # "license_title" : "Creative Commons CCZero",
            # "license_url" : "http://www.opendefinition.org/licenses/cc-zero",

            license_url = dataset_dict.get('license_url', '')
            license_id = dataset_dict.get('license_id', '')
            license_title = dataset_dict.get('license_title', '')

            if license_url:
                license = URIRef(license_url)
                g.add((license, RDF['type'], DCATAPIT.LicenseDocument))
                g.add((distribution, DCT.license, license))

                if license_id:
                    # log.debug('Adding license id: %s', license_id)
                    g.add((license, FOAF.name, Literal(license_id)))
                elif license_title:
                    # log.debug('Adding license title: %s', license_title)
                    g.add((license, FOAF.name, Literal(license_title)))
                else:
                    g.add((license, FOAF.name, Literal('unknown')))
                    log.warn('License not found for dataset: %s', title)


    def _add_agent(self, _dict, ref, key, _type):
        ''' Stores the Agent in this format:
                <dct:publisher rdf:resource="http://dati.gov.it/resource/Amministrazione/r_liguri"/>
                    <dcatapit:Agent rdf:about="http://dati.gov.it/resource/Amministrazione/r_liguri">
                        <rdf:type rdf:resource="&foaf;Agent"/>
                        <dct:identifier>r_liguri</dct:identifier>
                        <foaf:name>Regione Liguria</foaf:name>
                    </dcatapit:Agent>
        '''

        value = self._get_dict_value(_dict, key)
        if value:
            agent_name, agent_id = value.split(',')

            agent = BNode()

            self.g.add((agent, RDF['type'], DCATAPIT.Agent))
            self.g.add((ref, _type, agent))

            # g.add((agent, RDF['type'], URIRef('&foaf;Agent')))
            self.g.add((agent, FOAF.name, Literal(agent_name)))
            self.g.add((agent, DCT.identifier, Literal(agent_id)))


    def _add_uri_node(self, _dict, ref, item, base_uri=''):

        key, pred, fallback, _type = item

        value = self._get_dict_value(_dict, key)
        if value:
            self.g.add((ref, pred, _type(base_uri + value)))

    def _remove_node(self, _dict, ref, item):

        key, pred, fallback, _type = item

        value = self._get_dict_value(_dict, key)
        if value:
            self.g.remove((ref, pred, _type(value)))

    def graph_from_catalog(self, catalog_dict, catalog_ref):

        g = self.g

        for prefix, namespace in it_namespaces.iteritems():
            g.bind(prefix, namespace)

        ### replace Catalog node
        g.add((catalog_ref, RDF.type, DCATAPIT.Catalog))
        g.remove((catalog_ref, RDF.type, DCAT.Catalog))


        ### publisher
        pub_agent_name = config.get('ckanext.dcatapit_configpublisher_name', 'unknown')
        pub_agent_id = config.get('ckanext.dcatapit_configpublisher_code_identifier', 'unknown')

        agent = BNode()
        self.g.add((agent, RDF['type'], DCATAPIT.Agent))
        self.g.add((catalog_ref, DCT.publisher, agent))
        self.g.add((agent, FOAF.name, Literal(pub_agent_name)))
        self.g.add((agent, DCT.identifier, Literal(pub_agent_id)))

        ### issued date
        issued = config.get('ckanext.dcatapit_config.catalog_issued', '1900-01-01')
        if issued:
            self._add_date_triple(catalog_ref, DCT.issued, issued)

        ### theme
        theme = config.get('ckanext.dcatapit_config.catalog_theme')
        self.g.add((catalog_ref, DCAT.theme, URIRef(THEME_BASE_URI + theme)))

        ### language
        lang2 = config.get('ckanext.dcatapit_config.catalog_theme', 'it')
        lang3 = languages_mapping.get(lang2) or 'ITA'
        self.g.add((catalog_ref, DCT.language, URIRef(LANG_BASE_URI + lang3)))
        self.g.remove((catalog_ref, DCT.language, Literal(config.get('ckan.locale_default', 'en'))))


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

    uri = '{0}/organization/{1}'.format(catalog_uri().rstrip('/'), orga_dict['id'])

    return uri