#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : service.py
@Author  : caixiongjiang
@Date    : 2026/1/22
@Function: 
    Document Inspection 业务服务层
    
    职责：
    - 编排整个文档检查流程
    - 协调各个组件（Extractor、Validator、PromptBuilder）
    - 管理检查结果的保存和查询
    - 生成提示词
    
    注意：
    - 暂时使用同步执行（不使用 Redis 任务队列）
    - 等 Redis 开发完成后再添加异步任务支持
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

import uuid
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger

from src.services.mineru.service import MinerUService
from src.services.storage.service import FileStorageService
from src.services.apps.document_inspection.extractor import DataExtractor
from src.services.apps.document_inspection.validator import RuleValidator
from src.services.apps.document_inspection.config_manager import DocumentConfigManager
from db.mysql.repositories.apps.document_inspection_repository import (
    DocumentInspectionRepository
)
from src.services.apps.document_inspection.schemas import (
    MeetingRecord,
    ValidationResult,
    CheckRequest,
    CheckResponse,
    CheckResultResponse,
    ExportPromptRequest,
    ExportPromptResponse,
    CheckHistoryItem,
    CheckHistoryResponse,
    CheckStatus,
    RuleSeverity,
)
from src.agents.document_compliance.prompts import (
    build_compliance_prompt,
    estimate_token_count,
)


