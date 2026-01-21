#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : file_storage.py
@Author  : caixiongjiang
@Date    : 2026/1/21
@Function: 
    文件存储服务数据库模型
@Modify History:
    2026/1/21 - 初始版本（从 src/services/storage/models.py 迁移）
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from sqlalchemy import Column, String, Integer, DateTime, JSON, Index
from datetime import datetime
from typing import Dict, Any, Optional

from db.mysql.models.base_model import Base

from src.services.storage.constants import FileStatus, FileCategory


class FileMetadata(Base):
    """
    文件元数据表
    
    存储所有上传文件的元数据信息，用于：
    - 文件查询和管理
    - 过期文件清理
    - 文件处理状态跟踪
    - 与 Agent 业务逻辑关联
    """
    __tablename__ = "file_metadata"
    
    # ========== 主键 ==========
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    
    # ========== 文件标识 ==========
    file_id = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="文件唯一标识符（UUID格式）"
    )
    
    # ========== 文件基本信息 ==========
    original_filename = Column(String(255), nullable=False, comment="原始文件名")
    storage_path = Column(String(500), nullable=False, comment="存储路径（相对路径）")
    file_size = Column(Integer, nullable=False, comment="文件大小（字节）")
    mime_type = Column(String(100), nullable=False, comment="MIME类型")
    category = Column(
        String(20),
        nullable=False,
        default=FileCategory.TEMP.value,
        comment="文件分类: temp/session/permanent"
    )
    
    # ========== 时间信息 ==========
    upload_time = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
        comment="上传时间"
    )
    expires_at = Column(
        DateTime,
        nullable=True,
        comment="过期时间（null表示永不过期）"
    )
    
    # ========== 关联信息 ==========
    uploaded_by = Column(String(50), nullable=True, comment="上传者ID")
    session_id = Column(String(50), nullable=True, index=True, comment="会话ID")
    agent_type = Column(String(50), nullable=True, comment="关联的Agent类型")
    
    # ========== 处理状态 ==========
    processing_status = Column(
        String(20),
        nullable=False,
        default=FileStatus.UPLOADED.value,
        comment="处理状态: uploaded/parsing/completed/failed"
    )
    
    # ========== 额外元数据 ==========
    extra_metadata = Column(
        JSON,
        nullable=True,
        default={},
        comment="额外元数据（JSON格式）"
    )
    
    # ========== 审计字段 ==========
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
        comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间"
    )
    
    # ========== 索引 ==========
    __table_args__ = (
        Index("idx_category_status", "category", "processing_status"),
        Index("idx_expires_at", "expires_at"),
        Index("idx_uploaded_by", "uploaded_by"),
        {"comment": "文件元数据表"}
    )
    
    # ========== 实例方法 ==========
    
    def is_expired(self) -> bool:
        """
        检查文件是否已过期
        
        Returns:
            bool: 是否过期
        """
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            Dict[str, Any]: 字典格式的文件元数据
        """
        return {
            "id": self.id,
            "file_id": self.file_id,
            "original_filename": self.original_filename,
            "storage_path": self.storage_path,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "category": self.category,
            "upload_time": self.upload_time.isoformat() if self.upload_time else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "uploaded_by": self.uploaded_by,
            "session_id": self.session_id,
            "agent_type": self.agent_type,
            "processing_status": self.processing_status,
            "metadata": self.extra_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_expired": self.is_expired()
        }
    
    def update_status(self, status: str, metadata_update: Optional[Dict[str, Any]] = None):
        """
        更新处理状态
        
        Args:
            status: 新状态
            metadata_update: 需要更新的元数据
        """
        self.processing_status = status
        
        if metadata_update:
            if self.extra_metadata is None:
                self.extra_metadata = {}
            self.extra_metadata.update(metadata_update)
        
        self.updated_at = datetime.now()
    
    def __repr__(self):
        return (
            f"<FileMetadata(file_id='{self.file_id}', "
            f"filename='{self.original_filename}', "
            f"category='{self.category}', "
            f"status='{self.processing_status}')>"
        )
