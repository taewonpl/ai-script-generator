"""
RAG Document Processor
Handles the complete document processing pipeline from file upload to ChromaDB indexing
"""

import asyncio
import hashlib
import logging
import mimetypes
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from uuid import uuid4

import aiofiles
import chromadb
from chromadb.config import Settings
import pytesseract
from PIL import Image, ImageEnhance
import fitz  # PyMuPDF
from docx import Document as DocxDocument
import pandas as pd

from generation_service.models.rag_jobs import RAGJobStatus, RAGJobErrorCode


logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """File information for processing"""
    name: str
    size: int
    content_type: str
    sha256: str
    path: str


@dataclass
class ProcessingResult:
    """Result of document processing"""
    success: bool
    document_id: Optional[str] = None
    chunks_indexed: int = 0
    processing_time_seconds: float = 0.0
    extraction_method: Optional[str] = None
    ocr_confidence: Optional[float] = None
    error_status: Optional[RAGJobStatus] = None
    error_code: Optional[RAGJobErrorCode] = None
    error_message: Optional[str] = None


class FileHash:
    """Utility class for file hashing"""
    
    @staticmethod
    def compute_sha256(file_path: str) -> str:
        """Compute SHA-256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    @staticmethod
    async def compute_sha256_async(file_path: str) -> str:
        """Compute SHA-256 hash of a file asynchronously"""
        sha256_hash = hashlib.sha256()
        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(4096):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()


class TextExtractor:
    """Handles text extraction from various file formats"""
    
    @staticmethod
    async def extract_from_pdf(file_path: str, force_ocr: bool = False) -> tuple[str, str, Optional[float]]:
        """
        Extract text from PDF with fallback to OCR
        Returns: (text, method, ocr_confidence)
        """
        try:
            doc = fitz.open(file_path)
            text_content = []
            ocr_confidence = None
            method = "text"
            
            # Try text extraction first unless OCR is forced
            if not force_ocr:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text()
                    if text.strip():
                        text_content.append(text)
                
                if text_content and len("".join(text_content).strip()) > 50:
                    doc.close()
                    return "\n\n".join(text_content), method, ocr_confidence
            
            # Fall back to OCR
            logger.info(f"Falling back to OCR for {file_path} (force_ocr={force_ocr})")
            text_content = []
            confidence_scores = []
            method = "ocr" if force_ocr else "hybrid"
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                
                # Save temp image for OCR
                temp_img_path = f"/tmp/page_{page_num}_{uuid4().hex[:8]}.png"
                with open(temp_img_path, "wb") as img_file:
                    img_file.write(img_data)
                
                try:
                    # Enhance image for better OCR
                    img = Image.open(temp_img_path)
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(2.0)
                    img.save(temp_img_path)
                    
                    # Perform OCR with confidence data
                    ocr_data = pytesseract.image_to_data(
                        img, output_type=pytesseract.Output.DICT, lang='eng+kor'
                    )
                    
                    # Extract text and calculate confidence
                    page_text = pytesseract.image_to_string(img, lang='eng+kor')
                    if page_text.strip():
                        text_content.append(page_text)
                        
                        # Calculate average confidence for this page
                        confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
                        if confidences:
                            confidence_scores.append(sum(confidences) / len(confidences))
                    
                finally:
                    # Clean up temp image
                    if os.path.exists(temp_img_path):
                        os.remove(temp_img_path)
            
            doc.close()
            
            if confidence_scores:
                ocr_confidence = sum(confidence_scores) / len(confidence_scores) / 100.0
            
            final_text = "\n\n".join(text_content)
            if len(final_text.strip()) < 10:
                raise Exception("Extracted text too short, likely OCR failure")
                
            return final_text, method, ocr_confidence
            
        except Exception as e:
            logger.error(f"PDF extraction failed for {file_path}: {e}")
            raise
    
    @staticmethod
    async def extract_from_docx(file_path: str) -> tuple[str, str, Optional[float]]:
        """Extract text from DOCX file"""
        try:
            doc = DocxDocument(file_path)
            paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
            return "\n\n".join(paragraphs), "text", None
        except Exception as e:
            logger.error(f"DOCX extraction failed for {file_path}: {e}")
            raise
    
    @staticmethod
    async def extract_from_txt(file_path: str) -> tuple[str, str, Optional[float]]:
        """Extract text from plain text file"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            return content, "text", None
        except UnicodeDecodeError:
            # Try different encodings
            for encoding in ['cp949', 'euc-kr', 'latin-1']:
                try:
                    async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
                        content = await f.read()
                    return content, "text", None
                except UnicodeDecodeError:
                    continue
            raise Exception("Unable to decode text file with any supported encoding")
        except Exception as e:
            logger.error(f"TXT extraction failed for {file_path}: {e}")
            raise


