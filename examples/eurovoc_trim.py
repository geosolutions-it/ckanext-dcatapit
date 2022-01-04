#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import sys
from xml.etree import cElementTree as etree


def get_ids(ids_file):
    with open(ids_file, 'rt') as f:
        return [l.strip() for l in f.readlines() if l.strip()]


def parse_doc(doc_file):
    _ns = etree.iterparse(doc_file, events=('start-ns',))
    nsmap = dict(ns[1] for ns in _ns)

    return etree.parse(doc_file), nsmap


def main():
    try:
        ids_file, doc_file = sys.argv[1:][-2:]
    except (ValueError, IndexError,):
        print('Usage: {} IDS_FILE DOC_FILE'.format(__file__))
        return

    ids = get_ids(ids_file)
    doc, nsmap = parse_doc(doc_file)
    NS_RDF = nsmap['rdf']
    NS_SKOS = nsmap['skos']

    root = doc.getroot()
    ndoc = etree.Element(f'{{{NS_RDF}}}RDF')
    for ns, uri in nsmap.items():
        etree.register_namespace(ns, uri)

    for el in doc.findall(f'{{{NS_RDF}}}Description'):
        ref = el.get(f'{{{NS_RDF}}}about')
        if ref in ids:
            ndoc.append(el)

            for subref in el.findall(f'{{{NS_SKOS}}}hasTopConcept'):

                subref_id = subref.get(f'{{{NS_RDF}}}resource')
                subel = doc.find(f'Description[@about="{subref_id}"]')
                if subel:
                    ndoc.append(subel)

    etree.dump(ndoc)


if __name__ == '__main__':
    main()
