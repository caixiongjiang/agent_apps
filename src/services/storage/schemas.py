#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : schemas.py
@Author  : caixiongjiang
@Date    : 2026/1/21
@Function: 
    文件存储服务数据模型（Pydantic）
@Modify History:
    2026/1/21 - 初始版本
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.services.storage.constants import FileCategory, FileStatus


# ========== 请求模型 ==========

class UploadFileRequest(BaseModel):
    """文件上传请求模型"""
    category: str = Field(default=FileCategory.TEMP.value, description="文件分类: temp/session/permanent")
    session_id: Optional[str] = Field(None, description="会话ID（用于关联同一会话的文件）")
    user_id: Optional[str] = Field(None, description="用户ID（统一字段名）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")
    auto_parse: bool = Field(default=False, description="是否自动触发MinerU解析")
    
    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """验证文件分类"""
        valid_categories = [c.value for c in FileCategory]
        if v not in valid_categories:
            raise ValueError(f"无效的文件分类: {v}, 可选值: {valid_categories}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "category": "session",
                "session_id": "sess_123456",
                "user_id": "user_001",
                "metadata": {"source": "web", "purpose": "compliance_check"},
                "auto_parse": True
            }
        }


class BatchUploadRequest(BaseModel):
    """批量上传请求模型"""
    category: str = Field(default=FileCategory.TEMP.value, description="文件分类")
    session_id: Optional[str] = Field(None, description="会话ID")
    user_id: Optional[str] = Field(None, description="用户ID（统一字段名）")
    auto_parse: bool = Field(default=False, description="是否自动解析")


# ========== 响应模型 ==========

class UploadFileResponse(BaseModel):
    """文件上传响应模型"""
    file_id: str = Field(..., description="文件唯一标识符")
    original_filename: str = Field(..., description="原始文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    mime_type: str = Field(..., description="MIME类型")
    category: str = Field(..., description="文件分类")
    storage_path: str = Field(..., description="存储路径（相对路径）")
    upload_time: datetime = Field(..., description="上传时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    preview_url: Optional[str] = Field(None, description="预览链接（暂未实现）")
    processing_status: str = Field(default=FileStatus.UPLOADED.value, description="处理状态")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "file_abc123def456",
                "original_filename": "document.pdf",
                "file_size": 1024000,
                "mime_type": "application/pdf",
                "category": "session",
                "storage_path": "session/ab/cd/ef/abcdef123456.pdf",
                "upload_time": "2026-01-21T10:30:00",
                "expires_at": "2026-01-21T12:30:00",
                "preview_url": None,
                "processing_status": "uploaded"
            }
        }


class BatchUploadResponse(BaseModel):
    """批量上传响应模型"""
    total_count: int = Field(..., description="总文件数")
    success_count: int = Field(..., description="成功上传数")
    failed_count: int = Field(..., description="失败数")
    results: List[UploadFileResponse] = Field(default_factory=list, description="成功上传的文件")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="失败的文件和错误信息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_count": 3,
                "success_count": 2,
                "failed_count": 1,
                "results": [
                    {
                        "file_id": "file_001",
                        "original_filename": "doc1.pdf",
                        "file_size": 1024000,
                        "mime_type": "application/pdf",
                        "category": "session",
                        "storage_path": "session/ab/cd/ef/file_001.pdf",
                        "upload_time": "2026-01-21T10:30:00",
                        "expires_at": "2026-01-21T12:30:00",
                        "preview_url": None,
                        "processing_status": "uploaded"
                    }
                ],
                "errors": [
                    {
                        "filename": "doc3.pdf",
                        "error": "文件类型不支持"
                    }
                ]
            }
        }


class FileInfoResponse(BaseModel):
    """文件信息响应模型"""
    file_id: str = Field(..., description="文件ID")
    original_filename: str = Field(..., description="原始文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    mime_type: str = Field(..., description="MIME类型")
    category: str = Field(..., description="文件分类")
    storage_path: str = Field(..., description="存储路径")
    
    upload_time: datetime = Field(..., description="上传时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    
    user_id: Optional[str] = Field(None, description="用户ID（统一字段名）")
    session_id: Optional[str] = Field(None, description="会话ID")
    agent_type: Optional[str] = Field(None, description="关联的Agent类型")
    processing_status: str = Field(..., description="处理状态")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")
    
    # 扩展字段
    is_expired: bool = Field(default=False, description="是否已过期")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "file_abc123",
                "original_filename": "meeting_notes.pdf",
                "file_size": 2048000,
                "mime_type": "application/pdf",
                "category": "session",
                "storage_path": "session/ab/cd/ef/file_abc123.pdf",
                "upload_time": "2026-01-21T10:30:00",
                "expires_at": "2026-01-21T12:30:00",
                "user_id": "user_001",
                "session_id": "sess_123",
                "agent_type": "document_compliance",
                "processing_status": "completed",
                "metadata": {"parsed": True, "pages": 15},
                "is_expired": False,
                "created_at": "2026-01-21T10:30:00",
                "updated_at": "2026-01-21T10:35:00"
            }
        }


class DeleteFileResponse(BaseModel):
    """文件删除响应模型"""
    file_id: str = Field(..., description="文件ID")
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "file_abc123",
                "success": True,
                "message": "文件删除成功"
            }
        }


class FileListResponse(BaseModel):
    """文件列表响应模型"""
    total: int = Field(..., description="总数量")
    items: List[FileInfoResponse] = Field(..., description="文件列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 10,
                "items": []
            }
        }


class CleanupResponse(BaseModel):
    """清理响应模型"""
    success: bool = Field(..., description="是否成功")
    cleaned_count: int = Field(..., description="清理文件数")
    message: str = Field(..., description="响应消息")
    details: Dict[str, Any] = Field(default_factory=dict, description="详细信息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "cleaned_count": 15,
                "message": "清理完成",
                "details": {
                    "temp_files": 10,
                    "session_files": 5
                }
            }
        }


# ========== 内部使用的数据模型 ==========

class FileInfo(BaseModel):
    """文件信息内部模型（用于 FileManager 返回）"""
    file_id: str
    original_filename: str
    storage_path: str
    file_size: int
    mime_type: str
    category: str
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
