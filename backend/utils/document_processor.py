import uuid
import PyPDF2
import docx
from typing import Dict, Any, Optional
import logging
import io

from backend.utils.enhanced_document_processor import EnhancedDocumentProcessor

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Legacy document processor - now wraps EnhancedDocumentProcessor for backward compatibility
    """
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize document processor with enhanced backend
        
        Args:
            config: Configuration dictionary for document processing
        """
        # Initialize enhanced processor with configuration
        processor_config = config or {}
        
        # Add default configuration for enhanced features
        processor_config.setdefault('docling', {
            'enable_ocr': True,
            'enable_table_extraction': True
        })
        
        self.enhanced_processor = EnhancedDocumentProcessor(processor_config)
        
        # Keep legacy supported types for backward compatibility
        self.supported_types = {
            "application/pdf": self._process_pdf,
            "text/plain": self._process_text,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": self._process_docx,
            "text/markdown": self._process_markdown,
        }
        
        logger.info("Document processor initialized with enhanced backend")

    async def process_file(
        self, filename: str, content: bytes, file_type: str
    ) -> Dict[str, Any]:
        """
        Process uploaded file and extract text content
        Now uses enhanced processor with Docling support

        Args:
            filename: Name of the uploaded file
            content: File content as bytes
            file_type: MIME type of the file

        Returns:
            Dictionary with processed document information
        """
        try:
            # Use enhanced processor for better document handling
            result = await self.enhanced_processor.process_file(
                filename=filename,
                content=content,
                file_type=file_type,
                options={'extract_topics': True}
            )
            
            # Transform result to match legacy format for backward compatibility
            legacy_result = {
                'document_id': result['document_id'],
                'filename': result['filename'],
                'content': result['content'],
                'type': result['type'],
                'word_count': result['metadata'].get('word_count', 0),
                'character_count': result['metadata'].get('character_count', 0),
                # Add enhanced features
                'metadata': result['metadata'],
                'structure': result.get('structure'),
                'tables': result.get('tables', []),
                'images': result.get('images', []),
                'key_topics': result.get('key_topics', []),
                'processing_info': result.get('processing_info', {})
            }
            
            return legacy_result

        except Exception as e:
            logger.error("Document processing error: %s", str(e), exc_info=True)
            raise Exception(f"Failed to process document: {str(e)}") from e

    async def _process_pdf(self, content: bytes) -> str:
        """
        Extract text from PDF content
        """
        try:
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"

            return text

        except Exception as e:
            logger.error(f"PDF processing error: {str(e)}")
            raise Exception(f"Failed to process PDF: {str(e)}")

    async def _process_docx(self, content: bytes) -> str:
        """
        Extract text from DOCX content
        """
        try:
            doc_file = io.BytesIO(content)
            doc = docx.Document(doc_file)

            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"

            return text

        except Exception as e:
            logger.error(f"DOCX processing error: {str(e)}")
            raise Exception(f"Failed to process DOCX: {str(e)}")

    async def _process_text(self, content: bytes) -> str:
        """
        Process plain text content
        """
        try:
            return content.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Text processing error: {str(e)}")
            raise Exception(f"Failed to process text: {str(e)}")

    async def _process_markdown(self, content: bytes) -> str:
        """
        Process Markdown content
        """
        try:
            # For now, just treat as plain text
            # Could add markdown parsing later
            return content.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Markdown processing error: {str(e)}")
            raise Exception(f"Failed to process markdown: {str(e)}")

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text content
        """
        # Remove excessive whitespace
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if line:  # Skip empty lines
                cleaned_lines.append(line)

        # Join with single newlines
        cleaned_text = "\n".join(cleaned_lines)

        # Remove excessive spaces
        import re

        cleaned_text = re.sub(r" +", " ", cleaned_text)

        return cleaned_text

    def extract_key_topics(self, content: str) -> list:
        """
        Extract key topics from document content
        """
        # Simple keyword extraction - could be enhanced with NLP
        words = content.lower().split()

        # Filter out common words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }

        word_freq = {}
        for word in words:
            if word not in stop_words and len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Return top 10 most frequent words as key topics
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:10]]
