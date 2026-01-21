#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : __init__.py
@Author  : caixiongjiang
@Date    : 2026/1/21
@Function: 
    路由注册中心 - 统一管理所有路由
@Modify History:
    2026/1/21 - 重构路由结构，分离通用服务和业务应用
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from fastapi import APIRouter
from api.routes.common import router as common_router

# 创建主路由
router = APIRouter()

# 注册通用服务路由（不添加额外标签，使用子路由自己的标签）
router.include_router(common_router)

# TODO: 注册业务应用路由
# from api.routes.apps import router as apps_router
# router.include_router(apps_router)

__all__ = ["router"]