class TextChunker:
    """Handles text chunking for embedding"""
    
    @staticmethod
    def chunk_text(
        text: str, 
        chunk_size: int = 1024, 
        chunk_overlap: int = 128,
        min_chunk_size: int = 50
    ) -> List[str]:
        """
        Split text into overlapping chunks
        """
        if not text or len(text.strip()) < min_chunk_size:
            return []
        
        # Simple sentence-aware chunking
        sentences = text.split('. ')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # If adding this sentence would exceed chunk size, finalize current chunk
            potential_chunk = f"{current_chunk}. {sentence}" if current_chunk else sentence
            
            if len(potential_chunk) > chunk_size and current_chunk:
                # Add current chunk
                if len(current_chunk.strip()) >= min_chunk_size:
                    chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap
                if chunk_overlap > 0 and current_chunk:
                    # Take last part of current chunk as overlap
                    overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else current_chunk
                    current_chunk = f"{overlap_text}. {sentence}"
                else:
                    current_chunk = sentence
            else:
                current_chunk = potential_chunk
        
        # Add final chunk
        if current_chunk.strip() and len(current_chunk.strip()) >= min_chunk_size:
            chunks.append(current_chunk.strip())
        
        return chunks


class RAGProcessor:
    """Main RAG processing service"""
    
    def __init__(self, 
                 upload_dir: str = "/tmp/rag_uploads",
                 chroma_host: str = "localhost",
                 chroma_port: int = 8000):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.HttpClient(
            host=chroma_host,
            port=chroma_port,
            settings=Settings(allow_reset=True, anonymized_telemetry=False)
        )
        
        # Get or create collection
        try:
            self.collection = self.chroma_client.get_collection(name="rag_documents")
        except:
            self.collection = self.chroma_client.create_collection(
                name="rag_documents",
                metadata={"hnsw:space": "cosine"}
            )
    
    async def get_file_info(self, file_id: str) -> Optional[FileInfo]:
        """Get file information by file ID (mock implementation)"""
        # In production, this would query a file storage service
        # For now, assume files are stored in upload directory
        
        file_path = self.upload_dir / file_id
        if not file_path.exists():
            return None
        
        stat = file_path.stat()
        content_type, _ = mimetypes.guess_type(str(file_path))
        
        return FileInfo(
            name=file_path.name,
            size=stat.st_size,
            content_type=content_type or "application/octet-stream",
            sha256=await FileHash.compute_sha256_async(str(file_path)),
            path=str(file_path)
        )
    
    async def process_document(
        self,
        file_id: str,
        job_id: str,
        project_id: str,
        chunk_size: int = 1024,
        chunk_overlap: int = 128,
        force_ocr: bool = False,
        progress_callback: Optional[Callable[[RAGJobStatus, float, str], None]] = None
    ) -> ProcessingResult:
        """Process a document through the complete RAG pipeline"""
        
        start_time = time.time()
        
        try:
            # Get file info
            file_info = await self.get_file_info(file_id)
            if not file_info:
                return ProcessingResult(
                    success=False,
                    error_status=RAGJobStatus.FAILED_EXTRACT,
                    error_code=RAGJobErrorCode.FILE_NOT_FOUND,
                    error_message="File not found"
                )
            
            if progress_callback:
                await progress_callback(RAGJobStatus.EXTRACTING, 25, "Extracting text")
            
            # Extract text based on file type
            try:
                if file_info.content_type == "application/pdf":
                    text, method, ocr_confidence = await TextExtractor.extract_from_pdf(
                        file_info.path, force_ocr
                    )
                elif file_info.content_type in [
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/msword"
                ]:
                    text, method, ocr_confidence = await TextExtractor.extract_from_docx(file_info.path)
                elif file_info.content_type.startswith("text/"):
                    text, method, ocr_confidence = await TextExtractor.extract_from_txt(file_info.path)
                else:
                    return ProcessingResult(
                        success=False,
                        error_status=RAGJobStatus.FAILED_EXTRACT,
                        error_code=RAGJobErrorCode.UNSUPPORTED_FORMAT,
                        error_message=f"Unsupported file type: {file_info.content_type}"
                    )
                    
            except Exception as e:
                logger.error(f"Text extraction failed: {e}")
                return ProcessingResult(
                    success=False,
                    error_status=RAGJobStatus.FAILED_EXTRACT,
                    error_code=RAGJobErrorCode.NO_TEXT_FOUND,
                    error_message=str(e)
                )
            
            if progress_callback:
                await progress_callback(RAGJobStatus.CHUNKING, 60, "Chunking text")
            
            # Chunk text
            chunks = TextChunker.chunk_text(text, chunk_size, chunk_overlap)
            if not chunks:
                return ProcessingResult(
                    success=False,
                    error_status=RAGJobStatus.FAILED_EMBED,
                    error_code=RAGJobErrorCode.CHUNKING_FAILED,
                    error_message="No valid chunks created from text"
                )
            
            if progress_callback:
                await progress_callback(RAGJobStatus.EMBEDDING, 80, "Generating embeddings")
            
            # Create document ID and prepare metadata
            document_id = f"doc-{uuid4()}"
            
            # Prepare data for ChromaDB
            chunk_ids = [f"{document_id}-chunk-{i}" for i in range(len(chunks))]
            metadatas = []
            
            for i, chunk in enumerate(chunks):
                metadata = {
                    "document_id": document_id,
                    "project_id": project_id,
                    "file_name": file_info.name,
                    "file_type": file_info.content_type,
                    "file_sha256": file_info.sha256,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "extraction_method": method,
                    "job_id": job_id,
                }
                
                if ocr_confidence is not None:
                    metadata["ocr_confidence"] = ocr_confidence
                    
                metadatas.append(metadata)
            
            # Add to ChromaDB with automatic embedding
            try:
                self.collection.add(
                    documents=chunks,
                    metadatas=metadatas,
                    ids=chunk_ids
                )
                
                if progress_callback:
                    await progress_callback(RAGJobStatus.INDEXED, 100, "Indexing complete")
                
                processing_time = time.time() - start_time
                
                return ProcessingResult(
                    success=True,
                    document_id=document_id,
                    chunks_indexed=len(chunks),
                    processing_time_seconds=processing_time,
                    extraction_method=method,
                    ocr_confidence=ocr_confidence
                )
                
            except Exception as e:
                logger.error(f"ChromaDB indexing failed: {e}")
                return ProcessingResult(
                    success=False,
                    error_status=RAGJobStatus.FAILED_STORE,
                    error_code=RAGJobErrorCode.CHROMADB_CONNECTION_FAILED,
                    error_message=str(e)
                )
                
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            return ProcessingResult(
                success=False,
                error_status=RAGJobStatus.FAILED_EXTRACT,
                error_code=RAGJobErrorCode.UNKNOWN_ERROR,
                error_message=str(e)
            )
    
    async def delete_document_chunks(self, document_id: str):
        """Delete all chunks for a document from ChromaDB"""
        try:
            # Get all chunk IDs for this document
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            if results and results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
            else:
                logger.warning(f"No chunks found for document {document_id}")
                
        except Exception as e:
            logger.error(f"Failed to delete chunks for document {document_id}: {e}")
            raise
    
    async def search_documents(
        self, 
        query: str, 
        project_id: str,
        n_results: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search documents by similarity"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"project_id": project_id}
            )
            
            # Filter by similarity threshold
            filtered_results = []
            if results['distances'] and results['distances'][0]:
                for i, distance in enumerate(results['distances'][0]):
                    # Convert distance to similarity (assuming cosine distance)
                    similarity = 1.0 - distance
                    if similarity >= similarity_threshold:
                        filtered_results.append({
                            'id': results['ids'][0][i],
                            'document': results['documents'][0][i],
                            'metadata': results['metadatas'][0][i],
                            'similarity': similarity
                        })
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Document search failed: {e}")
            raise