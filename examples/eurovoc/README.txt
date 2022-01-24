Load the EUROVOC file (you may want to make sure the URL in the script is still valid at the time you will be using the script):

    ./eurovoc_download.sh

Unzip it:

    unzip eurovoc_skos.zip 


Generate the trimmed down version (it takes ~20 seconds):

   ./eurovoc_trim.sh eurovoc-skos-ap-eu.rdf

Last command creates a file named `eurovoc-skos.reduced.rdf`.
This is the one that shall be used when loading the subthemes.
