#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : __init__.py
@Author  : caixiongjiang
@Date    : 2026/1/21
@Function: 
    通用服务路由模块 - 统一管理所有通用服务路由和前缀
@Modify History:
    2026/1/21 - 创建通用服务路由模块，统一管理路由前缀
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from fastapi import APIRouter
from api.routes.common.mineru import router as mineru_router
from api.routes.common.storage import router as storage_router

# 创建通用服务的主路由（统一前缀）
router = APIRouter(prefix="/api/v1/common")

# 注册各个通用服务路由（每个子模块添加自己的前缀）
router.include_router(mineru_router, prefix="/mineru")
router.include_router(storage_router, prefix="/storage")

# 后续添加其他通用服务示例：
# from api.routes.common.translation import router as translation_router
# router.include_router(translation_router, prefix="/translation")

# 导出所有路由
__all__ = ["router", "mineru_router", "storage_router"]
