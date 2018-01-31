set -e
set -x

echo "This is travis-build.bash..."

echo "Installing the packages that CKAN requires..."

# remove faulty mongodb repo, we don't use it anyway
sudo rm -f /etc/apt/sources.list.d/mongodb-3.2.list
sudo add-apt-repository --remove 'http://us-central1.gce.archive.ubuntu.com/ubuntu/ main restricted'
sudo add-apt-repository --remove 'http://us-central1.gce.archive.ubuntu.com/ubuntu/ universe'
sudo add-apt-repository --remove 'http://us-central1.gce.archive.ubuntu.com/ubuntu/ multiverse'
sudo add-apt-repository 'http://archive.ubuntu.com/ubuntu/'
sudo add-apt-repository 'http://archive.ubuntu.com/ubuntu/ universe'
sudo add-apt-repository 'http://archive.ubuntu.com/ubuntu/ multiverse'
sudo apt-get -qq --fix-missing update
sudo apt-get install solr-jetty libcommons-fileupload-java


# PostGIS 2.1 already installed on Travis

echo "Installing CKAN and its Python dependencies..."
git clone https://github.com/ckan/ckan
cd ckan
if [ $CKANVERSION == 'master' ]
then
    echo "CKAN version: master"
else
    CKAN_TAG=$(git tag | grep ^ckan-$CKANVERSION | sort --version-sort | tail -n 1)
    git checkout $CKAN_TAG
    echo "CKAN version: ${CKAN_TAG#ckan-}"
fi

python setup.py develop

pip install -r requirements.txt --allow-all-external
pip install -r dev-requirements.txt --allow-all-external
cd -

echo
echo "Setting up Solr..."
printf "NO_START=0\nJETTY_HOST=127.0.0.1\nJETTY_PORT=8983\nJAVA_HOME=$JAVA_HOME" | sudo tee /etc/default/jetty
sudo cp ckan/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml
sudo sed -i -e 's-</fields>-<field name="dcat_theme" type="string" indexed="true" stored="false" multiValued="true"/>\n</fields>-g' /etc/solr/conf/schema.xml
sudo sed -i -e 's-</fields>-<field name="dcat_subtheme" type="string" indexed="true" stored="false" multiValued="true"/>\n</fields>-g' /etc/solr/conf/schema.xml
sudo sed -i -e 's-</fields>-<field name="dcat_subtheme_*" type="string" indexed="true" stored="false" multiValued="true"/>\n</fields>-g' /etc/solr/conf/schema.xml
sudo sed -i -e 's-</fields>-<field name="organization_region_*" type="string" indexed="true" stored="false" multiValued="false"/>\n</fields>-g' /etc/solr/conf/schema.xml
sudo sed -i -e 's-</fields>-<field name="resource_license_*" type="string" indexed="true" stored="false" multiValued="true"/>\n</fields>-g' /etc/solr/conf/schema.xml
sudo sed -i -e 's-</fields>-<field name="resource_license" type="string" indexed="true" stored="false" multiValued="true"/>\n</fields>-g' /etc/solr/conf/schema.xml

sudo service jetty restart

echo
echo "Creating the PostgreSQL user and database..."

sudo -u postgres psql -c "CREATE USER ckan_default WITH PASSWORD 'pass';"
sudo -u postgres psql -c "CREATE USER datastore_default WITH PASSWORD 'pass';"
sudo -u postgres psql -c 'CREATE DATABASE ckan_test WITH OWNER ckan_default;'
sudo -u postgres psql -c 'CREATE DATABASE datastore_test WITH OWNER ckan_default;'

echo
echo "Setting up PostGIS on the database..."

sudo -u postgres psql -d ckan_test -c 'CREATE EXTENSION postgis;'
sudo -u postgres psql -d ckan_test -c 'ALTER VIEW geometry_columns OWNER TO ckan_default;'
sudo -u postgres psql -d ckan_test -c 'ALTER TABLE spatial_ref_sys OWNER TO ckan_default;'

echo "Install other libraries required..."
sudo apt-get install python-dev libxml2-dev libxslt1-dev libgeos-c1

echo "Initialising the database..."
cd ckan
paster db init -c test-core.ini
cd -

echo "Installing ckanext-harvest and its requirements..."
git clone https://github.com/ckan/ckanext-harvest
cd ckanext-harvest
python setup.py develop
pip install -r pip-requirements.txt --allow-all-external
paster harvester initdb -c ../ckan/test-core.ini
cd -

echo "Installing ckanext-dcat and its requirements..."
git clone https://github.com/ckan/ckanext-dcat
cd ckanext-dcat
python setup.py develop
pip install -r requirements.txt --allow-all-external
cd -

echo "Installing ckanext-spatial and its requirements..."
git clone https://github.com/ckan/ckanext-spatial
cd ckanext-spatial
python setup.py develop
pip install -r pip-requirements.txt --allow-all-external
paster spatial initdb -c ../ckan/test-core.ini
cd -

echo "Installing ckanext-multilang and its requirements..."
git clone https://github.com/geosolutions-it/ckanext-multilang
cd ckanext-multilang
python setup.py develop
paster multilangdb initdb -c ../ckan/test-core.ini
cd -

echo "Installing ckanext-dcatapit and its requirements..."
python setup.py develop
pip install -r dev-requirements.txt
paster vocabulary initdb -c ckan/test-core.ini

echo "Moving test.ini into a subdir..."
mkdir subdir
mv test.ini subdir

echo "travis-build.bash is done."