class DocumentInspectionService:
    """
    Document Inspection 业务服务
    
    编排文档检查的完整流程
    """
    
    def __init__(
        self,
        mineru_service: MinerUService,
        storage_service: FileStorageService,
        config_manager: DocumentConfigManager,
        db_repository: DocumentInspectionRepository,
    ):
        """
        初始化业务服务
        
        Args:
            mineru_service: MinerU 解析服务
            storage_service: 文件存储服务
            config_manager: 配置管理器
            db_repository: 数据库访问层
        """
        self.mineru_service = mineru_service
        self.storage_service = storage_service
        self.config_manager = config_manager
        self.db_repository = db_repository
        
        # 初始化数据提取器
        self.extractor = DataExtractor()
        
        logger.info("Document Inspection Service 初始化完成")
    
    async def check_document(
        self,
        request: CheckRequest,
        user_id: str
    ) -> CheckResponse:
        """
        执行文档检查（同步版本，用户级规则）
        
        流程：
        1. 验证文件是否存在
        2. 调用 MinerU 解析文档
        3. 提取会议纪要数据
        4. 获取用户的规则配置
        5. 执行规则校验
        6. 保存检查结果到数据库
        7. 返回完整结果
        
        Args:
            request: 检查请求
            user_id: 用户ID（用于加载用户的规则配置）
        
        Returns:
            CheckResponse: 检查响应（包含完整结果）
        """
        check_id = self._generate_check_id()
        start_time = time.time()
        
        logger.info(f"开始文档检查: check_id={check_id}, file_id={request.file_id}")
        
        try:
            # 1. 验证文件是否存在
            file_info = self.storage_service.get_file_info(request.file_id)
            if not file_info:
                raise FileNotFoundError(f"文件不存在: {request.file_id}")
            
            # 2. 验证文件所有权（安全检查）
            if file_info.user_id and file_info.user_id != user_id:
                raise PermissionError(f"无权访问该文件: {request.file_id}")
            
            logger.info(f"文件信息: {file_info.original_filename}")
            
            # 3. 调用 MinerU 解析文档
            logger.info("开始解析文档...")
            # 获取文件路径（使用公开接口）
            file_path, mime_type, _ = self.storage_service.get_file_stream(request.file_id)
            
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            
            parse_result = await self.mineru_service.parse_document(
                file_bytes=file_bytes,
                file_name=file_info.original_filename,
                auto_pagination=True
            )
            
            logger.info(f"文档解析完成: {parse_result.pages} 页")
            
            # 4. 提取会议纪要数据
            logger.info("开始提取会议纪要数据...")
            meeting_record = self.extractor.extract_from_markdown(
                parse_result.markdown_content
            )
            
            logger.info("会议纪要数据提取完成")
            
            # 5. 获取用户的规则配置
            logger.info(f"获取用户 {user_id} 的规则配置...")
            rules = self.config_manager.get_all_rules(
                user_id=user_id,
                enabled_only=True
            )
            
            logger.info(f"加载用户 {user_id} 的 {len(rules)} 条规则")
            
            # 6. 执行规则校验
            logger.info("开始规则校验...")
            validator = RuleValidator(rules)
            validation_results = validator.validate(meeting_record)
            
            # 统计结果
            error_count = sum(
                1 for r in validation_results 
                if not r.is_valid and r.severity == RuleSeverity.ERROR
            )
            warning_count = sum(
                1 for r in validation_results 
                if not r.is_valid and r.severity == RuleSeverity.WARNING
            )
            is_compliant = (error_count == 0)
            
            logger.info(f"校验完成: {error_count} 个错误, {warning_count} 个警告")
            
            # 7. 保存检查结果到数据库
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            check_data = {
                "check_id": check_id,
                "file_id": request.file_id,
                "check_time": datetime.now(),
                "status": CheckStatus.COMPLETED,
                "meeting_record": meeting_record.model_dump(),
                "validation_results": [r.model_dump() for r in validation_results],
                "coordinates": parse_result.coordinates,
                "error_count": error_count,
                "warning_count": warning_count,
                "is_compliant": is_compliant,
                "processing_time_ms": processing_time_ms,
                "user_id": user_id,  # 修复：使用方法参数中的 user_id
                "session_id": request.session_id,
                "original_filename": file_info.original_filename,
            }
            
            self.db_repository.save_check_result(check_data)
            
            logger.info(f"检查结果已保存: check_id={check_id}")
            
            # 8. 返回完整结果
            return CheckResponse(
                check_id=check_id,
                file_id=request.file_id,
                status=CheckStatus.COMPLETED,
                message="检查完成",
                meeting_record=meeting_record,
                validation_results=validation_results,
                error_count=error_count,
                warning_count=warning_count,
                is_compliant=is_compliant,
                coordinates=parse_result.coordinates,
                check_time=datetime.now(),
                processing_time_ms=processing_time_ms,
            )
            
        except FileNotFoundError as e:
            logger.error(f"文件不存在: {e}")
            
            # 保存失败记录
            self._save_failed_check(
                check_id=check_id,
                file_id=request.file_id,
                error_message=str(e),
                user_id=user_id,  # 修复：使用方法参数中的 user_id
                session_id=request.session_id,
            )
            
            return CheckResponse(
                check_id=check_id,
                file_id=request.file_id,
                status=CheckStatus.FAILED,
                message=f"文件不存在: {str(e)}",
            )
            
        except Exception as e:
            logger.error(f"文档检查失败: {e}", exc_info=True)
            
            # 保存失败记录
            self._save_failed_check(
                check_id=check_id,
                file_id=request.file_id,
                error_message=str(e),
                user_id=user_id,  # 修复：使用方法参数中的 user_id
                session_id=request.session_id,
            )
            
            return CheckResponse(
                check_id=check_id,
                file_id=request.file_id,
                status=CheckStatus.FAILED,
                message=f"检查失败: {str(e)}",
            )
    
    def get_check_result(self, check_id: str) -> Optional[CheckResultResponse]:
        """
        获取检查结果详情
        
        Args:
            check_id: 检查任务ID
        
        Returns:
            Optional[CheckResultResponse]: 检查结果，不存在则返回 None
        """
        try:
            check = self.db_repository.get_check_by_id(check_id)
            
            if not check:
                logger.warning(f"检查记录不存在: {check_id}")
                return None
            
            # 转换为响应模型
            return CheckResultResponse(
                check_id=check.check_id,
                file_id=check.file_id,
                status=CheckStatus(check.status.value),
                meeting_record=MeetingRecord(**check.meeting_record),
                validation_results=[
                    ValidationResult(**r) for r in check.validation_results
                ],
                error_count=check.error_count,
                warning_count=check.warning_count,
                is_compliant=check.is_compliant,
                coordinates=check.coordinates,
                check_time=check.check_time,
                user_id=check.user_id,
                session_id=check.session_id,
                original_filename=check.original_filename,
            )
            
        except Exception as e:
            logger.error(f"获取检查结果失败 ({check_id}): {e}")
            raise
    
    def export_prompt(
        self,
        request: ExportPromptRequest
    ) -> Optional[ExportPromptResponse]:
        """
        导出 AI 提示词
        
        Args:
            request: 导出提示词请求
        
        Returns:
            Optional[ExportPromptResponse]: 提示词响应，检查记录不存在则返回 None
        """
        try:
            # 获取检查结果
            check = self.db_repository.get_check_by_id(request.check_id)
            
            if not check:
                logger.warning(f"检查记录不存在: {request.check_id}")
                return None
            
            # 转换为模型
            meeting_record = MeetingRecord(**check.meeting_record)
            validation_results = [
                ValidationResult(**r) for r in check.validation_results
            ]
            
            # 构建提示词
            prompt = build_compliance_prompt(
                meeting_record=meeting_record,
                validation_results=validation_results,
                template_name=request.template_name,
                include_raw_data=request.include_raw_data,
            )
            
            # 估算 token 数量
            token_count = estimate_token_count(prompt)
            
            logger.info(f"导出提示词成功: check_id={request.check_id}, tokens={token_count}")
            
            return ExportPromptResponse(
                check_id=request.check_id,
                prompt=prompt,
                token_count=token_count,
                template_name=request.template_name,
                generated_at=datetime.now(),
            )
            
        except Exception as e:
            logger.error(f"导出提示词失败 ({request.check_id}): {e}")
            raise
    
    def get_history(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        file_id: Optional[str] = None,
        status: Optional[str] = None,
        is_compliant: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> CheckHistoryResponse:
        """
        查询检查历史记录
        
        Args:
            user_id: 用户ID过滤（可选）
            session_id: 会话ID过滤（可选）
            file_id: 文件ID过滤（可选）
            status: 状态过滤（可选）
            is_compliant: 合规性过滤（可选）
            limit: 每页数量
            offset: 偏移量
        
        Returns:
            CheckHistoryResponse: 历史记录列表响应
        """
        try:
            # 查询记录
            checks = self.db_repository.list_checks(
                user_id=user_id,
                session_id=session_id,
                file_id=file_id,
                status=status,
                is_compliant=is_compliant,
                limit=limit,
                offset=offset,
            )
            
            # 统计总数
            total_count = self.db_repository.count_checks(
                user_id=user_id,
                session_id=session_id,
                file_id=file_id,
                status=status,
                is_compliant=is_compliant,
            )
            
            # 转换为响应模型
            items = [
                CheckHistoryItem(
                    check_id=check.check_id,
                    file_id=check.file_id,
                    original_filename=check.original_filename,
                    status=CheckStatus(check.status.value),
                    is_compliant=check.is_compliant,
                    error_count=check.error_count,
                    warning_count=check.warning_count,
                    check_time=check.check_time,
                    user_id=check.user_id,
                )
                for check in checks
            ]
            
            logger.info(f"查询历史记录: {len(items)}/{total_count}")
            
            return CheckHistoryResponse(
                total_count=total_count,
                items=items,
                limit=limit,
                offset=offset,
            )
            
        except Exception as e:
            logger.error(f"查询历史记录失败: {e}")
            raise
    
    # ==================== 辅助方法 ====================
    
    def _generate_check_id(self) -> str:
        """生成检查任务ID"""
        return f"check_{uuid.uuid4().hex[:16]}"
    
    def _save_failed_check(
        self,
        check_id: str,
        file_id: str,
        error_message: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """保存失败的检查记录"""
        try:
            check_data = {
                "check_id": check_id,
                "file_id": file_id,
                "check_time": datetime.now(),
                "status": CheckStatus.FAILED,
                "error_message": error_message,
                "error_count": 0,
                "warning_count": 0,
                "is_compliant": False,
                "user_id": user_id,
                "session_id": session_id,
            }
            
            self.db_repository.save_check_result(check_data)
            logger.info(f"保存失败记录: check_id={check_id}")
            
        except Exception as e:
            logger.error(f"保存失败记录失败: {e}")
