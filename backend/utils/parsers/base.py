from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParsedDocument:
    """
    Standardized document representation after parsing
    """
    content: str
    metadata: Dict[str, Any]
    structure: Optional[Dict[str, Any]] = None
    tables: Optional[List[Dict[str, Any]]] = None
    images: Optional[List[Dict[str, Any]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            'content': self.content,
            'metadata': self.metadata,
            'structure': self.structure,
            'tables': self.tables or [],
            'images': self.images or []
        }


class DocumentParser(ABC):
    """
    Abstract base class for document parsers
    """
    
    @abstractmethod
    def can_parse(self, file_type: str, filename: str) -> bool:
        """
        Check if this parser can handle the given file type
        
        Args:
            file_type: MIME type of the file
            filename: Name of the file
            
        Returns:
            bool: True if parser can handle this file type
        """
        pass
    
    @abstractmethod
    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        """
        Parse document content
        
        Args:
            content: File content as bytes
            filename: Name of the file
            
        Returns:
            ParsedDocument: Parsed document with structured data
        """
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[str]:
        """
        Get list of supported MIME types
        
        Returns:
            List[str]: List of supported MIME types
        """
        pass


class ParseError(Exception):
    """Custom exception for parsing errors"""
    
    def __init__(self, message: str, parser_type: str, original_error: Optional[Exception] = None):
        self.message = message
        self.parser_type = parser_type
        self.original_error = original_error
        super().__init__(self.message)
