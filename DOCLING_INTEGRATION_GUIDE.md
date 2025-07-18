# Docling Integration Guide for AI Lecturer

## Vue d'ensemble

Ce guide couvre l'intégration complète de Docling dans le système AI Lecturer, fournissant des capacités avancées de traitement de documents avec OCR, extraction de tableaux, analyse de structure et bien plus.

## Architecture

### Composants principaux

1. **DoclingParser** (`backend/utils/parsers/docling_parser.py`)
   - Parser avancé utilisant la bibliothèque Docling
   - Support OCR pour documents scannés
   - Extraction de tableaux et images
   - Analyse de structure de document

2. **ParserFactory** (`backend/utils/parsers/factory.py`)
   - Sélection intelligente de parsers
   - Mécanisme de fallback
   - Métriques de performance
   - Gestion des configurations

3. **DoclingService** (`backend/utils/docling_service.py`)
   - Service de haut niveau pour Docling
   - Gestion du cache et des instances
   - Traitement par lots
   - Monitoring des performances

4. **EnhancedDocumentProcessor** (`backend/utils/enhanced_document_processor.py`)
   - Processeur de documents amélioré
   - Intégration avec tous les parsers
   - Extraction de sujets clés
   - Génération de résumés

## Configuration

### Variables d'environnement

```bash
# Activation de Docling
DOCLING_ENABLED=true

# Configuration OCR
DOCLING_OCR_ENABLED=true

# Extraction de tableaux
DOCLING_TABLE_EXTRACTION=true

# Mode de traitement (accurate/fast)
DOCLING_PROCESSING_MODE=accurate

# Timeout en secondes
DOCLING_TIMEOUT=300

# Taille maximale de fichier (bytes)
DOCLING_MAX_FILE_SIZE=52428800  # 50MB
```

### Configuration dans le code

```python
from backend.config import settings

# Configuration Docling
docling_config = {
    'enable_ocr': settings.docling_ocr_enabled,
    'enable_table_extraction': settings.docling_table_extraction,
    'processing_mode': settings.docling_processing_mode,
    'timeout': settings.docling_timeout,
    'max_file_size': settings.docling_max_file_size
}

# Configuration du service
service_config = {
    'cache_size': 10,
    'cache_ttl': 3600,
    'max_concurrent': 3
}
```

## Utilisation

### 1. Traitement de base d'un document

```python
from backend.utils.parsers.docling_parser import DoclingParser

# Initialiser le parser
parser = DoclingParser({
    'enable_ocr': True,
    'enable_table_extraction': True,
    'processing_mode': 'accurate'
})

# Traiter un document
with open('document.pdf', 'rb') as f:
    content = f.read()

parsed_doc = await parser.parse(content, 'document.pdf')

# Accéder aux résultats
print(f"Contenu: {parsed_doc.content}")
print(f"Métadonnées: {parsed_doc.metadata}")
print(f"Structure: {parsed_doc.structure}")
print(f"Tableaux: {len(parsed_doc.tables)}")
print(f"Images: {len(parsed_doc.images)}")
```

### 2. Utilisation avec le processeur amélioré

```python
from backend.utils.enhanced_document_processor import EnhancedDocumentProcessor

# Initialiser le processeur
processor = EnhancedDocumentProcessor({
    'docling': {
        'enable_ocr': True,
        'enable_table_extraction': True,
        'processing_mode': 'fast'
    },
    'extract_key_topics': True,
    'max_content_length': 100000
})

# Traiter un document
result = await processor.process_file(
    filename='document.pdf',
    content=file_content,
    file_type='application/pdf',
    options={
        'extract_topics': True,
        'generate_summary': True
    }
)

# Résultat complet
print(f"Document ID: {result['document_id']}")
print(f"Contenu: {result['content']}")
print(f"Sujets clés: {result['key_topics']}")
print(f"Résumé: {result['summary']}")
```

