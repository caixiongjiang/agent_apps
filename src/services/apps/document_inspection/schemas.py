#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : schemas.py
@Author  : caixiongjiang
@Date    : 2026/1/22
@Function: 
    数据模型定义（Document Inspection Service）
    
    模型分类：
    - 领域模型：MeetingRecord（会议纪要标准结构）
    - 校验模型：ValidationResult（校验结果）
    - 请求模型：CheckRequest, ExportPromptRequest 等
    - 响应模型：CheckResponse, CheckResultResponse 等
    - 配置模型：RuleConfigModel, CreateRuleRequest 等
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== 枚举定义 ====================

class RuleCategory(str, Enum):
    """规则类别枚举"""
    COMPLETENESS = "completeness"  # 完整性检查
    LOGIC = "logic"                # 逻辑校验
    FORMAT = "format"              # 格式校验
    CONTENT = "content"            # 内容校验


class RuleSeverity(str, Enum):
    """规则严重级别枚举"""
    ERROR = "error"      # 错误（必须修复）
    WARNING = "warning"  # 警告（建议修复）
    INFO = "info"        # 信息（提示）


class CheckStatus(str, Enum):
    """检查状态枚举"""
    PENDING = "pending"        # 等待中
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败


# ==================== 领域模型 ====================

class MeetingRecord(BaseModel):
    """
    会议纪要标准结构（领域模型）
    
    从 MinerU 解析结果中提取的标准化会议纪要数据
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "meeting_time_start": "09:00",
                "meeting_time_end": "11:30",
                "meeting_duration": 150,
                "attendees_expected": 10,
                "attendees_actual": 8,
                "absent_reason": "张三、李四因公出差",
                "host": "王经理",
                "recorder": "小李",
                "place": "会议室A",
                "content_body": "会议主要讨论了..."
            }
        }
    )
    
    # 时间信息
    meeting_time_start: Optional[str] = Field(
        None, 
        description="会议开始时间（格式：HH:MM）",
        examples=["09:00", "14:30"]
    )
    meeting_time_end: Optional[str] = Field(
        None, 
        description="会议结束时间（格式：HH:MM）",
        examples=["11:30", "17:00"]
    )
    meeting_duration: Optional[int] = Field(
        None, 
        description="会议时长（分钟）",
        ge=0,
        examples=[90, 120, 150]
    )
    meeting_date: Optional[str] = Field(
        None,
        description="会议日期（格式：YYYY-MM-DD）",
        examples=["2026-01-22"]
    )
    
    # 参会人员信息
    attendees_expected: Optional[int] = Field(
        None, 
        description="应到人数",
        ge=0
    )
    attendees_actual: Optional[int] = Field(
        None, 
        description="实到人数",
        ge=0
    )
    absent_reason: Optional[str] = Field(
        None, 
        description="缺席原因及人员"
    )
    attendees_list: Optional[List[str]] = Field(
        None,
        description="参会人员名单"
    )
    
    # 元数据
    host: Optional[str] = Field(
        None, 
        description="主持人"
    )
    recorder: Optional[str] = Field(
        None, 
        description="记录人"
    )
    place: Optional[str] = Field(
        None, 
        description="会议地点"
    )
    meeting_topic: Optional[str] = Field(
        None,
        description="会议主题"
    )
    
    # 正文内容
    content_body: Optional[str] = Field(
        None, 
        description="会议纪要正文内容"
    )
    
    # 其他字段
    attachments: Optional[List[str]] = Field(
        default_factory=list,
        description="附件列表"
    )
    raw_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="原始提取数据（用于调试）"
    )


class ValidationResult(BaseModel):
    """
    单个字段的校验结果
    
    包含校验详情、错误信息、原始值和期望值
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field": "meeting_time_start",
                "is_valid": False,
                "severity": "error",
                "error_msg": "缺少必填字段：会议开始时间",
                "original_value": None,
                "expected_value": "HH:MM 格式的时间",
                "rule_id": "completeness_001"
            }
        }
    )
    
    field: str = Field(..., description="字段名称")
    is_valid: bool = Field(..., description="是否通过校验")
    severity: RuleSeverity = Field(
        default=RuleSeverity.ERROR, 
        description="严重级别"
    )
    error_msg: Optional[str] = Field(None, description="错误信息")
    original_value: Any = Field(None, description="原始值")
    expected_value: Optional[Any] = Field(None, description="期望值")
    rule_id: Optional[str] = Field(None, description="触发的规则ID")
    suggestion: Optional[str] = Field(None, description="修改建议")


