#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : schemas.py
@Author  : caixiongjiang
@Date    : 2026/1/19
@Function: 
    MinerU 服务的数据模型定义 - 简化版
@Modify History:
    2026/1/19 - 简化模型，移除任务状态管理
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# ========== 请求模型 ==========

class ParseRequest(BaseModel):
    """解析请求模型"""
    file_name: str = Field(..., description="文件名")
    auto_pagination: bool = Field(default=True, description="是否自动分页处理大文件")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_name": "document.pdf",
                "auto_pagination": True
            }
        }


class BatchParseRequest(BaseModel):
    """批量解析请求模型"""
    file_names: List[str] = Field(..., description="文件名列表")
    auto_pagination: bool = Field(default=True, description="是否自动分页")


# ========== 响应模型 ==========

class ParseResult(BaseModel):
    """解析结果模型（完整结果）"""
    file_name: str = Field(..., description="文件名")
    
    # 解析结果
    struct_content: Dict[str, Any] = Field(..., description="结构化内容")
    markdown_content: str = Field(..., description="Markdown内容")
    pages: int = Field(..., description="页数")
    
    # 坐标信息（用于前端画框）
    coordinates: Optional[Dict[str, Any]] = Field(None, description="元素坐标信息")
    
    # 元数据
    meta: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    # 时间信息（可选）
    parsed_at: Optional[datetime] = Field(None, description="解析时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_name": "document.pdf",
                "pages": 15,
                "markdown_content": "# 标题\n\n内容...",
                "struct_content": {
                    "root": [
                        {
                            "page_idx": 0,
                            "page_size": {"width": 595, "height": 842},
                            "page_info": []
                        }
                    ]
                },
                "coordinates": {
                    "page_0": []
                }
            }
        }


class BatchParseResult(BaseModel):
    """批量解析结果模型"""
    total_count: int = Field(..., description="总文档数")
    success_count: int = Field(..., description="成功数")
    failed_count: int = Field(..., description="失败数")
    results: List[ParseResult] = Field(..., description="解析结果列表")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="错误信息")


# ========== 配置模型 ==========

class PaginationConfig(BaseModel):
    """分页配置模型"""
    max_pages_per_request: int = Field(
        default=10,
        ge=1,
        le=50,
        description="每次请求最大页数"
    )
    max_concurrent_requests: int = Field(
        default=3,
        ge=1,
        le=10,
        description="最大并发请求数"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "max_pages_per_request": 10,
                "max_concurrent_requests": 3
            }
        }
