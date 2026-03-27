#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : storage.py
@Author  : caixiongjiang
@Date    : 2026/1/21
@Function: 
    文件存储服务路由
@Modify History:
    2026/1/21 - 初始版本
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Query
from fastapi.responses import FileResponse
from typing import List, Optional
from pathlib import Path

from src.services.storage import (
    FileStorageService,
    UploadFileResponse,
    BatchUploadResponse,
    FileInfoResponse,
    DeleteFileResponse,
    CleanupResponse,
    FileManager
)

# 创建路由（不包含前缀，由上层统一管理）
router = APIRouter(tags=["Storage - 文件存储"])


# ========== 依赖注入 ==========

def get_storage_service() -> FileStorageService:
    """
    获取文件存储服务实例（依赖注入）
    
    使用 ConfigManager 加载配置，创建 FileManager 和数据库连接池
    """
    from src.utils.config_manager import get_config_manager
    from db.mysql.connection import get_mysql_manager
    
    # 获取配置管理器
    config_manager = get_config_manager()
    
    # 获取文件存储配置
    storage_config = config_manager.get_storage_config()
    storage_root = Path(storage_config.get("storage_root", "./upload"))
    use_hash_structure = storage_config.get("use_hash_structure", True)
    enable_compression = storage_config.get("enable_compression", False)
    
    # 创建 FileManager
    file_manager = FileManager(
        storage_root=storage_root,
        use_hash_structure=use_hash_structure,
        enable_compression=enable_compression
    )
    
    # 获取数据库连接管理器（使用连接池）
    db_manager = get_mysql_manager()
    
    # 创建服务实例
    service = FileStorageService(
        file_manager=file_manager,
        db_manager=db_manager,
        enable_db_sync=True
    )
    
    return service


# ========== 路由端点 ==========

