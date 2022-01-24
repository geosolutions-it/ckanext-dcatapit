cat official/filetypes-skos.rdf |\
   xmlstarlet ed -d "//*[@xml:lang][not(contains('it en fr de es', @xml:lang))]" | \
   xmlstarlet ed -d "//at:op-mapped-code" |  \
   xmlstarlet ed -d "//skos:Concept[not(skos:prefLabel/@xml:lang)]" | \
   xmlstarlet ed -d "//skos:Concept/at:*" | \
   xmlstarlet ed -d "//skos:Concept/atold:*" | \
   xmlstarlet ed -d "//skos:Concept/skos:inScheme" | \
   xmlstarlet ed -d "//skos:Concept/skos:altLabel"  \
    > filetypes-filtered.tmp.rdf

for lang in it en fr de es ; do
   xmlstarlet ed -d "//skos:Concept[not(skos:prefLabel/@xml:lang)]" | \


