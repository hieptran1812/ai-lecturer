import uuid
from typing import Dict, Any, Optional, List
import logging
from pathlib import Path

from .parsers.factory import ParserFactory
from .parsers.base import ParsedDocument, ParseError

logger = logging.getLogger(__name__)


class EnhancedDocumentProcessor:
    """
    Enhanced document processor with support for multiple parsers and advanced features
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize enhanced document processor
        
        Args:
            config: Configuration dictionary for parsers and processing
        """
        self.config = config or {}
        self.parser_factory = ParserFactory(config)
        
        # Configuration for document processing
        self.max_content_length = self.config.get('max_content_length', 100000)  # 100KB
        self.extract_key_topics = self.config.get('extract_key_topics', True)
        
        logger.info("Enhanced document processor initialized")
    
    async def process_file(
        self, 
        filename: str, 
        content: bytes, 
        file_type: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process uploaded file and extract comprehensive information
        
        Args:
            filename: Name of the uploaded file
            content: File content as bytes
            file_type: MIME type of the file
            options: Optional processing options
            
        Returns:
            Dictionary with comprehensive document information
        """
        try:
            document_id = str(uuid.uuid4())
            processing_options = options or {}
            
            # Validate file size
            if len(content) > self.config.get('max_file_size', 10 * 1024 * 1024):  # 10MB default
                raise ValueError(f"File too large: {len(content)} bytes")
            
            # Parse document using appropriate parser
            parsed_doc = await self.parser_factory.parse_document(
                content=content,
                filename=filename,
                file_type=file_type
            )
            
            # Process the parsed document
            processed_result = await self._process_parsed_document(
                parsed_doc=parsed_doc,
                document_id=document_id,
                options=processing_options
            )
            
            logger.info(f"Document processed successfully: {document_id}")
            return processed_result
            
        except ParseError as e:
            logger.error(f"Document parsing failed: {str(e)}")
            raise Exception(f"Failed to parse document: {str(e)}")
        except Exception as e:
            logger.error(f"Document processing error: {str(e)}", exc_info=True)
            raise Exception(f"Failed to process document: {str(e)}")
    
    async def _process_parsed_document(
        self,
        parsed_doc: ParsedDocument,
        document_id: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process parsed document and extract additional information
        
        Args:
            parsed_doc: Parsed document from parser
            document_id: Unique document identifier
            options: Processing options
            
        Returns:
            Dictionary with processed document information
        """
        result = {
            'document_id': document_id,
            'filename': parsed_doc.metadata.get('filename', 'unknown'),
            'content': parsed_doc.content,
            'type': parsed_doc.metadata.get('parser_type', 'unknown'),
            'metadata': parsed_doc.metadata,
            'structure': parsed_doc.structure,
            'tables': parsed_doc.tables or [],
            'images': parsed_doc.images or [],
            'processing_info': {
                'parser_used': parsed_doc.metadata.get('parser_type', 'unknown'),
                'content_length': len(parsed_doc.content),
                'has_structure': parsed_doc.structure is not None,
                'has_tables': bool(parsed_doc.tables),
                'has_images': bool(parsed_doc.images)
            }
        }
        
        # Extract key topics if enabled
        if self.extract_key_topics and options.get('extract_topics', True):
            result['key_topics'] = self._extract_key_topics(parsed_doc.content)
        
        # Extract summary if requested
        if options.get('generate_summary', False):
            result['summary'] = self._generate_summary(parsed_doc.content)
        
        # Validate content length
        if len(parsed_doc.content) > self.max_content_length:
            result['content_truncated'] = True
            result['content'] = parsed_doc.content[:self.max_content_length] + "\n[Content truncated...]"
        
        return result
    
    def _extract_key_topics(self, content: str) -> List[str]:
        """
        Extract key topics from document content
        
        Args:
            content: Document text content
            
        Returns:
            List[str]: List of key topics/keywords
        """
        try:
            # Simple keyword extraction - could be enhanced with NLP
            words = content.lower().split()
            
            # Filter out common stop words
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
                'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
                'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us',
                'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
            }
            
            # Count word frequencies
            word_freq = {}
            for word in words:
                # Remove punctuation and filter short words
                clean_word = ''.join(char for char in word if char.isalnum())
                if len(clean_word) > 3 and clean_word not in stop_words:
                    word_freq[clean_word] = word_freq.get(clean_word, 0) + 1
            
            # Return top 15 most frequent words as key topics
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            return [word for word, freq in sorted_words[:15]]
            
        except Exception as e:
            logger.warning(f"Failed to extract key topics: {str(e)}")
            return []
    
    def _generate_summary(self, content: str, max_sentences: int = 3) -> str:
        """
        Generate a basic summary of the document content
        
        Args:
            content: Document text content
            max_sentences: Maximum number of sentences in summary
            
        Returns:
            str: Basic summary of the document
        """
        try:
            # Split into sentences
            sentences = content.split('.')
            
            # Clean and filter sentences
            clean_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20:  # Filter very short sentences
                    clean_sentences.append(sentence)
            
            # Take first few sentences as summary
            if clean_sentences:
                summary_sentences = clean_sentences[:max_sentences]
                return '. '.join(summary_sentences) + '.'
            
            return "No summary available."
            
        except Exception as e:
            logger.warning(f"Failed to generate summary: {str(e)}")
            return "Summary generation failed."
    
    def get_supported_types(self) -> List[str]:
        """
        Get all supported file types
        
        Returns:
            List[str]: List of supported MIME types
        """
        return self.parser_factory.get_supported_types()
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics and available parsers
        
        Returns:
            Dict[str, Any]: Processing statistics
        """
        return {
            'available_parsers': self.parser_factory.get_available_parsers(),
            'supported_types': self.get_supported_types(),
            'max_file_size': self.config.get('max_file_size', 10 * 1024 * 1024),
            'max_content_length': self.max_content_length
        }
