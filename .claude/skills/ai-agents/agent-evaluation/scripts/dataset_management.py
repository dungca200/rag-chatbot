#!/usr/bin/env python3
"""
Dataset Management for Agent Evaluation.

Create, version, and manage evaluation datasets:
- LangSmith dataset creation
- Local dataset handling
- Dataset versioning
- Example management
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional, Any
from pathlib import Path

from langsmith import Client


# ============================================================================
# Local Dataset Management
# ============================================================================

class LocalDataset:
    """
    Manage evaluation datasets locally.

    Useful for:
    - Development and testing
    - Version control with git
    - Offline evaluation
    - Dataset portability

    Example:
        dataset = LocalDataset("qa_test")
        dataset.add_example(
            inputs={"question": "What is 2+2?"},
            outputs={"answer": "4"}
        )
        dataset.save("datasets/qa_test.json")
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.examples: list[dict] = []
        self.created_at = datetime.now().isoformat()
        self.version = "1.0.0"
        self.metadata: dict = {}

    def add_example(
        self,
        inputs: dict,
        outputs: dict,
        metadata: Optional[dict] = None
    ) -> str:
        """Add an example to the dataset."""
        example_id = str(uuid.uuid4())
        self.examples.append({
            "id": example_id,
            "inputs": inputs,
            "outputs": outputs,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        })
        return example_id

    def add_examples(self, examples: list[dict]):
        """Add multiple examples at once."""
        for ex in examples:
            self.add_example(
                inputs=ex.get("inputs", {}),
                outputs=ex.get("outputs", {}),
                metadata=ex.get("metadata")
            )

    def remove_example(self, example_id: str) -> bool:
        """Remove an example by ID."""
        for i, ex in enumerate(self.examples):
            if ex["id"] == example_id:
                self.examples.pop(i)
                return True
        return False

    def get_example(self, example_id: str) -> Optional[dict]:
        """Get an example by ID."""
        for ex in self.examples:
            if ex["id"] == example_id:
                return ex
        return None

    def filter(self, **kwargs) -> list[dict]:
        """Filter examples by metadata fields."""
        results = []
        for ex in self.examples:
            match = True
            for key, value in kwargs.items():
                if ex.get("metadata", {}).get(key) != value:
                    match = False
                    break
            if match:
                results.append(ex)
        return results

    def split(
        self,
        train_ratio: float = 0.8,
        seed: int = 42
    ) -> tuple["LocalDataset", "LocalDataset"]:
        """Split dataset into train and test sets."""
        import random
        random.seed(seed)

        examples = self.examples.copy()
        random.shuffle(examples)

        split_idx = int(len(examples) * train_ratio)

        train_dataset = LocalDataset(f"{self.name}_train")
        test_dataset = LocalDataset(f"{self.name}_test")

        train_dataset.examples = examples[:split_idx]
        test_dataset.examples = examples[split_idx:]

        return train_dataset, test_dataset

    def save(self, filepath: str):
        """Save dataset to JSON file."""
        data = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "examples": self.examples
        }

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "LocalDataset":
        """Load dataset from JSON file."""
        with open(filepath) as f:
            data = json.load(f)

        dataset = cls(data["name"], data.get("description", ""))
        dataset.version = data.get("version", "1.0.0")
        dataset.created_at = data.get("created_at", datetime.now().isoformat())
        dataset.metadata = data.get("metadata", {})
        dataset.examples = data.get("examples", [])

        return dataset

    def to_langsmith_format(self) -> list[dict]:
        """Convert to LangSmith upload format."""
        return [
            {"inputs": ex["inputs"], "outputs": ex["outputs"]}
            for ex in self.examples
        ]

    def __len__(self) -> int:
        return len(self.examples)

    def __iter__(self):
        return iter(self.examples)


# ============================================================================
# LangSmith Dataset Manager
# ============================================================================

