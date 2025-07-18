#!/usr/bin/env python3
"""
Test script for enhanced document processing with Docling integration
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.utils.enhanced_document_processor import EnhancedDocumentProcessor
from backend.utils.parsers.factory import ParserFactory
from backend.config import settings


async def test_docling_integration():
    """Test Docling integration with sample documents"""
    print("🚀 Testing Enhanced Document Processing with Docling")
    print("=" * 60)
    
    # Test configuration
    config = {
        'max_file_size': 10 * 1024 * 1024,  # 10MB
        'max_content_length': 100000,  # 100KB
        'extract_key_topics': True,
        'docling': {
            'enable_ocr': True,
            'enable_table_extraction': True
        }
    }
    
    # Initialize processor
    try:
        processor = EnhancedDocumentProcessor(config)
        print("✅ Enhanced Document Processor initialized successfully")
        
        # Get processing stats
        stats = processor.get_processing_stats()
        print(f"📊 Available parsers: {stats['available_parsers']}")
        print(f"📋 Supported types: {len(stats['supported_types'])} types")
        
    except Exception as e:
        print(f"❌ Failed to initialize processor: {e}")
        return False
    
    # Test parser factory
    try:
        factory = ParserFactory(config)
        print(f"🏭 Parser factory initialized with: {factory.get_available_parsers()}")
        
    except Exception as e:
        print(f"❌ Parser factory error: {e}")
        return False
    
    # Test with sample text
    print("\n📝 Testing with sample text content...")
    
    sample_text = """
    # Sample Document
    
    This is a sample document for testing the enhanced document processing system.
    
    ## Key Features
    
    - Advanced parsing with Docling
    - Table extraction capabilities
    - OCR support for images
    - Structured content analysis
    
    ## Sample Table
    
    | Feature | Status | Notes |
    |---------|--------|-------|
    | Docling | ✅ | Advanced parsing |
    | OCR | ✅ | Image text extraction |
    | Tables | ✅ | Structure detection |
    
    This document demonstrates the enhanced capabilities of our document processing system.
    """
    
    try:
        result = await processor.process_file(
            filename="sample.md",
            content=sample_text.encode('utf-8'),
            file_type="text/markdown",
            options={'extract_topics': True, 'generate_summary': True}
        )
        
        print("✅ Sample document processed successfully")
        print(f"📄 Document ID: {result['document_id']}")
        print(f"📊 Content length: {len(result['content'])} characters")
        print(f"🔍 Parser used: {result['processing_info']['parser_used']}")
        print(f"📋 Structure available: {result['processing_info']['has_structure']}")
        print(f"📊 Tables found: {len(result['tables'])}")
        print(f"🖼️ Images found: {len(result['images'])}")
        
        if result.get('key_topics'):
            print(f"🏷️ Key topics: {result['key_topics'][:5]}...")
            
        if result.get('summary'):
            print(f"📝 Summary: {result['summary'][:100]}...")
            
    except Exception as e:
        print(f"❌ Error processing sample document: {e}")
        return False
    
    print("\n🎉 All tests completed successfully!")
    return True


async def test_specific_parsers():
    """Test specific parsers individually"""
    print("\n🔧 Testing Individual Parsers")
    print("=" * 30)
    
    config = {'docling': {'enable_ocr': True, 'enable_table_extraction': True}}
    
    # Test Docling parser
    try:
        from backend.utils.parsers.docling_parser import DoclingParser
        docling_parser = DoclingParser(config['docling'])
        print(f"✅ Docling parser initialized")
        print(f"📋 Supported types: {len(docling_parser.get_supported_types())}")
        
        # Test can_parse method
        test_cases = [
            ("application/pdf", "test.pdf"),
            ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "test.docx"),
            ("text/html", "test.html"),
            ("application/json", "test.json")  # Should return False
        ]
        
        for file_type, filename in test_cases:
            can_parse = docling_parser.can_parse(file_type, filename)
            status = "✅" if can_parse else "❌"
            print(f"{status} {filename} ({file_type}): {can_parse}")
            
    except Exception as e:
        print(f"❌ Docling parser test failed: {e}")
    
    # Test Legacy parser
    try:
        from backend.utils.parsers.legacy_parser import LegacyParser
        legacy_parser = LegacyParser()
        print(f"✅ Legacy parser initialized")
        print(f"📋 Supported types: {len(legacy_parser.get_supported_types())}")
        
    except Exception as e:
        print(f"❌ Legacy parser test failed: {e}")


if __name__ == "__main__":
    print("🧪 Enhanced Document Processing Test Suite")
    print("=" * 50)
    
    async def main():
        success = await test_docling_integration()
        await test_specific_parsers()
        
        if success:
            print("\n🎯 Integration test completed successfully!")
            print("💡 The enhanced document processing system is ready to use.")
        else:
            print("\n⚠️ Some tests failed. Please check the logs.")
            
    asyncio.run(main())
