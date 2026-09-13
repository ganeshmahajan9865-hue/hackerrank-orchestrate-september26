"""
Document Loader Module — RAG Subsystem

Recursively loads markdown and text guidance files from the knowledge directory.
Extracts document metadata including topic categories and relative paths.
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Document:
    path: str
    topic: str
    title: str
    content: str
    metadata: Dict[str, Any]


class DocumentLoader:
    """Loads knowledge documents from local directory tree."""

    def __init__(self, base_dir: str = 'knowledge'):
        self.base_dir = os.path.abspath(base_dir)

    def load(self) -> List[Document]:
        """Loads all .md and .txt files from knowledge base."""
        if not os.path.exists(self.base_dir):
            return []

        documents: List[Document] = []
        for root, _, files in os.walk(self.base_dir):
            for file in sorted(files):
                if file.endswith(('.md', '.txt')):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.base_dir).replace('\\', '/')
                    
                    # Extract topic from parent directory
                    parts = rel_path.split('/')
                    topic = parts[0] if len(parts) > 1 else 'general'

                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                    except Exception as e:
                        print(f"Warning: Could not read {full_path}: {e}")
                        continue

                    # Extract title from first markdown header
                    title = file
                    for line in content.splitlines():
                        line_stripped = line.strip()
                        if line_stripped.startswith('#'):
                            title = line_stripped.lstrip('#').strip()
                            break

                    documents.append(Document(
                        path=rel_path,
                        topic=topic,
                        title=title,
                        content=content,
                        metadata={
                            'filename': file,
                            'full_path': full_path,
                            'char_count': len(content)
                        }
                    ))

        return documents
