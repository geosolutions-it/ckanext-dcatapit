Here some details about how the various files has been retrieved (or reprocessed, or created).

## Vocabularies

In the `vocabularies/` directory you can find the files ready to be loaded into CKAN.
They may be either the original official files, or a trimmed version that only includes entries fitting DCATAPIT specs.

You will also find copies of the original files in a Release entry in github (in order not to add unused heavy files in the checkout), and the scripts for processing the original files in `vocabularies/scripts`.


### Data themes

Official page:
   https://op.europa.eu/it/web/eu-vocabularies/at-dataset/-/resource/dataset/data-theme/

Download command:
```bash
wget "https://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http%3A%2F%2Fpublications.europa.eu%2Fresource%2Fcellar%2F2c758808-fdd6-11ea-b44f-01aa75ed71a1.0001.02%2FDOC_1&fileName=data-theme-skos.rdf" -O official/data-theme-skos.rdf
```

Processing:

Script `scripts/data-theme-trim.sh`:

- Read `official/data-theme-skos.rdf`
- Filter out unused languages
- Create trimmed file `data-theme-filtered.rdf`


### Subtheme mapping

Download command:
```bash
wget https://github.com/italia/daf-ontologie-vocabolari-controllati/raw/master/VocabolariControllati/theme-subtheme-mapping/theme-subtheme-mapping.rdf
```


### Places

Official page:  
   https://op.europa.eu/it/web/eu-vocabularies/at-dataset/-/resource/dataset/place/


Download command:
```bash
wget "https://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http%3A%2F%2Fpublications.europa.eu%2Fresource%2Fcellar%2F87ec948c-581c-11ec-91ac-01aa75ed71a1.0001.04%2FDOC_1&fileName=places-skos.rdf" -O official/places-skos.rdf
```

Processing:

Script `scripts/places-trim.sh`:

- Read `official/places-skos.rdf`
- Filter out non Italian places
- Filter out unused languages
- Create trimmed file `places-filtered.rdf`

### Languages

Official page:  
   https://op.europa.eu/it/web/eu-vocabularies/at-dataset/-/resource/dataset/language/

Download command:
```bash
wget "https://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http%3A%2F%2Fpublications.europa.eu%2Fresource%2Fcellar%2F87f03e0d-581c-11ec-91ac-01aa75ed71a1.0001.05%2FDOC_1&fileName=languages-skos.rdf" -O official/languages-skos.rdf
```

Processing:

Script `scripts/languages-trim.sh`:

- Read `official/languages-skos.rdf`
- Filter out unused languages
- Filter out unused elements
- Create trimmed file `languages-filtered.rdf`


### Frequencies

Official page:  
   https://op.europa.eu/it/web/eu-vocabularies/at-dataset/-/resource/dataset/frequency/

Download command:
```bash
wget "https://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http%3A%2F%2Fpublications.europa.eu%2Fresource%2Fcellar%2Fe20301fe-928e-11e9-9369-01aa75ed71a1.0001.02%2FDOC_1&fileName=frequencies-skos.rdf" -O official/frequencies-skos.rdf
```

Processing:

Script `scripts/frequencies-trim.sh`:


- Read `official/frequencies-skos.rdf`
- Filter out unused languages
- Filter out unused elements
- Create trimmed file `frequencies-filtered.rdf`






copies of the original files downloaded from the official sites:

- `/vocabularies/theme-subtheme-mapping.rdf`:
  ```bash
  wget https://github.com/italia/daf-ontologie-vocabolari-controllati/raw/master/VocabolariControllati/theme-subtheme-mapping/theme-subtheme-mapping.rdf
  ```
- `/vocabularies/data-theme-skos.rdf`:
  ```bash
  wget 'https://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http%3A%2F%2Fpublications.europa.eu%2Fresource%2Fcellar%2F2c758808-fdd6-11ea-b44f-01aa75ed71a1.0001.02%2FDOC_1&fileName=data-theme-skos.rdf' -O data-theme-skos.rdf
  ```


wget 'https://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http%3A%2F%2Fpublications.europa.eu%2Fresource%2Fcellar%2F87ec948c-581c-11ec-91ac-01aa75ed71a1.0001.04%2FDOC_1&fileName=places-skos.rdf' -O places-skos.rdf





https://op.europa.eu/it/web/eu-vocabularies/at-dataset/-/resource/dataset/frequency/
https://op.europa.eu/it/web/eu-vocabularies/at-dataset/-/resource/dataset/file-type/




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
