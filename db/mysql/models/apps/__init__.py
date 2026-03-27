#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : __init__.py
@Author  : caixiongjiang
@Date    : 2026/1/22
@Function: 
    Apps 业务模块数据库模型
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from db.mysql.models.apps.document_inspection import (
    RuleConfig,
    CheckHistory,
)

__all__ = [
    "RuleConfig",
    "CheckHistory",
]