### 3. Utilisation du service Docling

```python
from backend.utils.docling_service import get_docling_service

# Obtenir le service
service = get_docling_service()

# Vérifier l'état de santé
health = await service.health_check()
print(f"Service status: {health['status']}")

# Traiter un document
result = await service.process_document(
    content=file_content,
    filename='document.pdf',
    options={
        'ocr_enabled': True,
        'table_extraction': True
    }
)

# Traitement par lots
documents = [
    {'content': doc1_content, 'filename': 'doc1.pdf'},
    {'content': doc2_content, 'filename': 'doc2.pdf'}
]

results = await service.batch_process_documents(documents)
```

### 4. Utilisation des API endpoints

```bash
# Vérification de santé
curl -X GET "http://localhost:8000/api/docling/health"

# Statistiques du service
curl -X GET "http://localhost:8000/api/docling/stats"

# Traitement d'un document
curl -X POST "http://localhost:8000/api/docling/process" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"

# Traitement par lots
curl -X POST "http://localhost:8000/api/docling/batch" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf"

# Vider le cache
curl -X DELETE "http://localhost:8000/api/docling/cache"
```

## Formats de documents supportés

### Docling Parser
- **PDF** (application/pdf)
- **DOCX** (application/vnd.openxmlformats-officedocument.wordprocessingml.document)
- **DOC** (application/msword)
- **PPTX** (application/vnd.openxmlformats-officedocument.presentationml.presentation)
- **XLSX** (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
- **HTML** (text/html)
- **Markdown** (text/markdown)

### Legacy Parser (fallback)
- **PDF** (application/pdf)
- **DOCX** (application/vnd.openxmlformats-officedocument.wordprocessingml.document)
- **TXT** (text/plain)
- **Markdown** (text/markdown)

## Structure des résultats

### ParsedDocument

```python
{
    'content': str,        # Contenu textuel extrait
    'metadata': {          # Métadonnées du document
        'filename': str,
        'file_size': int,
        'parser_type': str,
        'page_count': int,
        'word_count': int,
        'character_count': int,
        'title': str,
        'author': str,
        'creation_date': str,
        # ... autres métadonnées
    },
    'structure': {         # Structure du document
        'sections': [],
        'headings': [],
        'pages': [],
        'paragraphs': [],
        'lists': []
    },
    'tables': [           # Tableaux extraits
        {
            'table_id': int,
            'rows': int,
            'columns': int,
            'page': int,
            'content': dict,
            'csv_content': str,
            'caption': str
        }
    ],
    'images': [           # Images détectées
        {
            'image_id': int,
            'page': int,
            'width': int,
            'height': int,
            'format': str,
            'caption': str,
            'alt_text': str
        }
    ]
}
```

### Réponse API améliorée

```json
{
    "status": "success",
    "document": {
        "filename": "document.pdf",
        "content": "Contenu extrait...",
        "metadata": { "..." },
        "structure": { "..." },
        "tables": [],
        "images": [],
        "key_topics": ["sujet1", "sujet2"],
        "summary": "Résumé du document...",
        "processing_info": {
            "parser_type": "docling",
            "processing_time": 2.5,
            "content_length": 5000
        }
    }
}
```

## Gestion des erreurs

### Types d'erreurs

1. **ParseError** - Erreur de parsing
2. **ImportError** - Docling non disponible
3. **ValueError** - Fichier trop volumineux
4. **TimeoutError** - Timeout de traitement
5. **RuntimeError** - Service indisponible

### Mécanisme de fallback

```python
# Le système utilise automatiquement le fallback
try:
    # Tentative avec Docling
    result = await docling_parser.parse(content, filename)
except ParseError:
    # Fallback vers legacy parser
    result = await legacy_parser.parse(content, filename)
```

## Monitoring et métriques

### Métriques du service

```python
# Obtenir les statistiques
stats = service.get_service_stats()

print(f"Documents traités: {stats['documents_processed']}")
print(f"Taux de réussite cache: {stats['cache_hit_rate']:.2%}")
print(f"Temps de traitement moyen: {stats['average_processing_time']:.2f}s")
print(f"Uptime: {stats['uptime_seconds']:.0f}s")
```

### Métriques du parser

```python
# Métriques de performance
metrics = parser.get_performance_metrics()

print(f"Documents: {metrics['documents_processed']}")
print(f"Erreurs: {metrics['errors']}")
print(f"Temps moyen: {metrics['average_processing_time']:.2f}s")
```

## Optimisation des performances

### Configuration pour vitesse

```python
# Configuration rapide
fast_config = {
    'enable_ocr': False,           # Désactiver OCR si pas nécessaire
    'enable_table_extraction': False,  # Désactiver extraction tableaux
    'processing_mode': 'fast',     # Mode rapide
    'timeout': 60,                 # Timeout plus court
    'max_file_size': 10 * 1024 * 1024  # Limite plus stricte
}
```

### Configuration pour précision

```python
# Configuration précise
accurate_config = {
    'enable_ocr': True,
    'enable_table_extraction': True,
    'processing_mode': 'accurate',
    'timeout': 300,
    'max_file_size': 50 * 1024 * 1024
}
```

### Traitement par lots

```python
# Traitement concurrent
documents = [...]  # Liste de documents

# Traiter avec limite de concurrence
results = await service.batch_process_documents(
    documents,
    max_concurrent=3
)
```

## Dépannage

### Problèmes courants

1. **Docling non disponible**
   ```bash
   pip install docling
   ```

2. **Timeout de traitement**
   ```python
   # Augmenter le timeout
   config['timeout'] = 600  # 10 minutes
   ```

3. **Fichier trop volumineux**
   ```python
   # Augmenter la limite
   config['max_file_size'] = 100 * 1024 * 1024  # 100MB
   ```

4. **Erreurs de mémoire**
   ```python
   # Réduire la taille du cache
   service_config['cache_size'] = 5
   ```

### Logging et debugging

```python
import logging

# Activer le logging détaillé
logging.basicConfig(level=logging.DEBUG)

# Logger spécifique
logger = logging.getLogger('backend.utils.parsers.docling_parser')
logger.setLevel(logging.DEBUG)
```

## Tests

### Test complet

```bash
# Exécuter la suite de tests
python test_docling_comprehensive.py
```

### Test spécifique

```python
# Tester un parser spécifique
from backend.utils.parsers.docling_parser import DoclingParser

parser = DoclingParser()
supported_types = parser.get_supported_types()
print(f"Types supportés: {supported_types}")
```

## Mise à jour et maintenance

### Mise à jour de Docling

```bash
# Mettre à jour Docling
pip install --upgrade docling
```

### Nettoyage du cache

```python
# Vider le cache du service
service.clear_cache()
```

### Monitoring continu

```python
# Vérification de santé périodique
health = await service.health_check()
if health['status'] != 'healthy':
    logger.warning(f"Service unhealthy: {health}")
```

## Bonnes pratiques

1. **Toujours vérifier la disponibilité de Docling**
2. **Utiliser le mécanisme de fallback**
3. **Configurer des timeouts appropriés**
4. **Limiter la taille des fichiers**
5. **Monitorer les performances**
6. **Gérer les erreurs de manière gracieuse**
7. **Utiliser le cache pour améliorer les performances**
8. **Traiter les documents par lots quand possible**

## Conclusion

L'intégration Docling dans AI Lecturer fournit des capacités avancées de traitement de documents avec une architecture robuste, des mécanismes de fallback et une gestion complète des erreurs. Le système est conçu pour être performant, fiable et facile à maintenir.

Pour plus d'informations, consultez la documentation technique dans les fichiers sources ou exécutez la suite de tests pour valider l'installation.
