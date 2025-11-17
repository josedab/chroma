# Part 4: Extending and Integrating Chroma

## What You'll Learn

By the end of this post, you'll understand:
- How to create custom embedding functions
- The EmbeddingFunction protocol and built-in implementations
- Sparse embeddings for hybrid search (BM25 + dense vectors)
- Collection configuration and schemas
- Integration with LangChain, LlamaIndex, and other frameworks
- Extension points in the Chroma architecture
- Best practices for building on Chroma

## Introduction: Chroma as a Platform

Chroma isn't just a database—it's a platform for building vector-powered applications. While it works great out of the box, its real power comes from its extensibility. Whether you're integrating with existing ML pipelines, using specialized embedding models, or building custom workflows, Chroma provides clean extension points.

In this post, we'll explore how to customize Chroma's behavior, integrate it into your stack, and leverage its flexible architecture.

## Embedding Functions: The Gateway to Your Models

Embedding functions are Chroma's abstraction for converting raw data (text, images, etc.) into vectors. They're the bridge between your data and the vector store.

### The EmbeddingFunction Protocol

Here's the core interface:

```python
# File: chromadb/api/types.py:747-777
# https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/api/types.py#L747-L777

class EmbeddingFunction(Protocol[D]):
    """
    A protocol for embedding functions. To implement a new embedding function,
    you need to implement the following methods at minimum:
    - __call__

    For future compatibility, it is strongly recommended to also implement:
    - __init__
    - name
    - build_from_config
    - get_config
    """

    @abstractmethod
    def __call__(self, input: D) -> Embeddings:
        """Transform input into embeddings.

        Args:
            input: Data to embed (documents, images, etc.)

        Returns:
            List of embedding vectors (List[List[float]])
        """
        ...

    def embed_query(self, input: D) -> Embeddings:
        """Get the embeddings for a query input.

        This method is optional, and if not implemented,
        the default behavior is to call __call__.
        """
        return self.__call__(input)

    # Optional but recommended:
    def name(self) -> str:
        """Return the name of this embedding function."""
        ...

    def build_from_config(self, config: Dict[str, Any]) -> "EmbeddingFunction[D]":
        """Construct from configuration dict."""
        ...

    def get_config(self) -> Dict[str, Any]:
        """Return configuration as dict."""
        ...

    def default_space(self) -> Space:
        """Return the recommended distance metric (l2, cosine, ip)."""
        ...
```

**Key Design Points**:
- **Protocol-based**: Duck typing, no forced inheritance
- **Generic over input type**: `EmbeddingFunction[Documents]` vs `EmbeddingFunction[Images]`
- **Config methods**: Enable serialization and reconstruction

### Built-in Embedding Functions

Chroma provides 20+ built-in embedding functions for common use cases:

```python
# File: chromadb/utils/embedding_functions/__init__.py (excerpt)
# https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/utils/embedding_functions/__init__.py

# Dense embeddings
from chromadb.utils.embedding_functions import (
    OpenAIEmbeddingFunction,          # OpenAI's text-embedding-ada-002
    CohereEmbeddingFunction,          # Cohere's embed models
    SentenceTransformerEmbeddingFunction,  # Hugging Face models
    GoogleVertexEmbeddingFunction,    # Google Cloud Vertex AI
    OllamaEmbeddingFunction,          # Local Ollama models
    JinaEmbeddingFunction,            # Jina AI models
    VoyageAIEmbeddingFunction,        # Voyage AI models
    # ... many more
)

# Sparse embeddings
from chromadb.utils.embedding_functions import (
    ChromaBm25EmbeddingFunction,      # BM25 for lexical search
    HuggingFaceSparseEmbeddingFunction,  # SPLADE models
    FastembedSparseEmbeddingFunction,  # Fast sparse embeddings
)
```

### Creating a Custom Embedding Function

Let's build a simple custom embedding function:

```python
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from typing import List, Dict, Any
import numpy as np

class CustomTF_IDFEmbeddingFunction(EmbeddingFunction[Documents]):
    """Simple TF-IDF embedding function as an example."""

    def __init__(self, max_features: int = 1000):
        """Initialize with configuration.

        Args:
            max_features: Maximum number of features for TF-IDF
        """
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.max_features = max_features
        self.vectorizer = TfidfVectorizer(max_features=max_features)
        self.is_fit = False

    def __call__(self, input: Documents) -> Embeddings:
        """Transform documents into TF-IDF vectors.

        Args:
            input: List of document strings

        Returns:
            List of embedding vectors
        """
        if not self.is_fit:
            # Fit on first call (you might want to fit separately in production)
            self.vectorizer.fit(input)
            self.is_fit = True

        # Transform to TF-IDF vectors
        tfidf_matrix = self.vectorizer.transform(input)

        # Convert sparse matrix to list of dense arrays
        return [
            np.array(row.toarray()[0], dtype=np.float32)
            for row in tfidf_matrix
        ]

    @staticmethod
    def name() -> str:
        return "custom_tfidf"

    def default_space(self) -> str:
        # Cosine similarity is standard for TF-IDF
        return "cosine"

    def supported_spaces(self) -> List[str]:
        return ["cosine", "l2", "ip"]

    def get_config(self) -> Dict[str, Any]:
        return {
            "max_features": self.max_features,
        }

    @staticmethod
    def build_from_config(config: Dict[str, Any]) -> "CustomTF_IDFEmbeddingFunction":
        return CustomTF_IDFEmbeddingFunction(
            max_features=config.get("max_features", 1000)
        )


# Usage:
import chromadb

client = chromadb.Client()
ef = CustomTF_IDFEmbeddingFunction(max_features=500)

collection = client.create_collection(
    name="tfidf_collection",
    embedding_function=ef,
    metadata={"hnsw:space": "cosine"}
)

collection.add(
    documents=["AI is transforming software", "Machine learning models"],
    ids=["1", "2"]
)

results = collection.query(
    query_texts=["artificial intelligence"],
    n_results=1
)
```

### A Real-World Example: SentenceTransformerEmbeddingFunction

Let's examine a production embedding function:

```python
# File: chromadb/utils/embedding_functions/sentence_transformer_embedding_function.py
# https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/utils/embedding_functions/sentence_transformer_embedding_function.py

class SentenceTransformerEmbeddingFunction(EmbeddingFunction[Documents]):
    # Shared model cache across instances
    models: Dict[str, Any] = {}

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
        normalize_embeddings: bool = False,
        **kwargs: Any,
    ):
        """Initialize SentenceTransformerEmbeddingFunction.

        Args:
            model_name: Identifier of the SentenceTransformer model
            device: Device used for computation ("cpu", "cuda", etc.)
            normalize_embeddings: Whether to normalize returned vectors
            **kwargs: Additional arguments to pass to the model
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ValueError(
                "The sentence_transformers package is not installed. "
                "Please install it with `pip install sentence_transformers`"
            )

        self.model_name = model_name
        self.device = device
        self.normalize_embeddings = normalize_embeddings
        self.kwargs = kwargs

        # Cache models globally to avoid reloading
        if model_name not in self.models:
            self.models[model_name] = SentenceTransformer(
                model_name_or_path=model_name,
                device=device,
                **kwargs
            )
        self._model = self.models[model_name]

    def __call__(self, input: Documents) -> Embeddings:
        """Generate embeddings for the given documents."""
        embeddings = self._model.encode(
            list(input),
            convert_to_numpy=True,
            normalize_embeddings=self.normalize_embeddings,
        )
        return [np.array(embedding, dtype=np.float32) for embedding in embeddings]

    @staticmethod
    def name() -> str:
        return "sentence_transformer"

    def default_space(self) -> Space:
        # If normalize_embeddings is True, cosine is equivalent to dot product
        return "cosine"

    def supported_spaces(self) -> List[Space]:
        return ["cosine", "l2", "ip"]

    def get_config(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "device": self.device,
            "normalize_embeddings": self.normalize_embeddings,
            "kwargs": self.kwargs,
        }
```

**Design Highlights**:
- **Model caching**: Prevents reloading heavy models
- **Lazy imports**: Only imports sentence-transformers if used
- **Configuration serialization**: Can reconstruct from config
- **Flexible initialization**: Accepts arbitrary kwargs for the underlying model

## Hybrid Search: Dense + Sparse Embeddings

Modern retrieval often combines dense vectors (semantic similarity) with sparse vectors (lexical matching). Chroma supports this via sparse embeddings:

```python
from chromadb.utils.embedding_functions import ChromaBm25EmbeddingFunction
import chromadb

client = chromadb.Client()

# Create sparse embedding function for BM25
bm25_ef = ChromaBm25EmbeddingFunction()

collection = client.create_collection(
    name="hybrid_collection",
    embedding_function=bm25_ef,  # Sparse embedding function
)

# Add documents - BM25 creates sparse vectors automatically
collection.add(
    documents=[
        "Chroma is a vector database for AI applications",
        "HNSW enables fast approximate nearest neighbor search",
        "Embedding functions transform data into vectors",
    ],
    ids=["doc1", "doc2", "doc3"]
)

# Query combines dense and sparse signals
results = collection.query(
    query_texts=["vector search algorithms"],
    n_results=2
)
```

### Understanding Sparse Vectors

```python
# Sparse vector representation
SparseVector = {
    'indices': List[int],   # Dimension indices with non-zero values
    'values': List[float],  # Corresponding values
}

# Example: A 1000-dimensional sparse vector with only 10 non-zero values
sparse = {
    'indices': [5, 23, 47, 91, 158, 203, 371, 489, 612, 891],
    'values': [0.8, 0.6, 0.9, 0.4, 0.7, 0.5, 0.6, 0.8, 0.3, 0.9],
}
# This represents a 1000-dim vector where only these 10 positions are non-zero
```

