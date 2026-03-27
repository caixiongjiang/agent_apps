#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : document_compliance.py
@Author  : caixiongjiang
@Date    : 2026/1/22
@Function: 
    Document Compliance Agent API 路由
    
    接口分类：
    - 核心业务接口：文档检查、结果查询、提示词导出、历史记录
    - 配置管理接口：规则 CRUD
    
    注意：
    - 会话配置接口暂不实现，等 Redis 开发后补充
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from fastapi import APIRouter, HTTPException, Depends, Query, Header
from typing import Optional, List
from loguru import logger

from src.services.apps.document_inspection.service import DocumentInspectionService
from src.services.apps.document_inspection.config_manager import DocumentConfigManager
from src.services.apps.document_inspection.schemas import (
    CheckRequest,
    CheckResponse,
    CheckResultResponse,
    ExportPromptRequest,
    ExportPromptResponse,
    CheckHistoryResponse,
    CreateRuleRequest,
    UpdateRuleRequest,
    RuleConfigModel,
    RuleListResponse,
    EffectiveConfigResponse,
)
from src.services.mineru.service import MinerUService
from src.services.storage.service import FileStorageService
from db.mysql.repositories.apps.document_inspection_repository import (
    DocumentInspectionRepository
)
from db.mysql.connection import get_mysql_manager

# 创建路由（不包含前缀，由上层统一管理）
router = APIRouter(tags=["Document Compliance - 文档合规检查"])


# ========== 依赖注入 ==========