@router.post("/upload", response_model=UploadFileResponse, summary="上传文件")
async def upload_file(
    file: UploadFile = File(..., description="上传的文件"),
    category: str = Form("temp", description="文件分类: temp/session/permanent"),
    session_id: Optional[str] = Form(None, description="会话ID"),
    user_id: Optional[str] = Form(None, description="用户ID（统一字段名）"),
    agent_type: Optional[str] = Form(None, description="关联的Agent类型"),
    auto_parse: bool = Form(False, description="是否自动触发MinerU解析"),
    service: FileStorageService = Depends(get_storage_service)
):
    """
    上传文件
    
    - 支持 PDF、图片、Word 等格式
    - 自动分类管理（temp/session/permanent）
    - 可选自动触发 MinerU 解析
    - 返回 file_id 用于后续操作
    
    **文件分类**:
    - `temp`: 临时文件（1小时后自动清理）
    - `session`: 会话文件（2小时后自动清理）
    - `permanent`: 永久文件（手动删除）
    
    **示例**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/common/storage/upload" \\
         -F "file=@document.pdf" \\
         -F "category=session" \\
         -F "session_id=sess_123" \\
         -F "auto_parse=true"
    ```
    
    **返回**:
    ```json
    {
      "file_id": "file_abc123def456",
      "original_filename": "document.pdf",
      "file_size": 1024000,
      "mime_type": "application/pdf",
      "category": "session",
      "storage_path": "session/ab/cd/ef/file_abc123def456.pdf",
      "upload_time": "2026-01-21T10:30:00",
      "expires_at": "2026-01-21T12:30:00",
      "processing_status": "uploaded"
    }
    ```
    """
    try:
        # 读取文件内容
        file_bytes = await file.read()
        
        # 上传文件（service现在是同步的，不需要await）
        result = service.upload_file(
            file_bytes=file_bytes,
            file_name=file.filename,
            category=category,
            session_id=session_id,
            user_id=user_id,
            agent_type=agent_type,
            auto_parse=auto_parse
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IOError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/upload/batch", response_model=BatchUploadResponse, summary="批量上传文件")
async def upload_files_batch(
    files: List[UploadFile] = File(..., description="上传的文件列表"),
    category: str = Form("temp", description="文件分类"),
    session_id: Optional[str] = Form(None, description="会话ID"),
    user_id: Optional[str] = Form(None, description="用户ID（统一字段名）"),
    agent_type: Optional[str] = Form(None, description="Agent类型"),
    auto_parse: bool = Form(False, description="是否自动解析"),
    service: FileStorageService = Depends(get_storage_service)
):
    """
    批量上传文件
    
    - 支持一次上传多个文件（最多10个）
    - 并行处理所有文件
    - 返回每个文件的上传结果
    
    **示例**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/common/storage/upload/batch" \\
         -F "files=@doc1.pdf" \\
         -F "files=@doc2.pdf" \\
         -F "files=@doc3.pdf" \\
         -F "category=session"
    ```
    """
    try:
        # 读取所有文件
        file_list = []
        for file in files:
            file_bytes = await file.read()
            file_list.append((file_bytes, file.filename))
        
        # 批量上传（service现在是同步的，不需要await）
        result = service.batch_upload_files(
            files=file_list,
            category=category,
            session_id=session_id,
            user_id=user_id,
            agent_type=agent_type,
            auto_parse=auto_parse
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量上传失败: {str(e)}")


@router.get("/files/{file_id}", summary="下载文件")
async def download_file(
    file_id: str,
    service: FileStorageService = Depends(get_storage_service)
):
    """
    下载文件
    
    - 返回文件流（自动设置正确的 Content-Type）
    - 检查文件是否过期
    - 支持浏览器预览（PDF、图片等）
    
    **示例**:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/common/storage/files/file_abc123" \\
         -o downloaded_file.pdf
    ```
    """
    try:
        # 获取文件流（service现在是同步的，不需要await）
        file_path, mime_type, original_filename = service.get_file_stream(file_id)
        
        # 返回文件响应
        return FileResponse(
            path=str(file_path),
            media_type=mime_type,
            filename=original_filename
        )
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=410, detail=str(e))  # 410 Gone (已过期)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@router.get("/files/{file_id}/info", response_model=FileInfoResponse, summary="获取文件信息")
async def get_file_info(
    file_id: str,
    service: FileStorageService = Depends(get_storage_service)
):
    """
    获取文件元数据
    
    - 返回文件的详细信息
    - 包括上传时间、过期时间、处理状态等
    
    **示例**:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/common/storage/files/file_abc123/info"
    ```
    """
    try:
        # service现在是同步的，不需要await
        result = service.get_file_info(file_id)
        return result
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.delete("/files/{file_id}", response_model=DeleteFileResponse, summary="删除文件")
async def delete_file(
    file_id: str,
    user_id: Optional[str] = Query(None, description="用户ID（用于权限检查）"),
    service: FileStorageService = Depends(get_storage_service)
):
    """
    删除文件
    
    - 删除物理文件和数据库记录
    - 可选权限检查（验证上传者）
    
    **示例**:
    ```bash
    curl -X DELETE "http://localhost:8000/api/v1/common/storage/files/file_abc123"
    ```
    """
    try:
        # service现在是同步的，不需要await
        result = service.delete_file(file_id, user_id=user_id)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.get("/files", response_model=List[FileInfoResponse], summary="查询文件列表")
async def list_files(
    session_id: Optional[str] = Query(None, description="会话ID过滤"),
    category: Optional[str] = Query(None, description="分类过滤"),
    user_id: Optional[str] = Query(None, description="用户ID过滤（统一字段名）"),
    agent_type: Optional[str] = Query(None, description="Agent类型过滤"),
    limit: int = Query(100, le=500, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    service: FileStorageService = Depends(get_storage_service)
):
    """
    查询文件列表
    
    - 支持多种过滤条件
    - 支持分页查询
    - 按上传时间倒序排列
    
    **示例**:
    ```bash
    # 查询某个会话的所有文件
    curl -X GET "http://localhost:8000/api/v1/common/storage/files?session_id=sess_123"
    
    # 查询临时文件
    curl -X GET "http://localhost:8000/api/v1/common/storage/files?category=temp&limit=50"
    ```
    """
    try:
        # service现在是同步的，不需要await
        results = service.list_files(
            session_id=session_id,
            category=category,
            user_id=user_id,
            agent_type=agent_type,
            limit=limit,
            offset=offset
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/cleanup", response_model=CleanupResponse, summary="清理过期文件")
async def cleanup_expired_files(
    service: FileStorageService = Depends(get_storage_service)
):
    """
    清理过期文件（管理员接口）
    
    - 自动删除所有过期的临时文件和会话文件
    - 同时删除物理文件和数据库记录
    - 返回清理统计信息
    
    **注意**: 建议配置定时任务自动执行，而不是手动调用
    
    **示例**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/common/storage/cleanup"
    ```
    """
    try:
        # service现在是同步的，不需要await
        result = service.cleanup_expired_files()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")
