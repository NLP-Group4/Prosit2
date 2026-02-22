"""
RAG Module — Retrieval-Augmented Generation for the PromptToSpec agent.

Handles document chunking, embedding via Gemini, storage in pgvector,
and similarity-based retrieval to provide context for spec generation.
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from typing import Optional

from google import genai
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.platform_db import Document, DocumentChunk

logger = logging.getLogger(__name__)

# Embedding model config
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768

# Chunking config
DEFAULT_CHUNK_SIZE = 500  # characters
DEFAULT_CHUNK_OVERLAP = 50  # characters


# ---------------------------------------------------------------------------
# Gemini embedding client
# ---------------------------------------------------------------------------

def _get_genai_client() -> genai.Client:
    """Get a configured Gemini client."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY environment variable is required for embeddings")
    return genai.Client(api_key=api_key)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(
    text_content: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """
    Split text into overlapping chunks.

    Args:
        text_content: Full document text.
        chunk_size: Maximum characters per chunk.
        overlap: Overlap between consecutive chunks.

    Returns:
        List of text chunks.
    """
    if not text_content.strip():
        return []

    # Split on paragraph boundaries when possible
    paragraphs = text_content.split("\n\n")
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current.strip())
            # If a single paragraph exceeds chunk_size, split by chars
            if len(para) > chunk_size:
                for i in range(0, len(para), chunk_size - overlap):
                    chunks.append(para[i:i + chunk_size].strip())
            else:
                current = para
                continue
            current = ""

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if c]


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of text chunks using Gemini.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (each 768-dimensional).
    """
    if not texts:
        return []

    client = _get_genai_client()

    # Gemini embedding API supports batch embedding
    embeddings: list[list[float]] = []

    # Process in batches of 100 (API limit)
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch,
            config={
                "output_dimensionality": EMBEDDING_DIMENSIONS,
            },
        )
        for emb in response.embeddings:
            embeddings.append(emb.values)

    return embeddings


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def content_hash(content: str) -> str:
    """Generate a SHA-256 hash of text content for deduplication."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def store_document(
    db: Session,
    user_id: uuid.UUID,
    filename: str,
    text_content: str,
) -> Document:
    """
    Process and store a document: chunk → embed → save to pgvector.

    Args:
        db: Database session.
        user_id: Owner user ID.
        filename: Original filename.
        text_content: Extracted text content.

    Returns:
        The created Document record.
    """
    # Check for duplicate content
    doc_hash = content_hash(text_content)
    existing = db.query(Document).filter(
        Document.user_id == user_id,
        Document.content_hash == doc_hash,
    ).first()
    if existing:
        logger.info(f"Document already exists: {existing.filename} (hash match)")
        return existing

    # Create document record
    doc = Document(
        user_id=user_id,
        filename=filename,
        content_hash=doc_hash,
    )
    db.add(doc)
    db.flush()  # Get doc.id before creating chunks

    # Chunk the text
    chunks = chunk_text(text_content)
    if not chunks:
        db.commit()
        return doc

    logger.info(f"Chunking '{filename}': {len(chunks)} chunks")

    # Embed all chunks
    embeddings = embed_texts(chunks)
    logger.info(f"Embedded {len(embeddings)} chunks")

    # Store chunks with embeddings
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        db_chunk = DocumentChunk(
            document_id=doc.id,
            user_id=user_id,
            chunk_index=idx,
            content=chunk,
            embedding=embedding,
        )
        db.add(db_chunk)

    db.commit()
    db.refresh(doc)
    logger.info(f"Stored document '{filename}' with {len(chunks)} chunks")
    return doc


def delete_document(db: Session, user_id: uuid.UUID, document_id: uuid.UUID) -> bool:
    """Delete a document and all its chunks."""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user_id,
    ).first()
    if not doc:
        return False

    # Chunks cascade-delete via FK
    db.delete(doc)
    db.commit()
    return True


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve_context(
    db: Session,
    user_id: uuid.UUID,
    query: str,
    top_k: int = 5,
) -> str:
    """
    Retrieve the most relevant document chunks for a query.

    Uses cosine similarity via pgvector to find the top-K most relevant
    chunks from the user's uploaded documents.

    Args:
        db: Database session.
        user_id: Owner user ID.
        query: The user's prompt/query to match against.
        top_k: Number of chunks to retrieve.

    Returns:
        Concatenated relevant text chunks, or empty string if none found.
    """
    # Check if user has any documents
    doc_count = db.query(Document).filter(Document.user_id == user_id).count()
    if doc_count == 0:
        return ""

    # Embed the query
    query_embedding = embed_texts([query])
    if not query_embedding:
        return ""

    embedding_vector = query_embedding[0]

    # pgvector cosine similarity search
    # Using raw SQL for the vector operation
    result = db.execute(
        text("""
            SELECT content, 1 - (embedding <=> cast(:query_vec as vector)) AS similarity
            FROM document_chunks
            WHERE user_id = :user_id
            ORDER BY embedding <=> cast(:query_vec as vector)
            LIMIT :top_k
        """),
        {
            "query_vec": str(embedding_vector),
            "user_id": str(user_id),
            "top_k": top_k,
        },
    ).fetchall()

    if not result:
        return ""

    # Build context string with source markers
    context_parts = []
    for row in result:
        content = row[0]
        similarity = row[1]
        if similarity > 0.3:  # Only include reasonably relevant chunks
            context_parts.append(content)

    if not context_parts:
        return ""

    return "\n---\n".join(context_parts)
