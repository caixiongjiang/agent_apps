#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : mineru.py
@Author  : caixiongjiang
@Date    : 2026/1/21
@Function: 
    MinerU 文档解析服务路由
@Modify History:
    2026/1/21 - 从 services.py 拆分出来
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from typing import List

from src.services.mineru.schemas import ParseResult, BatchParseResult, PaginationConfig
from src.services.mineru.service import MinerUService, BatchMinerUService

# 创建路由（不包含前缀，由上层统一管理）
router = APIRouter(tags=["MinerU - 文档解析"])


# ========== 依赖注入 ==========

def get_mineru_service() -> MinerUService:
    """
    获取 MinerU 服务实例（依赖注入）
    
    使用 ConfigManager 和 EnvManager 加载配置
    """
    from src.utils.config_manager import get_config_manager
    from src.utils.env_manager import get_env_manager
    from pathlib import Path
    
    # 获取配置管理器和环境变量管理器
    config_manager = get_config_manager()
    env_manager = get_env_manager()
    
    # 获取完整的 MinerU 配置（config.toml + .env）
    mineru_full_config = config_manager.get_mineru_full_config(env_manager)
    
    # 获取分页配置
    mineru_config_section = config_manager.get_mineru_config()
    max_pages_per_request = mineru_config_section.get("max_pages_per_request", 10)
    max_concurrent_requests = mineru_config_section.get("max_concurrent_requests", 3)
    
    # 获取文件上传配置
    file_upload_config = config_manager.get_file_upload_config()
    storage_path = Path(file_upload_config.get("temp_dir", "./uploads"))
    
    return MinerUService(
        mineru_config=mineru_full_config,
        max_pages_per_request=max_pages_per_request,
        max_concurrent_requests=max_concurrent_requests,
        storage_path=storage_path
    )


# ========== 路由端点 ==========

@router.post("/parse", response_model=ParseResult, summary="解析文档")
async def parse_document(
    file: UploadFile = File(..., description="上传的文件"),
    auto_pagination: bool = Query(True, description="是否自动分页处理大文件"),
    mineru_service: MinerUService = Depends(get_mineru_service)
):
    """
    解析文档（同步等待）
    
    - 支持 PDF、图片等格式
    - **自动分页**: 大文件自动分页并行处理（可配置）
    - **同步返回**: 等待解析完成后返回完整结果
    - **智能优化**: 自动检测页数，合理分配并发
    
    **分页策略**:
    - 每次请求最大 10 页（可配置）
    - 最大并发 3 个请求（可配置）
    - 自动合并分页结果
    
    **示例**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/common/mineru/parse" \\
         -F "file=@document.pdf" \\
         -F "auto_pagination=true"
    ```
    
    **返回**:
    ```json
    {
      "file_name": "document.pdf",
      "pages": 15,
      "struct_content": {...},
      "markdown_content": "...",
      "coordinates": {...}
    }
    ```
    """
    try:
        # 读取文件内容
        file_bytes = await file.read()
        
        # 解析文档（异步等待）
        result = await mineru_service.parse_document(
            file_bytes=file_bytes,
            file_name=file.filename,
            auto_pagination=auto_pagination
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


@router.post("/parse/batch", response_model=BatchParseResult, summary="批量解析文档")
async def parse_documents_batch(
    files: List[UploadFile] = File(..., description="上传的文件列表"),
    auto_pagination: bool = Query(True, description="是否自动分页"),
    mineru_service: MinerUService = Depends(get_mineru_service)
):
    """
    批量解析文档
    
    - 支持一次上传多个文件
    - 并行处理所有文件
    - 返回所有文件的解析结果
    
    **示例**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/common/mineru/parse/batch" \\
         -F "files=@doc1.pdf" \\
         -F "files=@doc2.pdf" \\
         -F "files=@doc3.pdf"
    ```
    """
    try:
        # 读取所有文件
        file_list = []
        for file in files:
            file_bytes = await file.read()
            file_list.append((file_bytes, file.filename))
        
        # 批量解析
        batch_service = BatchMinerUService(mineru_service)
        results = await batch_service.parse_documents(file_list, auto_pagination)
        
        # 统计结果
        success_results = [r for r in results if isinstance(r, ParseResult)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        return BatchParseResult(
            total_count=len(results),
            success_count=len(success_results),
            failed_count=len(failed_results),
            results=success_results,
            errors=[
                {"file_name": file_list[i][1], "error": str(failed_results[i])}
                for i in range(len(failed_results))
            ]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量解析失败: {str(e)}")


@router.get("/config", response_model=PaginationConfig, summary="获取分页配置")
async def get_pagination_config(
    mineru_service: MinerUService = Depends(get_mineru_service)
):
    """
    获取当前的分页配置
    
    **返回**:
    ```json
    {
      "max_pages_per_request": 10,
      "max_concurrent_requests": 3
    }
    ```
    """
    return PaginationConfig(
        max_pages_per_request=mineru_service.max_pages_per_request,
        max_concurrent_requests=mineru_service.max_concurrent_requests
    )
