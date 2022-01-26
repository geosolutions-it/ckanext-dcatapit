cat official/frequencies-skos.rdf |\
   xmlstarlet ed -d "//*[@xml:lang][not(contains('it en fr de es', @xml:lang))]" | \
   xmlstarlet ed -d "//at:op-mapped-code" |  \
   xmlstarlet ed -d "//skos:Concept[not(skos:prefLabel/@xml:lang)]" | \
   xmlstarlet ed -d "//skos:Concept/at:*" | \
   xmlstarlet ed -d "//skos:Concept/atold:*" | \
   xmlstarlet ed -d "//skos:Concept/skos:inScheme" | \
   xmlstarlet ed -d "//skos:Concept/skos:altLabel"  \
    > frequencies-filtered.rdf

