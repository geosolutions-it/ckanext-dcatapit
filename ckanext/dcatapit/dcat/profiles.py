from rdflib.namespace import Namespace, RDF, RDFS
from rdflib import URIRef, BNode, Literal

from ckanext.dcat.profiles import RDFProfile


DCT = Namespace("http://purl.org/dc/terms/")


class ItalianDCATAPProfile(RDFProfile):
    '''
    An RDF profile for the Italian DCAT-AP recommendation for data portals
    It requires the European DCAT-AP profile (`euro_dcat_ap`)
    '''

    def parse_dataset(self, dataset_dict, dataset_ref):
        return dataset_dict

    def graph_from_dataset(self, dataset_dict, dataset_ref):
		pass