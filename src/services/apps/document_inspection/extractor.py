#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : extractor.py
@Author  : caixiongjiang
@Date    : 2026/1/22
@Function: 
    数据提取器（Data Extractor）
    
    功能：
    - 从 MinerU 解析结果中提取会议纪要字段
    - 使用正则表达式匹配关键信息
    - 支持多种格式变体
    - 处理 Markdown 和 JSON 两种输入格式
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

import re
from typing import Dict, Any, Optional, Tuple, List
from loguru import logger

from src.services.apps.document_inspection.schemas import MeetingRecord


class DataExtractor:
    """
    数据提取器（基于正则表达式）
    
    从 MinerU 的解析结果中提取会议纪要的标准化字段
    """
    
    def __init__(self, extraction_rules: Optional[Dict[str, Any]] = None):
        """
        初始化数据提取器
        
        Args:
            extraction_rules: 自定义提取规则（可选）
        """
        self.extraction_rules = extraction_rules or self._get_default_rules()
    
    @staticmethod
    def _get_default_rules() -> Dict[str, Any]:
        """
        获取默认提取规则
        
        Returns:
            Dict[str, Any]: 默认规则字典
        """
        return {
            # 时间相关
            "meeting_date": [
                r"(?:会议日期|日期|时间)[：:]\s*(\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)",
                r"(\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)\s*(?:会议|纪要)",
            ],
            "meeting_time_start": [
                r"(?:开始时间|起始时间)[：:]\s*(\d{1,2}:\d{2})",
                r"(?:会议时间|时间)[：:]\s*(\d{1,2}:\d{2})\s*[-~至到]",
            ],
            "meeting_time_end": [
                r"(?:结束时间|终止时间)[：:]\s*(\d{1,2}:\d{2})",
                r"[-~至到]\s*(\d{1,2}:\d{2})",
            ],
            "meeting_duration": [
                r"(?:会议时长|时长|历时)[：:]\s*(\d+)\s*(?:分钟|分)",
                r"(?:会议时长|时长|历时)[：:]\s*(\d+\.?\d*)\s*(?:小时|时)",
            ],
            
            # 人员相关
            "attendees_expected": [
                r"(?:应到|应参加)[：:]\s*(\d+)\s*人",
                r"应到\s*(\d+)",
            ],
            "attendees_actual": [
                r"(?:实到|实际参加|实际到会)[：:]\s*(\d+)\s*人",
                r"实到\s*(\d+)",
            ],
            "absent_reason": [
                r"(?:缺席原因|请假|缺席)[：:]\s*(.+?)(?:\n|$)",
                r"(?:未到|缺席)[：:]\s*(.+?)(?:\n|$)",
            ],
            "host": [
                r"(?:主持人|主持)[：:]\s*([^\n]+)",
                r"(?:会议主持|主持人)[：:]\s*([^\n]+)",
            ],
            "recorder": [
                r"(?:记录人|记录|记录员)[：:]\s*([^\n]+)",
                r"(?:会议记录|记录人)[：:]\s*([^\n]+)",
            ],
            "place": [
                r"(?:会议地点|地点|会议室)[：:]\s*([^\n]+)",
                r"(?:地点|会议地点)[：:]\s*([^\n]+)",
            ],
            "meeting_topic": [
                r"(?:会议主题|主题|议题)[：:]\s*([^\n]+)",
                r"(?:关于|主题)[：:]\s*([^\n]+)",
            ],
        }
    
    def extract_from_markdown(self, markdown: str) -> MeetingRecord:
        """
        从 Markdown 文本中提取会议纪要
        
        Args:
            markdown: MinerU 解析的 Markdown 文本
        
        Returns:
            MeetingRecord: 提取的会议纪要数据
        """
        logger.info("开始从 Markdown 提取会议纪要数据")
        
        extracted_data = {}
        
        # 提取各个字段
        extracted_data["meeting_date"] = self._extract_field(
            markdown, "meeting_date"
        )
        extracted_data["meeting_time_start"] = self._extract_field(
            markdown, "meeting_time_start"
        )
        extracted_data["meeting_time_end"] = self._extract_field(
            markdown, "meeting_time_end"
        )
        
        # 提取时长（可能是分钟或小时）
        duration_str = self._extract_field(markdown, "meeting_duration")
        extracted_data["meeting_duration"] = self._parse_duration(duration_str)
        
        # 提取人员信息
        extracted_data["attendees_expected"] = self._extract_int_field(
            markdown, "attendees_expected"
        )
        extracted_data["attendees_actual"] = self._extract_int_field(
            markdown, "attendees_actual"
        )
        extracted_data["absent_reason"] = self._extract_field(
            markdown, "absent_reason"
        )
        
        # 提取参会人员列表
        extracted_data["attendees_list"] = self._extract_attendees_list(markdown)
        
        # 提取元数据
        extracted_data["host"] = self._extract_field(markdown, "host")
        extracted_data["recorder"] = self._extract_field(markdown, "recorder")
        extracted_data["place"] = self._extract_field(markdown, "place")
        extracted_data["meeting_topic"] = self._extract_field(markdown, "meeting_topic")
        
        # 提取正文内容
        extracted_data["content_body"] = self._extract_content_body(markdown)
        
        # 保存原始数据（用于调试）
        extracted_data["raw_data"] = {"markdown_length": len(markdown)}
        
        logger.info(f"提取完成，提取到 {len([v for v in extracted_data.values() if v])} 个非空字段")
        
        return MeetingRecord(**extracted_data)
    
    def extract_from_json(self, json_data: Dict[str, Any]) -> MeetingRecord:
        """
        从 JSON 结构化数据中提取会议纪要
        
        Args:
            json_data: MinerU 解析的 JSON 数据
        
        Returns:
            MeetingRecord: 提取的会议纪要数据
        """
        logger.info("开始从 JSON 提取会议纪要数据")
        
        # 如果 JSON 中已经是结构化的会议纪要数据，直接使用
        if "meeting_time_start" in json_data or "host" in json_data:
            logger.info("检测到结构化会议纪要数据，直接使用")
            return MeetingRecord(**json_data)
        
        # 否则，尝试从 JSON 的文本字段中提取
        text_content = self._extract_text_from_json(json_data)
        if text_content:
            return self.extract_from_markdown(text_content)
        
        logger.warning("JSON 数据中未找到可提取的文本内容")
        return MeetingRecord()
    
    def _extract_field(self, text: str, field_name: str) -> Optional[str]:
        """
        提取单个字段
        
        Args:
            text: 文本内容
            field_name: 字段名称
        
        Returns:
            Optional[str]: 提取的值，未找到则返回 None
        """
        patterns = self.extraction_rules.get(field_name, [])
        
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                logger.debug(f"提取字段 {field_name}: {value}")
                return value
        
        logger.debug(f"未找到字段: {field_name}")
        return None
    
    def _extract_int_field(self, text: str, field_name: str) -> Optional[int]:
        """
        提取整数字段
        
        Args:
            text: 文本内容
            field_name: 字段名称
        
        Returns:
            Optional[int]: 提取的整数值，未找到或转换失败则返回 None
        """
        value_str = self._extract_field(text, field_name)
        if value_str:
            try:
                return int(value_str)
            except ValueError:
                logger.warning(f"字段 {field_name} 无法转换为整数: {value_str}")
        return None
    
    def _parse_duration(self, duration_str: Optional[str]) -> Optional[int]:
        """
        解析时长字符串为分钟数
        
        Args:
            duration_str: 时长字符串（如 "90" 或 "1.5"）
        
        Returns:
            Optional[int]: 时长（分钟），解析失败则返回 None
        """
        if not duration_str:
            return None
        
        try:
            # 尝试直接转换为整数（假设单位是分钟）
            if "." not in duration_str:
                return int(duration_str)
            else:
                # 如果是小数，假设单位是小时
                hours = float(duration_str)
                return int(hours * 60)
        except ValueError:
            logger.warning(f"无法解析时长: {duration_str}")
            return None
    
    def _extract_attendees_list(self, text: str) -> Optional[List[str]]:
        """
        提取参会人员名单
        
        Args:
            text: 文本内容
        
        Returns:
            Optional[List[str]]: 参会人员列表
        """
        # 尝试匹配 "参会人员：张三、李四、王五" 格式
        patterns = [
            r"(?:参会人员|与会人员|出席人员)[：:]\s*([^\n]+)",
            r"(?:参加人员|参与人员)[：:]\s*([^\n]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                attendees_str = match.group(1).strip()
                # 分割人员名单（支持逗号、顿号、分号）
                attendees = re.split(r'[,，、;；]', attendees_str)
                attendees = [name.strip() for name in attendees if name.strip()]
                if attendees:
                    logger.debug(f"提取参会人员: {attendees}")
                    return attendees
        
        return None
    
    def _extract_content_body(self, text: str) -> Optional[str]:
        """
        提取会议正文内容
        
        策略：
        1. 查找 "会议内容" 或 "会议纪要" 等标题
        2. 提取标题后的所有内容
        3. 如果没有明确标题，提取文本的主要部分
        
        Args:
            text: 文本内容
        
        Returns:
            Optional[str]: 会议正文内容
        """
        # 尝试匹配明确的内容标题
        content_patterns = [
            r"(?:会议内容|会议纪要|纪要内容|会议记录)[：:]\s*\n([\s\S]+)",
            r"(?:一、|1\.|【)(?:会议内容|主要内容)(?:】|\))\s*\n([\s\S]+)",
        ]
        
        for pattern in content_patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                logger.debug(f"提取会议内容: {len(content)} 字符")
                return content
        
        # 如果没有明确标题，提取主要文本部分
        # 跳过前面的元数据部分，提取后面的内容
        lines = text.split('\n')
        content_lines = []
        start_extracting = False
        
        for line in lines:
            # 如果遇到长段落，开始提取
            if len(line.strip()) > 50:
                start_extracting = True
            
            if start_extracting:
                content_lines.append(line)
        
        if content_lines:
            content = '\n'.join(content_lines).strip()
            logger.debug(f"提取会议内容（自动识别）: {len(content)} 字符")
            return content
        
        logger.warning("未找到会议正文内容")
        return None
    
    def _extract_text_from_json(self, json_data: Dict[str, Any]) -> Optional[str]:
        """
        从 JSON 数据中提取文本内容
        
        Args:
            json_data: JSON 数据
        
        Returns:
            Optional[str]: 提取的文本内容
        """
        # 常见的文本字段名
        text_fields = ["text", "content", "markdown", "body", "data"]
        
        for field in text_fields:
            if field in json_data and isinstance(json_data[field], str):
                return json_data[field]
        
        # 如果是嵌套结构，递归查找
        for value in json_data.values():
            if isinstance(value, dict):
                text = self._extract_text_from_json(value)
                if text:
                    return text
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                for item in value:
                    text = self._extract_text_from_json(item)
                    if text:
                        return text
        
        return None
    
    def extract_time_range(
        self,
        start_time: Optional[str],
        end_time: Optional[str]
    ) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        """
        提取时间范围并计算时长
        
        Args:
            start_time: 开始时间（HH:MM）
            end_time: 结束时间（HH:MM）
        
        Returns:
            Tuple[Optional[str], Optional[str], Optional[int]]: 
                (开始时间, 结束时间, 时长分钟数)
        """
        if not start_time or not end_time:
            return start_time, end_time, None
        
        try:
            # 解析时间
            start_hour, start_minute = map(int, start_time.split(':'))
            end_hour, end_minute = map(int, end_time.split(':'))
            
            # 计算时长（分钟）
            start_minutes = start_hour * 60 + start_minute
            end_minutes = end_hour * 60 + end_minute
            
            # 处理跨天情况
            if end_minutes < start_minutes:
                end_minutes += 24 * 60
            
            duration = end_minutes - start_minutes
            
            logger.debug(f"计算时长: {start_time} - {end_time} = {duration} 分钟")
            return start_time, end_time, duration
            
        except Exception as e:
            logger.warning(f"计算时长失败: {e}")
            return start_time, end_time, None
    
    def extract_attendees(
        self,
        expected: Optional[int],
        actual: Optional[int],
        absent_reason: Optional[str]
    ) -> Tuple[Optional[int], Optional[int], Optional[str]]:
        """
        提取参会人员信息
        
        Args:
            expected: 应到人数
            actual: 实到人数
            absent_reason: 缺席原因
        
        Returns:
            Tuple[Optional[int], Optional[int], Optional[str]]: 
                (应到人数, 实到人数, 缺席原因)
        """
        # 验证人数逻辑
        if expected is not None and actual is not None:
            if actual > expected:
                logger.warning(f"实到人数({actual})大于应到人数({expected})，可能存在错误")
        
        return expected, actual, absent_reason


# ==================== 便捷函数 ====================

def extract_meeting_record_from_mineru_result(
    mineru_result: Dict[str, Any]
) -> MeetingRecord:
    """
    从 MinerU 解析结果中提取会议纪要
    
    Args:
        mineru_result: MinerU 解析结果（包含 markdown_content 或 struct_content）
    
    Returns:
        MeetingRecord: 提取的会议纪要数据
    """
    extractor = DataExtractor()
    
    # 优先使用 Markdown 内容
    if "markdown_content" in mineru_result and mineru_result["markdown_content"]:
        return extractor.extract_from_markdown(mineru_result["markdown_content"])
    
    # 其次使用结构化内容
    if "struct_content" in mineru_result and mineru_result["struct_content"]:
        return extractor.extract_from_json(mineru_result["struct_content"])
    
    # 如果都没有，返回空记录
    logger.warning("MinerU 结果中未找到可提取的内容")
    return MeetingRecord()
