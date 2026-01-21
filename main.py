#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : main.py
@Author  : caixiongjiang
@Date    : 2026/1/10 21:15
@Function: 
    FastAPI 应用入口
@Modify History:
         
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.utils.config_manager import get_config_manager
from src.utils.env_manager import get_env_manager
from api import routes

# 初始化配置管理器
config_manager = get_config_manager()
env_manager = get_env_manager()

# 获取应用配置
app_name = "Agent Apps"
app_version = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    mineru_config = config_manager.get_mineru_config()
    file_upload_config = config_manager.get_file_upload_config()
    
    logger.info(f"🚀 {app_name} v{app_version} 启动中...")
    logger.info(f"📝 API 文档: http://localhost:8000/docs")
    logger.info(f"🔧 MinerU 服务: {mineru_config.get('api_url', 'Not configured')}")
    logger.info(f"📑 MinerU 分页配置: 每次{mineru_config.get('max_pages_per_request', 10)}页, 并发{mineru_config.get('max_concurrent_requests', 3)}个")
    
    # 创建存储目录
    storage_path = Path(file_upload_config.get("temp_dir", "./uploads"))
    storage_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 文件存储路径: {storage_path}")
    
    # 配置健康检查
    if config_manager.check_health():
        logger.info("✅ 配置健康检查通过")
    else:
        logger.warning("⚠️  配置健康检查发现问题，请检查配置文件")
    
    yield  # 应用运行中
    
    # 关闭时执行
    logger.info(f"👋 {app_name} 正在关闭...")


# 创建 FastAPI 应用
app = FastAPI(
    title=app_name,
    version=app_version,
    description="Agent Apps - 智能助手应用平台",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan  # 使用生命周期管理器
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该配置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(routes.router)

# 健康检查
@app.get("/health", tags=["Health"])
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "app_name": app_name,
        "version": app_version,
        "config_status": "ok" if config_manager.check_health() else "warning"
    }

# 根路径
@app.get("/", tags=["Root"])
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用 {app_name}",
        "version": app_version,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    # 从环境变量获取启动配置
    app_env = env_manager.get_app_env()
    is_debug = env_manager.is_debug()
    
    logger.info(f"🌍 运行环境: {app_env}")
    logger.info(f"🐛 调试模式: {is_debug}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=is_debug,
        log_level="info"
    )
