Here some details about how the various files has been retrieved (or reprocessed, or created).

## Vocabularies

In the `vocabularies/` directory you can find the files ready to be loaded into CKAN.
They may be either the original official files, or a processed version that only includes entries fitting DCATAPIT specs.

You will also find copies of the original files in a Release entry in github (in order not to add unused heavy files in the repository checkout), and the scripts for processing the original files in `vocabularies/scripts`.

In order to be able to run the trimming scripts, you need to install the [xmlstarlet](http://xmlstar.sourceforge.net/) package.

### Data themes

- Official page:  
   https://op.europa.eu/it/web/eu-vocabularies/at-dataset/-/resource/dataset/data-theme/

- Download command:
   ```bash
   wget "https://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http%3A%2F%2Fpublications.europa.eu%2Fresource%2Fcellar%2F2c758808-fdd6-11ea-b44f-01aa75ed71a1.0001.02%2FDOC_1&fileName=data-theme-skos.rdf" -O official/data-theme-skos.rdf
   ```

- Processing:
  - Script `scripts/data-theme-trim.sh`:
    - Read `official/data-theme-skos.rdf`
    - Filter out unused languages
  - Final processed file: `data-theme-filtered.rdf`
  
### Places

- Official page:  
   https://op.europa.eu/it/web/eu-vocabularies/at-dataset/-/resource/dataset/place/

- Download command:
    ```bash
    wget "https://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http%3A%2F%2Fpublications.europa.eu%2Fresource%2Fcellar%2F87ec948c-581c-11ec-91ac-01aa75ed71a1.0001.04%2FDOC_1&fileName=places-skos.rdf" -O official/places-skos.rdf
    ```

- Processing:
  - Script `scripts/places-trim.sh`:
    - Read `official/places-skos.rdf`
    - Filter out non Italian places
    - Filter out unused languages
  - Final processed file `places-filtered.rdf`

### Languages

- Official page:  
   https://op.europa.eu/it/web/eu-vocabularies/at-dataset/-/resource/dataset/language/

- Download command:
    ```bash
    wget "https://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http%3A%2F%2Fpublications.europa.eu%2Fresource%2Fcellar%2F87f03e0d-581c-11ec-91ac-01aa75ed71a1.0001.05%2FDOC_1&fileName=languages-skos.rdf" -O official/languages-skos.rdf
    ```

- Processing:
  - Script `scripts/languages-trim.sh`:
    - Read `official/languages-skos.rdf`
    - Filter out unused languages
    - Filter out unused elements
  - Final processed file `languages-filtered.rdf`
  
### Frequencies

- Official page:  
   https://op.europa.eu/it/web/eu-vocabularies/at-dataset/-/resource/dataset/frequency/

- Download command:
    ```bash
    wget "https://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http%3A%2F%2Fpublications.europa.eu%2Fresource%2Fcellar%2Fe20301fe-928e-11e9-9369-01aa75ed71a1.0001.02%2FDOC_1&fileName=frequencies-skos.rdf" -O official/frequencies-skos.rdf
    ```

- Processing:
  - Script `scripts/frequencies-trim.sh`:
    - Read `official/frequencies-skos.rdf`
    - Filter out unused languages
    - Filter out unused elements
  - Final processed file `frequencies-filtered.rdf`
  
### File types

- Official page:  
    https://op.europa.eu/it/web/eu-vocabularies/at-dataset/-/resource/dataset/file-type/

- Download command:
    ```bash
    wget "https://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http%3A%2F%2Fpublications.europa.eu%2Fresource%2Fcellar%2F7c112635-581c-11ec-91ac-01aa75ed71a1.0001.04%2FDOC_1&fileName=filetypes-skos.rdf" -O official/filetypes-skos.rdf
    ```

- Processing
  - Script `scripts/filetypes-trim.sh`:
    - Read `official/filetypes-skos.rdf`
    - Filter out unused languages
    - Filter out unused elements
    - Add missing `it` `de` `fr` `es` entries
  - Final processed file `frequencies-filtered.rdf`

    
### Subtheme mapping

Subthemes mapping file is not from `op.europa.eu` and it does not need any further processing.

- Download command:
    ```bash
    wget https://github.com/italia/daf-ontologie-vocabolari-controllati/raw/master/VocabolariControllati/theme-subtheme-mapping/theme-subtheme-mapping.rdf
    ```

### EUROVOC

We're using a subset of EUROVOC concepts for extracting localized label for subthemes, 
which are only provided in `it` and `en` in the `theme-subtheme-mapping.rdf` file.

- Official page:
  https://op.europa.eu/it/web/eu-vocabularies/dataset/-/resource?uri=http://publications.europa.eu/resource/dataset/eurovoc#

- Download command:
    ```bash
    wget "https://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http%3A%2F%2Fpublications.europa.eu%2Fresource%2Fcellar%2Fbcd714b1-5f05-11ec-9c6c-01aa75ed71a1.0001.05%2FDOC_1&fileName=eurovoc_skos.zip" -O official/eurovoc_skos.zip
    ```

- Processing
  - Unzip the file, you'll get the file `eurovoc-skos-ap-eu.rdf`
    ```bash
    unzip  official/eurovoc_skos.zip  -d official/
    ``` 
  - Call script ```scripts/eurovoc-trim.sh official/eurovoc-skos-ap-eu.rdf```  
    It's a big file, so it will take a bit.
  - Final processed file `eurovoc-skos-filtered.rdf` (about 1% of the original size)
  
### Licenses

- Download command:
    ```bash
    wget https://raw.githubusercontent.com/italia/daf-ontologie-vocabolari-controllati/master/VocabolariControllati/licences/licences.rdf
    ```

## Examples

In the `examples/` directory there are some sample files.

## Tests

In the `tests/files/` directory there are overly simplified files used in tests.

- `/ckanext/dcatapit/tests/files/data-theme-skos.rdf`:
  ```bash
   xmlstarlet ed -d "//*[@xml:lang][not(contains('it en fr de', @xml:lang))]" vocabularies/data-theme-skos.rdf > ckanext/dcatapit/tests/files/data-theme-skos.rdf
  ```

- `/ckanext/dcatapit/tests/files/eurovoc_filtered.rdf`  
  This file contains the labels for only the used subthemes.  
  In order to create this file you need an usable EUROVOC file (the `eurovoc-filtered.rdf` described above is perfectly fine)
  and the subtheme mapping.  
  You can recreate this file using the `create_eurovoc_for_test.py` script:
  ```bash
  ./create_eurovoc_for_test.py ../../../../vocabularies/theme-subtheme-mapping.rdf  ../../../../vocabularies/eurovoc-filtered.rdf 
  ```
