IN=${1? "Missing input EUROVOC file"}

echo Removing unneeded languages
xmlstarlet ed -d "//*[@xml:lang][not(contains('it en fr de', @xml:lang))]" \
    $IN > eurovoc-tmp.01.rdf

echo Removing "skosxl Labels" concepts
xmlstarlet ed -N skosxl="http://www.w3.org/2008/05/skos-xl#" -N rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"  \
    -d '//rdf:Description[rdf:type/@rdf:resource="http://www.w3.org/2008/05/skos-xl#Label"]'  \
    eurovoc-tmp.01.rdf > eurovoc-tmp.02.rdf

echo Removing skosxl elements
xmlstarlet ed -N skosxl="http://www.w3.org/2008/05/skos-xl#" -d '//skosxl:*' \
    eurovoc-tmp.02.rdf > eurovoc-tmp.03.rdf

echo Removing euvoc elements
xmlstarlet ed -N euvoc="http://publications.europa.eu/ontology/euvoc#" -d '//euvoc:*' \
    eurovoc-tmp.03.rdf > eurovoc-tmp.04.rdf

echo Removing "euvoc xlNotes" concepts
xmlstarlet ed -N skosxl="http://www.w3.org/2008/05/skos-xl#" -N rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" \
    -d '//rdf:Description[rdf:type/@rdf:resource="http://publications.europa.eu/ontology/euvoc#XlNote"]'  \
    eurovoc-tmp.04.rdf > eurovoc-tmp.05.rdf

echo Removing relational elements:
# used elements: skos:hasTopConcept
oldname=eurovoc-tmp.05.rdf;
for name in dct:created dct:hasPart dct:isPartOf dct:modified \
            skos:altLabel skos:broader skos:definition skos:historyNote skos:inScheme \
            skos:narrower skos:notation skos:related skos:scopeNote skos:topConceptOf ; do
   newfilename=eurovoc-tmp.06.00${name}.rdf
   echo "   Removing $name"
   xmlstarlet ed -N skos="http://www.w3.org/2004/02/skos/core#" -N dct="http://purl.org/dc/terms/" \
       -d "//${name}" $oldname > $newfilename
   oldname=$newfilename
done
cp $newfilename eurovoc-tmp.06.rdf

echo Removing euvoc xlNotations concepts
xmlstarlet ed -N skosxl="http://www.w3.org/2008/05/skos-xl#" -N rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" \
    -d '//rdf:Description[rdf:type/@rdf:resource="http://publications.europa.eu/ontology/euvoc#XlNotation"]'  \
    eurovoc-tmp.06.rdf > eurovoc-tmp.07.rdf

#echo Removing xlScopeNote elements
#xmlstarlet ed -N euvoc="http://publications.europa.eu/ontology/euvoc#" -N rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"  \
#    -d '//euvoc:xlScopeNote'  \
#    eurovoc-skos.07.rdf > eurovoc-skos.08.rdf

echo Removing xlScopeNote concepts '(heuristic)'
xmlstarlet ed -d  '//rdf:Description[starts-with(@rdf:about,"http://eurovoc.europa.eu/note_")]' \
    eurovoc-tmp.07.rdf > eurovoc-tmp.08.rdf

echo Removing other xl stuff '(heuristic)'
xmlstarlet ed -d  '//rdf:Description[starts-with(@rdf:about,"http://eurovoc.europa.eu/xl_")]' \
    eurovoc-tmp.08.rdf > eurovoc-tmp.09.rdf

echo Removing empty versionInfo
xmlstarlet ed -N owl="http://www.w3.org/2002/07/owl#" -d '//owl:versionInfo[text()="n/a"]' \
    eurovoc-tmp.09.rdf > eurovoc-tmp.10.rdf

echo Removing empty Descriptions
xmlstarlet ed -d '//rdf:Description[not(*)]' \
    eurovoc-tmp.10.rdf > eurovoc-tmp.11.rdf

cp eurovoc-tmp.11.rdf eurovoc-skos.reduced.rdf

# rm eurovoc-tmp*rdf
