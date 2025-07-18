from typing import List, Dict, Any, Optional
import logging
import io
from pathlib import Path
import tempfile
import os
import time
import asyncio
from contextlib import asynccontextmanager

from .base import DocumentParser, ParsedDocument, ParseError

logger = logging.getLogger(__name__)

# Check Docling availability
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import PdfFormatOption
    DOCLING_AVAILABLE = True
    logger.info("Docling library loaded successfully")
except ImportError as e:
    logger.warning(f"Docling not available: {e}")
    DOCLING_AVAILABLE = False
    DocumentConverter = None
    InputFormat = None
    PdfPipelineOptions = None
    PdfFormatOption = None


class DoclingParser(DocumentParser):
    """
    Advanced document parser using Docling for comprehensive document processing.
    
    This parser provides enhanced capabilities including:
    - OCR for scanned documents
    - Table structure extraction
    - Image detection and metadata
    - Document structure analysis
    - Multi-format support (PDF, DOCX, PPTX, etc.)
    
    Features:
    - Automatic fallback for unsupported formats
    - Memory-efficient processing
    - Comprehensive error handling
    - Performance metrics tracking
    """
    
    # Supported MIME types mapping
    SUPPORTED_FORMATS = {
        'application/pdf': '.pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
        'text/html': '.html',
        'text/markdown': '.md',
        'text/plain': '.txt'
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Docling parser with configuration.
        
        Args:
            config: Configuration dictionary for parser settings
                - enable_ocr (bool): Enable OCR processing
                - enable_table_extraction (bool): Enable table extraction
                - processing_mode (str): 'accurate' or 'fast'
                - max_file_size (int): Maximum file size in bytes
                - timeout (int): Processing timeout in seconds
        """
        if not DOCLING_AVAILABLE:
            raise ParseError(
                "Docling library not available. Please install docling package.",
                "DoclingParser",
                ImportError("Docling not installed")
            )
        
        self.config = config or {}
        self._performance_metrics = {
            'documents_processed': 0,
            'total_processing_time': 0,
            'errors': 0,
            'average_processing_time': 0
        }
        
        # Configuration defaults
        self.enable_ocr = self.config.get('enable_ocr', True)
        self.enable_table_extraction = self.config.get('enable_table_extraction', True)
        self.processing_mode = self.config.get('processing_mode', 'accurate')
        self.max_file_size = self.config.get('max_file_size', 50 * 1024 * 1024)  # 50MB
        self.timeout = self.config.get('timeout', 300)  # 5 minutes
        
        self.converter = None
        self._init_converter()
        
    def _init_converter(self) -> None:
        """Initialize the Docling document converter with optimized settings."""
        try:
            # Configure pipeline options for better performance
            pipeline_options = PdfPipelineOptions(
                do_ocr=self.enable_ocr,
                do_table_structure=self.enable_table_extraction,
                table_structure_options={
                    "do_cell_matching": True,
                    "mode": self.processing_mode
                }
            )
            
            # Create converter with format-specific options
            format_options = {
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
            
            self.converter = DocumentConverter(
                format_options=format_options
            )
            
            logger.info(f"Docling converter initialized - OCR: {self.enable_ocr}, "
                       f"Tables: {self.enable_table_extraction}, Mode: {self.processing_mode}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Docling converter: {str(e)}")
            raise ParseError(
                f"Failed to initialize Docling parser: {str(e)}",
                "DoclingParser",
                e
            )
    
    def can_parse(self, file_type: str, filename: str) -> bool:
        """
        Check if Docling can parse this file type.
        
        Args:
            file_type: MIME type of the file
            filename: Name of the file
            
        Returns:
            bool: True if Docling can handle this file type
        """
        if not DOCLING_AVAILABLE:
            return False
            
        # Check by MIME type
        if file_type in self.SUPPORTED_FORMATS:
            return True
            
        # Check by file extension as fallback
        file_ext = Path(filename).suffix.lower()
        return file_ext in self.SUPPORTED_FORMATS.values()
    
    def get_supported_types(self) -> List[str]:
        """
        Get list of MIME types supported by Docling.
        
        Returns:
            List[str]: List of supported MIME types
        """
        return list(self.SUPPORTED_FORMATS.keys())
    
    @asynccontextmanager
    async def _create_temp_file(self, content: bytes, filename: str):
        """
        Create a temporary file for Docling processing.
        
        Args:
            content: File content as bytes
            filename: Original filename for suffix detection
            
        Yields:
            str: Path to temporary file
        """
        suffix = Path(filename).suffix or '.tmp'
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            yield tmp_file_path
        finally:
            # Clean up temporary file
            try:
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
            except OSError as e:
                logger.warning(f"Failed to cleanup temporary file {tmp_file_path}: {e}")
    
    def _validate_file_size(self, content: bytes, filename: str) -> None:
        """
        Validate file size before processing.
        
        Args:
            content: File content as bytes
            filename: Name of the file
            
        Raises:
            ParseError: If file is too large
        """
        file_size = len(content)
        if file_size > self.max_file_size:
            raise ParseError(
                f"File {filename} is too large: {file_size} bytes "
                f"(max: {self.max_file_size} bytes)",
                "DoclingParser",
                ValueError("File too large")
            )
    
    def _update_performance_metrics(self, processing_time: float, success: bool) -> None:
        """
        Update performance metrics.
        
        Args:
            processing_time: Time taken for processing
            success: Whether processing was successful
        """
        self._performance_metrics['documents_processed'] += 1
        self._performance_metrics['total_processing_time'] += processing_time
        
        if not success:
            self._performance_metrics['errors'] += 1
        
        # Calculate average processing time
        if self._performance_metrics['documents_processed'] > 0:
            self._performance_metrics['average_processing_time'] = (
                self._performance_metrics['total_processing_time'] /
                self._performance_metrics['documents_processed']
            )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for this parser.
        
        Returns:
            Dict[str, Any]: Performance metrics
        """
        return self._performance_metrics.copy()
    
    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        """
        Parse document using Docling with comprehensive error handling and performance tracking.
        
        Args:
            content: File content as bytes
            filename: Name of the file
            
        Returns:
            ParsedDocument: Parsed document with structured data
            
        Raises:
            ParseError: If parsing fails
        """
        start_time = time.time()
        success = False
        
        try:
            # Validate file size first
            self._validate_file_size(content, filename)
            
            logger.info(f"Starting Docling parsing for {filename} ({len(content)} bytes)")
            
            # Use async context manager for temporary file
            async with self._create_temp_file(content, filename) as tmp_file_path:
                # Run conversion in executor to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self._convert_document_sync,
                    tmp_file_path,
                    filename
                )
                
                # Extract content and metadata
                text_content = self._extract_text_content(result)
                metadata = self._extract_metadata(result, filename, len(content))
                structure = self._extract_structure(result)
                tables = self._extract_tables(result)
                images = self._extract_images(result)
                
                # Create parsed document
                parsed_doc = ParsedDocument(
                    content=text_content,
                    metadata=metadata,
                    structure=structure,
                    tables=tables,
                    images=images
                )
                
                success = True
                processing_time = time.time() - start_time
                
                logger.info(f"Docling parsing completed for {filename} in {processing_time:.2f}s")
                
                return parsed_doc
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Docling parsing failed for {filename} after {processing_time:.2f}s: {str(e)}")
            
            if isinstance(e, ParseError):
                raise
            else:
                raise ParseError(
                    f"Failed to parse document {filename} with Docling: {str(e)}",
                    "DoclingParser",
                    e
                )
        finally:
            # Always update metrics
            processing_time = time.time() - start_time
            self._update_performance_metrics(processing_time, success)
    
    def _convert_document_sync(self, file_path: str, filename: str) -> Any:
        """
        Synchronous document conversion (to be run in executor).
        
        Args:
            file_path: Path to temporary file
            filename: Original filename for logging
            
        Returns:
            Docling conversion result
        """
        try:
            logger.debug(f"Converting {filename} using Docling")
            result = self.converter.convert(file_path)
            logger.debug(f"Docling conversion completed for {filename}")
            return result
        except Exception as e:
            logger.error(f"Docling conversion failed for {filename}: {str(e)}")
            raise
    
    def _extract_text_content(self, result: Any) -> str:
        """
        Extract text content from Docling result.
        
        Args:
            result: Docling conversion result
            
        Returns:
            str: Extracted text content
        """
        try:
            if hasattr(result, 'document') and hasattr(result.document, 'export_to_markdown'):
                text_content = result.document.export_to_markdown()
                if text_content:
                    return text_content
            
            # Fallback to plain text extraction
            if hasattr(result, 'document') and hasattr(result.document, 'export_to_text'):
                return result.document.export_to_text()
            
            logger.warning("No text content could be extracted from document")
            return ""
            
        except Exception as e:
            logger.warning(f"Failed to extract text content: {str(e)}")
            return ""
    
    def _extract_metadata(self, result: Any, filename: str, file_size: int) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from Docling result.
        
        Args:
            result: Docling conversion result
            filename: Original filename
            file_size: Original file size
            
        Returns:
            Dict[str, Any]: Extracted metadata
        """
        try:
            doc = result.document
            metadata = {
                'filename': filename,
                'file_size': file_size,
                'parser_type': 'docling',
                'parser_version': getattr(result, 'version', 'unknown'),
                'processing_time': time.time()
            }
            
            # Basic document information
            if hasattr(doc, 'pages'):
                metadata['page_count'] = len(doc.pages)
            
            # Text statistics
            text_content = self._extract_text_content(result)
            if text_content:
                metadata.update({
                    'word_count': len(text_content.split()),
                    'character_count': len(text_content),
                    'line_count': len(text_content.split('\n'))
                })
            
            # Document-specific metadata if available
            if hasattr(doc, 'metadata') and doc.metadata:
                doc_metadata = doc.metadata
                metadata.update({
                    'title': getattr(doc_metadata, 'title', ''),
                    'author': getattr(doc_metadata, 'author', ''),
                    'subject': getattr(doc_metadata, 'subject', ''),
                    'creator': getattr(doc_metadata, 'creator', ''),
                    'producer': getattr(doc_metadata, 'producer', ''),
                    'creation_date': getattr(doc_metadata, 'creation_date', ''),
                    'modification_date': getattr(doc_metadata, 'modification_date', '')
                })
            
            # Content structure metrics
            if hasattr(doc, 'tables'):
                metadata['table_count'] = len(doc.tables)
            
            if hasattr(doc, 'pictures'):
                metadata['image_count'] = len(doc.pictures)
            
            # Language detection if available
            if hasattr(doc, 'language'):
                metadata['language'] = doc.language
            
            return metadata
            
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {str(e)}")
            return {
                'filename': filename,
                'file_size': file_size,
                'parser_type': 'docling',
                'error': str(e),
                'processing_time': time.time()
            }
    
    def _extract_structure(self, result: Any) -> Dict[str, Any]:
        """
        Extract comprehensive document structure information.
        
        Args:
            result: Docling conversion result
            
        Returns:
            Dict[str, Any]: Document structure information
        """
        try:
            doc = result.document
            structure = {
                'sections': [],
                'headings': [],
                'pages': [],
                'paragraphs': [],
                'lists': []
            }
            
            # Extract page information
            if hasattr(doc, 'pages'):
                for i, page in enumerate(doc.pages):
                    page_info = {
                        'page_number': i + 1,
                        'width': getattr(page, 'width', 0),
                        'height': getattr(page, 'height', 0),
                        'rotation': getattr(page, 'rotation', 0)
                    }
                    
                    # Add page-specific content if available
                    if hasattr(page, 'elements'):
                        page_info['element_count'] = len(page.elements)
                    
                    structure['pages'].append(page_info)
            
            # Extract text elements and classify them
            if hasattr(doc, 'texts'):
                for text_element in doc.texts:
                    element_info = {
                        'text': getattr(text_element, 'text', ''),
                        'page': getattr(text_element, 'page', 0),
                        'bbox': getattr(text_element, 'bbox', None)
                    }
                    
                    # Classify text elements
                    if hasattr(text_element, 'label'):
                        label = text_element.label.lower()
                        
                        if 'heading' in label or 'title' in label:
                            element_info['level'] = self._determine_heading_level(text_element)
                            structure['headings'].append(element_info)
                        elif 'paragraph' in label:
                            structure['paragraphs'].append(element_info)
                        elif 'list' in label:
                            structure['lists'].append(element_info)
                        else:
                            structure['sections'].append(element_info)
            
            # Sort headings by page and position
            structure['headings'] = sorted(
                structure['headings'],
                key=lambda x: (x.get('page', 0), x.get('bbox', {}).get('y', 0))
            )
            
            return structure
            
        except Exception as e:
            logger.warning(f"Failed to extract structure: {str(e)}")
            return {
                'error': str(e),
                'sections': [],
                'headings': [],
                'pages': []
            }
    
    def _extract_tables(self, result: Any) -> List[Dict[str, Any]]:
        """
        Extract comprehensive table information from document.
        
        Args:
            result: Docling conversion result
            
        Returns:
            List[Dict[str, Any]]: List of table information
        """
        try:
            tables = []
            doc = result.document
            
            if hasattr(doc, 'tables'):
                for i, table in enumerate(doc.tables):
                    table_data = {
                        'table_id': i,
                        'page': getattr(table, 'page', 0),
                        'bbox': getattr(table, 'bbox', None)
                    }
                    
                    # Extract table dimensions
                    if hasattr(table, 'num_rows'):
                        table_data['rows'] = table.num_rows
                    if hasattr(table, 'num_cols'):
                        table_data['columns'] = table.num_cols
                    
                    # Extract table content in multiple formats
                    content_extracted = False
                    
                    # Try to get structured data
                    if hasattr(table, 'export_to_dict'):
                        try:
                            table_data['content'] = table.export_to_dict()
                            content_extracted = True
                        except Exception as e:
                            logger.debug(f"Failed to export table {i} to dict: {e}")
                    
                    # Try to get CSV format
                    if hasattr(table, 'export_to_csv') and not content_extracted:
                        try:
                            table_data['csv_content'] = table.export_to_csv()
                            content_extracted = True
                        except Exception as e:
                            logger.debug(f"Failed to export table {i} to CSV: {e}")
                    
                    # Try to get raw data
                    if hasattr(table, 'data') and not content_extracted:
                        try:
                            table_data['raw_data'] = table.data
                            content_extracted = True
                        except Exception as e:
                            logger.debug(f"Failed to get raw data for table {i}: {e}")
                    
                    # Extract table headers if available
                    if hasattr(table, 'header'):
                        table_data['header'] = table.header
                    
                    # Add table caption if available
                    if hasattr(table, 'caption'):
                        table_data['caption'] = table.caption
                    
                    # Mark if content was successfully extracted
                    table_data['content_extracted'] = content_extracted
                    
                    tables.append(table_data)
            
            return tables
            
        except Exception as e:
            logger.warning(f"Failed to extract tables: {str(e)}")
            return []
    
    def _extract_images(self, result: Any) -> List[Dict[str, Any]]:
        """
        Extract comprehensive image information from document.
        
        Args:
            result: Docling conversion result
            
        Returns:
            List[Dict[str, Any]]: List of image information
        """
        try:
            images = []
            doc = result.document
            
            if hasattr(doc, 'pictures'):
                for i, picture in enumerate(doc.pictures):
                    image_data = {
                        'image_id': i,
                        'page': getattr(picture, 'page', 0),
                        'bbox': getattr(picture, 'bbox', None)
                    }
                    
                    # Extract image dimensions
                    if hasattr(picture, 'width'):
                        image_data['width'] = picture.width
                    if hasattr(picture, 'height'):
                        image_data['height'] = picture.height
                    
                    # Extract image format information
                    if hasattr(picture, 'format'):
                        image_data['format'] = picture.format
                    if hasattr(picture, 'dpi'):
                        image_data['dpi'] = picture.dpi
                    
                    # Add image caption if available
                    if hasattr(picture, 'caption'):
                        image_data['caption'] = picture.caption
                    
                    # Add alt text if available
                    if hasattr(picture, 'alt_text'):
                        image_data['alt_text'] = picture.alt_text
                    
                    # Try to extract image metadata
                    if hasattr(picture, 'metadata'):
                        image_data['metadata'] = picture.metadata
                    
                    # Check if image has text content (for OCR)
                    if hasattr(picture, 'text_content'):
                        image_data['text_content'] = picture.text_content
                    
                    images.append(image_data)
            
            return images
            
        except Exception as e:
            logger.warning(f"Failed to extract images: {str(e)}")
            return []
    
    def _determine_heading_level(self, text_element: Any) -> int:
        """
        Determine heading level based on text element properties.
        
        Args:
            text_element: Text element from Docling
            
        Returns:
            int: Heading level (1-6)
        """
        try:
            # Check if explicit level is provided
            if hasattr(text_element, 'level'):
                return min(max(int(text_element.level), 1), 6)
            
            # Analyze font size if available
            if hasattr(text_element, 'font_size'):
                font_size = text_element.font_size
                if font_size >= 20:
                    return 1
                elif font_size >= 18:
                    return 2
                elif font_size >= 16:
                    return 3
                elif font_size >= 14:
                    return 4
                elif font_size >= 12:
                    return 5
                else:
                    return 6
            
            # Check label for explicit level information
            if hasattr(text_element, 'label'):
                label = text_element.label.lower()
                if 'h1' in label or 'title' in label:
                    return 1
                elif 'h2' in label or 'subtitle' in label:
                    return 2
                elif 'h3' in label:
                    return 3
                elif 'h4' in label:
                    return 4
                elif 'h5' in label:
                    return 5
                elif 'h6' in label:
                    return 6
            
            # Analyze text content for patterns
            if hasattr(text_element, 'text'):
                text = text_element.text.strip()
                if text.isupper() and len(text) < 100:
                    return 1  # All caps likely to be main heading
                elif text.endswith(':') and len(text) < 50:
                    return 2  # Colon endings often section headings
            
            # Default to level 3 for unknown headings
            return 3
            
        except Exception as e:
            logger.debug(f"Failed to determine heading level: {e}")
            return 3
