#!/usr/bin/env python
import logging

import sys
from rdflib import Graph
from rdflib.namespace import OWL, RDF, SKOS


log = logging.getLogger(__name__)

allowed_languages = ('it', 'de', 'fr', 'en')
outfile = 'eurovoc_filtered.rdf'


def load_subthemes(themes, eurovoc):
    themes_g = Graph()
    eurovoc_g = Graph()

    print(f'Loading subthemes mapping...')
    themes_g.parse(themes)
    print(f'Loading EUROVOC... (this may take a while)...')
    eurovoc_g.parse(eurovoc)

    print(f'Filtering themes')
    g = create_filtered_graph(themes_g, eurovoc_g)

    g.serialize(destination=outfile)
    print(f'Filtered EUROVOC file saved as {outfile}')


def create_filtered_graph(themes_g, eurovoc_g) -> Graph:
    g = Graph()
    g.bind("skos", SKOS)

    concept = SKOS.Concept
    for theme in themes_g.subjects(RDF.type, concept):
        theme_name = str(theme).split("/")[-1]
        print(f'Loading subthemes for {theme} --> {theme_name}')
        sub_themes = themes_g.objects(theme, SKOS.narrowMatch)
        for sub_theme in sub_themes:
            print(f'     Loading subtheme {theme_name}::{sub_theme}')
            add_subtheme(eurovoc_g, g, theme_name, sub_theme)
    return g


def add_subtheme(eurovoc, filtered, theme_ref, subtheme_ref, parent=None):

    filtered.add((subtheme_ref, RDF['type'], SKOS.Concept))

    cnt = 0
    for l in eurovoc.objects(subtheme_ref, SKOS.prefLabel):
        if l.language in allowed_languages:
            print(f'         Adding label {theme_ref}::{subtheme_ref}::{l}')
            filtered.add((subtheme_ref, SKOS.prefLabel, l))
            cnt = cnt + 1

    if cnt == 0:
        print(f'**** NO LABELS FOUND FOR {subtheme_ref}')
    elif cnt < len(allowed_languages):
        print(f'**** ONLY {cnt} LABELS FOUND FOR {subtheme_ref}')


def main():
    try:
        mapping_file, eurovoc_file = sys.argv[1:][-2:]
    except (NameError, ValueError) as e:
        print(f'\nUsage: {__file__} MAPPING_FILE EUROVOC_FILE\n\n')
        exit(1)

    try:
        load_subthemes(mapping_file, eurovoc_file)
    except (ValueError, IndexError,) as e:
        print(e)


# needed in order to avoid to run this file as test
if __name__ == '__main__':
    main()
