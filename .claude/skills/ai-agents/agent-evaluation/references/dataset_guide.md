# Dataset Guide

Creating, managing, and versioning evaluation datasets.

## Dataset Structure

### Basic Format

```json
{
  "name": "qa_dataset",
  "description": "Question-answer evaluation set",
  "version": "1.0.0",
  "examples": [
    {
      "id": "uuid-123",
      "inputs": {"question": "What is 2+2?"},
      "outputs": {"answer": "4"},
      "metadata": {"difficulty": "easy"}
    }
  ]
}
```

### LangSmith Format

```python
# Each example has inputs and outputs
example = {
    "inputs": {
        "question": "What is the capital of France?",
        "context": "France is a country in Europe..."
    },
    "outputs": {
        "answer": "Paris",
        "keywords": ["Paris", "capital"]
    }
}
```

## Dataset Types

### Q&A Dataset

```python
qa_examples = [
    {
        "inputs": {"question": "What is Python?"},
        "outputs": {"answer": "A programming language"}
    },
    {
        "inputs": {"question": "What is 2+2?"},
        "outputs": {"answer": "4"}
    }
]
```

### RAG Dataset

```python
rag_examples = [
    {
        "inputs": {
            "context": "Python was created by Guido van Rossum in 1991.",
            "question": "Who created Python?"
        },
        "outputs": {
            "answer": "Guido van Rossum"
        }
    }
]
```

### Classification Dataset

```python
classification_examples = [
    {
        "inputs": {"text": "I love this product!"},
        "outputs": {"label": "positive"}
    },
    {
        "inputs": {"text": "This is terrible."},
        "outputs": {"label": "negative"}
    }
]
```

### Multi-Turn Conversation

```python
conversation_examples = [
    {
        "inputs": {
            "messages": [
                {"role": "user", "content": "Hi!"},
                {"role": "assistant", "content": "Hello!"},
                {"role": "user", "content": "What's 2+2?"}
            ]
        },
        "outputs": {
            "response": "2+2 equals 4."
        }
    }
]
```

## Creating Datasets

### Local Dataset

```python
from scripts.dataset_management import LocalDataset

dataset = LocalDataset("my_dataset", "Description")

dataset.add_example(
    inputs={"question": "..."},
    outputs={"answer": "..."},
    metadata={"source": "manual"}
)

dataset.save("datasets/my_dataset.json")
```

### LangSmith Dataset

```python
from scripts.dataset_management import LangSmithDatasetManager

manager = LangSmithDatasetManager()

# Create dataset
manager.create_dataset("my_dataset", "Description")

# Add examples
manager.add_examples("my_dataset", [
    {"inputs": {...}, "outputs": {...}},
    {"inputs": {...}, "outputs": {...}}
])
```

### From Production Logs

```python
def create_from_logs(logs: list, human_labels: dict) -> LocalDataset:
    """Create dataset from production logs with human labels."""
    dataset = LocalDataset("production_samples")

    for log in logs:
        if log["id"] in human_labels:
            dataset.add_example(
                inputs={"question": log["input"]},
                outputs={
                    "answer": human_labels[log["id"]],
                    "original_response": log["output"]
                },
                metadata={
                    "source": "production",
                    "timestamp": log["timestamp"]
                }
            )

    return dataset
```

## Dataset Templates

### Using Templates

```python
from scripts.dataset_management import DatasetTemplates

# Q&A
qa = DatasetTemplates.qa_dataset([
    ("What is Python?", "A programming language"),
    ("What is 2+2?", "4")
])

# RAG
rag = DatasetTemplates.rag_dataset([
    ("Context here", "Question?", "Answer")
])

# Classification
cls = DatasetTemplates.classification_dataset([
    ("Great product!", "positive"),
    ("Terrible service.", "negative")
])
```

## Dataset Splits

### Train/Test Split

```python
dataset = LocalDataset.load("full_dataset.json")

train, test = dataset.split(
    train_ratio=0.8,
    seed=42  # For reproducibility
)

train.save("train.json")
test.save("test.json")
```

### Stratified Split

```python
def stratified_split(dataset, key: str, train_ratio: float):
    """Split maintaining category distribution."""
    categories = {}

    for ex in dataset:
        cat = ex["metadata"].get(key, "unknown")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(ex)

    train_examples = []
    test_examples = []

    for cat, examples in categories.items():
        split_idx = int(len(examples) * train_ratio)
        train_examples.extend(examples[:split_idx])
        test_examples.extend(examples[split_idx:])

    return train_examples, test_examples
```

