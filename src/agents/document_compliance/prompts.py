#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : prompts.py
@Author  : caixiongjiang
@Date    : 2026/01/22
@Function: 
    提示词定义（Document Compliance Agent）
    
    功能：
    - 定义合规检查提示词模板
    - 提供提示词构建函数
    - 支持多种模板变体
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from typing import List, Dict, Any, Optional
from src.services.apps.document_inspection.schemas import (
    MeetingRecord,
    ValidationResult,
    RuleSeverity
)


# ==================== 提示词模板定义 ====================

COMPLIANCE_CHECK_PROMPT_TEMPLATE = """你是一个专业的会议纪要合规检查专家。请根据以下信息进行深度校验。

## 📋 会议纪要内容

**会议时间**: {meeting_time}
**会议时长**: {meeting_duration}
**参会人员**: 应到 {attendees_expected} 人，实到 {attendees_actual} 人
**缺席情况**: {absent_reason}
**主持人**: {host}
**记录人**: {recorder}
**会议地点**: {place}
**会议主题**: {meeting_topic}

**会议正文**:
{content_body}

---

## ⚠️ 基础校验结果

{validation_results}

---

## 📝 请完成以下任务

1. **复核基础校验**: 检查上述自动校验发现的问题是否准确，是否存在误报
2. **完整性检查**: 评估会议纪要是否包含所有必要信息（时间、地点、人员、内容等）
3. **逻辑性检查**: 验证时长计算、人数统计等数据的逻辑一致性
4. **内容质量评估**: 评价会议内容是否清晰、完整、准确
5. **合规性建议**: 提供具体的改进建议和修改方案

## 📊 输出格式

请以结构化的 JSON 格式输出你的分析结果，包含以下字段：
- `overall_assessment`: 整体评估（优秀/良好/合格/不合格）
- `verified_issues`: 确认的问题列表（每项包含：字段、问题描述、严重程度）
- `additional_issues`: 新发现的问题列表
- `suggestions`: 改进建议列表
- `compliance_score`: 合规评分（0-100）
"""


SIMPLE_COMPLIANCE_CHECK_PROMPT_TEMPLATE = """请检查以下会议纪要的合规性：

{meeting_content}

基础校验发现的问题：
{validation_results}

请提供：
1. 问题确认和补充
2. 改进建议
"""


STRICT_COMPLIANCE_CHECK_PROMPT_TEMPLATE = """## 🔍 会议纪要合规性严格审查

### 审查依据
- 《会议纪要管理规范》
- 《文档格式标准》
- 《信息完整性要求》

### 审查对象

{meeting_content}

### 自动检测问题

{validation_results}

### 审查要求

1. **必填项检查**（一票否决）
   - 会议时间必须精确到分钟
   - 参会人员必须有完整名单
   - 会议内容必须详实

2. **格式规范检查**
   - 时间格式统一
   - 人员信息格式统一
   - 内容结构清晰

3. **逻辑一致性检查**
   - 时长与时间段匹配
   - 人数统计准确
   - 缺席原因说明充分

4. **内容质量检查**
   - 无错别字
   - 无语句不通
   - 无关键信息缺失

### 输出要求

请严格按照以下 JSON Schema 输出：

```json
{{
  "is_compliant": boolean,
  "compliance_level": "严格合规|基本合规|不合规",
  "critical_issues": [
    {{"field": "字段名", "issue": "问题描述", "must_fix": true}}
  ],
  "warnings": [
    {{"field": "字段名", "issue": "问题描述", "suggestion": "建议"}}
  ],
  "score_breakdown": {{
    "completeness": 0-25,
    "accuracy": 0-25,
    "format": 0-25,
    "content_quality": 0-25
  }},
  "total_score": 0-100,
  "reviewer_notes": "审查备注"
}}
```
"""


# ==================== 提示词构建函数 ====================