def get_current_user_id(
    x_user_id: str = Header(..., description="用户ID（从请求头获取）")
) -> str:
    """
    从请求头获取当前用户ID
    
    Args:
        x_user_id: 请求头中的用户ID（X-User-Id）
    
    Returns:
        str: 用户ID
    
    注意：
        - 这是临时方案，生产环境应该使用 JWT 认证
        - 未来会改为从 JWT Token 中解析用户信息
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="用户ID缺失")
    
    return x_user_id

def get_document_service() -> DocumentInspectionService:
    """
    获取 Document Inspection Service 实例（依赖注入）
    
    使用 ConfigManager 和 EnvManager 加载配置
    """
    from src.utils.config_manager import get_config_manager
    from src.utils.env_manager import get_env_manager
    from pathlib import Path
    
    # 获取配置管理器
    config_manager = get_config_manager()
    env_manager = get_env_manager()
    
    # 创建 MinerU Service
    mineru_full_config = config_manager.get_mineru_full_config(env_manager)
    mineru_config_section = config_manager.get_mineru_config()
    file_upload_config = config_manager.get_file_upload_config()
    
    mineru_service = MinerUService(
        mineru_config=mineru_full_config,
        max_pages_per_request=mineru_config_section.get("max_pages_per_request", 10),
        max_concurrent_requests=mineru_config_section.get("max_concurrent_requests", 3),
        storage_path=Path(file_upload_config.get("temp_dir", "./uploads"))
    )
    
    # 创建 Storage Service
    storage_config = config_manager.get_storage_config()
    from src.services.storage.file_manager import FileManager
    
    file_manager = FileManager(
        storage_root=Path(storage_config.get("storage_root", "./upload")),
        use_hash_structure=storage_config.get("use_hash_structure", True),
        enable_compression=storage_config.get("enable_compression", False)
    )
    
    db_manager = get_mysql_manager()
    
    storage_service = FileStorageService(
        file_manager=file_manager,
        db_manager=db_manager,
        enable_db_sync=True
    )
    
    # 创建 Repository 和 Config Manager
    repository = DocumentInspectionRepository(db_manager)
    doc_config_manager = DocumentConfigManager(repository)
    
    # 创建 Document Service
    service = DocumentInspectionService(
        mineru_service=mineru_service,
        storage_service=storage_service,
        config_manager=doc_config_manager,
        db_repository=repository,
    )
    
    return service


def get_config_manager_dep() -> DocumentConfigManager:
    """获取配置管理器实例（依赖注入）"""
    db_manager = get_mysql_manager()
    repository = DocumentInspectionRepository(db_manager)
    return DocumentConfigManager(repository)


# ========== 核心业务接口 ==========

@router.post("/check", response_model=CheckResponse, summary="执行文档检查")
async def check_document(
    request: CheckRequest,
    user_id: str = Depends(get_current_user_id),
    service: DocumentInspectionService = Depends(get_document_service)
):
    """
    执行文档合规性检查（同步返回结果，使用用户的规则配置）
    
    流程：
    1. 验证文件是否存在
    2. 调用 MinerU 解析文档
    3. 提取会议纪要数据
    4. 执行用户的规则校验
    5. 保存检查结果
    6. 返回完整结果
    
    **示例**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/apps/document-compliance/check" \\
         -H "Content-Type: application/json" \\
         -H "X-User-Id: user_001" \\
         -d '{
           "file_id": "file_abc123def456",
           "save_to_kb": false,
           "session_id": "sess_xyz789"
         }'
    ```
    
    **返回**:
    ```json
    {
      "check_id": "check_abc123",
      "file_id": "file_abc123def456",
      "status": "completed",
      "message": "检查完成",
      "meeting_record": {...},
      "validation_results": [...],
      "error_count": 2,
      "warning_count": 1,
      "is_compliant": false,
      "check_time": "2026-01-22T10:30:00",
      "processing_time_ms": 3500
    }
    ```
    """
    try:
        result = await service.check_document(request, user_id)
        return result
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"文档检查失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检查失败: {str(e)}")


@router.get("/check/{check_id}", response_model=CheckResultResponse, summary="获取检查结果")
async def get_check_result(
    check_id: str,
    service: DocumentInspectionService = Depends(get_document_service)
):
    """
    获取历史检查结果详情
    
    **示例**:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/apps/document-compliance/check/check_abc123"
    ```
    """
    try:
        result = service.get_check_result(check_id)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"检查记录不存在: {check_id}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取检查结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/export-prompt", response_model=ExportPromptResponse, summary="导出AI提示词")
async def export_prompt(
    request: ExportPromptRequest,
    service: DocumentInspectionService = Depends(get_document_service)
):
    """
    导出用于 AI 深度校验的提示词
    
    基于检查结果生成格式化的提示词文本
    
    **示例**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/apps/document-compliance/export-prompt" \\
         -H "Content-Type: application/json" \\
         -d '{
           "check_id": "check_abc123",
           "template_name": "default",
           "include_raw_data": false
         }'
    ```
    """
    try:
        result = service.export_prompt(request)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"检查记录不存在: {request.check_id}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出提示词失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.get("/history", response_model=CheckHistoryResponse, summary="查询检查历史")
async def get_check_history(
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
    session_id: Optional[str] = Query(None, description="会话ID过滤"),
    file_id: Optional[str] = Query(None, description="文件ID过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    is_compliant: Optional[bool] = Query(None, description="合规性过滤"),
    limit: int = Query(50, le=200, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    service: DocumentInspectionService = Depends(get_document_service)
):
    """
    查询检查历史记录列表
    
    支持多种过滤条件和分页查询
    
    **示例**:
    ```bash
    # 查询某个会话的所有检查记录
    curl -X GET "http://localhost:8000/api/v1/apps/document-compliance/history?session_id=sess_123"
    
    # 查询不合规的记录
    curl -X GET "http://localhost:8000/api/v1/apps/document-compliance/history?is_compliant=false&limit=20"
    ```
    """
    try:
        result = service.get_history(
            user_id=user_id,
            session_id=session_id,
            file_id=file_id,
            status=status,
            is_compliant=is_compliant,
            limit=limit,
            offset=offset,
        )
        
        return result
        
    except Exception as e:
        logger.error(f"查询历史记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


# ========== 配置管理接口（规则管理） ==========

@router.get("/config/rules", response_model=RuleListResponse, summary="获取用户的规则列表")
async def get_rules(
    user_id: str = Depends(get_current_user_id),
    enabled_only: bool = Query(True, description="是否只返回启用的规则"),
    category: Optional[str] = Query(None, description="规则类别过滤"),
    group_name: Optional[str] = Query(None, description="规则分组过滤"),
    config_manager: DocumentConfigManager = Depends(get_config_manager_dep)
):
    """
    获取当前用户的规则配置列表
    
    **示例**:
    ```bash
    # 获取用户所有启用的规则
    curl -X GET "http://localhost:8000/api/v1/apps/document-compliance/config/rules" \\
         -H "X-User-Id: user_001"
    
    # 获取用户的完整性检查规则
    curl -X GET "http://localhost:8000/api/v1/apps/document-compliance/config/rules?category=completeness" \\
         -H "X-User-Id: user_001"
    ```
    """
    try:
        rules = config_manager.get_all_rules(
            user_id=user_id,
            enabled_only=enabled_only,
            category=category,
            group_name=group_name
        )
        
        enabled_count = sum(1 for r in rules if r.enabled)
        disabled_count = len(rules) - enabled_count
        
        return RuleListResponse(
            total_count=len(rules),
            rules=rules,
            enabled_count=enabled_count,
            disabled_count=disabled_count,
        )
        
    except Exception as e:
        logger.error(f"获取规则列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/config/rules", response_model=RuleConfigModel, summary="创建用户规则")
async def create_rule(
    request: CreateRuleRequest,
    user_id: str = Depends(get_current_user_id),
    config_manager: DocumentConfigManager = Depends(get_config_manager_dep)
):
    """
    为当前用户创建新的规则配置
    
    **示例**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/apps/document-compliance/config/rules" \\
         -H "Content-Type: application/json" \\
         -H "X-User-Id: user_001" \\
         -d '{
           "rule_name": "会议主持人",
           "category": "completeness",
           "enabled": true,
           "severity": "error",
           "parameters": {},
           "validator_function": "validate_required_fields",
           "error_message_template": "缺少必填字段: {field}",
           "group_name": "会议基本信息"
         }'
    ```
    """
    try:
        rule = config_manager.create_rule(user_id, request)
        return rule
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建规则失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.get("/config/rules/{rule_id}", response_model=RuleConfigModel, summary="获取规则详情")
async def get_rule(
    rule_id: str,
    user_id: str = Depends(get_current_user_id),
    config_manager: DocumentConfigManager = Depends(get_config_manager_dep)
):
    """获取单个规则配置详情（仅限本人的规则）"""
    try:
        rule = config_manager.get_rule(rule_id, user_id)
        
        if not rule:
            raise HTTPException(status_code=404, detail=f"规则不存在或无权限: {rule_id}")
        
        return rule
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取规则详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.put("/config/rules/{rule_id}", response_model=RuleConfigModel, summary="更新用户规则")
async def update_rule(
    rule_id: str,
    request: UpdateRuleRequest,
    user_id: str = Depends(get_current_user_id),
    config_manager: DocumentConfigManager = Depends(get_config_manager_dep)
):
    """
    更新用户的规则配置（仅限本人的规则）
    """
    try:
        rule = config_manager.update_rule(rule_id, request, user_id)
        
        if not rule:
            raise HTTPException(status_code=404, detail=f"规则不存在或无权限: {rule_id}")
        
        return rule
        
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新规则失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/config/rules/{rule_id}", summary="删除用户规则")
async def delete_rule(
    rule_id: str,
    user_id: str = Depends(get_current_user_id),
    config_manager: DocumentConfigManager = Depends(get_config_manager_dep)
):
    """
    删除用户的规则配置（仅限本人的规则）
    """
    try:
        success = config_manager.delete_rule(rule_id, user_id=user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"规则不存在或无权限: {rule_id}")
        
        return {"success": True, "message": f"规则已删除: {rule_id}"}
        
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除规则失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.get("/config/effective", response_model=EffectiveConfigResponse, summary="获取有效配置")
async def get_effective_config(
    session_id: Optional[str] = Query(None, description="会话ID"),
    enabled_only: bool = Query(True, description="是否只返回启用的规则"),
    user_id: str = Depends(get_current_user_id),
    config_manager: DocumentConfigManager = Depends(get_config_manager_dep)
):
    """
    获取有效配置（合并 MySQL 规则配置和 Redis 会话配置）
    
    **注意**: 暂时只返回 MySQL 规则配置，等 Redis 开发完成后会合并会话配置
    
    **示例**:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/apps/document-compliance/config/effective?session_id=sess_123" \\
         -H "X-User-Id: user_001"
    ```
    """
    try:
        effective_config = config_manager.get_effective_config(
            user_id=user_id,
            session_id=session_id,
            enabled_only=enabled_only
        )
        
        return EffectiveConfigResponse(
            rules=[RuleConfigModel(**r) for r in effective_config["rules"]],
            session_config=effective_config["session_config"],
            config_source=effective_config["config_source"],
        )
        
    except Exception as e:
        logger.error(f"获取有效配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
