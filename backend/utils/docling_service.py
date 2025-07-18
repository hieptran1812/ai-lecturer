"""
Docling Service for managing document processing instances and caching.

This service provides a high-level interface for Docling operations with:
- Instance management and caching
- Configuration management
- Performance monitoring
- Error handling and recovery
"""

from typing import Dict, Any, Optional, List
import logging
import asyncio
from datetime import datetime

from .parsers.docling_parser import DoclingParser, DOCLING_AVAILABLE
from .parsers.base import ParsedDocument, ParseError
from ..config import settings

logger = logging.getLogger(__name__)


class DoclingService:
    """
    Service for managing Docling document processing with caching and optimization.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Docling service.
        
        Args:
            config: Service configuration
        """
        self.config = config or self._get_default_config()
        self._parser_cache: Dict[str, DoclingParser] = {}
        self._processing_queue = asyncio.Queue()
        self._stats = {
            'documents_processed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'total_processing_time': 0.0,
            'service_started': datetime.now()
        }
        
        # Initialize service if Docling is available
        if not DOCLING_AVAILABLE:
            logger.warning("Docling not available, service will be disabled")
            self._enabled = False
        else:
            self._enabled = True
            logger.info("Docling service initialized successfully")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration from settings."""
        return {
            'enabled': settings.docling_enabled,
            'ocr_enabled': settings.docling_ocr_enabled,
            'table_extraction': settings.docling_table_extraction,
            'processing_mode': settings.docling_processing_mode,
            'timeout': settings.docling_timeout,
            'max_file_size': settings.docling_max_file_size,
            'cache_size': 10,  # Number of parser instances to cache
            'cache_ttl': 3600,  # Cache TTL in seconds
        }
    
    @property
    def enabled(self) -> bool:
        """Check if service is enabled."""
        return self._enabled and DOCLING_AVAILABLE
    
    def get_parser(self, config_key: str = 'default') -> DoclingParser:
        """
        Get or create a cached parser instance.
        
        Args:
            config_key: Configuration key for parser caching
            
        Returns:
            DoclingParser: Parser instance
        """
        if not self.enabled:
            raise RuntimeError("Docling service is not enabled")
        
        # Check cache first
        if config_key in self._parser_cache:
            self._stats['cache_hits'] += 1
            return self._parser_cache[config_key]
        
        # Create new parser
        self._stats['cache_misses'] += 1
        parser = DoclingParser(self.config)
        
        # Cache the parser (with size limit)
        if len(self._parser_cache) >= self.config.get('cache_size', 10):
            # Remove oldest entry
            oldest_key = next(iter(self._parser_cache))
            del self._parser_cache[oldest_key]
        
        self._parser_cache[config_key] = parser
        logger.debug("Created and cached new parser for key: %s", config_key)
        
        return parser
    
    async def process_document(
        self,
        content: bytes,
        filename: str,
        options: Optional[Dict[str, Any]] = None
    ) -> ParsedDocument:
        """
        Process document using Docling with caching and optimization.
        
        Args:
            content: Document content as bytes
            filename: Original filename
            options: Processing options
            
        Returns:
            ParsedDocument: Processed document
        """
        if not self.enabled:
            raise RuntimeError("Docling service is not enabled")
        
        start_time = datetime.now()
        
        try:
            # Validate file size
            if len(content) > self.config.get('max_file_size', 50 * 1024 * 1024):
                raise ValueError(f"File too large: {len(content)} bytes")
            
            # Get parser for this processing task
            config_key = self._get_config_key(options)
            parser = self.get_parser(config_key)
            
            # Process document
            result = await parser.parse(content, filename)
            
            # Update stats
            processing_time = (datetime.now() - start_time).total_seconds()
            self._stats['documents_processed'] += 1
            self._stats['total_processing_time'] += processing_time
            
            logger.info("Document processed successfully: %s (%.2fs)", filename, processing_time)
            
            return result
            
        except Exception as e:
            self._stats['errors'] += 1
            logger.error("Document processing failed: %s - %s", filename, str(e))
            raise ParseError(f"Docling processing failed: {str(e)}", "DoclingService", e)
    
    def _get_config_key(self, options: Optional[Dict[str, Any]]) -> str:
        """
        Generate configuration key for parser caching.
        
        Args:
            options: Processing options
            
        Returns:
            str: Configuration key
        """
        if not options:
            return 'default'
        
        # Create key based on relevant options
        key_parts = []
        
        if options.get('ocr_enabled') != self.config.get('ocr_enabled'):
            key_parts.append(f"ocr_{options.get('ocr_enabled')}")
        
        if options.get('table_extraction') != self.config.get('table_extraction'):
            key_parts.append(f"tables_{options.get('table_extraction')}")
        
        if options.get('processing_mode') != self.config.get('processing_mode'):
            key_parts.append(f"mode_{options.get('processing_mode')}")
        
        return '_'.join(key_parts) if key_parts else 'default'
    
    async def batch_process_documents(
        self,
        documents: List[Dict[str, Any]],
        max_concurrent: int = 3
    ) -> List[ParsedDocument]:
        """
        Process multiple documents concurrently.
        
        Args:
            documents: List of documents to process
                Each document should have: content, filename, options
            max_concurrent: Maximum concurrent processing
            
        Returns:
            List[ParsedDocument]: List of processed documents
        """
        if not self.enabled:
            raise RuntimeError("Docling service is not enabled")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single(doc: Dict[str, Any]) -> ParsedDocument:
            async with semaphore:
                return await self.process_document(
                    doc['content'],
                    doc['filename'],
                    doc.get('options')
                )
        
        # Process all documents concurrently
        tasks = [process_single(doc) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log them
        processed_docs = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Failed to process document %s: %s", 
                           documents[i]['filename'], str(result))
            else:
                processed_docs.append(result)
        
        return processed_docs
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get service statistics.
        
        Returns:
            Dict[str, Any]: Service statistics
        """
        uptime = datetime.now() - self._stats['service_started']
        
        stats = self._stats.copy()
        stats.update({
            'uptime_seconds': uptime.total_seconds(),
            'cache_size': len(self._parser_cache),
            'cache_hit_rate': (
                self._stats['cache_hits'] / 
                max(1, self._stats['cache_hits'] + self._stats['cache_misses'])
            ),
            'average_processing_time': (
                self._stats['total_processing_time'] / 
                max(1, self._stats['documents_processed'])
            ),
            'enabled': self.enabled,
            'config': self.config
        })
        
        return stats
    
    def clear_cache(self) -> None:
        """Clear parser cache."""
        self._parser_cache.clear()
        logger.info("Parser cache cleared")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the service.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        health = {
            'status': 'healthy',
            'enabled': self.enabled,
            'docling_available': DOCLING_AVAILABLE,
            'cache_size': len(self._parser_cache),
            'errors': self._stats['errors'],
            'timestamp': datetime.now().isoformat()
        }
        
        if not self.enabled:
            health['status'] = 'disabled'
            health['message'] = 'Docling service is disabled'
        
        # Test basic functionality
        if self.enabled:
            try:
                parser = self.get_parser('health_check')
                # Simple test - just check if parser is working
                if parser.converter is None:
                    health['status'] = 'unhealthy'
                    health['message'] = 'Parser not properly initialized'
            except Exception as e:
                health['status'] = 'unhealthy'
                health['message'] = f'Health check failed: {str(e)}'
        
        return health


# Global service instance
_docling_service: Optional[DoclingService] = None


def get_docling_service() -> DoclingService:
    """
    Get or create global Docling service instance.
    
    Returns:
        DoclingService: Global service instance
    """
    global _docling_service
    
    if _docling_service is None:
        _docling_service = DoclingService()
    
    return _docling_service


async def initialize_docling_service(config: Optional[Dict[str, Any]] = None) -> DoclingService:
    """
    Initialize Docling service with configuration.
    
    Args:
        config: Service configuration
        
    Returns:
        DoclingService: Initialized service
    """
    global _docling_service
    
    _docling_service = DoclingService(config)
    
    # Perform health check
    health = await _docling_service.health_check()
    logger.info("Docling service health check: %s", health['status'])
    
    return _docling_service