class LangSmithDatasetManager:
    """
    Manage datasets in LangSmith.

    Requires LANGSMITH_API_KEY environment variable.

    Example:
        manager = LangSmithDatasetManager()
        manager.create_dataset("qa_test", "QA test dataset")
        manager.add_examples("qa_test", [
            {"inputs": {"q": "..."}, "outputs": {"a": "..."}}
        ])
    """

    def __init__(self):
        self.client = Client()

    def create_dataset(
        self,
        name: str,
        description: str = "",
        data_type: str = "kv"
    ) -> str:
        """
        Create a new dataset in LangSmith.

        Args:
            name: Dataset name
            description: Dataset description
            data_type: "kv" for key-value, "llm" for LLM data

        Returns:
            Dataset ID
        """
        dataset = self.client.create_dataset(
            dataset_name=name,
            description=description,
            data_type=data_type
        )
        return str(dataset.id)

    def list_datasets(self) -> list[dict]:
        """List all datasets."""
        datasets = list(self.client.list_datasets())
        return [
            {
                "id": str(d.id),
                "name": d.name,
                "description": d.description,
                "created_at": str(d.created_at) if d.created_at else None
            }
            for d in datasets
        ]

    def get_dataset(self, name: str) -> Optional[dict]:
        """Get dataset by name."""
        try:
            dataset = self.client.read_dataset(dataset_name=name)
            return {
                "id": str(dataset.id),
                "name": dataset.name,
                "description": dataset.description
            }
        except Exception:
            return None

    def add_examples(
        self,
        dataset_name: str,
        examples: list[dict]
    ):
        """
        Add examples to a dataset.

        Args:
            dataset_name: Name of the dataset
            examples: List of {"inputs": {...}, "outputs": {...}}
        """
        self.client.create_examples(
            inputs=[ex["inputs"] for ex in examples],
            outputs=[ex.get("outputs", {}) for ex in examples],
            dataset_name=dataset_name
        )

    def add_example(
        self,
        dataset_name: str,
        inputs: dict,
        outputs: dict
    ):
        """Add a single example."""
        self.add_examples(dataset_name, [{"inputs": inputs, "outputs": outputs}])

    def list_examples(self, dataset_name: str, limit: int = 100) -> list[dict]:
        """List examples in a dataset."""
        examples = list(self.client.list_examples(dataset_name=dataset_name, limit=limit))
        return [
            {
                "id": str(ex.id),
                "inputs": ex.inputs,
                "outputs": ex.outputs
            }
            for ex in examples
        ]

    def delete_dataset(self, dataset_name: str):
        """Delete a dataset."""
        self.client.delete_dataset(dataset_name=dataset_name)

    def upload_local_dataset(self, local_dataset: LocalDataset) -> str:
        """Upload a local dataset to LangSmith."""
        # Create dataset
        dataset_id = self.create_dataset(
            name=local_dataset.name,
            description=local_dataset.description
        )

        # Add examples
        examples = local_dataset.to_langsmith_format()
        self.add_examples(local_dataset.name, examples)

        return dataset_id

    def download_to_local(self, dataset_name: str) -> LocalDataset:
        """Download a LangSmith dataset to local format."""
        dataset_info = self.get_dataset(dataset_name)
        if not dataset_info:
            raise ValueError(f"Dataset not found: {dataset_name}")

        local = LocalDataset(
            name=dataset_name,
            description=dataset_info.get("description", "")
        )

        examples = self.list_examples(dataset_name, limit=10000)
        for ex in examples:
            local.add_example(
                inputs=ex["inputs"],
                outputs=ex["outputs"],
                metadata={"langsmith_id": ex["id"]}
            )

        return local


# ============================================================================
# Dataset Templates
# ============================================================================

class DatasetTemplates:
    """Pre-built templates for common evaluation scenarios."""

    @staticmethod
    def qa_dataset(examples: list[tuple[str, str]]) -> LocalDataset:
        """
        Create a Q&A dataset.

        Args:
            examples: List of (question, answer) tuples
        """
        dataset = LocalDataset("qa_dataset", "Question-Answer evaluation dataset")
        for q, a in examples:
            dataset.add_example(
                inputs={"question": q},
                outputs={"answer": a}
            )
        return dataset

    @staticmethod
    def rag_dataset(examples: list[tuple[str, str, str]]) -> LocalDataset:
        """
        Create a RAG dataset.

        Args:
            examples: List of (context, question, answer) tuples
        """
        dataset = LocalDataset("rag_dataset", "RAG evaluation dataset")
        for ctx, q, a in examples:
            dataset.add_example(
                inputs={"context": ctx, "question": q},
                outputs={"answer": a}
            )
        return dataset

    @staticmethod
    def classification_dataset(examples: list[tuple[str, str]]) -> LocalDataset:
        """
        Create a classification dataset.

        Args:
            examples: List of (text, label) tuples
        """
        dataset = LocalDataset("classification_dataset", "Text classification dataset")
        for text, label in examples:
            dataset.add_example(
                inputs={"text": text},
                outputs={"label": label}
            )
        return dataset

    @staticmethod
    def summarization_dataset(examples: list[tuple[str, str]]) -> LocalDataset:
        """
        Create a summarization dataset.

        Args:
            examples: List of (document, summary) tuples
        """
        dataset = LocalDataset("summarization_dataset", "Text summarization dataset")
        for doc, summary in examples:
            dataset.add_example(
                inputs={"document": doc},
                outputs={"summary": summary}
            )
        return dataset


# ============================================================================
# Dataset Versioning
# ============================================================================

