# OpenRouter Free-Model Notes

Checked October 23, 2026, Arizona time.

The supplied OpenRouter credential works. The Hello World request succeeded through `openrouter/free` and reported cost **0**. OpenRouter is a development option; it is not connected to the Streamlit app. The working application still uses Gemini.

## Required cost policy

Use this OpenRouter access only with free models. Start with `openrouter/free`; a specific `:free` variant can be used after checking its availability and zero pricing. Set prompt and completion price ceilings to zero. Do not add paid model fallbacks, paid routing aliases, or paid add-ons. When free capacity is unavailable, report the limitation and retain the retrieved source information.

The tested request preference was:

```json
{
  "provider": {
    "max_price": {"prompt": 0, "completion": 0}
  }
}
```

For a future integration, keep the key in server configuration or a local environment variable. Never include it in source files or saved traces. No credential value was saved with these tests.

## Results

| Check | Outcome | Reported cost |
| --- | --- | --- |
| Hello World using `openrouter/free` | Passed; returned a Python print statement in 5.901 s | 0 |
| Free-router RAG with JSON Schema | HTTP 429 from the shared upstream free pool | No usage returned |
| One free-router retry | HTTP 200, but all 1,800 output tokens were consumed by reasoning; no JSON answer | 0 |
| Fixed free model with reasoning disabled | HTTP 200 in 9.309 s; valid JSON, but an overly restrictive abstention | 0 |

The Hello World router selected `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`. The later structured request selected `nvidia/nemotron-3.5-super-vl:free`; that same free variant was tested with `reasoning.enabled=false`. These are observed model choices, not a quality ranking or a guarantee of future availability.

The RAG experiments used the existing keyword retriever and a synthetic incoming-student profile with AI/hardware interests. They passed the real retrieved evidence, allowed course IDs, application rule results, and the existing answer schema to OpenRouter. No Gemini embedding or generation calls were made for these experiments.

The final model declined to recommend anything because the student's enrollment eligibility was unresolved. That is too restrictive for the intended learning-plan explanation: it should preserve unknown eligibility while still explaining supported courses and resources. Its empty recommendation list does not demonstrate successful citation use. This provider has not passed the project's full RAG acceptance check.

## Integration decision

Keep Gemini as the current application generator. Before adding OpenRouter as a selectable option, test a free model that reliably produces useful source-grounded recommendations, record which model actually served each request, handle free-pool rate limits and empty output, and enforce the free-only policy in the adapter. An OpenRouter generation option would still need a separately configured embedding provider for semantic retrieval; this test does not make the whole application free.

The current AI key field accepts Gemini credentials. OpenRouter needs its own generation adapter before it can be selected. The saved key-free evidence is in [the test trace](evidence/openrouter_free_2026-10-23.json). Existing application code was not changed by this review.

## Official references

- [Free-model collection](https://openrouter.ai/collections/free-models)
- [Free Models Router](https://openrouter.ai/docs/guides/routing/routers/free-router)
- [Provider selection and maximum price](https://openrouter.ai/docs/guides/routing/provider-selection)
- [Structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
