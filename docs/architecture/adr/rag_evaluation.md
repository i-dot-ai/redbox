# Architecture Decision Record (ADR) template <!-- Replace with ADR title -->

This is a template for EdgeX Foundry ADR.

Source: https://docs.edgexfoundry.org/2.3/design/adr/template/


### Submitters

List ADR submitters.

Format:

- Andy Symonds


## Change Log

List the changes to the document, incl. state, date, and PR URL.

State is one of: pending, approved, amended, deprecated.

Date is an ISO 8601 (YYYY-MM-DD) string.

PR is the pull request that submitted the change, including information such as the diff, contributors, and reviewers.

Format:

- \[ADR in review]\(https://github.com/i-dot-ai/redbox/pull/330) 2024-05-13

<!-- - \[Status of ADR e.g. approved, amended, etc.\]\(URL of pull request\) YYYY-MM-DD -->


## Referenced Use Case(s)

List all relevant use case / requirements documents.

ADR requires at least one relevant, approved use case.

Format:

- \[Evaluation of Redbox chat\]\


## Context

Describe:

- We need robust LLM evaluation in place, to give ourselves and users confidence that redbox is working as it should and to avoid undesirable side effects of using LLMs, such as hallucinations that would reduce trust in the tools we are building.

- We conducted a spike on using the [DeepEval framework](https://github.com/confident-ai/deepeval) for RAG evaluation and testing


## Proposed Design

Details of the design (without getting into implementation where possible).

Outline of spike:

- Collect / generate a basic dataset for evaluation (focus on MVP functionality: chat)

- Notebook developed to test /rag endpoint with DeepEval

- Explore and have some ideas/skeleton code for how DeepEval can fit into existing CI-CD pipeline with an eye on integration tests for LLM

- Document main findings in this ADR document


## Considerations

### Pros to using DeepEval
- By following the more traditional testing and metrics driven techniques, we can nicely separately functional, performance, and responsibility testing in different test files

- Offers a thorough evaluation framework for RAG endpoints, but also summarisation and other future functions

- Easily integrates into our CI/CD pipeline

- Bridges unit testing and evaluation for Redbox

#### Cons to using DeepEval
- `DeepEval` synthesizer for generating synthetic data, does not yet create ‘expected_output’ (currently null). The ability to also generate ‘expected_outcome’ will be in next release according to the Discord channel. Given context, DeepEval synthesizer will generate input questions. In the meantime, we can simply generate the expected_outcome using LLM and prompting

- If included in all CI/CD, frontend dev work that is not touching backend will still be running these tests and incuring an LLM cost (albeit small). Perhaps just make some tests to run only when backend directories are changed

- You need to login to Confident AI / use API key to view different evaluations against each other. Not an issue for CI/CD, however, without logging in/paying you cannot really use these evaluations for experimentation and improving your RAG pipeline; if we go another way are we reinventing the wheel? But it would be open source. If we do go another way, e.g. MLFlow + RAGAS metrics, is it still worth using DeepEval for CI/CD over just pytest?

- Monitoring in production and real-time evaluation is only evailable when logging into Confident AI using API / pricing involved

- Still need to check if any data is transmitted to confident AI when you do NO login or if you login once, but no longer want to use Confident AI hosted platform

## Decision

<!-- Document any agreed upon important implementation detail, caveats, future considerations, remaining or deferred design issues.

Document any part of the requirements not satisfied by the proposed design. -->

- Using `DeepEval` hosted platform on Confident AI is not a dealbreaker at the moment, so we can continue with using `DeepEval` for evaluating Redbox chat

- We will still look into if we can combine MLFlow + DeepEval in a separate spike.


## Other Related ADRs

<!-- List any relevant ADRs - such as a design decision for a sub-component of a feature, a design deprecated as a result of this design, etc.. 

Format:

- \[ADR Title\]\(URL\) - Relevance -->


## References

<!-- List additional references.

Format:

- \[Title\]\(URL\) --> 
[Link to Redbox RAG evaluation notebook for this spike](../../../notebooks/evaluation/redbox_rag_evaluation.ipynb)