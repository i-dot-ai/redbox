# Large Language Model Setup

Redbox uses LiteLLM as an abstract wrapper around different Large Language Models (LLMs). This allows us to switch between different LLMs without changing the codebase. Currently, we have tested the following LLM providers:

- [OpenAI](https://platform.openai.com/docs/models)
    - `gpt-3.5-turbo`
    - `gpt-3.5-16k`
    - `gpt-4`
    - `gpt-4-32k`
    - `gpt-4-turbo`
    - `gpt-4o`
- [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models)
    - `gpt-3.5-turbo`
    - `gpt-3.5-16k`
    - `gpt-4`
    - `gpt-4-32k`
    - `gpt-4-turbo`
    - `gpt-4o`

Please note that exclusion from this list does not mean that the LLM is not supported, it just means that we have not tested it yet. If you would like to use a different LLM, please refer to the [LiteLLM documentation](https://docs.litellm.ai/docs/providers)

## OpenAI

To use OpenAI as the LLM provider, you will need to set the following environment variables in your `.env` file:

```bash
OPENAI_API_KEY=your_openai_api_key
```

## Azure OpenAI Service

To use Azure OpenAI Service as the LLM provider, you will need to set the following environment variables in your `.env` file:

```bash
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
AZURE_OPENAI_MODEL=azure/your_azure_openai_deployment_name
```

!!! info "LiteLLM Note"
    Please note that `AZURE_OPENAI_MODEL` has `azure/` as a prefix. This is because LiteLLM uses the `provider/model` format to specify the model.

## Other Providers

Redbox would welcome any contributions to add support for other LLM providers. If you would like to add support for a new provider, please refer to the [LiteLLM documentation](https://docs.litellm.ai/docs/providers) and create a pull request with the necessary changes. Please refer to the contribution guidelines for more information on how to contribute to Redbox.