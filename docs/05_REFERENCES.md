# References

## Course materials

- ECE425525_MidProject_Guidelines.pdf: midpoint requirements and grading.
- [Instructor Overleaf project](https://www.overleaf.com/read/qzzwpbhvqfhm#3acca7): report template, six sample papers, and related tools/videos.
- Earlier project approach and brainstorming sheet: background for the current scope.

The six sample papers and their associated tools/videos need review before the report is finalized.

## Technical references

| Source | Use |
| --- | --- |
| [Lewis et al., Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401) | Research basis for retrieval plus generation |
| [Google embedding documentation](https://ai.google.dev/gemini-api/docs/embeddings) | Embedding adapter and query/document formats |
| [Google structured outputs](https://ai.google.dev/gemini-api/docs/structured-output) | Generation response schemas and limits |
| [Reciprocal Rank Fusion](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion) | Combining ranked retrieval results |
| [Streamlit forms](https://docs.streamlit.io/develop/concepts/architecture/forms) | Explicit form submission |
| [Streamlit caching and state](https://docs.streamlit.io/get-started/fundamentals/advanced-concepts) | Reusing computations and managing interaction state |
| [Streamlit authentication](https://docs.streamlit.io/develop/concepts/connections/authentication) | Sign-in for the hosted pilot |
| [Adzuna search](https://developer.adzuna.com/docs/search) | Listings, filters, and available description snippets |

Technical references were checked October 22, 2026. Account access, model availability, SDK behavior, and provider limits still need implementation testing.

Gemini Embedding 2 is the initial 2026 technology candidate. RAG, BM25, cosine similarity, and RRF are established methods. Other researched models and graph methods are optional follow-up experiments.

## Academic sources

The starter collection uses current catalog entries for [ECE101](https://catalog.arizona.edu/courses/0432351), [ECE369A](https://catalog.arizona.edu/courses/0366021), [ECE372A](https://catalog.arizona.edu/courses/0367521), [ECE425](https://catalog.arizona.edu/courses/0435981), and [CSC120](https://catalog.arizona.edu/courses/0393701). Their public course enrollment fields expose requirement IDs. Four ECE rules remain unknown. The collection stores paraphrased summaries, links, and description hashes.

The [current Computer Science program requirements](https://catalog.arizona.edu/programs/COSCBS/program-requirements-a1nCj), foundation section R1299/L40, provide a reviewed CSC120 condition. The app links this source and evaluates its alternatives separately. Department guidance lists different alternatives, so unusual substitutions still need advisor confirmation. This condition does not establish complete enrollment eligibility.

The initial resources are [PyTorch Quickstart](https://docs.pytorch.org/tutorials/beginner/basics/quickstart_tutorial.html) and [CS50 OpenCourseWare](https://cs50.harvard.edu/x/).

Use the [University of Arizona Catalog](https://catalog.arizona.edu/) for the relevant catalog edition and official course requirements. Program requirements come from the corresponding degree/program entry. Dated syllabi and department pages can provide additional topic information.

Source review matters even on official domains:

- [ECE 175](https://ece.engineering.arizona.edu/undergrad-programs/courses/ECE175) and [ECE 369A](https://ece.engineering.arizona.edu/undergrad-programs/courses/ECE369A) include descriptions labeled as 2021–2022 catalog data.
- The [ECE 414A page](https://ece.engineering.arizona.edu/undergrad-programs/courses/ECE414A) has a photovoltaic title and learning outcomes, but a computer-architecture description.
- The [ECE 525 entry](https://ece.engineering.arizona.edu/grad-programs/courses/ECE525) is graduate-level. Its relationship to ECE 425 does not establish interchangeable enrollment rules.

These notes came from the October 22 source review. Verify the appropriate catalog entry before using any of these pages as current academic evidence.

## Collection procedure

Resolve actual course links, capture the original prerequisite wording, record edition/URL/retrieval time/hash, and review the record before marking it verified. Preserve alternatives and concurrent-enrollment conditions.

Start with five manually reviewed courses if automated extraction takes too long. Include supporting prerequisites outside ECE when needed. Later, automate the same process and review changed fields.

Use original provider pages for online resources and actual job-provider responses for opportunities. Record check dates. A retrieval timestamp does not establish when a resource was published or whether a job remains open.
