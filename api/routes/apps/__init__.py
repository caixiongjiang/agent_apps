#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : __init__.py
@Author  : caixiongjiang
@Date    : 2026/1/22
@Function: 
    业务应用路由模块 - 统一管理所有业务应用路由和前缀
@Modify History:
    2026/1/22 - 创建业务应用路由模块，统一管理路由前缀
    2026/1/23 - 重构路由结构，添加 /api/v1/apps 统一前缀
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from fastapi import APIRouter
from api.routes.apps.document_compliance import router as document_compliance_router

# 创建业务应用的主路由（统一前缀）
router = APIRouter(prefix="/api/v1/apps")

# 注册各个业务应用路由（每个子模块添加自己的前缀）
router.include_router(document_compliance_router, prefix="/document-compliance")

# 后续添加其他业务应用示例：
# from api.routes.apps.deep_research import router as deep_research_router
# router.include_router(deep_research_router, prefix="/deep-research")

# 导出所有路由
__all__ = ["router", "document_compliance_router"]