**Why sparse vectors?**
- **Lexical matching**: BM25 captures exact term matches
- **Complementary to dense**: Dense vectors miss exact terminology
- **Hybrid fusion**: Reciprocal Rank Fusion combines both rankings
- **Storage efficiency**: Only store non-zero dimensions

## Collection Configuration and Schemas

Collections can be extensively configured to match your use case:

```python
import chromadb
from chromadb.api.types import (
    Schema,
    HnswIndexConfig,
    FtsIndexConfig,
    IntInvertedIndexConfig,
)

client = chromadb.Client()

# Define a schema for your collection
schema = Schema(
    fields={
        "document": {
            "type": "string",
            "index": FtsIndexConfig(),  # Full-text search index
        },
        "embedding": {
            "type": "float_list",
            "index": HnswIndexConfig(
                space="cosine",
                M=32,                    # More connections
                ef_construction=200,     # Higher quality
            ),
        },
        "category": {
            "type": "string",
            "index": IntInvertedIndexConfig(),  # Fast filtering
        },
        "score": {
            "type": "float",
        },
    }
)

collection = client.create_collection(
    name="configured_collection",
    metadata={
        # HNSW parameters
        "hnsw:space": "cosine",
        "hnsw:M": 32,
        "hnsw:construction_ef": 200,
        "hnsw:search_ef": 100,

        # Additional metadata
        "description": "Production collection with optimized settings"
    },
    # schema=schema,  # Schema system (newer API)
)
```

### Collection Metadata Best Practices

```python
# Development/testing collection
dev_collection = client.create_collection(
    name="dev_collection",
    metadata={
        "hnsw:space": "l2",
        "hnsw:M": 8,              # Lower memory usage
        "hnsw:search_ef": 50,     # Faster queries
        "environment": "development",
    }
)

# Production collection
prod_collection = client.create_collection(
    name="prod_collection",
    metadata={
        "hnsw:space": "cosine",
        "hnsw:M": 32,             # Better recall
        "hnsw:construction_ef": 200,
        "hnsw:search_ef": 100,
        "environment": "production",
        "version": "1.0",
        "owner": "ml-team",
    }
)
```

## Integration with LangChain

LangChain is the most popular framework for building LLM applications. Chroma integrates seamlessly:

```python
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

# Load documents
loader = TextLoader("./data/state_of_the_union.txt")
documents = loader.load()

# Split into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
docs = text_splitter.split_documents(documents)

# Create Chroma vectorstore
embedding_function = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(
    documents=docs,
    embedding=embedding_function,
    persist_directory="./chroma_db",
    collection_name="langchain_collection"
)

# Use for retrieval
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 4}
)

# Query
results = retriever.get_relevant_documents(
    "What did the president say about Ketanji Brown Jackson?"
)

# Or use in a chain
from langchain.chains import RetrievalQA
from langchain_community.llms import OpenAI

qa_chain = RetrievalQA.from_chain_type(
    llm=OpenAI(),
    chain_type="stuff",
    retriever=retriever
)

answer = qa_chain.run("What are the main points about the economy?")
```

### LangChain Integration with Chroma Client

You can also use Chroma's native client with LangChain:

```python
from chromadb.utils.embedding_functions import ChromaLangchainEmbeddingFunction
from langchain_community.embeddings import OpenAIEmbeddings
import chromadb

# Wrap LangChain embedding function for Chroma
langchain_ef = OpenAIEmbeddings()
chroma_ef = ChromaLangchainEmbeddingFunction(langchain_ef)

# Use with Chroma client
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.create_collection(
    name="langchain_wrapped",
    embedding_function=chroma_ef
)

collection.add(
    documents=["AI is transforming software development"],
    ids=["1"]
)
```

## Integration with LlamaIndex

LlamaIndex (formerly GPT Index) provides another powerful abstraction:

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
import chromadb

# Load documents
documents = SimpleDirectoryReader("./data").load_data()

# Create Chroma client and collection
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("llamaindex_collection")

# Create vector store
vector_store = ChromaVectorStore(chroma_collection=collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Create index
index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context
)

# Query the index
query_engine = index.as_query_engine()
response = query_engine.query("What is the main topic of these documents?")
print(response)
```

## Extension Points in Chroma

Beyond embedding functions, Chroma provides several extension points:

### 1. Custom Segment Implementations

If you need specialized storage, implement the segment interfaces:

```python
from chromadb.segment import VectorReader
from chromadb.types import VectorQuery, VectorQueryResult, Segment
from chromadb.config import System
from typing import Sequence

