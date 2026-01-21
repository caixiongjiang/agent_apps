#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : file_storage_repository.py
@Author  : caixiongjiang
@Date    : 2026/1/21
@Function: 
    文件存储 Repository - 数据库 CRUD 操作
@Modify History:
    2026/1/21 - 初始版本
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from db.mysql.models.common.file_storage import FileMetadata
from src.services.storage.constants import FileStatus


class FileStorageRepository:
    """文件存储 Repository"""
    
    def __init__(self, session: Session):
        """
        初始化 Repository
        
        Args:
            session: SQLAlchemy 会话对象
        """
        self.session = session
    
    def create(
        self,
        file_id: str,
        original_filename: str,
        storage_path: str,
        file_size: int,
        mime_type: str,
        category: str,
        expires_at: Optional[datetime] = None,
        uploaded_by: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        processing_status: str = FileStatus.UPLOADED.value,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> FileMetadata:
        """
        创建文件元数据记录
        
        Args:
            file_id: 文件ID
            original_filename: 原始文件名
            storage_path: 存储路径
            file_size: 文件大小
            mime_type: MIME类型
            category: 文件分类
            expires_at: 过期时间
            uploaded_by: 上传者ID
            session_id: 会话ID
            agent_type: Agent类型
            processing_status: 处理状态
            extra_metadata: 额外元数据
        
        Returns:
            FileMetadata: 创建的文件元数据对象
        """
        file_metadata = FileMetadata(
            file_id=file_id,
            original_filename=original_filename,
            storage_path=storage_path,
            file_size=file_size,
            mime_type=mime_type,
            category=category,
            upload_time=datetime.now(),
            expires_at=expires_at,
            uploaded_by=uploaded_by,
            session_id=session_id,
            agent_type=agent_type,
            processing_status=processing_status,
            extra_metadata=extra_metadata or {}
        )
        
        self.session.add(file_metadata)
        self.session.commit()
        self.session.refresh(file_metadata)
        
        return file_metadata
    
    def get_by_file_id(self, file_id: str) -> Optional[FileMetadata]:
        """
        根据 file_id 查询文件元数据
        
        Args:
            file_id: 文件ID
        
        Returns:
            Optional[FileMetadata]: 文件元数据对象，不存在则返回 None
        """
        return self.session.query(FileMetadata).filter(
            FileMetadata.file_id == file_id
        ).first()
    
    def update_status(
        self,
        file_id: str,
        status: str,
        metadata_update: Optional[Dict[str, Any]] = None
    ) -> Optional[FileMetadata]:
        """
        更新文件处理状态
        
        Args:
            file_id: 文件ID
            status: 新状态
            metadata_update: 需要更新的元数据
        
        Returns:
            Optional[FileMetadata]: 更新后的文件元数据对象
        """
        file_metadata = self.get_by_file_id(file_id)
        
        if file_metadata:
            file_metadata.update_status(status, metadata_update)
            self.session.commit()
            self.session.refresh(file_metadata)
        
        return file_metadata
    
    def delete(self, file_id: str) -> bool:
        """
        删除文件元数据记录
        
        Args:
            file_id: 文件ID
        
        Returns:
            bool: 是否删除成功
        """
        file_metadata = self.get_by_file_id(file_id)
        
        if file_metadata:
            self.session.delete(file_metadata)
            self.session.commit()
            return True
        
        return False
    
    def list_files(
        self,
        session_id: Optional[str] = None,
        category: Optional[str] = None,
        uploaded_by: Optional[str] = None,
        agent_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FileMetadata]:
        """
        查询文件列表
        
        Args:
            session_id: 会话ID过滤
            category: 分类过滤
            uploaded_by: 上传者过滤
            agent_type: Agent类型过滤
            limit: 每页数量
            offset: 偏移量
        
        Returns:
            List[FileMetadata]: 文件元数据列表
        """
        query = self.session.query(FileMetadata)
        
        # 构建过滤条件
        conditions = []
        if session_id:
            conditions.append(FileMetadata.session_id == session_id)
        if category:
            conditions.append(FileMetadata.category == category)
        if uploaded_by:
            conditions.append(FileMetadata.uploaded_by == uploaded_by)
        if agent_type:
            conditions.append(FileMetadata.agent_type == agent_type)
        
        if conditions:
            query = query.filter(and_(*conditions))
        
        # 排序和分页
        query = query.order_by(FileMetadata.upload_time.desc())
        query = query.limit(limit).offset(offset)
        
        return query.all()
    
    def get_expired_files(self) -> List[FileMetadata]:
        """
        获取所有过期文件
        
        Returns:
            List[FileMetadata]: 过期文件列表
        """
        now = datetime.now()
        return self.session.query(FileMetadata).filter(
            and_(
                FileMetadata.expires_at.isnot(None),
                FileMetadata.expires_at < now
            )
        ).all()
    
    def count_by_category(self) -> Dict[str, int]:
        """
        统计各分类的文件数量
        
        Returns:
            Dict[str, int]: 分类统计结果
        """
        from sqlalchemy import func
        
        results = self.session.query(
            FileMetadata.category,
            func.count(FileMetadata.id).label('count')
        ).group_by(FileMetadata.category).all()
        
        return {category: count for category, count in results}
