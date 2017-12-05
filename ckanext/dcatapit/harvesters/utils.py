import json
import logging
import re

from ckan.model import Session
from ckan.model import Tag

from ckanext.dcatapit.model import DCATAPITTagVocabulary
from ckanext.dcatapit.model.license import License

log = logging.getLogger(__name__)

## Mapping between ISO frequencies and DCAT_AP-IT frequencies
_mapping_frequencies_to_mdr_vocabulary = {
    'biannually' : 'BIENNIAL',
    'asNeeded' : 'IRREG',
    'quarterly' : 'QUARTERLY',
    'fortnightly' : 'BIWEEKLY',
    'annually' : 'ANNUAL',
    'monthly' : 'MONTHLY',
    'weekly' : 'WEEKLY',
    'daily' : 'DAILY',
    'continual' : 'CONT',
    'notPlanned' : 'UNKNOWN',
    'irregular' : 'IRREG',
    'unknown' : 'UNKNOWN'
}

_mapping_languages_to_mdr_vocabulary = {
    'ita': 'ITA',
    'ger': 'DEU',
    'eng': 'ENG'
}

def get_responsible_party(citedResponsiblePartys, agent_config):
    for party in citedResponsiblePartys:
        role = agent_config.get('role', None)
        if not role:
            log.warning("Warning: Agent role missing in harvest configuration ...")

        if party["role"] == role:
            publisher_name = party["organisation-name"]
            agent_code, agent_name = get_agent(publisher_name, agent_config)

            name = agent_name or publisher_name

            if publisher_name:
                code = agent_code or agent_config.get('code', None)

            return [name, code]
    return [None, None]

def get_controlled_vocabulary_values(vocabulary_id, thesaurus_id, keywords):
    log.debug('::::: Collecting thesaurus data for dcatapit skos {0} from the metadata keywords :::::'.format(vocabulary_id))

    values = []

    #
    # Get all the places tag names by the vocabulary id
    #
    tag_names_list = get_vocabulary_tag_names(vocabulary_id)

    if len(tag_names_list) > 0:
        for key in keywords:
            if thesaurus_id and (thesaurus_id in key['thesaurus-identifier'] or thesaurus_id in key['thesaurus-title']):
                for k in key['keyword']:
                    query = Session.query(DCATAPITTagVocabulary) \
                        .filter(DCATAPITTagVocabulary.text==k, DCATAPITTagVocabulary.tag_name.in_(tag_names_list))
                    query = query.autoflush(True)
                    theme = query.first()

                    if theme and theme.tag_name:
                        values.append(theme.tag_name)
    return values

def get_vocabulary_tag_names(vocab_id_or_name):
    tag_names_list = []

    try:
        log.debug("Finding tag names by vocabulary \
            id or name for vocabulary {0}".format(vocab_id_or_name))
        tags = Tag.all(vocab_id_or_name)

        if tags:
            for tag in tags:
                tag_names_list.append(tag.name)
                log.debug("Tag name for tag {0} collected".format(tag.name))
        pass
    except Exception, e:
        log.error('Exception occurred while finding eu_themes tag names: %s', e)

    return tag_names_list

def get_agent(agent_string, agent_config):
    ## Agent Code
    code_regex = agent_config.get('code_regex', None)
    agent_code = re.search(code_regex.get('regex'), agent_string) if code_regex and code_regex.get('regex') else None

    if agent_code:
        regex_groups = code_regex.get('groups', None)

        if regex_groups:
            code = ''
            if isinstance(regex_groups, list) and len(regex_groups) > 0:
                for group in regex_groups:
                    code += agent_code.group(group)
            else:
                code = agent_code.group(regex_groups)

            agent_code = code

        agent_code = agent_code.lower().strip()

    ## Agent Name
    name_regex = agent_config.get('name_regex', None)
    agent_name = re.search(name_regex.get('regex'), agent_string) if name_regex and name_regex.get('regex') else None

    if agent_name:
        regex_groups = name_regex.get('groups', None)

        if regex_groups:
            code = ''
            if isinstance(regex_groups, list) and len(regex_groups) > 0:
                for group in regex_groups:
                    code += agent_name.group(group)
            else:
                code = agent_name.group(regex_groups)

            agent_name = code

        agent_name = agent_name.lstrip()

    return [agent_code, agent_name]

def get_license_from_package(pkg_dict):
    """
    Returns license from package
    """

    for_license = pkg_dict.get('license_title')
    license, fallback = License.find_by_token(for_license or 'Unknown')
    if fallback:
        log.warning("Got fallback license for %s", for_license)
    return license


def map_ckan_license(harvest_object=None, pkg_dict=None):
    """
    license in resources' extra:
        if it exists, perform simple validation. If not valid, replace with the unknown license type
        if it does not exist, try to map the dataset's license to a license in the controlled voc
        fallback to the unknown license type
    :param harvest_object:
    :param pkg_dict:
    :type harvest_object: HarvestObject model
    :type pkg_dict: dict dictized dataset

    :return: This will return dataset's dict with modified licenses
    :rtype: dict with dictized dataset
    """
    if not (harvest_object or pkg_dict) or (harvest_object and pkg_dict):
        raise ValueError("You should provide either harvest_object or pkg_dict")
    
    if harvest_object:
        data = json.loads(harvest_object.content)
    else:
        data = pkg_dict

    dataset_license = get_license_from_package(data)

    for res in data.get('resources') or []:
        if res.get('license_type'):
            l, _ = License.find_by_token(res['license_type'])
            res['license_type'] = l.uri
        else:
            res['license_type'] = dataset_license.uri
    return data
