cat official/data-theme-skos.rdf | xmlstarlet ed -d "//*[@xml:lang][not(contains('it en fr de es', @xml:lang))]" > data-theme-filtered.rdf


