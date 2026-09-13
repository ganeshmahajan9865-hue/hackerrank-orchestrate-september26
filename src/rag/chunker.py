"""
Document Chunker Module — RAG Subsystem

Splits knowledge documents into coherent, semantically focused chunks.
Attaches full provenance metadata (source, chunk_id, topic, section).
"""

import os
import re
from typing import List, Dict, Any
from dataclasses import dataclass

from .document_loader import Document


@dataclass
class DocumentChunk:
    chunk_id: str
    source: str
    topic: str
    section: str
    text: str
    metadata: Dict[str, Any]


class DocumentChunker:
    """Splits markdown and text documents by sections and paragraphs."""

    def __init__(self, target_chunk_words: int = 150, overlap_words: int = 25):
        self.target_chunk_words = target_chunk_words
        self.overlap_words = overlap_words

    def chunk_documents(self, documents: List[Document]) -> List[DocumentChunk]:
        """Processes all documents and returns a flat list of metadata-rich chunks."""
        all_chunks: List[DocumentChunk] = []
        for doc in documents:
            doc_chunks = self.chunk_single_document(doc)
            all_chunks.extend(doc_chunks)
        return all_chunks

    def chunk_single_document(self, doc: Document) -> List[DocumentChunk]:
        """Splits a single document by markdown headers or paragraph clusters."""
        stem = os.path.splitext(os.path.basename(doc.path))[0]
        lines = doc.content.split('\n')

        sections: List[tuple] = []  # (section_heading, section_text)
        current_heading = doc.title
        current_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('##'):
                if current_lines:
                    text_block = '\n'.join(current_lines).strip()
                    if text_block:
                        sections.append((current_heading, text_block))
                    current_lines = []
                current_heading = stripped.lstrip('#').strip()
            else:
                current_lines.append(line)

        if current_lines:
            text_block = '\n'.join(current_lines).strip()
            if text_block:
                sections.append((current_heading, text_block))

        # If no markdown sections, fall back to entire content
        if not sections:
            sections = [(doc.title, doc.content)]

        chunks: List[DocumentChunk] = []
        chunk_idx = 1

        for heading, sec_text in sections:
            # Clean text
            cleaned = re.sub(r'\n{3,}', '\n\n', sec_text).strip()
            words = cleaned.split()

            if len(words) <= self.target_chunk_words + 50:
                # Small enough to be a single chunk
                chunk_id = f"{stem}_{chunk_idx:02d}"
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    source=doc.path,
                    topic=doc.topic,
                    section=heading,
                    text=cleaned,
                    metadata={
                        'word_count': len(words),
                        'source': doc.path,
                        'topic': doc.topic,
                        'section': heading
                    }
                ))
                chunk_idx += 1
            else:
                # Split large section into overlapping windows
                start = 0
                while start < len(words):
                    end = min(start + self.target_chunk_words, len(words))
                    window_words = words[start:end]
                    chunk_text = ' '.join(window_words)
                    chunk_id = f"{stem}_{chunk_idx:02d}"

                    chunks.append(DocumentChunk(
                        chunk_id=chunk_id,
                        source=doc.path,
                        topic=doc.topic,
                        section=heading,
                        text=chunk_text,
                        metadata={
                            'word_count': len(window_words),
                            'source': doc.path,
                            'topic': doc.topic,
                            'section': heading
                        }
                    ))
                    chunk_idx += 1

                    if end == len(words):
                        break
                    start += (self.target_chunk_words - self.overlap_words)

        return chunks
