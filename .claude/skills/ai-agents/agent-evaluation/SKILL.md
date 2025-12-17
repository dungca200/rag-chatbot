---
name: agent-evaluation
description: Test and evaluate LangGraph agents systematically. Covers dataset creation, custom evaluators, LLM-as-judge patterns with Gemini, and automated benchmarking. Use when building evaluation pipelines, comparing model versions, or measuring agent quality.
license: Complete terms in LICENSE.txt
---

# Agent Evaluation Guide

## Overview

Systematically evaluate LangGraph agents using datasets, custom evaluators, and LLM-as-judge patterns with Gemini.

**Evaluation Stack:**
```
Datasets      → Test cases with inputs and expected outputs
Evaluators    → Scoring functions (exact match, similarity, LLM judge)
Experiments   → Track results across model versions
Analysis      → Compare performance and identify issues
```

## Quick Start

### Quick Evaluation (No Dataset Required)

```python
from scripts.evaluation_runner import quick_eval, contains_evaluator

def my_agent(inputs):
    # Your agent logic
    return {"answer": "Paris is the capital of France"}

test_cases = [
    {
        "inputs": {"question": "What is the capital of France?"},
        "outputs": {"answer": "Paris", "keywords": ["paris", "capital"]}
    }
]

results = quick_eval(
    target_function=my_agent,
    test_cases=test_cases,
    evaluators=[contains_evaluator]
)

print(f"Average score: {results['scores']['contains_keywords']['average']:.2f}")
```

### LLM-as-Judge Evaluation

```python
from scripts.llm_judge import CorrectnessJudge

judge = CorrectnessJudge()

result = judge.evaluate(
    question="What is the capital of France?",
    answer="The capital of France is Paris.",
    reference="Paris"
)

print(f"Correct: {result['score']}")
print(f"Reasoning: {result['reasoning']}")
```

### Dataset-Based Evaluation

```python
from langsmith.evaluation import evaluate
from scripts.evaluation_runner import exact_match_evaluator
from scripts.llm_judge import correctness_evaluator

results = evaluate(
    target_function=my_agent,
    data="qa_test_set",  # LangSmith dataset
    evaluators=[exact_match_evaluator, correctness_evaluator],
    experiment_prefix="qa_eval"
)
```

## Custom Evaluators

### Built-in Evaluators

```python
from scripts.custom_evaluators import EvaluatorFactory

# Get individual evaluator
exact_match = EvaluatorFactory.get("exact_match")
jaccard = EvaluatorFactory.get("jaccard")
fluency = EvaluatorFactory.get("fluency")

# Create evaluation suite
suite = EvaluatorFactory.create_suite([
    "exact_match",
    "jaccard",
    "fluency",
    "relevance"
])

# List available
print(EvaluatorFactory.list_available())
```

### Text Similarity Evaluators

```python
from scripts.custom_evaluators import (
    jaccard_similarity_evaluator,
    cosine_similarity_evaluator,
    levenshtein_evaluator
)

# Use in evaluation
evaluators = [
    jaccard_similarity_evaluator,
    cosine_similarity_evaluator,
    levenshtein_evaluator
]
```

### Semantic Similarity

```python
from scripts.custom_evaluators import semantic_similarity_evaluator
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
semantic_eval = semantic_similarity_evaluator(embeddings)
```

### Composite Evaluators

```python
from scripts.custom_evaluators import create_composite_evaluator

composite = create_composite_evaluator([
    ("jaccard", jaccard_similarity_evaluator, 0.3),
    ("fluency", fluency_evaluator, 0.3),
    ("relevance", relevance_evaluator, 0.4),
])
```

## LLM-as-Judge

### Correctness Judge

```python
from scripts.llm_judge import CorrectnessJudge

judge = CorrectnessJudge()
result = judge.evaluate(
    question="What is 2+2?",
    answer="4",
    reference="The answer is 4"
)
# {"key": "correctness", "score": 1.0, "reasoning": "..."}
```

### Groundedness Judge

```python
from scripts.llm_judge import GroundednessJudge

judge = GroundednessJudge()
result = judge.evaluate(
    context="Python was created by Guido van Rossum in 1991.",
    question="When was Python created?",
    answer="Python was first released in 1991."
)
# {"key": "groundedness", "score": 1.0, "raw_score": 5, "reasoning": "..."}
```

### Multi-Criteria Judge

```python
from scripts.llm_judge import MultiCriteriaJudge

judge = MultiCriteriaJudge()
result = judge.evaluate(
    question="Explain machine learning",
    answer="Machine learning is..."
)
# Returns scores for: relevance, accuracy, completeness, clarity, overall
```

### Custom Criteria

```python
from scripts.llm_judge import create_custom_evaluator

technical_accuracy = create_custom_evaluator(
    criteria="Technical Accuracy",
    description="Is the technical information correct and precise?"
)
```

### Pairwise Comparison