def build_compliance_prompt(
    meeting_record: MeetingRecord,
    validation_results: List[ValidationResult],
    template_name: str = "default",
    include_raw_data: bool = False,
    **kwargs
) -> str:
    """
    构建合规检查提示词
    
    Args:
        meeting_record: 会议纪要数据
        validation_results: 校验结果列表
        template_name: 模板名称（default/simple/strict）
        include_raw_data: 是否包含原始数据
        **kwargs: 额外参数
    
    Returns:
        str: 构建好的提示词文本
    """
    # 格式化会议时间
    meeting_time = _format_meeting_time(
        meeting_record.meeting_time_start,
        meeting_record.meeting_time_end,
        meeting_record.meeting_date
    )
    
    # 格式化会议时长
    meeting_duration = _format_duration(meeting_record.meeting_duration)
    
    # 格式化校验结果
    validation_text = _format_validation_results(validation_results)
    
    # 处理可能为 None 的字段
    meeting_content = _build_meeting_content(meeting_record)
    
    # 根据模板名称选择模板
    if template_name == "simple":
        template = SIMPLE_COMPLIANCE_CHECK_PROMPT_TEMPLATE
        return template.format(
            meeting_content=meeting_content,
            validation_results=validation_text
        )
    elif template_name == "strict":
        template = STRICT_COMPLIANCE_CHECK_PROMPT_TEMPLATE
        return template.format(
            meeting_content=meeting_content,
            validation_results=validation_text
        )
    else:  # default
        template = COMPLIANCE_CHECK_PROMPT_TEMPLATE
        return template.format(
            meeting_time=meeting_time,
            meeting_duration=meeting_duration,
            attendees_expected=meeting_record.attendees_expected or "未知",
            attendees_actual=meeting_record.attendees_actual or "未知",
            absent_reason=meeting_record.absent_reason or "无",
            host=meeting_record.host or "未记录",
            recorder=meeting_record.recorder or "未记录",
            place=meeting_record.place or "未记录",
            meeting_topic=meeting_record.meeting_topic or "未记录",
            content_body=meeting_record.content_body or "（内容为空）",
            validation_results=validation_text
        )


def estimate_token_count(prompt: str) -> int:
    """
    估算提示词的 Token 数量
    
    使用简单的启发式方法：
    - 中文字符：1 字符 ≈ 1.5 token
    - 英文单词：1 单词 ≈ 1.3 token
    - 标点符号：1 符号 ≈ 1 token
    
    Args:
        prompt: 提示词文本
    
    Returns:
        int: 估算的 token 数量
    """
    import re
    
    # 统计中文字符数量
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', prompt))
    
    # 统计英文单词数量
    english_words = len(re.findall(r'[a-zA-Z]+', prompt))
    
    # 统计标点符号数量
    punctuation = len(re.findall(r'[，。！？、；：""''（）【】《》\.,!?;:\'"()\[\]{}]', prompt))
    
    # 估算 token 数量
    token_count = int(
        chinese_chars * 1.5 +
        english_words * 1.3 +
        punctuation * 1.0
    )
    
    return token_count


# ==================== 辅助函数 ====================

def _format_meeting_time(
    start_time: Optional[str],
    end_time: Optional[str],
    date: Optional[str]
) -> str:
    """格式化会议时间"""
    if not start_time and not end_time and not date:
        return "未记录"
    
    parts = []
    if date:
        parts.append(date)
    if start_time:
        parts.append(f"{start_time}")
    if end_time:
        parts.append(f"- {end_time}")
    
    return " ".join(parts)


def _format_duration(duration: Optional[int]) -> str:
    """格式化会议时长"""
    if duration is None:
        return "未记录"
    
    if duration < 60:
        return f"{duration} 分钟"
    else:
        hours = duration // 60
        minutes = duration % 60
        if minutes == 0:
            return f"{hours} 小时"
        else:
            return f"{hours} 小时 {minutes} 分钟"