class CustomVectorSegment(VectorReader):
    """Custom vector storage implementation."""

    def __init__(self, system: System, segment: Segment):
        super().__init__(system, segment)
        # Initialize your custom storage
        self._custom_index = self._init_custom_index()

    def query_vectors(
        self, query: VectorQuery
    ) -> Sequence[Sequence[VectorQueryResult]]:
        """Implement custom vector search logic."""
        # Your implementation here
        pass

    def get_vectors(self, request_version_context, ids=None):
        """Implement vector retrieval."""
        # Your implementation here
        pass

    # ... implement other required methods
```

### 2. Custom Authentication Providers

For enterprise deployments:

```python
from chromadb.auth import ServerAuthenticationProvider
from chromadb.auth.UserIdentity import UserIdentity

class CustomAuthProvider(ServerAuthenticationProvider):
    """Custom authentication logic."""

    def authenticate(self, credentials: Dict[str, Any]) -> UserIdentity:
        """Validate credentials and return user identity."""
        # Your authentication logic
        # Could integrate with OAuth, LDAP, etc.
        pass
```

### 3. Custom Telemetry Clients

For monitoring and observability:

```python
from chromadb.telemetry.product import ProductTelemetryClient

class CustomTelemetryClient(ProductTelemetryClient):
    """Send telemetry to your monitoring system."""

    def capture(self, event: str, properties: Dict[str, Any]) -> None:
        """Capture telemetry events."""
        # Send to your monitoring system
        # (Prometheus, DataDog, etc.)
        pass
```

## Best Practices for Extending Chroma

### 1. Respect the Protocol Contract

```python
# ✅ Good: Implements required methods
class GoodEmbeddingFunction(EmbeddingFunction[Documents]):
    def __call__(self, input: Documents) -> Embeddings:
        return self.embed(input)

# ❌ Bad: Missing __call__
class BadEmbeddingFunction(EmbeddingFunction[Documents]):
    def embed(self, input: Documents) -> Embeddings:
        return []  # Doesn't implement __call__!
```

### 2. Handle Errors Gracefully

```python
class RobustEmbeddingFunction(EmbeddingFunction[Documents]):
    def __call__(self, input: Documents) -> Embeddings:
        try:
            return self._model.encode(input)
        except Exception as e:
            # Log the error
            logger.error(f"Embedding failed: {e}")
            # Provide fallback or re-raise with context
            raise ValueError(f"Failed to generate embeddings: {e}") from e
```

### 3. Make Configuration Serializable

```python
def get_config(self) -> Dict[str, Any]:
    # Only return JSON-serializable types
    return {
        "model_name": self.model_name,  # ✅ String
        "temperature": 0.7,              # ✅ Float
        "max_tokens": 100,                # ✅ Int
        # ❌ Don't include: self._model (not serializable)
    }
```

### 4. Document Expected Dimensions

```python
class FixedDimensionEmbeddingFunction(EmbeddingFunction[Documents]):
    """Generates 384-dimensional embeddings."""

    DIMENSION = 384

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = self._model.encode(input)
        # Validate dimensions
        for emb in embeddings:
            if len(emb) != self.DIMENSION:
                raise ValueError(
                    f"Expected {self.DIMENSION} dimensions, got {len(emb)}"
                )
        return embeddings
```

## Key Takeaways

1. **EmbeddingFunction is a Protocol** - Implement `__call__` at minimum, add config methods for persistence

2. **20+ built-in embedding functions** - Cover most common use cases (OpenAI, Cohere, Sentence Transformers, etc.)

3. **Sparse embeddings enable hybrid search** - Combine BM25/SPLADE with dense vectors for better retrieval

4. **Collection metadata configures behavior** - HNSW parameters, distance metrics, and custom fields

5. **LangChain and LlamaIndex integrate seamlessly** - Use Chroma as a vectorstore in larger applications

6. **Multiple extension points** - Segments, auth providers, telemetry clients can all be customized

7. **Follow best practices** - Respect protocols, handle errors, serialize config, document expectations

8. **Configuration over code** - Use metadata and settings to control behavior without changing code

## Next Steps

To put these concepts into practice:

1. **Create a custom embedding function** for your specific domain or model
2. **Experiment with sparse embeddings** - Compare BM25 vs dense vs hybrid search
3. **Build a LangChain application** using Chroma as the vectorstore
4. **Configure collections** for your production use case (HNSW params, metadata)
5. **Explore the built-in embedding functions** - Try different models and compare results

In **Part 5**, we'll analyze Chroma's performance characteristics, identify bottlenecks, explore optimization strategies, and understand how to benchmark and monitor your deployment.

---

**[← Part 3: Patterns and Practices](03-patterns-practices.md)** | **[Part 5: Performance Analysis →](05-performance-analysis.md)**

---

*Code examples from Chroma commit [`091f8bd`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e)*
