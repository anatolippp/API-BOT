import os
import requests

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")


def google_search(query: str, country: str, language: str, domain: str) -> dict:
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "q": query,
        "gl": country,
        "hl": language,
        "googleDomain": domain
    }

    response = requests.post(url, headers=headers, json=payload, timeout=15)
    response.raise_for_status()

    return response.json()