def _format_validation_results(validation_results: List[ValidationResult]) -> str:
    """格式化校验结果"""
    if not validation_results:
        return "✅ 未发现问题"
    
    # 按严重程度分组
    errors = [r for r in validation_results if not r.is_valid and r.severity == RuleSeverity.ERROR]
    warnings = [r for r in validation_results if not r.is_valid and r.severity == RuleSeverity.WARNING]
    infos = [r for r in validation_results if not r.is_valid and r.severity == RuleSeverity.INFO]
    
    result_lines = []
    
    # 错误
    if errors:
        result_lines.append("### ❌ 错误（必须修复）")
        for idx, error in enumerate(errors, 1):
            result_lines.append(
                f"{idx}. **{error.field}**: {error.error_msg}"
            )
            if error.original_value is not None:
                result_lines.append(f"   - 当前值: `{error.original_value}`")
            if error.expected_value is not None:
                result_lines.append(f"   - 期望值: `{error.expected_value}`")
            if error.suggestion:
                result_lines.append(f"   - 建议: {error.suggestion}")
        result_lines.append("")
    
    # 警告
    if warnings:
        result_lines.append("### ⚠️ 警告（建议修复）")
        for idx, warning in enumerate(warnings, 1):
            result_lines.append(
                f"{idx}. **{warning.field}**: {warning.error_msg}"
            )
            if warning.suggestion:
                result_lines.append(f"   - 建议: {warning.suggestion}")
        result_lines.append("")
    
    # 信息
    if infos:
        result_lines.append("### ℹ️ 信息提示")
        for idx, info in enumerate(infos, 1):
            result_lines.append(
                f"{idx}. **{info.field}**: {info.error_msg}"
            )
        result_lines.append("")
    
    # 统计
    result_lines.append(f"**统计**: 共 {len(errors)} 个错误，{len(warnings)} 个警告，{len(infos)} 个提示")
    
    return "\n".join(result_lines)


def _build_meeting_content(meeting_record: MeetingRecord) -> str:
    """构建会议内容摘要"""
    lines = []
    
    # 基本信息
    if meeting_record.meeting_date:
        lines.append(f"**日期**: {meeting_record.meeting_date}")
    
    if meeting_record.meeting_time_start or meeting_record.meeting_time_end:
        time_str = _format_meeting_time(
            meeting_record.meeting_time_start,
            meeting_record.meeting_time_end,
            None
        )
        lines.append(f"**时间**: {time_str}")
    
    if meeting_record.meeting_duration is not None:
        lines.append(f"**时长**: {_format_duration(meeting_record.meeting_duration)}")
    
    if meeting_record.place:
        lines.append(f"**地点**: {meeting_record.place}")
    
    if meeting_record.meeting_topic:
        lines.append(f"**主题**: {meeting_record.meeting_topic}")
    
    # 人员信息
    lines.append("")
    lines.append("**人员信息**:")
    if meeting_record.host:
        lines.append(f"- 主持人: {meeting_record.host}")
    if meeting_record.recorder:
        lines.append(f"- 记录人: {meeting_record.recorder}")
    if meeting_record.attendees_expected is not None or meeting_record.attendees_actual is not None:
        lines.append(
            f"- 参会情况: 应到 {meeting_record.attendees_expected or '?'} 人，"
            f"实到 {meeting_record.attendees_actual or '?'} 人"
        )
    if meeting_record.absent_reason:
        lines.append(f"- 缺席原因: {meeting_record.absent_reason}")
    
    if meeting_record.attendees_list:
        lines.append(f"- 参会人员: {', '.join(meeting_record.attendees_list)}")
    
    # 正文内容
    if meeting_record.content_body:
        lines.append("")
        lines.append("**会议内容**:")
        lines.append(meeting_record.content_body)
    
    return "\n".join(lines)


# ==================== 导出函数 ====================

__all__ = [
    "build_compliance_prompt",
    "estimate_token_count",
    "COMPLIANCE_CHECK_PROMPT_TEMPLATE",
    "SIMPLE_COMPLIANCE_CHECK_PROMPT_TEMPLATE",
    "STRICT_COMPLIANCE_CHECK_PROMPT_TEMPLATE",
]
