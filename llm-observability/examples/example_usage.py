from llmobs.client import LLMObserver


def main() -> None:
    observer = LLMObserver(
        api_base_url="http://localhost:8000",
        ollama_base_url="http://localhost:11434",
    )

    prompt = "Summarize observability best practices for LLM apps in 3 bullet points."
    response = observer.call_ollama(
        model="llama3.1",
        prompt=prompt,
        prompt_template_id=None,
    )

    print("Model response:")
    print(response.get("response", ""))


if __name__ == "__main__":
    main()
