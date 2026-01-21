#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : file_manager.py
@Author  : caixiongjiang
@Date    : 2026/1/21
@Function: 
    文件管理器 - 底层文件操作（类似 MinerU 的 client.py）
@Modify History:
    2026/1/21 - 初始版本
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

import uuid
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from loguru import logger

from src.services.storage.constants import (
    FileCategory,
    ALLOWED_MIME_TYPES,
    ALLOWED_EXTENSIONS,
    MIME_TO_EXTENSION,
    TEMP_FILE_EXPIRE_HOURS,
    SESSION_FILE_EXPIRE_HOURS,
    ERROR_MESSAGES
)
from src.services.storage.schemas import FileInfo


class FileManager:
    """
    文件管理器 - 负责底层文件操作
    
    功能：
    - 文件存储（本地文件系统）
    - 文件读取和删除
    - 哈希目录结构管理
    - 文件类型验证
    - 过期时间计算
    """
    
    def __init__(
        self,
        storage_root: Path,
        use_hash_structure: bool = True,
        enable_compression: bool = False
    ):
        """
        初始化文件管理器
        
        Args:
            storage_root: 存储根目录
            use_hash_structure: 是否使用哈希目录结构（避免单目录文件过多）
            enable_compression: 是否启用压缩（暂未实现）
        """
        self.storage_root = Path(storage_root)
        self.use_hash_structure = use_hash_structure
        self.enable_compression = enable_compression
        self.logger = logger
        
        # 确保存储根目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保所有必要的目录存在"""
        for category in FileCategory:
            category_dir = self.storage_root / category.value
            category_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"确保目录存在: {category_dir}")
    
    def save_file(
        self,
        file_bytes: bytes,
        file_name: str,
        category: str = FileCategory.TEMP.value
    ) -> FileInfo:
        """
        保存文件到本地
        
        Args:
            file_bytes: 文件字节内容
            file_name: 原始文件名
            category: 文件分类
        
        Returns:
            FileInfo: 文件信息对象
        
        Raises:
            ValueError: 文件类型不支持或文件名无效
            IOError: 文件保存失败
        """
        try:
            # 1. 验证文件名
            if not file_name or file_name.strip() == "":
                raise ValueError("文件名不能为空")
            
            # 2. 检测 MIME 类型
            mime_type = self._detect_mime_type(file_bytes, file_name)
            
            # 3. 验证文件类型
            if not self._validate_file_type(mime_type, file_name):
                raise ValueError(
                    ERROR_MESSAGES["invalid_file_type"].format(mime_type=mime_type)
                )
            
            # 4. 生成唯一文件ID
            file_id = self._generate_file_id()
            
            # 5. 计算存储路径
            storage_path = self._get_storage_path(file_id, file_name, category)
            
            # 6. 确保目标目录存在
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 7. 保存文件
            with open(storage_path, "wb") as f:
                f.write(file_bytes)
            
            # 8. 计算过期时间
            expires_at = self._calculate_expires_at(category)
            
            # 9. 计算相对路径（用于数据库存储）
            relative_path = storage_path.relative_to(self.storage_root)
            
            self.logger.info(
                f"✅ 文件保存成功: {file_name} -> {file_id} "
                f"({len(file_bytes) / 1024:.2f}KB)"
            )
            
            return FileInfo(
                file_id=file_id,
                original_filename=file_name,
                storage_path=str(relative_path),
                file_size=len(file_bytes),
                mime_type=mime_type,
                category=category,
                expires_at=expires_at
            )
            
        except Exception as e:
            self.logger.error(f"❌ 文件保存失败: {file_name}, 错误: {e}")
            raise IOError(ERROR_MESSAGES["upload_failed"].format(reason=str(e)))
    
    def get_file(self, file_id: str, storage_path: str) -> Tuple[Path, str]:
        """
        获取文件
        
        Args:
            file_id: 文件ID
            storage_path: 存储路径（相对路径）
        
        Returns:
            Tuple[Path, str]: (文件绝对路径, MIME类型)
        
        Raises:
            FileNotFoundError: 文件不存在
        """
        # 构建绝对路径
        file_path = self.storage_root / storage_path
        
        if not file_path.exists():
            raise FileNotFoundError(
                ERROR_MESSAGES["file_not_found"].format(file_id=file_id)
            )
        
        # 检测 MIME 类型
        mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        
        return file_path, mime_type
    
    def delete_file(self, file_id: str, storage_path: str) -> bool:
        """
        删除文件
        
        Args:
            file_id: 文件ID
            storage_path: 存储路径（相对路径）
        
        Returns:
            bool: 是否成功
        """
        try:
            # 构建绝对路径
            file_path = self.storage_root / storage_path
            
            if not file_path.exists():
                self.logger.warning(f"⚠️ 文件不存在，跳过删除: {file_id}")
                return False
            
            # 删除文件
            file_path.unlink()
            self.logger.info(f"✅ 文件删除成功: {file_id}")
            
            # 如果使用哈希结构，尝试删除空目录
            if self.use_hash_structure:
                self._cleanup_empty_directories(file_path.parent)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 文件删除失败: {file_id}, 错误: {e}")
            raise IOError(ERROR_MESSAGES["delete_failed"].format(reason=str(e)))
    
    def get_file_info(self, file_id: str, storage_path: str) -> Dict[str, Any]:
        """
        获取文件元数据
        
        Args:
            file_id: 文件ID
            storage_path: 存储路径
        
        Returns:
            Dict[str, Any]: 文件元数据
        
        Raises:
            FileNotFoundError: 文件不存在
        """
        file_path = self.storage_root / storage_path
        
        if not file_path.exists():
            raise FileNotFoundError(
                ERROR_MESSAGES["file_not_found"].format(file_id=file_id)
            )
        
        stat = file_path.stat()
        
        return {
            "file_id": file_id,
            "storage_path": storage_path,
            "file_size": stat.st_size,
            "modified_time": datetime.fromtimestamp(stat.st_mtime),
            "exists": True
        }
    
    # ========== 辅助方法 ==========
    
    def _generate_file_id(self) -> str:
        """
        生成唯一文件ID
        
        Returns:
            str: 文件ID（格式: file-xxxxxxxx）
        """
        unique_id = str(uuid.uuid4())
        return f"file-{unique_id}"
    
    def _get_storage_path(
        self,
        file_id: str,
        file_name: str,
        category: str
    ) -> Path:
        """
        计算存储路径
        
        Args:
            file_id: 文件ID
            file_name: 文件名
            category: 文件分类
        
        Returns:
            Path: 完整存储路径
        """
        # 提取文件扩展名
        file_ext = Path(file_name).suffix.lower()
        if not file_ext:
            file_ext = ".bin"
        
        # 基础路径：category/
        base_path = self.storage_root / category
        
        if self.use_hash_structure:
            # 使用哈希目录结构：category/ab/cd/ef/file_id.ext
            # 取 file_id 的前6个字符作为目录层级（去掉"file-"前缀）
            hash_part = file_id.replace("file-", "")[:6]
            return (
                base_path /
                hash_part[:2] /
                hash_part[2:4] /
                hash_part[4:6] /
                f"{file_id}{file_ext}"
            )
        else:
            # 扁平结构：category/file_id.ext
            return base_path / f"{file_id}{file_ext}"
    
    def _calculate_expires_at(self, category: str) -> Optional[datetime]:
        """
        计算过期时间
        
        Args:
            category: 文件分类
        
        Returns:
            Optional[datetime]: 过期时间（None表示永不过期）
        """
        now = datetime.now()
        
        if category == FileCategory.TEMP.value:
            return now + timedelta(hours=TEMP_FILE_EXPIRE_HOURS)
        elif category == FileCategory.SESSION.value:
            return now + timedelta(hours=SESSION_FILE_EXPIRE_HOURS)
        elif category == FileCategory.PERMANENT.value:
            return None
        else:
            # 默认按临时文件处理
            return now + timedelta(hours=TEMP_FILE_EXPIRE_HOURS)
    
    def _detect_mime_type(self, file_bytes: bytes, file_name: str) -> str:
        """
        检测文件的 MIME 类型
        
        Args:
            file_bytes: 文件字节内容
            file_name: 文件名
        
        Returns:
            str: MIME 类型
        """
        # 优先根据文件扩展名判断
        mime_type, _ = mimetypes.guess_type(file_name)
        
        if mime_type:
            return mime_type
        
        # 如果无法判断，尝试根据文件头判断
        if file_bytes.startswith(b"%PDF"):
            return "application/pdf"
        elif file_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif file_bytes.startswith(b"\x89PNG"):
            return "image/png"
        elif file_bytes.startswith(b"GIF8"):
            return "image/gif"
        elif file_bytes.startswith(b"PK\x03\x04"):
            # Office 文档（docx, xlsx, pptx）都是 ZIP 格式
            if file_name.endswith(".docx"):
                return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif file_name.endswith(".xlsx"):
                return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            elif file_name.endswith(".pptx"):
                return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        
        # 默认返回通用二进制类型
        return "application/octet-stream"
    
    def _validate_file_type(self, mime_type: str, file_name: str) -> bool:
        """
        验证文件类型是否支持
        
        Args:
            mime_type: MIME 类型
            file_name: 文件名
        
        Returns:
            bool: 是否支持
        """
        # 检查 MIME 类型白名单
        if mime_type in ALLOWED_MIME_TYPES:
            return True
        
        # 检查文件扩展名白名单
        file_ext = Path(file_name).suffix.lower()
        if file_ext in ALLOWED_EXTENSIONS:
            return True
        
        return False
    
    def _cleanup_empty_directories(self, directory: Path):
        """
        清理空目录（递归向上）
        
        Args:
            directory: 目录路径
        """
        try:
            # 只清理哈希结构目录，不删除根目录和分类目录
            if directory == self.storage_root:
                return
            
            if directory.parent == self.storage_root:
                return
            
            # 如果目录为空，删除它
            if directory.exists() and not any(directory.iterdir()):
                directory.rmdir()
                self.logger.debug(f"清理空目录: {directory}")
                
                # 递归清理父目录
                self._cleanup_empty_directories(directory.parent)
                
        except Exception as e:
            self.logger.warning(f"清理空目录失败: {directory}, 错误: {e}")
    
    def calculate_storage_usage(self) -> Dict[str, Any]:
        """
        计算存储使用情况
        
        Returns:
            Dict[str, Any]: 存储使用统计
        """
        usage = {
            "total_files": 0,
            "total_size": 0,
            "by_category": {}
        }
        
        for category in FileCategory:
            category_dir = self.storage_root / category.value
            
            if not category_dir.exists():
                usage["by_category"][category.value] = {
                    "files": 0,
                    "size": 0
                }
                continue
            
            category_files = 0
            category_size = 0
            
            for file_path in category_dir.rglob("*"):
                if file_path.is_file():
                    category_files += 1
                    category_size += file_path.stat().st_size
            
            usage["by_category"][category.value] = {
                "files": category_files,
                "size": category_size
            }
            
            usage["total_files"] += category_files
            usage["total_size"] += category_size
        
        return usage
