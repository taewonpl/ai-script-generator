"""
Security enhancements for RAG worker system
Includes file validation, Redis security, and resource limits
"""

import os
import magic
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
import logging

import redis
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Security configuration
MAX_FILE_SIZE_MB = int(os.getenv("RAG_MAX_FILE_SIZE_MB", "30"))
MAX_PAGES_PDF = int(os.getenv("RAG_MAX_PAGES_PDF", "500"))
ALLOWED_FILE_TYPES = os.getenv("RAG_ALLOWED_FILE_TYPES", "pdf,txt,md,doc,docx").split(",")
TEMP_FILE_TTL_HOURS = int(os.getenv("RAG_TEMP_FILE_TTL_HOURS", "2"))

# Redis security
REDIS_ENCRYPTION_KEY = os.getenv("RAG_REDIS_ENCRYPTION_KEY")
REDIS_ACL_USERNAME = os.getenv("REDIS_ACL_USERNAME", "rag_worker")
REDIS_CONNECTION_POOL_SIZE = int(os.getenv("REDIS_CONNECTION_POOL_SIZE", "10"))

# Content security
SUSPICIOUS_PATTERNS = [
    b'<script',
    b'javascript:',
    b'vbscript:',
    b'<?php',
    b'<%',
    b'{{',
    b'${',
]

DANGEROUS_EXTENSIONS = {
    '.exe', '.scr', '.bat', '.cmd', '.com', '.pif', '.vbs', '.js', '.jar',
    '.app', '.deb', '.pkg', '.dmg', '.zip', '.rar', '.7z'
}


@dataclass
class FileSecurityReport:
    """Security validation report for uploaded files"""
    is_safe: bool
    risk_score: float  # 0.0 = safe, 1.0 = dangerous
    issues: List[str]
    file_type_verified: bool
    size_compliant: bool
    content_scan_clean: bool
    metadata: Dict[str, any]


@dataclass
class RedisSecurityConfig:
    """Redis security configuration"""
    use_ssl: bool
    ssl_cert_reqs: str
    ssl_ca_certs: Optional[str]
    ssl_certfile: Optional[str] 
    ssl_keyfile: Optional[str]
    password: Optional[str]
    username: Optional[str]
    encrypt_data: bool
    connection_pool_size: int


