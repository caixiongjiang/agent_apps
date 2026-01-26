#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : document_inspection.py
@Author  : caixiongjiang
@Date    : 2026/1/22
@Function: 
    Document Inspection 数据库模型定义
    
    表设计：
    - rule_configs: 规则配置表（持久化存储）
    - check_history: 检查历史记录表
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from sqlalchemy import (
    Column, String, Integer, Boolean, JSON, DateTime, Text, Enum as SQLEnum, Index
)
from sqlalchemy.sql import func
from datetime import datetime
import enum

from db.mysql.models.base_model import Base


# ==================== 枚举定义 ====================

class RuleCategoryEnum(enum.Enum):
    """规则类别枚举"""
    COMPLETENESS = "completeness"  # 完整性检查
    LOGIC = "logic"                # 逻辑校验
    FORMAT = "format"              # 格式校验
    CONTENT = "content"            # 内容校验


class RuleSeverityEnum(enum.Enum):
    """规则严重级别枚举"""
    ERROR = "error"      # 错误
    WARNING = "warning"  # 警告
    INFO = "info"        # 信息


class CheckStatusEnum(enum.Enum):
    """检查状态枚举"""
    PENDING = "pending"        # 等待中
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败


# ==================== 数据库模型 ====================

class RuleConfig(Base):
    """
    规则配置表 - MySQL 持久化存储（用户级隔离）
    
    存储会议纪要检查规则的配置信息，每个用户拥有独立的规则集
    """
    __tablename__ = "rule_configs"
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    
    # 规则标识
    rule_id = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="规则ID（唯一标识）"
    )
    rule_name = Column(String(100), nullable=False, comment="规则名称")
    
    # 用户隔离（核心字段）
    user_id = Column(
        String(50),
        nullable=False,
        index=True,
        comment="所属用户ID（用户级规则隔离）"
    )
    
    # 规则分类
    category = Column(
        SQLEnum(RuleCategoryEnum),
        nullable=False,
        index=True,
        comment="规则类别"
    )
    
    # 规则定义
    description = Column(String(500), nullable=True, comment="规则描述")
    enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    severity = Column(
        SQLEnum(RuleSeverityEnum),
        default=RuleSeverityEnum.ERROR,
        nullable=False,
        comment="严重级别"
    )
    
    # 规则参数（JSON 格式）
    parameters = Column(
        JSON,
        nullable=False,
        default={},
        comment="规则参数（JSON 格式）"
    )
    
    # 校验逻辑
    validator_function = Column(
        String(100),
        nullable=False,
        comment="对应的 Python 函数名"
    )
    error_message_template = Column(
        Text,
        nullable=False,
        comment="错误消息模板"
    )
    
    # 元数据
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )
    
    # UI 相关字段
    display_order = Column(
        Integer,
        default=0,
        nullable=False,
        comment="显示顺序"
    )
    group_name = Column(
        String(50),
        nullable=True,
        comment="规则分组名称（如：会议基本信息、时间检查等）"
    )
    
    # 创建索引
    __table_args__ = (
        Index('idx_user_enabled', 'user_id', 'enabled'),
        Index('idx_user_category', 'user_id', 'category'),
        Index('idx_user_group', 'user_id', 'group_name'),
        {'comment': '规则配置表（用户级隔离）'}
    )
    
    def __repr__(self):
        return f"<RuleConfig(rule_id='{self.rule_id}', name='{self.rule_name}', enabled={self.enabled})>"


class CheckHistory(Base):
    """
    检查历史记录表
    
    存储文档检查的历史记录和结果
    """
    __tablename__ = "check_history"
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    
    # 检查标识
    check_id = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="检查任务ID（唯一标识）"
    )
    file_id = Column(
        String(50),
        nullable=False,
        index=True,
        comment="文件ID"
    )
    
    # 检查时间和状态
    check_time = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="检查时间"
    )
    status = Column(
        SQLEnum(CheckStatusEnum),
        nullable=False,
        default=CheckStatusEnum.COMPLETED,
        index=True,
        comment="检查状态"
    )
    
    # 检查结果（JSON 格式）
    meeting_record = Column(
        JSON,
        nullable=True,
        comment="会议纪要数据（JSON 格式）"
    )
    validation_results = Column(
        JSON,
        nullable=True,
        comment="校验结果列表（JSON 格式）"
    )
    
    # 坐标信息（用于前端标注）
    coordinates = Column(
        JSON,
        nullable=True,
        comment="字段在文档中的坐标信息（JSON 格式）"
    )
    
    # 统计信息
    error_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="错误数量"
    )
    warning_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="警告数量"
    )
    is_compliant = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="是否合规"
    )
    
    # 处理信息
    processing_time_ms = Column(
        Integer,
        nullable=True,
        comment="处理耗时（毫秒）"
    )
    error_message = Column(
        Text,
        nullable=True,
        comment="错误信息（如果检查失败）"
    )
    
    # 关联信息
    user_id = Column(
        String(50),
        nullable=True,
        index=True,
        comment="用户ID"
    )
    session_id = Column(
        String(50),
        nullable=True,
        index=True,
        comment="会话ID"
    )
    
    # 文件信息（冗余存储，方便查询）
    original_filename = Column(
        String(255),
        nullable=True,
        comment="原始文件名"
    )
    
    # 创建索引
    __table_args__ = (
        Index('idx_user_check_time', 'user_id', 'check_time'),
        Index('idx_session_check_time', 'session_id', 'check_time'),
        Index('idx_status_check_time', 'status', 'check_time'),
        Index('idx_compliant_check_time', 'is_compliant', 'check_time'),
        {'comment': '检查历史记录表'}
    )
    
    def __repr__(self):
        return f"<CheckHistory(check_id='{self.check_id}', file_id='{self.file_id}', status='{self.status.value}')>"
