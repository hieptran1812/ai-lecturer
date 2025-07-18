from typing import List, Optional, Dict, Any
import logging
import time

from .base import DocumentParser, ParsedDocument, ParseError
from .docling_parser import DoclingParser, DOCLING_AVAILABLE
from .legacy_parser import LegacyParser

logger = logging.getLogger(__name__)


class ParserFactory:
    """
    Factory class for creating and managing document parsers.
    
    This factory provides intelligent parser selection, fallback mechanisms,
    and performance tracking for document processing.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize parser factory with configuration.
        
        Args:
            config: Configuration dictionary for parsers
                - prefer_docling (bool): Whether to prefer Docling over legacy parsers
                - enable_fallback (bool): Whether to enable fallback to other parsers
                - docling (dict): Docling-specific configuration
                - legacy (dict): Legacy parser configuration
        """
        self.config = config or {}
        self.parsers: List[DocumentParser] = []
        self.parser_metrics: Dict[str, Dict[str, Any]] = {}
        self._initialize_parsers()
    
    def _initialize_parsers(self) -> None:
        """Initialize available parsers in order of preference."""
        prefer_docling = self.config.get('prefer_docling', True)
        
        # Initialize parsers based on preference and availability
        if prefer_docling and DOCLING_AVAILABLE:
            self._init_docling_parser()
        
        # Always initialize legacy parser as fallback
        self._init_legacy_parser()
        
        # If docling wasn't initialized first, try it now
        if not prefer_docling and DOCLING_AVAILABLE:
            self._init_docling_parser()
        
        logger.info(f"Initialized {len(self.parsers)} parsers: {self.get_available_parsers()}")
    
    def _init_docling_parser(self) -> None:
        """Initialize Docling parser if available."""
        try:
            docling_config = self.config.get('docling', {})
            docling_parser = DoclingParser(docling_config)
            self.parsers.append(docling_parser)
            self.parser_metrics['DoclingParser'] = {
                'initialized': True,
                'documents_processed': 0,
                'success_rate': 0.0,
                'average_processing_time': 0.0
            }
            logger.info("Docling parser initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Docling parser: {str(e)}")
            self.parser_metrics['DoclingParser'] = {
                'initialized': False,
                'error': str(e)
            }
    
    def _init_legacy_parser(self) -> None:
        """Initialize legacy parser."""
        try:
            legacy_config = self.config.get('legacy', {})
            legacy_parser = LegacyParser(legacy_config)
            self.parsers.append(legacy_parser)
            self.parser_metrics['LegacyParser'] = {
                'initialized': True,
                'documents_processed': 0,
                'success_rate': 0.0,
                'average_processing_time': 0.0
            }
            logger.info("Legacy parser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize legacy parser: {str(e)}")
            self.parser_metrics['LegacyParser'] = {
                'initialized': False,
                'error': str(e)
            }
    
    def get_parser(self, file_type: str, filename: str) -> Optional[DocumentParser]:
        """
        Get the best available parser for the given file type.
        
        Args:
            file_type: MIME type of the file
            filename: Name of the file
            
        Returns:
            DocumentParser: Best available parser or None if no parser available
        """
        # Find all parsers that can handle this file type
        compatible_parsers = [
            parser for parser in self.parsers
            if parser.can_parse(file_type, filename)
        ]
        
        if not compatible_parsers:
            logger.warning(f"No parser available for file type: {file_type} (filename: {filename})")
            return None
        
        # Select the best parser based on metrics and preference
        best_parser = self._select_best_parser(compatible_parsers, file_type, filename)
        
        logger.info(f"Selected parser: {best_parser.__class__.__name__} for {filename}")
        return best_parser
    
    def _select_best_parser(self, parsers: List[DocumentParser], file_type: str, filename: str) -> DocumentParser:
        """
        Select the best parser from compatible parsers.
        
        Args:
            parsers: List of compatible parsers
            file_type: MIME type of the file
            filename: Name of the file
            
        Returns:
            DocumentParser: Best parser
        """
        # If only one parser is available, return it
        if len(parsers) == 1:
            return parsers[0]
        
        # Score parsers based on various factors
        parser_scores = []
        
        for parser in parsers:
            parser_name = parser.__class__.__name__
            metrics = self.parser_metrics.get(parser_name, {})
            
            score = 0
            
            # Preference score (Docling preferred)
            if parser_name == 'DoclingParser':
                score += 10
            
            # Success rate score
            success_rate = metrics.get('success_rate', 0.5)
            score += success_rate * 5
            
            # Processing time score (lower is better)
            avg_time = metrics.get('average_processing_time', 10)
            score += max(0, 5 - avg_time)  # Bonus for faster processing
            
            # File type compatibility score
            if file_type in ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                if parser_name == 'DoclingParser':
                    score += 5  # Docling is better for complex documents
            
            parser_scores.append((parser, score))
        
        # Return parser with highest score
        best_parser = max(parser_scores, key=lambda x: x[1])[0]
        return best_parser
    
    def get_available_parsers(self) -> List[str]:
        """
        Get list of available parser names.
        
        Returns:
            List[str]: List of available parser class names
        """
        return [parser.__class__.__name__ for parser in self.parsers]
    
    def get_supported_types(self) -> List[str]:
        """
        Get all supported MIME types across all parsers.
        
        Returns:
            List[str]: List of all supported MIME types
        """
        supported_types = set()
        for parser in self.parsers:
            supported_types.update(parser.get_supported_types())
        return sorted(list(supported_types))
    
    def get_parser_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get performance metrics for all parsers.
        
        Returns:
            Dict[str, Dict[str, Any]]: Parser metrics
        """
        # Update metrics from parsers that support it
        for parser in self.parsers:
            if hasattr(parser, 'get_performance_metrics'):
                parser_name = parser.__class__.__name__
                parser_metrics = parser.get_performance_metrics()
                self.parser_metrics[parser_name].update(parser_metrics)
        
        return self.parser_metrics.copy()
    
    def _update_parser_metrics(self, parser_name: str, processing_time: float, success: bool) -> None:
        """
        Update parser performance metrics.
        
        Args:
            parser_name: Name of the parser
            processing_time: Time taken for processing
            success: Whether processing was successful
        """
        if parser_name not in self.parser_metrics:
            self.parser_metrics[parser_name] = {
                'documents_processed': 0,
                'successful_documents': 0,
                'total_processing_time': 0.0,
                'success_rate': 0.0,
                'average_processing_time': 0.0
            }
        
        metrics = self.parser_metrics[parser_name]
        metrics['documents_processed'] += 1
        metrics['total_processing_time'] += processing_time
        
        if success:
            metrics['successful_documents'] += 1
        
        # Update calculated metrics
        metrics['success_rate'] = metrics['successful_documents'] / metrics['documents_processed']
        metrics['average_processing_time'] = metrics['total_processing_time'] / metrics['documents_processed']
    
    async def parse_document(self, content: bytes, filename: str, file_type: str) -> ParsedDocument:
        """
        Parse document using the best available parser with intelligent fallback.
        
        Args:
            content: File content as bytes
            filename: Name of the file
            file_type: MIME type of the file
            
        Returns:
            ParsedDocument: Parsed document
            
        Raises:
            ParseError: If no parser can handle the file or all parsers fail
        """
        if not self.parsers:
            raise ParseError(
                "No parsers available",
                "ParserFactory",
                RuntimeError("No parsers initialized")
            )
        
        # Get primary parser
        primary_parser = self.get_parser(file_type, filename)
        
        if not primary_parser:
            raise ParseError(
                f"No parser available for file type: {file_type} (filename: {filename})",
                "ParserFactory",
                ValueError(f"Unsupported file type: {file_type}")
            )
        
        # Track all attempted parsers and their errors
        attempted_parsers = []
        errors = []
        
        # Try primary parser first
        start_time = time.time()
        try:
            result = await primary_parser.parse(content, filename)
            processing_time = time.time() - start_time
            
            self._update_parser_metrics(primary_parser.__class__.__name__, processing_time, True)
            
            logger.info("Successfully parsed %s with %s in %.2fs",
                        filename, primary_parser.__class__.__name__, processing_time)
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            attempted_parsers.append(primary_parser.__class__.__name__)
            errors.append(str(e))
            
            self._update_parser_metrics(primary_parser.__class__.__name__, processing_time, False)
            
            logger.warning(f"Primary parser {primary_parser.__class__.__name__} failed for {filename}: {str(e)}")
        
        # Try fallback parsers if enabled
        if self.config.get('enable_fallback', True):
            # Get all other compatible parsers
            compatible_parsers = [
                parser for parser in self.parsers
                if (parser != primary_parser and
                    parser.can_parse(file_type, filename))
            ]
            
            for fallback_parser in compatible_parsers:
                start_time = time.time()
                try:
                    logger.info(f"Trying fallback parser: {fallback_parser.__class__.__name__} for {filename}")
                    
                    result = await fallback_parser.parse(content, filename)
                    processing_time = time.time() - start_time
                    
                    self._update_parser_metrics(fallback_parser.__class__.__name__, processing_time, True)
                    
                    logger.info("Successfully parsed %s with fallback parser %s in %.2fs",
                                filename, fallback_parser.__class__.__name__, processing_time)
                    
                    return result
                    
                except Exception as e:
                    processing_time = time.time() - start_time
                    attempted_parsers.append(fallback_parser.__class__.__name__)
                    errors.append(str(e))
                    
                    self._update_parser_metrics(fallback_parser.__class__.__name__, processing_time, False)
                    
                    logger.warning(f"Fallback parser {fallback_parser.__class__.__name__} "
                                  f"also failed for {filename}: {str(e)}")
        
        # If all parsers failed, raise comprehensive error
        error_summary = f"All parsers failed for {filename}. Attempted: {', '.join(attempted_parsers)}"
        detailed_errors = '; '.join([f"{parser}: {error}" for parser, error in zip(attempted_parsers, errors)])
        
        logger.error(f"{error_summary}. Errors: {detailed_errors}")
        
        raise ParseError(
            f"{error_summary}. Last error: {errors[-1] if errors else 'Unknown error'}",
            "ParserFactory",
            RuntimeError(detailed_errors)
        )