class FileSecurityValidator:
    """Validates file security and safety"""
    
    def __init__(self):
        # Initialize libmagic for MIME type detection
        try:
            self.magic = magic.Magic(mime=True)
            self.magic_available = True
        except Exception as e:
            logger.warning(f"libmagic not available: {e}")
            self.magic_available = False
    
    def validate_file(self, file_path: str, declared_type: Optional[str] = None) -> FileSecurityReport:
        """Comprehensive file security validation"""
        
        issues = []
        risk_score = 0.0
        metadata = {}
        
        try:
            file_path_obj = Path(file_path)
            
            # Check if file exists
            if not file_path_obj.exists():
                return FileSecurityReport(
                    is_safe=False,
                    risk_score=1.0,
                    issues=["File does not exist"],
                    file_type_verified=False,
                    size_compliant=False,
                    content_scan_clean=False,
                    metadata={}
                )
            
            # 1. Size validation
            file_size = file_path_obj.stat().st_size
            max_size = MAX_FILE_SIZE_MB * 1024 * 1024
            size_compliant = file_size <= max_size
            
            if not size_compliant:
                issues.append(f"File too large: {file_size / (1024*1024):.1f}MB > {MAX_FILE_SIZE_MB}MB")
                risk_score += 0.3
            
            metadata['file_size'] = file_size
            
            # 2. Extension validation
            file_extension = file_path_obj.suffix.lower()
            if file_extension in DANGEROUS_EXTENSIONS:
                issues.append(f"Dangerous file extension: {file_extension}")
                risk_score += 0.8
            
            # 3. MIME type verification
            file_type_verified = False
            if self.magic_available:
                detected_mime = self.magic.from_file(file_path)
                metadata['detected_mime_type'] = detected_mime
                
                if declared_type and declared_type != detected_mime:
                    issues.append(f"MIME type mismatch: declared {declared_type}, detected {detected_mime}")
                    risk_score += 0.4
                
                # Check if detected type is allowed
                allowed_mimes = self._get_allowed_mime_types()
                file_type_verified = detected_mime in allowed_mimes
                
                if not file_type_verified:
                    issues.append(f"Unsupported MIME type: {detected_mime}")
                    risk_score += 0.5
            else:
                # Fallback to extension checking
                allowed_extensions = [f".{ext}" for ext in ALLOWED_FILE_TYPES]
                file_type_verified = file_extension in allowed_extensions
                
                if not file_type_verified:
                    issues.append(f"Unsupported file extension: {file_extension}")
                    risk_score += 0.5
            
            # 4. Content scanning
            content_scan_clean = self._scan_file_content(file_path)
            if not content_scan_clean:
                issues.append("Suspicious content patterns detected")
                risk_score += 0.6
            
            # 5. PDF-specific validations
            if file_extension == '.pdf' or (self.magic_available and 'pdf' in detected_mime):
                pdf_issues, pdf_risk = self._validate_pdf_specific(file_path)
                issues.extend(pdf_issues)
                risk_score += pdf_risk
            
            # 6. File integrity check
            try:
                file_hash = self._calculate_file_hash(file_path)
                metadata['sha256'] = file_hash
            except Exception as e:
                issues.append(f"Failed to calculate file hash: {e}")
                risk_score += 0.2
            
            # Determine overall safety
            is_safe = risk_score < 0.5 and len(issues) == 0
            
            return FileSecurityReport(
                is_safe=is_safe,
                risk_score=min(risk_score, 1.0),
                issues=issues,
                file_type_verified=file_type_verified,
                size_compliant=size_compliant,
                content_scan_clean=content_scan_clean,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"File security validation failed: {e}")
            return FileSecurityReport(
                is_safe=False,
                risk_score=1.0,
                issues=[f"Validation error: {e}"],
                file_type_verified=False,
                size_compliant=False,
                content_scan_clean=False,
                metadata={}
            )
    
    def _get_allowed_mime_types(self) -> Set[str]:
        """Get set of allowed MIME types"""
        mime_map = {
            'pdf': 'application/pdf',
            'txt': 'text/plain',
            'md': 'text/markdown',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }
        
        return {mime_map[ext] for ext in ALLOWED_FILE_TYPES if ext in mime_map}
    
    def _scan_file_content(self, file_path: str, chunk_size: int = 8192) -> bool:
        """Scan file content for suspicious patterns"""
        
        try:
            with open(file_path, 'rb') as f:
                # Read first few chunks to detect suspicious patterns
                for _ in range(10):  # Check first ~80KB
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Check for suspicious patterns
                    for pattern in SUSPICIOUS_PATTERNS:
                        if pattern in chunk.lower():
                            logger.warning(f"Suspicious pattern found in {file_path}: {pattern}")
                            return False
            
            return True
            
        except Exception as e:
            logger.error(f"Content scan failed for {file_path}: {e}")
            return False
    
    def _validate_pdf_specific(self, file_path: str) -> Tuple[List[str], float]:
        """PDF-specific security validations"""
        
        issues = []
        risk_score = 0.0
        
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                # Check page count
                page_count = len(pdf_reader.pages)
                if page_count > MAX_PAGES_PDF:
                    issues.append(f"PDF has too many pages: {page_count} > {MAX_PAGES_PDF}")
                    risk_score += 0.3
                
                # Check for JavaScript in PDF
                if pdf_reader.metadata and '/JS' in str(pdf_reader.metadata):
                    issues.append("PDF contains JavaScript")
                    risk_score += 0.7
                
                # Check for forms/actions that could be dangerous
                for page in pdf_reader.pages[:5]:  # Check first 5 pages
                    if '/AA' in str(page.get('/Annots', '')):  # Additional Actions
                        issues.append("PDF contains potentially dangerous actions")
                        risk_score += 0.5
                        break
                
        except ImportError:
            logger.warning("PyPDF2 not available for PDF validation")
        except Exception as e:
            issues.append(f"PDF validation error: {e}")
            risk_score += 0.2
        
        return issues, risk_score
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()


