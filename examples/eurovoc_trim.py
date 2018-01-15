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
        ids_file, doc_file= sys.argv[1:][-2:]
    except (ValueError, IndexError,):
        print("Usage: {} IDS_FILE DOC_FILE".format(__file__))
        return

    ids = get_ids(ids_file)
    doc, nsmap = parse_doc(doc_file)
    root = doc.getroot()
    ndoc = etree.Element('{{{}}}RDF'.format(nsmap['rdf']))
    for ns, uri in nsmap.items():
        etree.register_namespace(ns, uri)

    for el in doc.findall('{{{}}}Description'.format(nsmap['rdf'])):
        ref = el.get('{{{}}}about'.format(nsmap['rdf']))
        if ref in ids:
            ndoc.append(el)

            for subref in el.findall('{{{}}}hasTopConcept'.format(nsmap['skos'])):

                subref_id = subref.get('{{{}}}resource'.format(nsmap['rdf']))
                subel = doc.find('Description[@about="{}"]'.format(subref_id))
                if subel:
                    ndoc.append(subel)
                
    etree.dump(ndoc)

if __name__ == '__main__':
    main()
