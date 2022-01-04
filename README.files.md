Here some details about how the various files has been retrieved/created.

## Vocabularies

In the `vocabularies/` directory you can find copies of the original files downloaded from the official sites:  

- `/vocabularies/theme-subtheme-mapping.rdf`:
  ```bash
  wget https://github.com/italia/daf-ontologie-vocabolari-controllati/raw/master/VocabolariControllati/theme-subtheme-mapping/theme-subtheme-mapping.rdf
  ```
- `/vocabularies/data-theme-skos.rdf`:
  ```bash
  wget 'https://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http%3A%2F%2Fpublications.europa.eu%2Fresource%2Fcellar%2F2c758808-fdd6-11ea-b44f-01aa75ed71a1.0001.02%2FDOC_1&fileName=data-theme-skos.rdf' -O data-theme-skos.rdf
  ```

## Examples

In the `examples/` directory there are some sample files, and files derived from official ones.  

### EUROVOC

EUROVOC file is quite big (416MB). We're using a subset of its concepts for extracting localized label for subthemes.

Move into `examples/eurovoc` and download the official file:  

```bash
wget "https://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http%3A%2F%2Fpublications.europa.eu%2Fresource%2Fcellar%2Fbcd714b1-5f05-11ec-9c6c-01aa75ed71a1.0001.05%2FDOC_1&fileName=eurovoc_skos.zip" -O eurovoc_skos.zip
```

Unzip it, and you'll get the file `eurovoc-skos-ap-eu.rdf`.

Now let's trim out the unneeded elements; make sure you have the `xmlstarlet` command in your system. 
```bash
./eurovoc_trim.sh eurovoc-skos-ap-eu.rdf
```

At the end of the script, you'll have the file `eurovoc-skos.reduced.rdf`, whose size is about 1% of the original size.

## Tests

In the `tests/files/` directory there are overly simplified files used in tests.

- `/ckanext/dcatapit/tests/files/data-theme-skos.rdf`:
  ```bash
   xmlstarlet ed -d "//*[@xml:lang][not(contains('it en fr de', @xml:lang))]" vocabularies/data-theme-skos.rdf > ckanext/dcatapit/tests/files/data-theme-skos.rdf
  ```

- `/ckanext/dcatapit/tests/files/eurovoc_filtered.rdf`  
  This file contains the labels for only the used subthemes.  
  In order to create this file you need an usable EUROVOC file (the `eurovoc-skos.reduced.rdf` described above is perfectly fine)
  and the subtheme mapping.  
  You can recreate this file using the `create_eurovoc_for_test.py` script:
  ```bash
  ./create_eurovoc_for_test.py ../../../../vocabularies/theme-subtheme-mapping.rdf  ../../../../examples/eurovoc/eurovoc-skos.reduced.rdf 
  ```
