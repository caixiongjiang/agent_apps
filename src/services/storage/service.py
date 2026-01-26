#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : service.py
@Author  : caixiongjiang
@Date    : 2026/1/21
@Function: 
    文件存储服务层 - 业务编排（使用连接池和Repository）
@Modify History:
    2026/1/21 - 重构：使用连接池和Repository架构
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path

from loguru import logger

from db.mysql.connection.base import BaseMySQLManager
from db.mysql.repositories.common.file_storage_repository import FileStorageRepository
from src.services.storage.file_manager import FileManager
from src.services.storage.schemas import (
    UploadFileResponse,
    BatchUploadResponse,
    FileInfoResponse,
    DeleteFileResponse,
    CleanupResponse
)
from src.services.storage.constants import (
    FileStatus,
    FileCategory,
    MAX_FILE_SIZE,
    MAX_BATCH_SIZE,
    ERROR_MESSAGES
)


class FileStorageService:
    """
    文件存储服务层
    
    功能：
    - 文件上传和管理
    - 数据库同步（使用Repository）
    - 批量操作
    - 过期文件清理
    - 与 MinerU 集成
    """
    
    def __init__(
        self,
        file_manager: FileManager,
        db_manager: BaseMySQLManager,
        enable_db_sync: bool = True
    ):
        """
        初始化文件存储服务
        
        Args:
            file_manager: 文件管理器
            db_manager: 数据库连接管理器
            enable_db_sync: 是否启用数据库同步
        """
        self.file_manager = file_manager
        self.db_manager = db_manager
        self.enable_db_sync = enable_db_sync
        self.logger = logger
    
    def upload_file(
        self,
        file_bytes: bytes,
        file_name: str,
        category: str = FileCategory.TEMP.value,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        metadata: Dict[str, Any] = None,
        auto_parse: bool = False
    ) -> UploadFileResponse:
        """
        上传文件
        
        Args:
            file_bytes: 文件字节内容
            file_name: 原始文件名
            category: 文件分类
            session_id: 会话ID
            user_id: 用户ID（统一字段名）
            agent_type: 关联的Agent类型
            metadata: 额外元数据
            auto_parse: 是否自动触发MinerU解析
        
        Returns:
            UploadFileResponse: 上传响应
        
        Raises:
            ValueError: 文件验证失败
            IOError: 文件保存失败
        """
        start_time = datetime.now()
        
        try:
            # 1. 验证文件大小
            self._validate_file_size(file_bytes, file_name)
            
            # 2. 保存文件到本地（使用 FileManager）
            self.logger.info(f"📤 开始上传文件: {file_name} ({len(file_bytes) / 1024:.2f}KB)")
            file_info = self.file_manager.save_file(file_bytes, file_name, category)
            
            # 3. 保存元数据到数据库（使用 Repository）
            if self.enable_db_sync:
                with self.db_manager.get_session() as session:
                    repository = FileStorageRepository(session)
                    repository.create(
                        file_id=file_info.file_id,
                        original_filename=file_info.original_filename,
                        storage_path=file_info.storage_path,
                        file_size=file_info.file_size,
                        mime_type=file_info.mime_type,
                        category=file_info.category,
                        expires_at=file_info.expires_at,
                        user_id=user_id,
                        session_id=session_id,
                        agent_type=agent_type,
                        processing_status=FileStatus.UPLOADED.value,
                        extra_metadata=metadata or {}
                    )
            
            # 4. 如果启用自动解析，触发 MinerU（TODO: 实现与 MinerU 的集成）
            if auto_parse:
                self.logger.info(f"🔄 自动解析已启用: {file_info.file_id}")
                # TODO: 调用 MinerU 服务
                # self._trigger_mineru_parse(file_info.file_id)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"✅ 文件上传成功: {file_name}, 耗时: {duration:.2f}秒")
            
            # 5. 构建响应
            return UploadFileResponse(
                file_id=file_info.file_id,
                original_filename=file_info.original_filename,
                file_size=file_info.file_size,
                mime_type=file_info.mime_type,
                category=file_info.category,
                storage_path=file_info.storage_path,
                upload_time=datetime.now(),
                expires_at=file_info.expires_at,
                preview_url=None,  # TODO: 实现预览功能
                processing_status=FileStatus.UPLOADED.value
            )
            
        except Exception as e:
            self.logger.error(f"❌ 文件上传失败: {file_name}, 错误: {e}")
            raise
    
    def batch_upload_files(
        self,
        files: List[Tuple[bytes, str]],
        category: str = FileCategory.TEMP.value,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        auto_parse: bool = False
    ) -> BatchUploadResponse:
        """
        批量上传文件
        
        Args:
            files: 文件列表 [(file_bytes, file_name), ...]
            category: 文件分类
            session_id: 会话ID
            user_id: 用户ID（统一字段名）
            agent_type: Agent类型
            auto_parse: 是否自动解析
        
        Returns:
            BatchUploadResponse: 批量上传响应
        """
        # 验证批量大小
        if len(files) > MAX_BATCH_SIZE:
            raise ValueError(
                ERROR_MESSAGES["batch_too_large"].format(max_count=MAX_BATCH_SIZE)
            )
        
        self.logger.info(f"📦 开始批量上传 {len(files)} 个文件")
        
        results = []
        errors = []
        
        # 顺序上传
        for file_bytes, file_name in files:
            try:
                result = self.upload_file(
                    file_bytes=file_bytes,
                    file_name=file_name,
                    category=category,
                    session_id=session_id,
                    user_id=user_id,
                    agent_type=agent_type,
                    auto_parse=auto_parse
                )
                results.append(result)
            except Exception as e:
                self.logger.error(f"❌ 文件上传失败: {file_name}, 错误: {e}")
                errors.append({
                    "filename": file_name,
                    "error": str(e)
                })
        
        self.logger.info(
            f"✅ 批量上传完成: 成功 {len(results)}/{len(files)}, 失败 {len(errors)}"
        )
        
        return BatchUploadResponse(
            total_count=len(files),
            success_count=len(results),
            failed_count=len(errors),
            results=results,
            errors=errors
        )
    
    def get_file_info(self, file_id: str) -> FileInfoResponse:
        """
        获取文件信息
        
        Args:
            file_id: 文件ID
        
        Returns:
            FileInfoResponse: 文件信息
        
        Raises:
            FileNotFoundError: 文件不存在
        """
        with self.db_manager.get_session() as session:
            repository = FileStorageRepository(session)
            file_metadata = repository.get_by_file_id(file_id)
            
            if not file_metadata:
                raise FileNotFoundError(
                    ERROR_MESSAGES["file_not_found"].format(file_id=file_id)
                )
            
            return FileInfoResponse(
                file_id=file_metadata.file_id,
                original_filename=file_metadata.original_filename,
                file_size=file_metadata.file_size,
                mime_type=file_metadata.mime_type,
                category=file_metadata.category,
                storage_path=file_metadata.storage_path,
                upload_time=file_metadata.upload_time,
                expires_at=file_metadata.expires_at,
                user_id=file_metadata.user_id,
                session_id=file_metadata.session_id,
                agent_type=file_metadata.agent_type,
                processing_status=file_metadata.processing_status,
                metadata=file_metadata.extra_metadata or {},
                is_expired=file_metadata.is_expired(),
                created_at=file_metadata.created_at,
                updated_at=file_metadata.updated_at
            )
    
    def get_file_stream(self, file_id: str) -> Tuple[Path, str, str]:
        """
        获取文件流（用于下载）
        
        Args:
            file_id: 文件ID
        
        Returns:
            Tuple[Path, str, str]: (文件路径, MIME类型, 原始文件名)
        
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件已过期
        """
        with self.db_manager.get_session() as session:
            repository = FileStorageRepository(session)
            file_metadata = repository.get_by_file_id(file_id)
            
            if not file_metadata:
                raise FileNotFoundError(
                    ERROR_MESSAGES["file_not_found"].format(file_id=file_id)
                )
            
            # 检查是否过期
            if file_metadata.is_expired():
                raise ValueError(
                    ERROR_MESSAGES["file_expired"].format(file_id=file_id)
                )
            
            # 获取文件路径
            file_path, mime_type = self.file_manager.get_file(
                file_id,
                file_metadata.storage_path
            )
            
            return file_path, mime_type, file_metadata.original_filename
    
    def delete_file(
        self,
        file_id: str,
        user_id: Optional[str] = None
    ) -> DeleteFileResponse:
        """
        删除文件
        
        Args:
            file_id: 文件ID
            user_id: 用户ID（用于权限检查，可选）
        
        Returns:
            DeleteFileResponse: 删除响应
        """
        try:
            with self.db_manager.get_session() as session:
                repository = FileStorageRepository(session)
                file_metadata = repository.get_by_file_id(file_id)
                
                if not file_metadata:
                    return DeleteFileResponse(
                        file_id=file_id,
                        success=False,
                        message="文件不存在"
                    )
                
                # 权限检查（可选）
                if user_id and file_metadata.user_id:
                    if user_id != file_metadata.user_id:
                        return DeleteFileResponse(
                            file_id=file_id,
                            success=False,
                            message="无权删除该文件"
                        )
                
                # 删除物理文件
                self.file_manager.delete_file(file_id, file_metadata.storage_path)
                
                # 从数据库删除记录
                repository.delete(file_id)
            
            self.logger.info(f"✅ 文件删除成功: {file_id}")
            
            return DeleteFileResponse(
                file_id=file_id,
                success=True,
                message="文件删除成功"
            )
            
        except Exception as e:
            self.logger.error(f"❌ 文件删除失败: {file_id}, 错误: {e}")
            return DeleteFileResponse(
                file_id=file_id,
                success=False,
                message=f"删除失败: {str(e)}"
            )
    
    def list_files(
        self,
        session_id: Optional[str] = None,
        category: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FileInfoResponse]:
        """
        查询文件列表
        
        Args:
            session_id: 会话ID过滤
            category: 分类过滤
            user_id: 用户ID过滤（统一字段名）
            agent_type: Agent类型过滤
            limit: 每页数量
            offset: 偏移量
        
        Returns:
            List[FileInfoResponse]: 文件列表
        """
        with self.db_manager.get_session() as session:
            repository = FileStorageRepository(session)
            files = repository.list_files(
                session_id=session_id,
                category=category,
                user_id=user_id,
                agent_type=agent_type,
                limit=limit,
                offset=offset
            )
            
            return [
                FileInfoResponse(
                    file_id=f.file_id,
                    original_filename=f.original_filename,
                    file_size=f.file_size,
                    mime_type=f.mime_type,
                    category=f.category,
                    storage_path=f.storage_path,
                    upload_time=f.upload_time,
                    expires_at=f.expires_at,
                    user_id=f.user_id,
                    session_id=f.session_id,
                    agent_type=f.agent_type,
                    processing_status=f.processing_status,
                    metadata=f.extra_metadata or {},
                    is_expired=f.is_expired(),
                    created_at=f.created_at,
                    updated_at=f.updated_at
                )
                for f in files
            ]
    
    def cleanup_expired_files(self) -> CleanupResponse:
        """
        清理过期文件
        
        Returns:
            CleanupResponse: 清理响应
        """
        try:
            self.logger.info("🧹 开始清理过期文件")
            
            with self.db_manager.get_session() as session:
                repository = FileStorageRepository(session)
                expired_files = repository.get_expired_files()
                
                cleaned_count = 0
                details = {
                    "temp_files": 0,
                    "session_files": 0,
                    "errors": []
                }
                
                # 删除过期文件
                for file_metadata in expired_files:
                    try:
                        # 删除物理文件
                        self.file_manager.delete_file(
                            file_metadata.file_id,
                            file_metadata.storage_path
                        )
                        
                        # 删除数据库记录
                        repository.delete(file_metadata.file_id)
                        
                        cleaned_count += 1
                        
                        # 统计分类
                        if file_metadata.category == FileCategory.TEMP.value:
                            details["temp_files"] += 1
                        elif file_metadata.category == FileCategory.SESSION.value:
                            details["session_files"] += 1
                        
                    except Exception as e:
                        self.logger.error(
                            f"删除过期文件失败: {file_metadata.file_id}, 错误: {e}"
                        )
                        details["errors"].append({
                            "file_id": file_metadata.file_id,
                            "error": str(e)
                        })
            
            self.logger.info(f"✅ 清理完成: 共清理 {cleaned_count} 个过期文件")
            
            return CleanupResponse(
                success=True,
                cleaned_count=cleaned_count,
                message=f"成功清理 {cleaned_count} 个过期文件",
                details=details
            )
            
        except Exception as e:
            self.logger.error(f"❌ 清理过期文件失败: {e}")
            
            return CleanupResponse(
                success=False,
                cleaned_count=0,
                message=f"清理失败: {str(e)}",
                details={}
            )
    
    # ========== 私有辅助方法 ==========
    
    def _validate_file_size(self, file_bytes: bytes, file_name: str):
        """验证文件大小"""
        if len(file_bytes) > MAX_FILE_SIZE:
            raise ValueError(
                ERROR_MESSAGES["file_too_large"].format(
                    max_size=MAX_FILE_SIZE / 1024 / 1024
                )
            )
