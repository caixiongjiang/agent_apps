#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : __init__.py
@Author  : caixiongjiang
@Date    : 2026/1/22
@Function: 
    Apps 业务模块数据访问层
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from db.mysql.repositories.apps.document_inspection_repository import (
    DocumentInspectionRepository,
)

__all__ = [
    "DocumentInspectionRepository",
]
