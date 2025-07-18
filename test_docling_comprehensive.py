#!/usr/bin/env python3
"""
Comprehensive test suite for Docling integration in AI Lecturer.

This test suite validates:
- Docling parser functionality
- Parser factory selection
- Document processing pipeline
- Error handling and fallback mechanisms
- Performance metrics
- Service health checks
"""

import os
import sys
import asyncio
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.config import settings
from backend.utils.parsers.docling_parser import DoclingParser, DOCLING_AVAILABLE
from backend.utils.parsers.legacy_parser import LegacyParser
from backend.utils.parsers.factory import ParserFactory
from backend.utils.enhanced_document_processor import EnhancedDocumentProcessor
from backend.utils.docling_service import DoclingService, get_docling_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DoclingIntegrationTest:
    """Comprehensive test suite for Docling integration."""
    
    def __init__(self):
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
    def log_test_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
        
        if passed:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"{test_name}: {message}")
            
        if message:
            logger.info(f"  → {message}")
    
    def skip_test(self, test_name: str, reason: str):
        """Skip a test."""
        logger.info(f"⏭️  SKIP: {test_name} - {reason}")
        self.test_results['skipped'] += 1
    
    async def test_docling_availability(self):
        """Test Docling library availability."""
        try:
            if DOCLING_AVAILABLE:
                self.log_test_result("Docling availability", True, "Docling is available")
            else:
                self.log_test_result("Docling availability", False, "Docling is not available")
        except Exception as e:
            self.log_test_result("Docling availability", False, str(e))
    
    async def test_docling_parser_init(self):
        """Test Docling parser initialization."""
        if not DOCLING_AVAILABLE:
            self.skip_test("Docling parser initialization", "Docling not available")
            return
        
        try:
            config = {
                'enable_ocr': True,
                'enable_table_extraction': True,
                'processing_mode': 'fast',
                'max_file_size': 10 * 1024 * 1024,
                'timeout': 60
            }
            
            parser = DoclingParser(config)
            
            # Test basic properties
            supported_types = parser.get_supported_types()
            self.log_test_result(
                "Docling parser initialization", 
                True, 
                f"Supports {len(supported_types)} file types"
            )
            
            # Test can_parse method
            can_parse_pdf = parser.can_parse('application/pdf', 'test.pdf')
            can_parse_docx = parser.can_parse(
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
                'test.docx'
            )
            
            self.log_test_result(
                "Docling parser file type support",
                can_parse_pdf and can_parse_docx,
                f"PDF: {can_parse_pdf}, DOCX: {can_parse_docx}"
            )
            
        except Exception as e:
            self.log_test_result("Docling parser initialization", False, str(e))
    
    async def test_legacy_parser_init(self):
        """Test legacy parser initialization."""
        try:
            config = {}
            parser = LegacyParser(config)
            
            supported_types = parser.get_supported_types()
            self.log_test_result(
                "Legacy parser initialization",
                True,
                f"Supports {len(supported_types)} file types"
            )
            
        except Exception as e:
            self.log_test_result("Legacy parser initialization", False, str(e))
    
    async def test_parser_factory(self):
        """Test parser factory functionality."""
        try:
            config = {
                'prefer_docling': True,
                'enable_fallback': True,
                'docling': {
                    'enable_ocr': True,
                    'enable_table_extraction': True
                }
            }
            
            factory = ParserFactory(config)
            
            # Test parser availability
            available_parsers = factory.get_available_parsers()
            self.log_test_result(
                "Parser factory initialization",
                len(available_parsers) > 0,
                f"Available parsers: {available_parsers}"
            )
            
            # Test parser selection
            pdf_parser = factory.get_parser('application/pdf', 'test.pdf')
            txt_parser = factory.get_parser('text/plain', 'test.txt')
            
            self.log_test_result(
                "Parser factory selection",
                pdf_parser is not None and txt_parser is not None,
                f"PDF parser: {pdf_parser.__class__.__name__ if pdf_parser else 'None'}, "
                f"TXT parser: {txt_parser.__class__.__name__ if txt_parser else 'None'}"
            )
            
            # Test supported types
            supported_types = factory.get_supported_types()
            self.log_test_result(
                "Parser factory supported types",
                len(supported_types) > 0,
                f"Supports {len(supported_types)} types"
            )
            
            # Test metrics
            metrics = factory.get_parser_metrics()
            self.log_test_result(
                "Parser factory metrics",
                isinstance(metrics, dict),
                f"Metrics available for {len(metrics)} parsers"
            )
            
        except Exception as e:
            self.log_test_result("Parser factory", False, str(e))
    
    async def test_enhanced_document_processor(self):
        """Test enhanced document processor."""
        try:
            config = {
                'docling': {
                    'enable_ocr': True,
                    'enable_table_extraction': True,
                    'processing_mode': 'fast'
                },
                'extract_key_topics': True,
                'max_content_length': 10000
            }
            
            processor = EnhancedDocumentProcessor(config)
            
            # Test basic functionality
            supported_types = processor.get_supported_types()
            self.log_test_result(
                "Enhanced document processor initialization",
                len(supported_types) > 0,
                f"Supports {len(supported_types)} file types"
            )
            
            # Test stats
            stats = processor.get_processing_stats()
            self.log_test_result(
                "Enhanced document processor stats",
                isinstance(stats, dict),
                f"Stats: {list(stats.keys())}"
            )
            
        except Exception as e:
            self.log_test_result("Enhanced document processor", False, str(e))
    
    async def test_docling_service(self):
        """Test Docling service."""
        try:
            service = get_docling_service()
            
            # Test service availability
            self.log_test_result(
                "Docling service initialization",
                service is not None,
                f"Service enabled: {service.enabled}"
            )
            
            # Test health check
            health = await service.health_check()
            self.log_test_result(
                "Docling service health check",
                health['status'] in ['healthy', 'disabled'],
                f"Status: {health['status']}"
            )
            
            # Test stats
            stats = service.get_service_stats()
            self.log_test_result(
                "Docling service stats",
                isinstance(stats, dict),
                f"Uptime: {stats.get('uptime_seconds', 0):.2f}s"
            )
            
        except Exception as e:
            self.log_test_result("Docling service", False, str(e))
    
    async def test_document_processing_with_sample(self):
        """Test document processing with sample text."""
        try:
            # Create a simple text document
            sample_content = """
            # Sample Document
            
            This is a sample document for testing the Docling integration.
            
            ## Features
            
            - Document parsing
            - Text extraction
            - Structure analysis
            
            ## Table Example
            
            | Feature | Status |
            |---------|--------|
            | Parsing | ✅ |
            | OCR     | ✅ |
            | Tables  | ✅ |
            
            ## Conclusion
            
            This document demonstrates the capabilities of the enhanced document processor.
            """
            
            # Test with enhanced processor
            config = {
                'docling': {
                    'enable_ocr': False,  # Not needed for text
                    'enable_table_extraction': True,
                    'processing_mode': 'fast'
                },
                'extract_key_topics': True
            }
            
            processor = EnhancedDocumentProcessor(config)
            
            # Process the sample document
            result = await processor.process_file(
                filename='sample.md',
                content=sample_content.encode('utf-8'),
                file_type='text/markdown',
                options={'extract_topics': True, 'generate_summary': True}
            )
            
            # Validate result
            has_content = len(result['content']) > 0
            has_metadata = 'metadata' in result
            has_structure = 'structure' in result
            
            self.log_test_result(
                "Document processing with sample",
                has_content and has_metadata and has_structure,
                f"Content length: {len(result['content'])}, "
                f"Parser: {result['metadata'].get('parser_type', 'unknown')}"
            )
            
        except Exception as e:
            self.log_test_result("Document processing with sample", False, str(e))
    
    async def test_configuration_validation(self):
        """Test configuration validation."""
        try:
            # Test settings availability
            config_items = [
                'docling_enabled',
                'docling_ocr_enabled',
                'docling_table_extraction',
                'docling_processing_mode',
                'docling_timeout',
                'docling_max_file_size'
            ]
            
            available_settings = []
            for item in config_items:
                if hasattr(settings, item):
                    available_settings.append(item)
            
            self.log_test_result(
                "Configuration validation",
                len(available_settings) == len(config_items),
                f"Available settings: {len(available_settings)}/{len(config_items)}"
            )
            
            # Test configuration values
            docling_enabled = settings.docling_enabled
            max_file_size = settings.docling_max_file_size
            
            self.log_test_result(
                "Configuration values",
                isinstance(docling_enabled, bool) and isinstance(max_file_size, int),
                f"Docling enabled: {docling_enabled}, Max file size: {max_file_size}"
            )
            
        except Exception as e:
            self.log_test_result("Configuration validation", False, str(e))
    
    async def run_all_tests(self):
        """Run all tests."""
        logger.info("🚀 Starting Docling Integration Test Suite")
        logger.info("=" * 50)
        
        # Run all tests
        await self.test_docling_availability()
        await self.test_docling_parser_init()
        await self.test_legacy_parser_init()
        await self.test_parser_factory()
        await self.test_enhanced_document_processor()
        await self.test_docling_service()
        await self.test_document_processing_with_sample()
        await self.test_configuration_validation()
        
        # Print summary
        logger.info("=" * 50)
        logger.info("📊 Test Results Summary")
        logger.info(f"✅ Passed: {self.test_results['passed']}")
        logger.info(f"❌ Failed: {self.test_results['failed']}")
        logger.info(f"⏭️  Skipped: {self.test_results['skipped']}")
        
        if self.test_results['errors']:
            logger.error("❌ Errors:")
            for error in self.test_results['errors']:
                logger.error(f"  - {error}")
        
        total_tests = self.test_results['passed'] + self.test_results['failed']
        success_rate = (self.test_results['passed'] / total_tests * 100) if total_tests > 0 else 0
        
        logger.info(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.test_results['failed'] == 0:
            logger.info("🎉 All tests passed!")
        else:
            logger.warning(f"⚠️  {self.test_results['failed']} test(s) failed")
        
        return self.test_results


async def main():
    """Main test runner."""
    test_suite = DoclingIntegrationTest()
    results = await test_suite.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if results['failed'] == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