# ==================== 请求模型 ====================

class CheckRequest(BaseModel):
    """
    文档检查请求
    
    发起文档合规性检查的请求参数
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_id": "file_abc123def456",
                "save_to_kb": False,
                "custom_rules": None,
                "session_id": "sess_xyz789"
            }
        }
    )
    
    file_id: str = Field(
        ..., 
        description="文件ID（从 Storage Service 获取）",
        min_length=1
    )
    save_to_kb: bool = Field(
        default=False, 
        description="是否保存到知识库"
    )
    custom_rules: Optional[Dict[str, Any]] = Field(
        None, 
        description="自定义规则覆盖（高级功能）"
    )
    session_id: Optional[str] = Field(
        None, 
        description="会话ID（用于会话配置）"
    )


class ExportPromptRequest(BaseModel):
    """
    导出提示词请求
    
    基于检查结果导出用于 AI 深度校验的提示词
    """
    check_id: str = Field(
        ..., 
        description="检查任务ID",
        min_length=1
    )
    template_name: Optional[str] = Field(
        default="default",
        description="提示词模板名称"
    )
    include_raw_data: bool = Field(
        default=False,
        description="是否包含原始数据"
    )


class BatchCheckRequest(BaseModel):
    """批量文档检查请求"""
    file_ids: List[str] = Field(
        ...,
        description="文件ID列表",
        min_length=1,
        max_length=20
    )
    save_to_kb: bool = Field(default=False)
    session_id: Optional[str] = None
    user_id: Optional[str] = None


# ==================== 响应模型 ====================

class CheckResponse(BaseModel):
    """
    文档检查响应（同步版本）
    
    由于暂时没有 Redis，直接返回完整的检查结果
    """
    check_id: str = Field(..., description="检查任务ID")
    file_id: str = Field(..., description="文件ID")
    status: CheckStatus = Field(..., description="检查状态")
    message: Optional[str] = Field(None, description="状态消息")
    
    # 直接包含检查结果（同步模式）
    meeting_record: Optional[MeetingRecord] = Field(None, description="会议纪要数据")
    validation_results: Optional[List[ValidationResult]] = Field(
        None, 
        description="校验结果列表"
    )
    error_count: Optional[int] = Field(None, description="错误数量")
    warning_count: Optional[int] = Field(None, description="警告数量")
    is_compliant: Optional[bool] = Field(None, description="是否合规")
    
    # 坐标信息（用于前端标注）
    coordinates: Optional[Dict[str, Any]] = Field(
        None, 
        description="字段在文档中的坐标信息"
    )
    
    # 元信息
    check_time: Optional[datetime] = Field(None, description="检查时间")
    processing_time_ms: Optional[int] = Field(None, description="处理耗时（毫秒）")


class CheckResultResponse(BaseModel):
    """
    检查结果详情响应
    
    用于查询历史检查结果
    """
    check_id: str = Field(..., description="检查任务ID")
    file_id: str = Field(..., description="文件ID")
    status: CheckStatus = Field(..., description="检查状态")
    
    # 检查结果
    meeting_record: MeetingRecord = Field(..., description="会议纪要数据")
    validation_results: List[ValidationResult] = Field(
        ..., 
        description="校验结果列表"
    )
    
    # 统计信息
    error_count: int = Field(default=0, description="错误数量")
    warning_count: int = Field(default=0, description="警告数量")
    is_compliant: bool = Field(..., description="是否合规")
    
    # 坐标信息
    coordinates: Optional[Dict[str, Any]] = Field(
        None, 
        description="字段在文档中的坐标信息"
    )
    
    # 元信息
    check_time: datetime = Field(..., description="检查时间")
    user_id: Optional[str] = Field(None, description="用户ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    
    # 原始文件信息
    original_filename: Optional[str] = Field(None, description="原始文件名")


class ExportPromptResponse(BaseModel):
    """
    导出提示词响应
    
    包含生成的提示词文本和统计信息
    """
    check_id: str = Field(..., description="检查任务ID")
    prompt: str = Field(..., description="生成的提示词文本")
    token_count: int = Field(..., description="Token 数量（估算）")
    template_name: str = Field(default="default", description="使用的模板名称")
    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="生成时间"
    )


class CheckHistoryItem(BaseModel):
    """检查历史记录项（简化版）"""
    check_id: str
    file_id: str
    original_filename: Optional[str]
    status: CheckStatus
    is_compliant: bool
    error_count: int
    warning_count: int
    check_time: datetime
    user_id: Optional[str]


class CheckHistoryResponse(BaseModel):
    """检查历史记录列表响应"""
    total_count: int = Field(..., description="总记录数")
    items: List[CheckHistoryItem] = Field(..., description="历史记录列表")
    limit: int = Field(..., description="每页数量")
    offset: int = Field(..., description="偏移量")


class BatchCheckResponse(BaseModel):
    """批量检查响应"""
    total_count: int
    success_count: int
    failed_count: int
    results: List[CheckResponse]
    errors: List[Dict[str, str]] = Field(default_factory=list)


# ==================== 配置管理模型 ====================

class RuleConfigModel(BaseModel):
    """
    规则配置模型（用于 API 传输）
    
    对应数据库中的规则配置表（用户级隔离）
    """
    model_config = ConfigDict(from_attributes=True)
    
    rule_id: str = Field(..., description="规则ID（唯一标识）")
    rule_name: str = Field(..., description="规则名称")
    user_id: str = Field(..., description="所属用户ID（用户级隔离）")
    category: RuleCategory = Field(..., description="规则类别")
    description: Optional[str] = Field(None, description="规则描述")
    enabled: bool = Field(default=True, description="是否启用")
    severity: RuleSeverity = Field(default=RuleSeverity.ERROR, description="严重级别")
    
    # 规则参数（JSON 格式）
    parameters: Dict[str, Any] = Field(
        default_factory=dict, 
        description="规则参数"
    )
    
    # 校验逻辑
    validator_function: str = Field(
        ..., 
        description="对应的 Python 函数名"
    )
    error_message_template: str = Field(
        ..., 
        description="错误消息模板"
    )
    
    # UI 相关
    display_order: int = Field(default=0, description="显示顺序")
    group_name: Optional[str] = Field(None, description="规则分组名称（如：会议基本信息、时间检查等）")
    
    # 元数据
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateRuleRequest(BaseModel):
    """
    创建用户规则请求
    
    注意：user_id 会从认证信息中自动提取，不需要在请求体中提供
    """
    rule_id: Optional[str] = Field(None, max_length=50, description="规则ID（可选，不提供则自动生成）")
    rule_name: str = Field(..., min_length=1, max_length=100, description="规则名称")
    category: RuleCategory = Field(..., description="规则类别")
    description: Optional[str] = Field(None, max_length=500, description="规则描述")
    enabled: bool = Field(default=True, description="是否启用")
    severity: RuleSeverity = Field(default=RuleSeverity.ERROR, description="严重级别")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="规则参数")
    validator_function: str = Field(..., min_length=1, max_length=100, description="校验函数名")
    error_message_template: str = Field(..., min_length=1, description="错误消息模板")
    display_order: int = Field(default=0, description="显示顺序")
    group_name: Optional[str] = Field(None, max_length=50, description="规则分组名称")


class UpdateRuleRequest(BaseModel):
    """
    更新用户规则请求
    
    注意：只能修改自己的规则
    """
    rule_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    enabled: Optional[bool] = None
    severity: Optional[RuleSeverity] = None
    parameters: Optional[Dict[str, Any]] = None
    error_message_template: Optional[str] = None
    display_order: Optional[int] = None
    group_name: Optional[str] = Field(None, max_length=50, description="规则分组名称")


class RuleListResponse(BaseModel):
    """规则列表响应"""
    total_count: int
    rules: List[RuleConfigModel]
    enabled_count: int
    disabled_count: int


# ==================== 配置响应模型 ====================

class EffectiveConfigResponse(BaseModel):
    """
    有效配置响应
    
    暂时只包含 MySQL 规则配置，等 Redis 开发后会合并会话配置
    """
    rules: List[RuleConfigModel] = Field(..., description="规则配置列表")
    session_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="会话配置（暂时为空）"
    )
    config_source: str = Field(
        default="mysql_only",
        description="配置来源"
    )