class RedisSecurityManager:
    """Manages secure Redis connections and data encryption"""
    
    def __init__(self, config: RedisSecurityConfig):
        self.config = config
        self._cipher = None
        
        if config.encrypt_data and REDIS_ENCRYPTION_KEY:
            try:
                self._cipher = Fernet(REDIS_ENCRYPTION_KEY.encode())
            except Exception as e:
                logger.error(f"Failed to initialize encryption: {e}")
    
    def create_secure_connection(self, redis_url: str) -> redis.Redis:
        """Create secure Redis connection with SSL/TLS and ACL"""
        
        connection_kwargs = {
            'decode_responses': False if self.config.encrypt_data else True,
            'socket_keepalive': True,
            'socket_keepalive_options': {},
            'retry_on_timeout': True,
            'health_check_interval': 30,
            'max_connections': self.config.connection_pool_size,
        }
        
        # Add SSL configuration
        if self.config.use_ssl:
            connection_kwargs.update({
                'ssl': True,
                'ssl_cert_reqs': self.config.ssl_cert_reqs,
            })
            
            if self.config.ssl_ca_certs:
                connection_kwargs['ssl_ca_certs'] = self.config.ssl_ca_certs
            if self.config.ssl_certfile:
                connection_kwargs['ssl_certfile'] = self.config.ssl_certfile
            if self.config.ssl_keyfile:
                connection_kwargs['ssl_keyfile'] = self.config.ssl_keyfile
        
        # Add authentication
        if self.config.password:
            connection_kwargs['password'] = self.config.password
        if self.config.username:
            connection_kwargs['username'] = self.config.username
        
        # Create connection pool
        if redis_url:
            connection_kwargs['url'] = redis_url
        
        return redis.Redis(**connection_kwargs)
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt data for storage in Redis"""
        
        if not self._cipher:
            return data
        
        try:
            encrypted = self._cipher.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return data
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data retrieved from Redis"""
        
        if not self._cipher:
            return encrypted_data
        
        try:
            decrypted = self._cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_data
    
    def secure_key(self, key: str) -> str:
        """Generate secure key with namespace prefix"""
        return f"rag:secure:{key}"


class TempFileManager:
    """Manages temporary files with automatic cleanup and security"""
    
    def __init__(self):
        self.temp_files: Set[str] = set()
        self.cleanup_enabled = True
    
    def create_temp_file(self, suffix: str = "", prefix: str = "rag_") -> str:
        """Create a secure temporary file"""
        
        # Use system temp directory with secure permissions
        temp_dir = tempfile.gettempdir()
        
        # Create temp file with restrictive permissions
        fd, temp_path = tempfile.mkstemp(
            suffix=suffix,
            prefix=prefix,
            dir=temp_dir
        )
        
        # Set restrictive permissions (owner read/write only)
        os.chmod(temp_path, 0o600)
        os.close(fd)
        
        self.temp_files.add(temp_path)
        
        logger.debug(f"Created secure temp file: {temp_path}")
        return temp_path
    
    def cleanup_temp_file(self, temp_path: str):
        """Securely delete temporary file"""
        
        if not self.cleanup_enabled:
            return
        
        try:
            if os.path.exists(temp_path):
                # Overwrite file with random data before deletion (simple secure delete)
                file_size = os.path.getsize(temp_path)
                with open(temp_path, 'wb') as f:
                    f.write(os.urandom(file_size))
                
                os.remove(temp_path)
                self.temp_files.discard(temp_path)
                logger.debug(f"Securely deleted temp file: {temp_path}")
        
        except Exception as e:
            logger.error(f"Failed to cleanup temp file {temp_path}: {e}")
    
    def cleanup_all_temp_files(self):
        """Clean up all tracked temporary files"""
        
        for temp_path in list(self.temp_files):
            self.cleanup_temp_file(temp_path)
    
    def __del__(self):
        """Cleanup on object destruction"""
        if self.cleanup_enabled:
            self.cleanup_all_temp_files()


