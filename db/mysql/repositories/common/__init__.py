#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : __init__.py
@Author  : caixiongjiang
@Date    : 2026/1/21
@Function: 
    通用服务 Repository 导出
@Modify History:
    2026/1/21 - 初始版本
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from db.mysql.repositories.common.file_storage_repository import FileStorageRepository

__all__ = [
    "FileStorageRepository",
]
