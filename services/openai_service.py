import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY", "")


def analyze_results_with_openai(search_results: dict) -> str:
    messages = [
        {
            "role": "system",
            "content": "Ты выступаешь в роли помощника, анализирующего поисковую выдачу."
        },
        {
            "role": "user",
            "content": (
                f"Проанализируй следующую Google-выдачу и составь краткое описание:\n"
                f"{search_results}\n"
            )
        }
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=500,
        temperature=0.7,
    )

    analyzed_text = response["choices"][0]["message"]["content"].strip()
    return analyzed_text
