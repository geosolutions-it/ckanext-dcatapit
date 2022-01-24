cat official/places-skos.rdf | xmlstarlet ed  -d '//skos:Concept[not(starts-with(at:op-code/text(), "ITA"))]'   | xmlstarlet ed -d "//*[@xml:lang][not(contains('it en fr de es', @xml:lang))]" > places-filtered.rdf

