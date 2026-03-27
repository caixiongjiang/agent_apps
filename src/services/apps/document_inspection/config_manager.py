#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : config_manager.py
@Author  : caixiongjiang
@Date    : 2026/1/22
@Function: 
    配置管理器（Document Inspection Config Manager）
    
    功能：
    - 管理规则配置（MySQL 持久化）
    - 管理会话配置（暂时返回空，等 Redis 开发后实现）
    - 合并有效配置（MySQL + Redis）
    
    注意：
    - 会话配置功能暂时不实现，等 Redis 开发完成后补充
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from typing import List, Optional, Dict, Any
from loguru import logger

from db.mysql.repositories.apps.document_inspection_repository import (
    DocumentInspectionRepository
)
from src.services.apps.document_inspection.schemas import (
    RuleConfigModel,
    CreateRuleRequest,
    UpdateRuleRequest,
)


class DocumentConfigManager:
    """
    Document Inspection 配置管理器（用户级隔离）
    
    职责：
    1. 规则配置 CRUD（MySQL，用户级隔离）
    2. 会话配置管理（暂时返回空，等 Redis 开发后实现）
    3. 有效配置合并（优先级：Redis > MySQL）
    """
    
    def __init__(self, db_repository: DocumentInspectionRepository):
        """
        初始化配置管理器
        
        Args:
            db_repository: 数据库访问层
        """
        self.db_repository = db_repository
        logger.info("配置管理器初始化完成")
    
    # ==================== 规则管理（MySQL，用户级隔离）====================
    
    def get_all_rules(
        self,
        user_id: str,
        enabled_only: bool = True,
        category: Optional[str] = None,
        group_name: Optional[str] = None
    ) -> List[RuleConfigModel]:
        """
        获取用户的规则配置列表
        
        Args:
            user_id: 用户ID（必需，用户级隔离）
            enabled_only: 是否只返回启用的规则
            category: 规则类别过滤（可选）
            group_name: 规则分组过滤（可选）
        
        Returns:
            List[RuleConfigModel]: 规则配置列表
        """
        try:
            rules = self.db_repository.get_all_rules(
                user_id=user_id,
                enabled_only=enabled_only,
                category=category,
                group_name=group_name,
                order_by_display=True
            )
            
            # 转换为 Pydantic 模型
            rule_models = [
                RuleConfigModel.model_validate(rule)
                for rule in rules
            ]
            
            logger.info(f"获取用户 {user_id} 的规则配置: {len(rule_models)} 条")
            return rule_models
            
        except Exception as e:
            logger.error(f"获取规则配置失败 (user_id={user_id}): {e}")
            raise
    
    def get_rule(self, rule_id: str, user_id: Optional[str] = None) -> Optional[RuleConfigModel]:
        """
        获取单个规则配置
        
        Args:
            rule_id: 规则ID
            user_id: 用户ID（可选，用于权限校验）
        
        Returns:
            Optional[RuleConfigModel]: 规则配置，不存在则返回 None
        """
        try:
            rule = self.db_repository.get_rule_by_id(rule_id, user_id)
            
            if rule:
                return RuleConfigModel.model_validate(rule)
            
            return None
            
        except Exception as e:
            logger.error(f"获取规则配置失败 ({rule_id}): {e}")
            raise
    
    def create_rule(self, user_id: str, rule_request: CreateRuleRequest) -> RuleConfigModel:
        """
        创建用户规则配置
        
        Args:
            user_id: 用户ID（规则归属）
            rule_request: 创建规则请求
        
        Returns:
            RuleConfigModel: 创建的规则配置
        
        Raises:
            ValueError: 如果 rule_id 已存在或 user_id 缺失
        """
        try:
            # 转换为字典
            rule_data = rule_request.model_dump()
            
            # 如果没有提供 rule_id，自动生成（使用 UUID）
            if not rule_data.get("rule_id"):
                rule_data["rule_id"] = self.db_repository.generate_rule_id()
            
            # 创建规则
            rule = self.db_repository.create_rule(user_id, rule_data)
            
            logger.info(f"用户 {user_id} 创建规则成功: {rule.rule_id}")
            return RuleConfigModel.model_validate(rule)
            
        except ValueError as e:
            logger.error(f"创建规则失败: {e}")
            raise
        except Exception as e:
            logger.error(f"创建规则失败: {e}")
            raise
    
    def update_rule(
        self,
        rule_id: str,
        update_request: UpdateRuleRequest,
        user_id: Optional[str] = None
    ) -> Optional[RuleConfigModel]:
        """
        更新用户规则配置
        
        Args:
            rule_id: 规则ID
            update_request: 更新规则请求
            user_id: 用户ID（可选，用于权限校验）
        
        Returns:
            Optional[RuleConfigModel]: 更新后的规则配置，不存在则返回 None
        
        Raises:
            ValueError: 如果规则不属于该用户
        """
        try:
            # 转换为字典，排除 None 值
            updates = update_request.model_dump(exclude_none=True)
            
            # 更新规则
            rule = self.db_repository.update_rule(
                rule_id=rule_id,
                updates=updates,
                user_id=user_id
            )
            
            if rule:
                logger.info(f"更新规则成功: {rule_id}")
                return RuleConfigModel.model_validate(rule)
            
            return None
            
        except ValueError as e:
            logger.error(f"更新规则失败: {e}")
            raise
        except Exception as e:
            logger.error(f"更新规则失败 ({rule_id}): {e}")
            raise
    
    def delete_rule(
        self,
        rule_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        删除用户规则配置
        
        Args:
            rule_id: 规则ID
            user_id: 用户ID（可选，用于权限校验）
        
        Returns:
            bool: 是否删除成功
        """
        try:
            success = self.db_repository.delete_rule(
                rule_id=rule_id,
                user_id=user_id
            )
            
            if success:
                logger.info(f"删除规则成功: {rule_id}")
            
            return success
            
        except ValueError as e:
            logger.error(f"删除规则失败: {e}")
            raise
        except Exception as e:
            logger.error(f"删除规则失败 ({rule_id}): {e}")
            raise
    
    def batch_update_rules(
        self,
        updates: List[Dict[str, Any]],
        allow_system: bool = False
    ) -> int:
        """
        批量更新规则配置
        
        Args:
            updates: 更新列表，每项包含 rule_id 和要更新的字段
            allow_system: 是否允许更新系统规则
        
        Returns:
            int: 成功更新的数量
        """
        try:
            success_count = self.db_repository.batch_update_rules(
                updates=updates,
                allow_system=allow_system
            )
            
            logger.info(f"批量更新规则: 成功 {success_count}/{len(updates)}")
            return success_count
            
        except Exception as e:
            logger.error(f"批量更新规则失败: {e}")
            raise
    
    # ==================== 会话配置（Redis）====================
    # 注意：以下方法暂时返回空或默认值，等 Redis 开发完成后实现
    
    def set_session_config(
        self,
        session_id: str,
        config: Dict[str, Any],
        ttl: int = 7200
    ) -> bool:
        """
        设置会话配置（暂未实现）
        
        Args:
            session_id: 会话ID
            config: 配置数据
            ttl: 过期时间（秒），默认 2 小时
        
        Returns:
            bool: 是否设置成功
        
        注意：
            暂时返回 False，等 Redis 开发完成后实现
        """
        logger.warning(f"会话配置功能暂未实现，session_id={session_id}")
        return False
    
    def get_session_config(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话配置（暂未实现）
        
        Args:
            session_id: 会话ID
        
        Returns:
            Dict[str, Any]: 会话配置，暂时返回空字典
        
        注意：
            暂时返回空字典，等 Redis 开发完成后实现
        """
        logger.debug(f"会话配置功能暂未实现，返回空配置，session_id={session_id}")
        return {}
    
    def clear_session_config(self, session_id: str) -> bool:
        """
        清除会话配置（暂未实现）
        
        Args:
            session_id: 会话ID
        
        Returns:
            bool: 是否清除成功
        
        注意：
            暂时返回 False，等 Redis 开发完成后实现
        """
        logger.warning(f"会话配置功能暂未实现，session_id={session_id}")
        return False
    
    # ==================== 有效配置合并 ====================
    
    def get_effective_config(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        enabled_only: bool = True
    ) -> Dict[str, Any]:
        """
        获取有效配置（合并 MySQL 和 Redis）
        
        优先级：Redis 会话配置 > MySQL 默认配置
        
        Args:
            user_id: 用户ID（必需）
            session_id: 会话ID（可选）
            enabled_only: 是否只返回启用的规则
        
        Returns:
            Dict[str, Any]: 有效配置
        
        注意：
            暂时只返回 MySQL 配置，等 Redis 开发完成后实现合并逻辑
        """
        try:
            # 获取 MySQL 规则配置（用户级别）
            rules = self.get_all_rules(user_id=user_id, enabled_only=enabled_only)
            
            # 获取会话配置（暂时返回空）
            session_config = {}
            if session_id:
                session_config = self.get_session_config(session_id)
            
            # 构建有效配置
            effective_config = {
                "rules": [rule.model_dump() for rule in rules],
                "session_config": session_config,
                "config_source": "mysql_only",  # 暂时只有 MySQL
            }
            
            logger.info(
                f"获取有效配置: {len(rules)} 条规则, "
                f"会话配置: {'是' if session_config else '否'}"
            )
            
            return effective_config
            
        except Exception as e:
            logger.error(f"获取有效配置失败: {e}")
            raise
    
    def get_enabled_rules_count(self, user_id: str) -> int:
        """
        获取启用的规则数量
        
        Args:
            user_id: 用户ID
        
        Returns:
            int: 启用的规则数量
        """
        try:
            rules = self.get_all_rules(user_id=user_id, enabled_only=True)
            return len(rules)
        except Exception as e:
            logger.error(f"获取启用规则数量失败: {e}")
            return 0
    
    def get_rules_by_category(self, user_id: str, category: str) -> List[RuleConfigModel]:
        """
        按类别获取规则配置
        
        Args:
            user_id: 用户ID
            category: 规则类别
        
        Returns:
            List[RuleConfigModel]: 规则配置列表
        """
        try:
            return self.get_all_rules(user_id=user_id, enabled_only=True, category=category)
        except Exception as e:
            logger.error(f"按类别获取规则失败 ({category}): {e}")
            return []


# ==================== 便捷函数 ====================

def create_config_manager(
    db_repository: DocumentInspectionRepository
) -> DocumentConfigManager:
    """
    创建配置管理器的便捷函数
    
    Args:
        db_repository: 数据库访问层
    
    Returns:
        DocumentConfigManager: 配置管理器实例
    """
    return DocumentConfigManager(db_repository)
