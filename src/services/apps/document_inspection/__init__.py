#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : __init__.py
@Author  : caixiongjiang
@Date    : 2026/1/22
@Function: 
    Document Inspection Service - 文档检查服务
    
    核心功能：
    - 文档解析（MinerU 集成）
    - 会议纪要数据提取
    - 规则校验引擎
    - 提示词生成
    - 配置管理
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from src.services.apps.document_inspection.schemas import (
    MeetingRecord,
    ValidationResult,
    CheckRequest,
    CheckResponse,
    CheckResultResponse,
    ExportPromptRequest,
    ExportPromptResponse,
)

__all__ = [
    "MeetingRecord",
    "ValidationResult",
    "CheckRequest",
    "CheckResponse",
    "CheckResultResponse",
    "ExportPromptRequest",
    "ExportPromptResponse",
]
