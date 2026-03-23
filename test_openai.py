import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load environment variables
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
openai_model = os.getenv("OPENAI_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")


async def test_openai_call():
    client = AsyncOpenAI(api_key=openrouter_api_key, base_url=openrouter_base_url)

    try:
        response = await client.chat.completions.create(
            model=openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "Extract key entities from questions. Return only entity names.",
                },
                {
                    "role": "user",
                    "content": "Extract the key entities from this question. Return a JSON array of entity names. Question: What is the current geopolitical situation in Ukraine?",
                },
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        print("Success! OpenAI API call worked.")
        print(f"Response: {content}")
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    import asyncio

    result = asyncio.run(test_openai_call())
    print(f"Test result: {'PASS' if result else 'FAIL'}")
