# Evaluation Patterns Guide

Patterns and best practices for evaluating LangGraph agents.

## When to Evaluate

### Development Phase

- After implementing new features
- When changing prompts or models
- Before deploying to production
- During A/B testing

### Production Phase

- Continuous monitoring
- After model updates
- When user feedback indicates issues
- Periodic quality audits

## Evaluation Types

### 1. Unit Evaluation

Test individual components in isolation.

```python
# Test a single function
def test_retriever():
    docs = retriever.search("test query")
    assert len(docs) > 0
    assert all(doc.score > 0.5 for doc in docs)
```

### 2. Integration Evaluation

Test the complete pipeline.

```python
# Test full agent
def test_agent_response():
    response = agent.invoke({"question": "What is 2+2?"})
    assert "4" in response["answer"]
```

### 3. Regression Evaluation

Compare against baseline performance.

```python
# Compare model versions
baseline_results = evaluate(baseline_agent, dataset)
new_results = evaluate(new_agent, dataset)

assert new_results["accuracy"] >= baseline_results["accuracy"]
```

### 4. A/B Evaluation

Compare two approaches head-to-head.

```python
# Pairwise comparison
for example in dataset:
    response_a = agent_a.invoke(example)
    response_b = agent_b.invoke(example)
    winner = judge.compare(response_a, response_b)
```

## Metric Types

### Exact Match

```python
def exact_match(prediction, reference):
    return 1.0 if prediction.strip().lower() == reference.strip().lower() else 0.0
```

Best for: Factual Q&A, classification, entity extraction

### Fuzzy Match

```python
def fuzzy_match(prediction, reference):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, prediction, reference).ratio()
```

Best for: Near-exact matching with typo tolerance

### Semantic Similarity

```python
def semantic_similarity(prediction, reference, embeddings):
    pred_vec = embeddings.embed(prediction)
    ref_vec = embeddings.embed(reference)
    return cosine_similarity(pred_vec, ref_vec)
```

Best for: Paraphrase detection, meaning comparison

### LLM-as-Judge

```python
def llm_judge(prediction, reference, question):
    prompt = f"Is this answer correct? Q: {question}, A: {prediction}, Ref: {reference}"
    return judge_llm.invoke(prompt)
```

Best for: Nuanced evaluation, complex criteria

## Evaluation Dimensions

### Correctness

Is the answer factually accurate?

```python
evaluators = [
    exact_match_evaluator,
    correctness_judge
]
```

### Groundedness

Is the answer supported by context?

```python
def groundedness(answer, context):
    """Check if all claims are in context."""
    return judge.evaluate_groundedness(answer, context)
```

### Relevance

Does the answer address the question?

```python
def relevance(answer, question):
    """Check if answer is relevant to question."""
    return judge.evaluate_relevance(answer, question)
```

### Completeness

Does the answer cover all aspects?

```python
def completeness(answer, expected_points):
    """Check if all expected points are covered."""
    covered = sum(1 for p in expected_points if p in answer)
    return covered / len(expected_points)
```

### Coherence

Is the answer well-structured?

```python
def coherence(answer):
    """Check logical flow and clarity."""
    return judge.evaluate_coherence(answer)
```

### Harmlessness

Is the answer safe and appropriate?

```python
def harmlessness(answer):
    """Check for harmful content."""
    return safety_classifier.check(answer)
```

## Evaluation Strategy

### Golden Set Evaluation

Maintain a curated set of high-quality examples.

```python
golden_set = [
    {"input": "...", "output": "...", "quality": "high"},
    # Carefully curated examples
]

# Always evaluate against golden set
results = evaluate(agent, golden_set, evaluators)
```

### Stratified Evaluation

Evaluate across different categories.

```python
categories = ["easy", "medium", "hard"]

for category in categories:
    subset = dataset.filter(difficulty=category)
    results[category] = evaluate(agent, subset)
```

### Sliding Window Evaluation

Track performance over time.

```python
window_size = 100
recent_scores = scores[-window_size:]
moving_average = sum(recent_scores) / len(recent_scores)
```

## Common Pitfalls

### 1. Overfitting to Test Set

- Use held-out test sets
- Regularly update evaluation data
- Don't tune on test results

### 2. Insufficient Coverage

- Include edge cases
- Test different question types
- Cover various difficulty levels

### 3. Metric Gaming

- Use multiple metrics
- Include human evaluation
- Monitor for regression in unmeasured areas

### 4. Ignoring Distribution Shift

- Regularly sample production data
- Update evaluation sets
- Track domain-specific performance

## Best Practices

### 1. Use Multiple Evaluators

```python
evaluators = [
    exact_match_evaluator,
    semantic_similarity_evaluator,
    correctness_judge,
    fluency_evaluator
]
```

### 2. Track Over Time

```python
experiment = {
    "date": datetime.now(),
    "model": "gemini-2.5-flash",
    "scores": results,
    "config": agent_config
}
history.append(experiment)
```

### 3. Automate CI/CD

```yaml
# GitHub Actions
- name: Run Evaluation
  run: python evaluate.py --dataset qa_test --threshold 0.85
```

### 4. Include Human Review

```python
# Sample for human review
sample = random.sample(results, 10)
for result in sample:
    human_grade = get_human_feedback(result)
    correlate_with_auto(result, human_grade)
```

## Evaluation Checklist

```markdown
Pre-Evaluation:
- [ ] Dataset is up to date
- [ ] Evaluators are appropriate for task
- [ ] Baseline metrics are established
- [ ] Test environment matches production

During Evaluation:
- [ ] Run on representative sample
- [ ] Check for errors/failures
- [ ] Monitor latency and costs

Post-Evaluation:
- [ ] Compare to baseline
- [ ] Document findings
- [ ] Update tracking systems
- [ ] Plan improvements
```