### K-Fold Split

```python
def k_fold_split(dataset, k: int = 5):
    """Create k folds for cross-validation."""
    examples = list(dataset)
    fold_size = len(examples) // k

    folds = []
    for i in range(k):
        start = i * fold_size
        end = start + fold_size if i < k - 1 else len(examples)
        folds.append(examples[start:end])

    return folds
```

## Dataset Versioning

### Version Manager

```python
from scripts.dataset_management import DatasetVersionManager

manager = DatasetVersionManager("datasets/")

# Save new version
manager.save_version(dataset, "1.0.0")

# Load specific version
dataset_v1 = manager.load_version("my_dataset", "1.0.0")

# Load latest
latest = manager.load_version("my_dataset")

# List versions
versions = manager.list_versions("my_dataset")
```

### Version Naming

```
Major.Minor.Patch

1.0.0 → Initial release
1.0.1 → Bug fixes in examples
1.1.0 → Added new examples
2.0.0 → Breaking changes (schema change)
```

### Comparing Versions

```python
diff = manager.compare_versions("dataset", "1.0.0", "1.1.0")
# {
#   "added": 10,      # New examples
#   "removed": 2,     # Removed examples
#   "unchanged": 88   # Same examples
# }
```

## Quality Guidelines

### Example Quality

Good example:
```json
{
  "inputs": {"question": "What is the capital of France?"},
  "outputs": {
    "answer": "Paris",
    "keywords": ["Paris", "capital", "France"]
  },
  "metadata": {
    "difficulty": "easy",
    "source": "geography_qa",
    "verified": true
  }
}
```

Bad example:
```json
{
  "inputs": {"q": "France capital?"},
  "outputs": {"a": "paris"}
}
```

### Coverage Checklist

```markdown
- [ ] Covers all major use cases
- [ ] Includes edge cases
- [ ] Various difficulty levels
- [ ] Different input formats
- [ ] Positive and negative examples
- [ ] Domain-specific scenarios
```

### Golden Set Criteria

1. **High Quality**: Carefully curated, verified correct
2. **Representative**: Covers typical use cases
3. **Stable**: Rarely changes
4. **Small**: 50-200 examples
5. **Diverse**: Different categories, difficulties

## LangSmith Integration

### Upload Local to LangSmith

```python
manager = LangSmithDatasetManager()
local = LocalDataset.load("local_dataset.json")

dataset_id = manager.upload_local_dataset(local)
print(f"Uploaded as: {dataset_id}")
```

### Download from LangSmith

```python
local = manager.download_to_local("langsmith_dataset")
local.save("downloaded_dataset.json")
```

### Sync Workflow

```python
def sync_datasets():
    """Keep local and LangSmith in sync."""
    manager = LangSmithDatasetManager()

    # Download latest from LangSmith
    remote = manager.download_to_local("production_eval")

    # Load local
    local = LocalDataset.load("local_eval.json")

    # Compare
    remote_ids = {ex["id"] for ex in remote}
    local_ids = {ex["id"] for ex in local}

    new_remote = remote_ids - local_ids
    new_local = local_ids - remote_ids

    print(f"New in remote: {len(new_remote)}")
    print(f"New in local: {len(new_local)}")
```

## Best Practices

### 1. Document Everything

```json
{
  "name": "customer_support_eval",
  "description": "Evaluation set for customer support agent",
  "created_by": "ml-team",
  "created_at": "2024-01-15",
  "schema": {
    "inputs": ["question", "context"],
    "outputs": ["answer", "category"]
  },
  "guidelines": "See GUIDELINES.md for labeling instructions"
}
```

### 2. Version Control

```bash
# Track datasets in git
datasets/
  customer_support_v1.0.0.json
  customer_support_v1.1.0.json
  manifest.json
```

### 3. Regular Updates

- Add production edge cases
- Remove outdated examples
- Update based on model changes
- Incorporate user feedback

### 4. Maintain Balance

```python
# Check category distribution
categories = Counter(ex["metadata"]["category"] for ex in dataset)
print(f"Distribution: {categories}")

# Ensure balance
min_count = min(categories.values())
balanced = balance_dataset(dataset, target_per_category=min_count)
```

### 5. Reproducibility

```python
# Always use seeds for splits
train, test = dataset.split(train_ratio=0.8, seed=42)

# Document split parameters
metadata = {
    "split_seed": 42,
    "train_ratio": 0.8,
    "split_date": "2024-01-15"
}
```
