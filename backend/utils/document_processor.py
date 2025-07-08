import uuid
import PyPDF2
import docx
from typing import Dict, Any, Optional
import logging
import io

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self):
        """
        Initialize document processor
        """
        self.supported_types = {
            "application/pdf": self._process_pdf,
            "text/plain": self._process_text,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": self._process_docx,
            "text/markdown": self._process_markdown,
        }

    async def process_file(
        self, filename: str, content: bytes, file_type: str
    ) -> Dict[str, Any]:
        """
        Process uploaded file and extract text content

        Args:
            filename: Name of the uploaded file
            content: File content as bytes
            file_type: MIME type of the file

        Returns:
            Dictionary with processed document information
        """
        try:
            document_id = str(uuid.uuid4())

            # Process based on file type
            if file_type in self.supported_types:
                processor_method = self.supported_types[file_type]
                text_content = await processor_method(content)
            else:
                # Fallback to treating as text
                text_content = content.decode("utf-8", errors="ignore")

            # Clean and prepare content
            cleaned_content = self._clean_text(text_content)

            return {
                "document_id": document_id,
                "filename": filename,
                "content": cleaned_content,
                "type": file_type,
                "word_count": len(cleaned_content.split()),
                "character_count": len(cleaned_content),
            }

        except Exception as e:
            logger.error(f"Document processing error: {str(e)}", exc_info=True)
            raise Exception(f"Failed to process document: {str(e)}")

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
