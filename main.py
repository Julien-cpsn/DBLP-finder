import requests
import json
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

def askChatGPT(keywords: str, publications: str):
    prompt = f"""Ton rôle est de trouver les publications en rapport avec des mots clés depuis une liste de publication donnée. Tu ne dois ni créer de mot clé, ni de publication.
    
    Mots clés:
    {keywords}

    Publications:
    {publications}"""

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-4o-mini",
    )

    print(chat_completion.choices[0].message.content)

def main():
    conf_name = input("Which conference to search for?\n")

    confs_response = requests.get(f"https://dblp.org/search/venue/api?q={conf_name}&format=json")
    confs_json_response = json.loads(confs_response.text)

    hits = confs_json_response['result']['hits']['hit']

    for hit in hits:
        acronym = str.lower(hit['info']['acronym'])
        url = hit['info']['url']

        print(f"Found conference: {acronym}")
        print(url)
        print()

        publ_response = requests.get(f"https://dblp.org/search/publ/api?q=stream%3Astreams%2Fconf%2F{acronym}%3A&h=1000&format=json")
        publ_json_response = json.loads(publ_response.text)

        publications = publ_json_response['result']['hits']['hit']

        print(f"Found {len(publications)} papers:")

        publications_str = ""

        for publication in publications:
            title = publication['info']['title']
            publications_str += f"- {title}\n"
        
        print(publications_str)

        askChatGPT("- Fork\n- Unikernel", publications_str)


if __name__ == "__main__":
    main()