class DatasetVersionManager:
    """
    Manage dataset versions.

    Tracks changes and allows rollback to previous versions.
    """

    def __init__(self, base_path: str = "datasets"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_version(self, dataset: LocalDataset, version: str = None):
        """Save a new version of the dataset."""
        if version:
            dataset.version = version
        else:
            # Auto-increment version
            parts = dataset.version.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            dataset.version = ".".join(parts)

        # Create versioned filename
        filename = f"{dataset.name}_v{dataset.version}.json"
        filepath = self.base_path / filename

        dataset.save(str(filepath))

        # Update latest symlink/reference
        self._update_latest(dataset.name, filename)

        return dataset.version

    def _update_latest(self, name: str, latest_file: str):
        """Update reference to latest version."""
        manifest_path = self.base_path / f"{name}_manifest.json"

        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)
        else:
            manifest = {"name": name, "versions": []}

        manifest["latest"] = latest_file
        manifest["versions"].append(latest_file)
        manifest["updated_at"] = datetime.now().isoformat()

        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

    def load_version(self, name: str, version: str = None) -> LocalDataset:
        """Load a specific version of a dataset."""
        if version:
            filename = f"{name}_v{version}.json"
        else:
            # Load latest
            manifest_path = self.base_path / f"{name}_manifest.json"
            with open(manifest_path) as f:
                manifest = json.load(f)
            filename = manifest["latest"]

        return LocalDataset.load(str(self.base_path / filename))

    def list_versions(self, name: str) -> list[str]:
        """List all versions of a dataset."""
        manifest_path = self.base_path / f"{name}_manifest.json"
        if not manifest_path.exists():
            return []

        with open(manifest_path) as f:
            manifest = json.load(f)

        return manifest.get("versions", [])

    def compare_versions(
        self,
        name: str,
        version1: str,
        version2: str
    ) -> dict:
        """Compare two versions of a dataset."""
        ds1 = self.load_version(name, version1)
        ds2 = self.load_version(name, version2)

        # Get example IDs
        ids1 = {ex["id"] for ex in ds1.examples}
        ids2 = {ex["id"] for ex in ds2.examples}

        return {
            "version1": version1,
            "version2": version2,
            "examples_v1": len(ds1),
            "examples_v2": len(ds2),
            "added": len(ids2 - ids1),
            "removed": len(ids1 - ids2),
            "unchanged": len(ids1 & ids2)
        }


# ============================================================================
# Demo Functions
# ============================================================================

def demo_local_dataset():
    """Demonstrate local dataset management."""

    print("=== Local Dataset Demo ===\n")

    # Create dataset
    dataset = LocalDataset("demo_qa", "Demo Q&A dataset")

    # Add examples
    dataset.add_example(
        inputs={"question": "What is 2+2?"},
        outputs={"answer": "4"}
    )
    dataset.add_example(
        inputs={"question": "What is the capital of France?"},
        outputs={"answer": "Paris"}
    )
    dataset.add_example(
        inputs={"question": "What color is the sky?"},
        outputs={"answer": "Blue"},
        metadata={"difficulty": "easy"}
    )

    print(f"Dataset: {dataset.name}")
    print(f"Examples: {len(dataset)}")

    # Filter by metadata
    easy = dataset.filter(difficulty="easy")
    print(f"Easy examples: {len(easy)}")

    # Split dataset
    train, test = dataset.split(train_ratio=0.7)
    print(f"Train: {len(train)}, Test: {len(test)}")


def demo_dataset_templates():
    """Demonstrate dataset templates."""

    print("=== Dataset Templates Demo ===\n")

    # Create Q&A dataset
    qa = DatasetTemplates.qa_dataset([
        ("What is Python?", "A programming language"),
        ("What is 2+2?", "4"),
        ("What is AI?", "Artificial Intelligence")
    ])
    print(f"Q&A Dataset: {len(qa)} examples")

    # Create RAG dataset
    rag = DatasetTemplates.rag_dataset([
        ("Python was created by Guido.", "Who created Python?", "Guido"),
        ("Paris is in France.", "Where is Paris?", "France")
    ])
    print(f"RAG Dataset: {len(rag)} examples")


def demo_versioning():
    """Demonstrate dataset versioning."""

    print("=== Dataset Versioning Demo ===\n")

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = DatasetVersionManager(tmpdir)

        # Create and save initial version
        dataset = LocalDataset("test_dataset")
        dataset.add_example(
            inputs={"q": "Question 1"},
            outputs={"a": "Answer 1"}
        )

        v1 = manager.save_version(dataset, "1.0.0")
        print(f"Saved version: {v1}")

        # Add more examples and save new version
        dataset.add_example(
            inputs={"q": "Question 2"},
            outputs={"a": "Answer 2"}
        )

        v2 = manager.save_version(dataset)
        print(f"Saved version: {v2}")

        # List versions
        versions = manager.list_versions("test_dataset")
        print(f"All versions: {versions}")

        # Compare versions
        comparison = manager.compare_versions("test_dataset", "1.0.0", "1.0.1")
        print(f"Comparison: {comparison}")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("Dataset Management Demonstrations\n")
    print("=" * 50 + "\n")

    demo_local_dataset()
    print("\n" + "=" * 50 + "\n")

    demo_dataset_templates()
    print("\n" + "=" * 50 + "\n")

    demo_versioning()
