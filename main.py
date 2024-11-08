import requests
import json
import os
from openai import OpenAI
from bs4 import BeautifulSoup

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

JSON_SCHEMA = """
{
    "titles": {
        "type": "array",
        "items": {
            "type": "string"
        }
    }
}
"""

PUBLICATIONS_FOUND = {}


def find_conferences(conference_name: str):
    """
    Find matching conferences from DBPL for the given conference name.

    :param conference_name:
    :return:
    """

    conferences_response = requests.get(f"https://dblp.org/search/venue/api?q={conference_name}&format=json")
    conferences_json_response = json.loads(conferences_response.text)

    matches = conferences_json_response['result']['hits']['hit']

    return matches

def find_publications(conference_acronym: str):
    """
    Find all the publications for a given conference.

    :param conference_acronym:
    :return:
    """

    publications_response = requests.get(f"https://dblp.org/search/publ/api?q=stream%3Astreams%2Fconf%2F{conference_acronym}%3A&h=1000&format=json")
    publications_response_json = json.loads(publications_response.text)

    publications = publications_response_json['result']['hits']['hit']

    return publications

def process_conference(conference: dict, keywords: str):
    """
    Retrieve publications for the given conference and tries to match keywords to publication titles.

    :param conference:
    :param keywords:
    :return:
    """

    acronym = conference['info']['acronym']
    acronym_lower = str.lower(acronym)
    url = conference['info']['url']

    print(f"Found conference: {acronym}")
    print(url)
    print()

    publications = find_publications(acronym_lower)
    publications_size = len(publications)

    print(f"Found {publications_size} papers")

    for index in range(0, publications_size, 50):
        batch = publications[index:index+50]
        process_batch(batch, keywords)

    print("Matching publications:")

    for title in PUBLICATIONS_FOUND:
        if PUBLICATIONS_FOUND[title]['matching']:
            link = PUBLICATIONS_FOUND[title]['ee']
            print(f"\t- {title} | {link}")

def process_batch(batch: list[dict], keywords: str):
    """
    Retrieve matching publications for the given batch.

    :param batch:
    :param keywords:
    :return:
    """
    batch_str = ""

    for publication in batch:
        title = publication['info']['title']

        batch_str += f"- {title}\n"
        PUBLICATIONS_FOUND[title] = publication['info']
        PUBLICATIONS_FOUND[title]['matching'] = False

    matching_publications_title = ask_chat_gpt(keywords, batch_str)

    for title in matching_publications_title:
        if title not in PUBLICATIONS_FOUND:
            continue

        if 'doi' in PUBLICATIONS_FOUND[title]:
            doi = PUBLICATIONS_FOUND[title]['doi']
            abstract = retrieve_abstract(doi)
            PUBLICATIONS_FOUND[title]['abstract'] = abstract

        PUBLICATIONS_FOUND[title]['matching'] = True

def ask_chat_gpt(keywords: str, publications: str):
    """
    Ask ChatGPT to match publications title for the given keywords.

    :param keywords:
    :param publications:
    :return:
    """

    prompt = f"""Your role is to find scientific publications linked to given keywords. You will only search in the given publication list with the given keyword list.
    
    Keywords :
    {keywords}

    Scientific publications :
    {publications}"""

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": f"""You are a helpful assistant designed to output JSON that follows the following json schema:\n{JSON_SCHEMA}"""
            },
            {

                "role": "user",
                "content": prompt,
            }
        ],
        response_format={
            "type": "json_object"
        },
        model="gpt-4o-mini",
    )

    chat_gpt_response = chat_completion.choices[0].message.content
    chat_gpt_response_json = json.loads(chat_gpt_response)

    publication_titles_found = chat_gpt_response_json['titles']

    if publication_titles_found is str:
        publication_titles_found = [publication_titles_found]

    return publication_titles_found


def retrieve_abstract(doi: str):
    """
    Retrieve the abstract for the given doi.

    :param doi:
    :return:
    """

    doi_response = requests.get(f"https://doi.org/{doi}")
    doi_response_html = doi_response.text

    soup = BeautifulSoup(doi_response_html, 'html.parser')

    if "acm" in doi_response.url:
        abstract_section = soup.find("section", {"id": "abstract"})
        abstract = abstract_section.div.text
    else:
        abstract = "Not found"

    return abstract


def main():
    conf_name = input("Which conference to search for?\n")
    keywords = input("What are you key words?\n")
    print()

    conferences = find_conferences(conf_name)

    for conference in conferences:
        process_conference(conference, keywords)

if __name__ == "__main__":
    main()