class ResourceLimitEnforcer:
    """Enforces resource limits during processing"""
    
    def __init__(self):
        self.max_memory_mb = int(os.getenv("RAG_MAX_MEMORY_MB", "512"))
        self.max_cpu_time_seconds = int(os.getenv("RAG_MAX_CPU_TIME", "300"))
        self.max_open_files = int(os.getenv("RAG_MAX_OPEN_FILES", "50"))
    
    def check_memory_usage(self) -> Tuple[bool, float]:
        """Check current memory usage"""
        
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            is_within_limit = memory_mb < self.max_memory_mb
            usage_percent = (memory_mb / self.max_memory_mb) * 100
            
            if not is_within_limit:
                logger.warning(f"Memory limit exceeded: {memory_mb:.1f}MB > {self.max_memory_mb}MB")
            
            return is_within_limit, usage_percent
            
        except ImportError:
            logger.warning("psutil not available for memory monitoring")
            return True, 0.0
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return True, 0.0
    
    def check_cpu_time(self, start_time: float) -> bool:
        """Check if CPU time limit is exceeded"""
        
        import time
        elapsed = time.time() - start_time
        
        if elapsed > self.max_cpu_time_seconds:
            logger.warning(f"CPU time limit exceeded: {elapsed:.1f}s > {self.max_cpu_time_seconds}s")
            return False
        
        return True
    
    def check_open_files(self) -> Tuple[bool, int]:
        """Check number of open file descriptors"""
        
        try:
            import psutil
            process = psutil.Process()
            open_files = process.num_fds() if hasattr(process, 'num_fds') else len(process.open_files())
            
            is_within_limit = open_files < self.max_open_files
            
            if not is_within_limit:
                logger.warning(f"Open files limit exceeded: {open_files} > {self.max_open_files}")
            
            return is_within_limit, open_files
            
        except ImportError:
            return True, 0
        except Exception as e:
            logger.error(f"Open files check failed: {e}")
            return True, 0


# Global instances
_file_validator = FileSecurityValidator()
_temp_file_manager = TempFileManager()
_resource_enforcer = ResourceLimitEnforcer()


def validate_file_security(file_path: str, declared_type: Optional[str] = None) -> FileSecurityReport:
    """Validate file security (global function)"""
    return _file_validator.validate_file(file_path, declared_type)


def create_secure_temp_file(suffix: str = "", prefix: str = "rag_") -> str:
    """Create secure temporary file (global function)"""
    return _temp_file_manager.create_temp_file(suffix, prefix)


def cleanup_temp_file(temp_path: str):
    """Cleanup temporary file (global function)"""
    _temp_file_manager.cleanup_temp_file(temp_path)


def check_resource_limits(start_time: float) -> Tuple[bool, Dict[str, any]]:
    """Check all resource limits (global function)"""
    
    memory_ok, memory_usage = _resource_enforcer.check_memory_usage()
    cpu_ok = _resource_enforcer.check_cpu_time(start_time)
    files_ok, open_files = _resource_enforcer.check_open_files()
    
    all_ok = memory_ok and cpu_ok and files_ok
    
    status = {
        'within_limits': all_ok,
        'memory_ok': memory_ok,
        'memory_usage_percent': memory_usage,
        'cpu_ok': cpu_ok,
        'files_ok': files_ok,
        'open_files_count': open_files,
    }
    
    return all_ok, status


def create_redis_security_config() -> RedisSecurityConfig:
    """Create Redis security configuration from environment"""
    
    return RedisSecurityConfig(
        use_ssl=os.getenv("REDIS_SSL", "false").lower() == "true",
        ssl_cert_reqs=os.getenv("REDIS_SSL_CERT_REQS", "required"),
        ssl_ca_certs=os.getenv("REDIS_SSL_CA_CERTS"),
        ssl_certfile=os.getenv("REDIS_SSL_CERTFILE"),
        ssl_keyfile=os.getenv("REDIS_SSL_KEYFILE"),
        password=os.getenv("REDIS_PASSWORD"),
        username=os.getenv("REDIS_ACL_USERNAME"),
        encrypt_data=os.getenv("REDIS_ENCRYPT_DATA", "false").lower() == "true",
        connection_pool_size=REDIS_CONNECTION_POOL_SIZE,
    )