#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : validator.py
@Author  : caixiongjiang
@Date    : 2026/1/22
@Function: 
    规则校验器（Rule Validator）
    
    功能：
    - 执行规则校验（完整性、逻辑性、格式）
    - 生成校验结果和错误信息
    - 支持自定义规则扩展
    - 基于 Pydantic + 自定义逻辑
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

import re
from typing import List, Dict, Any, Callable, Optional
from loguru import logger

from src.services.apps.document_inspection.schemas import (
    MeetingRecord,
    ValidationResult,
    RuleSeverity,
    RuleConfigModel,
)


class RuleValidator:
    """
    规则校验引擎
    
    根据规则配置校验会议纪要数据
    """
    
    def __init__(self, rules: List[RuleConfigModel]):
        """
        初始化校验器
        
        Args:
            rules: 规则配置列表
        """
        self.rules = rules
        self._validators: Dict[str, Callable] = {}
        self._build_validators()
    
    def _build_validators(self):
        """构建校验函数映射"""
        # 注册所有校验函数
        self._validators = {
            "validate_required_fields": self._validate_required_fields,
            "validate_time_format": self._validate_time_format,
            "validate_duration_logic": self._validate_duration_logic,
            "validate_attendees_logic": self._validate_attendees_logic,
            "validate_content_length": self._validate_content_length,
            "validate_time_range": self._validate_time_range,
            "validate_date_format": self._validate_date_format,
            "validate_attendees_count": self._validate_attendees_count,
        }
        
        logger.info(f"校验器初始化完成，加载 {len(self.rules)} 条规则")
    
    def validate(self, meeting_record: MeetingRecord) -> List[ValidationResult]:
        """
        执行所有规则校验
        
        Args:
            meeting_record: 会议纪要数据
        
        Returns:
            List[ValidationResult]: 校验结果列表
        """
        logger.info("开始执行规则校验")
        results = []
        
        for rule in self.rules:
            # 跳过未启用的规则
            if not rule.enabled:
                continue
            
            # 获取对应的校验函数
            validator_func = self._validators.get(rule.validator_function)
            if not validator_func:
                logger.warning(f"未找到校验函数: {rule.validator_function}")
                continue
            
            try:
                # 执行校验
                rule_results = validator_func(meeting_record, rule)
                if rule_results:
                    results.extend(rule_results)
            except Exception as e:
                logger.error(f"规则校验失败 ({rule.rule_id}): {e}")
                continue
        
        # 统计结果
        error_count = sum(1 for r in results if not r.is_valid and r.severity == RuleSeverity.ERROR)
        warning_count = sum(1 for r in results if not r.is_valid and r.severity == RuleSeverity.WARNING)
        
        logger.info(f"校验完成: {error_count} 个错误, {warning_count} 个警告")
        
        return results
    
    # ==================== 完整性校验 ====================
    
    def _validate_required_fields(
        self,
        record: MeetingRecord,
        rule: RuleConfigModel
    ) -> List[ValidationResult]:
        """
        完整性校验：检查必填字段
        
        规则参数：
        - required_fields: 必填字段列表
        """
        results = []
        required_fields = rule.parameters.get("required_fields", [])
        
        for field in required_fields:
            value = getattr(record, field, None)
            
            if value is None or (isinstance(value, str) and not value.strip()):
                results.append(ValidationResult(
                    field=field,
                    is_valid=False,
                    severity=rule.severity,
                    error_msg=rule.error_message_template.format(field=field),
                    original_value=value,
                    expected_value="非空值",
                    rule_id=rule.rule_id,
                    suggestion=f"请填写 {field} 字段"
                ))
        
        return results
    
    # ==================== 格式校验 ====================
    
    def _validate_time_format(
        self,
        record: MeetingRecord,
        rule: RuleConfigModel
    ) -> List[ValidationResult]:
        """
        格式校验：检查时间格式
        
        规则参数：
        - time_pattern: 时间格式正则表达式（默认 HH:MM）
        """
        results = []
        time_pattern = rule.parameters.get("time_pattern", r"^\d{1,2}:\d{2}$")
        
        # 检查开始时间
        if record.meeting_time_start:
            if not re.match(time_pattern, record.meeting_time_start):
                results.append(ValidationResult(
                    field="meeting_time_start",
                    is_valid=False,
                    severity=rule.severity,
                    error_msg=rule.error_message_template.format(
                        field="开始时间",
                        value=record.meeting_time_start
                    ),
                    original_value=record.meeting_time_start,
                    expected_value="HH:MM 格式",
                    rule_id=rule.rule_id,
                    suggestion="请使用 HH:MM 格式（如 09:00）"
                ))
        
        # 检查结束时间
        if record.meeting_time_end:
            if not re.match(time_pattern, record.meeting_time_end):
                results.append(ValidationResult(
                    field="meeting_time_end",
                    is_valid=False,
                    severity=rule.severity,
                    error_msg=rule.error_message_template.format(
                        field="结束时间",
                        value=record.meeting_time_end
                    ),
                    original_value=record.meeting_time_end,
                    expected_value="HH:MM 格式",
                    rule_id=rule.rule_id,
                    suggestion="请使用 HH:MM 格式（如 17:00）"
                ))
        
        return results
    
    def _validate_date_format(
        self,
        record: MeetingRecord,
        rule: RuleConfigModel
    ) -> List[ValidationResult]:
        """
        格式校验：检查日期格式
        
        规则参数：
        - date_pattern: 日期格式正则表达式（默认 YYYY-MM-DD）
        """
        results = []
        date_pattern = rule.parameters.get("date_pattern", r"^\d{4}-\d{2}-\d{2}$")
        
        if record.meeting_date:
            if not re.match(date_pattern, record.meeting_date):
                results.append(ValidationResult(
                    field="meeting_date",
                    is_valid=False,
                    severity=rule.severity,
                    error_msg=rule.error_message_template.format(
                        field="会议日期",
                        value=record.meeting_date
                    ),
                    original_value=record.meeting_date,
                    expected_value="YYYY-MM-DD 格式",
                    rule_id=rule.rule_id,
                    suggestion="请使用 YYYY-MM-DD 格式（如 2026-01-22）"
                ))
        
        return results
    
    def _validate_content_length(
        self,
        record: MeetingRecord,
        rule: RuleConfigModel
    ) -> List[ValidationResult]:
        """
        格式校验：检查内容长度
        
        规则参数：
        - min_length: 最小长度
        - max_length: 最大长度
        """
        results = []
        min_length = rule.parameters.get("min_length", 0)
        max_length = rule.parameters.get("max_length", 10000)
        
        if record.content_body:
            content_length = len(record.content_body)
            
            if content_length < min_length:
                results.append(ValidationResult(
                    field="content_body",
                    is_valid=False,
                    severity=rule.severity,
                    error_msg=rule.error_message_template.format(
                        field="会议内容",
                        length=content_length,
                        min=min_length
                    ),
                    original_value=f"{content_length} 字符",
                    expected_value=f"至少 {min_length} 字符",
                    rule_id=rule.rule_id,
                    suggestion=f"会议内容过短，建议补充详细信息"
                ))
            
            if content_length > max_length:
                results.append(ValidationResult(
                    field="content_body",
                    is_valid=False,
                    severity=rule.severity,
                    error_msg=rule.error_message_template.format(
                        field="会议内容",
                        length=content_length,
                        max=max_length
                    ),
                    original_value=f"{content_length} 字符",
                    expected_value=f"不超过 {max_length} 字符",
                    rule_id=rule.rule_id,
                    suggestion=f"会议内容过长，建议精简"
                ))
        
        return results
    
    # ==================== 逻辑校验 ====================
    
    def _validate_duration_logic(
        self,
        record: MeetingRecord,
        rule: RuleConfigModel
    ) -> List[ValidationResult]:
        """
        逻辑校验：检查时长计算是否正确
        
        规则参数：
        - tolerance_minutes: 允许的误差范围（分钟）
        """
        results = []
        tolerance = rule.parameters.get("tolerance_minutes", 5)
        
        # 如果三个字段都存在，检查逻辑
        if (record.meeting_time_start and 
            record.meeting_time_end and 
            record.meeting_duration is not None):
            
            try:
                # 计算实际时长
                start_hour, start_minute = map(int, record.meeting_time_start.split(':'))
                end_hour, end_minute = map(int, record.meeting_time_end.split(':'))
                
                start_minutes = start_hour * 60 + start_minute
                end_minutes = end_hour * 60 + end_minute
                
                # 处理跨天情况
                if end_minutes < start_minutes:
                    end_minutes += 24 * 60
                
                calculated_duration = end_minutes - start_minutes
                
                # 检查误差
                diff = abs(calculated_duration - record.meeting_duration)
                
                if diff > tolerance:
                    results.append(ValidationResult(
                        field="meeting_duration",
                        is_valid=False,
                        severity=rule.severity,
                        error_msg=rule.error_message_template.format(
                            actual=record.meeting_duration,
                            expected=calculated_duration
                        ),
                        original_value=record.meeting_duration,
                        expected_value=calculated_duration,
                        rule_id=rule.rule_id,
                        suggestion=f"根据开始和结束时间计算，时长应为 {calculated_duration} 分钟"
                    ))
            
            except Exception as e:
                logger.warning(f"时长逻辑校验失败: {e}")
        
        return results
    
    def _validate_time_range(
        self,
        record: MeetingRecord,
        rule: RuleConfigModel
    ) -> List[ValidationResult]:
        """
        逻辑校验：检查时间范围是否合理
        
        规则参数：
        - max_duration_hours: 最大会议时长（小时）
        """
        results = []
        max_duration_hours = rule.parameters.get("max_duration_hours", 8)
        
        if record.meeting_time_start and record.meeting_time_end:
            try:
                start_hour, start_minute = map(int, record.meeting_time_start.split(':'))
                end_hour, end_minute = map(int, record.meeting_time_end.split(':'))
                
                # 检查结束时间是否晚于开始时间
                if end_hour < start_hour or (end_hour == start_hour and end_minute <= start_minute):
                    # 可能是跨天，检查是否合理
                    if end_hour + 24 - start_hour > max_duration_hours:
                        results.append(ValidationResult(
                            field="meeting_time_end",
                            is_valid=False,
                            severity=rule.severity,
                            error_msg=rule.error_message_template.format(
                                start=record.meeting_time_start,
                                end=record.meeting_time_end
                            ),
                            original_value=record.meeting_time_end,
                            expected_value=f"晚于 {record.meeting_time_start}",
                            rule_id=rule.rule_id,
                            suggestion="请检查结束时间是否正确"
                        ))
            
            except Exception as e:
                logger.warning(f"时间范围校验失败: {e}")
        
        return results
    
    def _validate_attendees_logic(
        self,
        record: MeetingRecord,
        rule: RuleConfigModel
    ) -> List[ValidationResult]:
        """
        逻辑校验：检查参会人数逻辑
        
        规则参数：
        - require_absent_reason: 是否要求缺席原因
        """
        results = []
        require_absent_reason = rule.parameters.get("require_absent_reason", True)
        
        # 检查实到人数是否大于应到人数
        if (record.attendees_expected is not None and 
            record.attendees_actual is not None):
            
            if record.attendees_actual > record.attendees_expected:
                results.append(ValidationResult(
                    field="attendees_actual",
                    is_valid=False,
                    severity=rule.severity,
                    error_msg=rule.error_message_template.format(
                        actual=record.attendees_actual,
                        expected=record.attendees_expected
                    ),
                    original_value=record.attendees_actual,
                    expected_value=f"不超过 {record.attendees_expected}",
                    rule_id=rule.rule_id,
                    suggestion="实到人数不应大于应到人数"
                ))
            
            # 检查缺席原因
            if record.attendees_actual < record.attendees_expected:
                if require_absent_reason and not record.absent_reason:
                    results.append(ValidationResult(
                        field="absent_reason",
                        is_valid=False,
                        severity=rule.severity,
                        error_msg=rule.error_message_template.format(
                            field="缺席原因"
                        ),
                        original_value=None,
                        expected_value="缺席原因说明",
                        rule_id=rule.rule_id,
                        suggestion=f"有 {record.attendees_expected - record.attendees_actual} 人缺席，请说明原因"
                    ))
        
        return results
    
    def _validate_attendees_count(
        self,
        record: MeetingRecord,
        rule: RuleConfigModel
    ) -> List[ValidationResult]:
        """
        逻辑校验：检查参会人数是否合理
        
        规则参数：
        - min_attendees: 最小参会人数
        - max_attendees: 最大参会人数
        """
        results = []
        min_attendees = rule.parameters.get("min_attendees", 1)
        max_attendees = rule.parameters.get("max_attendees", 1000)
        
        if record.attendees_actual is not None:
            if record.attendees_actual < min_attendees:
                results.append(ValidationResult(
                    field="attendees_actual",
                    is_valid=False,
                    severity=rule.severity,
                    error_msg=rule.error_message_template.format(
                        count=record.attendees_actual,
                        min=min_attendees
                    ),
                    original_value=record.attendees_actual,
                    expected_value=f"至少 {min_attendees} 人",
                    rule_id=rule.rule_id,
                    suggestion=f"参会人数过少"
                ))
            
            if record.attendees_actual > max_attendees:
                results.append(ValidationResult(
                    field="attendees_actual",
                    is_valid=False,
                    severity=rule.severity,
                    error_msg=rule.error_message_template.format(
                        count=record.attendees_actual,
                        max=max_attendees
                    ),
                    original_value=record.attendees_actual,
                    expected_value=f"不超过 {max_attendees} 人",
                    rule_id=rule.rule_id,
                    suggestion=f"参会人数异常"
                ))
        
        return results
    
    # ==================== 内容校验 ====================
    
    def _validate_content(
        self,
        record: MeetingRecord,
        rule: RuleConfigModel
    ) -> List[ValidationResult]:
        """
        内容校验：检查敏感词、关键字等
        
        规则参数：
        - sensitive_words: 敏感词列表
        - required_keywords: 必需关键字列表
        """
        results = []
        
        # 敏感词检查
        sensitive_words = rule.parameters.get("sensitive_words", [])
        if sensitive_words and record.content_body:
            for word in sensitive_words:
                if word in record.content_body:
                    results.append(ValidationResult(
                        field="content_body",
                        is_valid=False,
                        severity=rule.severity,
                        error_msg=rule.error_message_template.format(
                            word=word
                        ),
                        original_value=word,
                        expected_value="不包含敏感词",
                        rule_id=rule.rule_id,
                        suggestion=f"请删除或替换敏感词: {word}"
                    ))
        
        # 必需关键字检查
        required_keywords = rule.parameters.get("required_keywords", [])
        if required_keywords and record.content_body:
            for keyword in required_keywords:
                if keyword not in record.content_body:
                    results.append(ValidationResult(
                        field="content_body",
                        is_valid=False,
                        severity=rule.severity,
                        error_msg=rule.error_message_template.format(
                            keyword=keyword
                        ),
                        original_value=None,
                        expected_value=f"包含关键字: {keyword}",
                        rule_id=rule.rule_id,
                        suggestion=f"建议添加关键字: {keyword}"
                    ))
        
        return results


# ==================== 便捷函数 ====================

def validate_meeting_record(
    meeting_record: MeetingRecord,
    rules: List[RuleConfigModel]
) -> List[ValidationResult]:
    """
    校验会议纪要的便捷函数
    
    Args:
        meeting_record: 会议纪要数据
        rules: 规则配置列表
    
    Returns:
        List[ValidationResult]: 校验结果列表
    """
    validator = RuleValidator(rules)
    return validator.validate(meeting_record)