```python
from scripts.llm_judge import PairwiseJudge

judge = PairwiseJudge()
result = judge.compare(
    question="What is Python?",
    answer_a="Python is a programming language.",
    answer_b="Python is a type of snake."
)
# {"winner": "A", "reasoning": "..."}
```

## Dataset Management

### Local Datasets

```python
from scripts.dataset_management import LocalDataset

# Create dataset
dataset = LocalDataset("qa_test", "Q&A evaluation set")

# Add examples
dataset.add_example(
    inputs={"question": "What is 2+2?"},
    outputs={"answer": "4"},
    metadata={"difficulty": "easy"}
)

# Save and load
dataset.save("datasets/qa_test.json")
loaded = LocalDataset.load("datasets/qa_test.json")
```

### Dataset Templates

```python
from scripts.dataset_management import DatasetTemplates

# Q&A dataset
qa = DatasetTemplates.qa_dataset([
    ("What is Python?", "A programming language"),
    ("What is 2+2?", "4")
])

# RAG dataset
rag = DatasetTemplates.rag_dataset([
    ("Context here", "Question?", "Answer")
])

# Classification dataset
cls = DatasetTemplates.classification_dataset([
    ("Great product!", "positive"),
    ("Terrible.", "negative")
])
```

### Dataset Splits

```python
# Train/test split
train, test = dataset.split(train_ratio=0.8, seed=42)

# Filter by metadata
easy_examples = dataset.filter(difficulty="easy")
```

### LangSmith Integration

```python
from scripts.dataset_management import LangSmithDatasetManager

manager = LangSmithDatasetManager()

# Create dataset
manager.create_dataset("qa_eval", "Q&A evaluation set")

# Add examples
manager.add_examples("qa_eval", [
    {"inputs": {"question": "..."}, "outputs": {"answer": "..."}}
])

# Upload local dataset
manager.upload_local_dataset(local_dataset)

# Download to local
local = manager.download_to_local("langsmith_dataset")
```

### Dataset Versioning

```python
from scripts.dataset_management import DatasetVersionManager

manager = DatasetVersionManager("datasets/")

# Save version
manager.save_version(dataset, "1.0.0")

# Load version
dataset_v1 = manager.load_version("my_dataset", "1.0.0")

# Compare versions
diff = manager.compare_versions("my_dataset", "1.0.0", "1.1.0")
```

## Running Evaluations

### With LangSmith

```python
from langsmith.evaluation import evaluate

results = evaluate(
    target_function=my_agent,
    data="dataset_name",
    evaluators=[evaluator1, evaluator2],
    experiment_prefix="experiment_v1",
    metadata={"model": "gemini-2.5-flash"}
)
```

### Experiment Comparison

```python
from scripts.evaluation_runner import ExperimentComparison

comparison = ExperimentComparison()
comparison.add_experiment("v1", results_v1)
comparison.add_experiment("v2", results_v2)

print(comparison.summary_table())
print(comparison.compare("correctness"))
```

### Batch Evaluation

```python
from scripts.evaluation_runner import run_batch_evaluation

results = run_batch_evaluation(
    target_functions={
        "baseline": baseline_agent,
        "improved": improved_agent
    },
    dataset_name="qa_test",
    evaluators=[exact_match_evaluator, correctness_evaluator]
)
```

## Evaluator Reference

| Evaluator | Type | Description |
|-----------|------|-------------|
| `exact_match` | Text | Exact string match |
| `jaccard` | Text | Word set overlap |
| `cosine` | Text | Word frequency similarity |
| `levenshtein` | Text | Edit distance similarity |
| `fluency` | Quality | Sentence structure check |
| `relevance` | Quality | Question-answer relevance |
| `json_structure` | Structure | JSON schema validation |
| `code_correctness` | Domain | Python syntax check |
| `math_accuracy` | Domain | Numeric answer check |
| `correctness_judge` | LLM | Factual correctness |
| `groundedness_judge` | LLM | Context grounding |
| `coherence_judge` | LLM | Logical structure |
| `helpfulness_judge` | LLM | User helpfulness |

## Environment Variables

```bash
LANGSMITH_API_KEY=lsv2_pt_xxxxx
LANGSMITH_PROJECT=my-evaluations
GOOGLE_API_KEY=your-gemini-api-key
```

## Dependencies

```
langsmith>=0.1.0
langchain>=0.3.0
langchain-google-genai>=2.0.0
pydantic>=2.0.0
```

## Reference Files

- [references/evaluation_patterns.md](references/evaluation_patterns.md) - When and how to evaluate
- [references/llm_judge_guide.md](references/llm_judge_guide.md) - LLM judge prompts and patterns
- [references/dataset_guide.md](references/dataset_guide.md) - Dataset creation and versioning

## Scripts

- `scripts/evaluation_runner.py` - Run evaluations, experiment tracking
- `scripts/custom_evaluators.py` - Text similarity, quality, domain evaluators
- `scripts/llm_judge.py` - Gemini-based LLM judges
- `scripts/dataset_management.py` - Local and LangSmith dataset management
