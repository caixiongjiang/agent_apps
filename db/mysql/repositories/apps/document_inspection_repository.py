#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : document_inspection_repository.py
@Author  : caixiongjiang
@Date    : 2026/1/22
@Function: 
    Document Inspection 数据访问层（Repository 模式）
    
    职责：
    - 封装所有数据库操作
    - 提供规则配置 CRUD 接口
    - 提供检查历史记录 CRUD 接口
    - 管理事务和会话
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from typing import List, Optional, Dict, Any
from sqlalchemy import and_, or_, desc
from sqlalchemy.orm import Session
from loguru import logger

from db.mysql.connection.base import BaseMySQLManager
from db.mysql.models.apps.document_inspection import (
    RuleConfig,
    CheckHistory,
    RuleCategoryEnum,
    CheckStatusEnum,
)


class DocumentInspectionRepository:
    """
    Document Inspection 数据访问层
    
    使用 Repository 模式封装数据库操作
    """
    
    def __init__(self, db_manager: BaseMySQLManager):
        """
        初始化 Repository
        
        Args:
            db_manager: 数据库连接管理器
        """
        self.db_manager = db_manager
    
    # ==================== 规则配置操作（用户级隔离）====================
    
    def get_all_rules(
        self,
        user_id: str,
        enabled_only: bool = True,
        category: Optional[str] = None,
        group_name: Optional[str] = None,
        order_by_display: bool = True
    ) -> List[RuleConfig]:
        """
        获取用户的规则配置列表
        
        Args:
            user_id: 用户ID（必需，用户级隔离）
            enabled_only: 是否只返回启用的规则
            category: 规则类别过滤（可选）
            group_name: 规则分组过滤（可选）
            order_by_display: 是否按显示顺序排序
        
        Returns:
            List[RuleConfig]: 规则配置列表
        """
        try:
            with self.db_manager.get_session() as session:
                query = session.query(RuleConfig).filter(
                    RuleConfig.user_id == user_id
                )
                
                # 过滤条件
                if enabled_only:
                    query = query.filter(RuleConfig.enabled == True)
                
                if category:
                    try:
                        category_enum = RuleCategoryEnum[category.upper()]
                        query = query.filter(RuleConfig.category == category_enum)
                    except KeyError:
                        logger.warning(f"无效的规则类别: {category}")
                
                if group_name:
                    query = query.filter(RuleConfig.group_name == group_name)
                
                # 排序
                if order_by_display:
                    query = query.order_by(
                        RuleConfig.group_name,
                        RuleConfig.display_order,
                        RuleConfig.id
                    )
                else:
                    query = query.order_by(RuleConfig.id)
                
                rules = query.all()
                logger.info(f"查询到用户 {user_id} 的 {len(rules)} 条规则配置")
                return rules
                
        except Exception as e:
            logger.error(f"查询规则配置失败 (user_id={user_id}): {e}")
            raise
    
    def get_rule_by_id(self, rule_id: str, user_id: Optional[str] = None) -> Optional[RuleConfig]:
        """
        根据 rule_id 获取规则配置
        
        Args:
            rule_id: 规则ID
            user_id: 用户ID（可选，用于权限校验）
        
        Returns:
            Optional[RuleConfig]: 规则配置对象，不存在则返回 None
        """
        try:
            with self.db_manager.get_session() as session:
                query = session.query(RuleConfig).filter(
                    RuleConfig.rule_id == rule_id
                )
                
                # 如果提供了 user_id，确保规则属于该用户
                if user_id:
                    query = query.filter(RuleConfig.user_id == user_id)
                
                rule = query.first()
                
                if rule:
                    logger.debug(f"找到规则: {rule_id}")
                else:
                    logger.debug(f"规则不存在: {rule_id}")
                
                return rule
                
        except Exception as e:
            logger.error(f"查询规则失败 ({rule_id}): {e}")
            raise
    
    def create_rule(self, user_id: str, rule_data: Dict[str, Any]) -> RuleConfig:
        """
        创建用户规则配置
        
        Args:
            user_id: 用户ID（规则归属）
            rule_data: 规则数据字典
        
        Returns:
            RuleConfig: 创建的规则对象
        
        Raises:
            ValueError: 如果 rule_id 已存在或 user_id 缺失
        """
        try:
            if not user_id:
                raise ValueError("user_id 不能为空")
            
            with self.db_manager.get_session() as session:
                # 检查 rule_id 是否已存在
                existing = session.query(RuleConfig).filter(
                    RuleConfig.rule_id == rule_data.get("rule_id")
                ).first()
                
                if existing:
                    raise ValueError(f"规则ID已存在: {rule_data.get('rule_id')}")
                
                # 确保 user_id 存在
                rule_data["user_id"] = user_id
                
                # 转换枚举类型
                if "category" in rule_data and isinstance(rule_data["category"], str):
                    rule_data["category"] = RuleCategoryEnum[rule_data["category"].upper()]
                
                if "severity" in rule_data and isinstance(rule_data["severity"], str):
                    from db.mysql.models.apps.document_inspection import RuleSeverityEnum
                    rule_data["severity"] = RuleSeverityEnum[rule_data["severity"].upper()]
                
                # 创建规则对象
                rule = RuleConfig(**rule_data)
                session.add(rule)
                session.commit()
                session.refresh(rule)
                
                logger.info(f"用户 {user_id} 创建规则成功: {rule.rule_id}")
                return rule
                
        except ValueError as e:
            logger.error(f"创建规则失败: {e}")
            raise
        except Exception as e:
            logger.error(f"创建规则失败: {e}")
            raise
    
    def update_rule(
        self,
        rule_id: str,
        updates: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Optional[RuleConfig]:
        """
        更新规则配置
        
        Args:
            rule_id: 规则ID
            updates: 更新的字段字典
            user_id: 用户ID（可选，用于权限校验）
        
        Returns:
            Optional[RuleConfig]: 更新后的规则对象，不存在则返回 None
        
        Raises:
            ValueError: 如果规则不属于该用户
        """
        try:
            with self.db_manager.get_session() as session:
                query = session.query(RuleConfig).filter(
                    RuleConfig.rule_id == rule_id
                )
                
                # 如果提供了 user_id，确保规则属于该用户
                if user_id:
                    query = query.filter(RuleConfig.user_id == user_id)
                
                rule = query.first()
                
                if not rule:
                    logger.warning(f"规则不存在或无权限: {rule_id}")
                    return None
                
                # 转换枚举类型
                if "severity" in updates and isinstance(updates["severity"], str):
                    from db.mysql.models.apps.document_inspection import RuleSeverityEnum
                    updates["severity"] = RuleSeverityEnum[updates["severity"].upper()]
                
                # 更新字段（保护字段不可更新）
                protected_fields = ["id", "rule_id", "user_id", "created_at"]
                for key, value in updates.items():
                    if hasattr(rule, key) and key not in protected_fields:
                        setattr(rule, key, value)
                
                session.commit()
                session.refresh(rule)
                
                logger.info(f"更新规则成功: {rule_id}")
                return rule
                
        except ValueError as e:
            logger.error(f"更新规则失败: {e}")
            raise
        except Exception as e:
            logger.error(f"更新规则失败 ({rule_id}): {e}")
            raise
    
    def delete_rule(self, rule_id: str, user_id: Optional[str] = None) -> bool:
        """
        删除规则配置
        
        Args:
            rule_id: 规则ID
            user_id: 用户ID（可选，用于权限校验）
        
        Returns:
            bool: 是否删除成功
        """
        try:
            with self.db_manager.get_session() as session:
                query = session.query(RuleConfig).filter(
                    RuleConfig.rule_id == rule_id
                )
                
                # 如果提供了 user_id，确保规则属于该用户
                if user_id:
                    query = query.filter(RuleConfig.user_id == user_id)
                
                rule = query.first()
                
                if not rule:
                    logger.warning(f"规则不存在或无权限: {rule_id}")
                    return False
                
                session.delete(rule)
                session.commit()
                
                logger.info(f"删除规则成功: {rule_id}")
                return True
                
        except Exception as e:
            logger.error(f"删除规则失败 ({rule_id}): {e}")
            raise
    
    def batch_update_rules(
        self,
        updates: List[Dict[str, Any]],
        user_id: Optional[str] = None
    ) -> int:
        """
        批量更新规则配置
        
        Args:
            updates: 更新列表，每项包含 rule_id 和要更新的字段
            user_id: 用户ID（可选，用于权限校验）
        
        Returns:
            int: 成功更新的数量
        """
        success_count = 0
        
        try:
            for update_item in updates:
                rule_id = update_item.pop("rule_id", None)
                if not rule_id:
                    logger.warning("批量更新项缺少 rule_id，跳过")
                    continue
                
                try:
                    result = self.update_rule(rule_id, update_item, user_id)
                    if result:
                        success_count += 1
                except Exception as e:
                    logger.error(f"批量更新规则失败 ({rule_id}): {e}")
                    continue
            
            logger.info(f"批量更新完成: 成功 {success_count}/{len(updates)}")
            return success_count
            
        except Exception as e:
            logger.error(f"批量更新规则失败: {e}")
            raise
    
    def generate_rule_id(self, user_id: str = None, field_name: str = None) -> str:
        """
        生成用户级别的规则ID（使用 UUID 确保唯一性且长度固定）
        
        Args:
            user_id: 用户ID（保留参数兼容性，但不再使用）
            field_name: 字段名（保留参数兼容性，但不再使用）
        
        Returns:
            str: 生成的规则ID（格式: rule_{12位UUID}，例如: rule_a1b2c3d4e5f6）
        
        注意：
            - 旧格式: rule_{user_id}_{field_name}_{timestamp} (太长)
            - 新格式: rule_{uuid} (固定长度，约17个字符)
        """
        import uuid
        # 使用 UUID4 生成唯一ID，取前12位十六进制字符
        unique_id = uuid.uuid4().hex[:12]
        return f"rule_{unique_id}"
    
    # ==================== 检查历史记录操作 ====================
    
    def save_check_result(self, check_data: Dict[str, Any]) -> CheckHistory:
        """
        保存检查结果到数据库
        
        Args:
            check_data: 检查结果数据字典
        
        Returns:
            CheckHistory: 创建的检查历史对象
        """
        try:
            with self.db_manager.get_session() as session:
                # 转换枚举类型
                if "status" in check_data and isinstance(check_data["status"], str):
                    check_data["status"] = CheckStatusEnum[check_data["status"].upper()]
                
                # 创建检查历史对象
                check_history = CheckHistory(**check_data)
                session.add(check_history)
                session.commit()
                session.refresh(check_history)
                
                logger.info(f"保存检查结果成功: {check_history.check_id}")
                return check_history
                
        except Exception as e:
            logger.error(f"保存检查结果失败: {e}")
            raise
    
    def get_check_by_id(self, check_id: str) -> Optional[CheckHistory]:
        """
        根据 check_id 获取检查历史记录
        
        Args:
            check_id: 检查任务ID
        
        Returns:
            Optional[CheckHistory]: 检查历史对象，不存在则返回 None
        """
        try:
            with self.db_manager.get_session() as session:
                check = session.query(CheckHistory).filter(
                    CheckHistory.check_id == check_id
                ).first()
                
                if check:
                    logger.debug(f"找到检查记录: {check_id}")
                else:
                    logger.debug(f"检查记录不存在: {check_id}")
                
                return check
                
        except Exception as e:
            logger.error(f"查询检查记录失败 ({check_id}): {e}")
            raise
    
    def list_checks(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        file_id: Optional[str] = None,
        status: Optional[str] = None,
        is_compliant: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[CheckHistory]:
        """
        查询检查历史记录列表
        
        Args:
            user_id: 用户ID过滤（可选）
            session_id: 会话ID过滤（可选）
            file_id: 文件ID过滤（可选）
            status: 状态过滤（可选）
            is_compliant: 合规性过滤（可选）
            limit: 每页数量
            offset: 偏移量
        
        Returns:
            List[CheckHistory]: 检查历史记录列表
        """
        try:
            with self.db_manager.get_session() as session:
                query = session.query(CheckHistory)
                
                # 过滤条件
                if user_id:
                    query = query.filter(CheckHistory.user_id == user_id)
                
                if session_id:
                    query = query.filter(CheckHistory.session_id == session_id)
                
                if file_id:
                    query = query.filter(CheckHistory.file_id == file_id)
                
                if status:
                    try:
                        status_enum = CheckStatusEnum[status.upper()]
                        query = query.filter(CheckHistory.status == status_enum)
                    except KeyError:
                        logger.warning(f"无效的状态值: {status}")
                
                if is_compliant is not None:
                    query = query.filter(CheckHistory.is_compliant == is_compliant)
                
                # 排序（按检查时间倒序）
                query = query.order_by(desc(CheckHistory.check_time))
                
                # 分页
                query = query.limit(limit).offset(offset)
                
                checks = query.all()
                logger.info(f"查询到 {len(checks)} 条检查记录")
                return checks
                
        except Exception as e:
            logger.error(f"查询检查记录列表失败: {e}")
            raise
    
    def count_checks(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        file_id: Optional[str] = None,
        status: Optional[str] = None,
        is_compliant: Optional[bool] = None
    ) -> int:
        """
        统计检查记录数量
        
        Args:
            user_id: 用户ID过滤（可选）
            session_id: 会话ID过滤（可选）
            file_id: 文件ID过滤（可选）
            status: 状态过滤（可选）
            is_compliant: 合规性过滤（可选）
        
        Returns:
            int: 记录数量
        """
        try:
            with self.db_manager.get_session() as session:
                query = session.query(CheckHistory)
                
                # 过滤条件（与 list_checks 保持一致）
                if user_id:
                    query = query.filter(CheckHistory.user_id == user_id)
                
                if session_id:
                    query = query.filter(CheckHistory.session_id == session_id)
                
                if file_id:
                    query = query.filter(CheckHistory.file_id == file_id)
                
                if status:
                    try:
                        status_enum = CheckStatusEnum[status.upper()]
                        query = query.filter(CheckHistory.status == status_enum)
                    except KeyError:
                        logger.warning(f"无效的状态值: {status}")
                
                if is_compliant is not None:
                    query = query.filter(CheckHistory.is_compliant == is_compliant)
                
                count = query.count()
                return count
                
        except Exception as e:
            logger.error(f"统计检查记录失败: {e}")
            raise
    
    def delete_check(self, check_id: str) -> bool:
        """
        删除检查历史记录
        
        Args:
            check_id: 检查任务ID
        
        Returns:
            bool: 是否删除成功
        """
        try:
            with self.db_manager.get_session() as session:
                check = session.query(CheckHistory).filter(
                    CheckHistory.check_id == check_id
                ).first()
                
                if not check:
                    logger.warning(f"检查记录不存在: {check_id}")
                    return False
                
                session.delete(check)
                session.commit()
                
                logger.info(f"删除检查记录成功: {check_id}")
                return True
                
        except Exception as e:
            logger.error(f"删除检查记录失败 ({check_id}): {e}")
            raise
