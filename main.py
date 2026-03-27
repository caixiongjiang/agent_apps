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


def print_routes(app: FastAPI):
    """打印所有路由信息（分类展示）"""
    from collections import defaultdict
    from fastapi.routing import APIRoute
    
    # 获取配置信息
    mineru_config = config_manager.get_mineru_config()
    storage_config = config_manager.get_storage_config()
    
    # 收集所有路由
    routes_by_prefix = defaultdict(list)
    
    for route in app.routes:
        if isinstance(route, APIRoute):
            path = route.path
            methods = list(route.methods)
            name = route.name
            summary = route.summary or route.name
            
            # 跳过 OpenAPI 相关路由
            if path in ["/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"]:
                continue
            
            # 分类路由
            if path.startswith("/api/v1/common/mineru"):
                prefix = "common_mineru"
            elif path.startswith("/api/v1/common/storage"):
                prefix = "common_storage"
            elif path.startswith("/api/v1/apps/"):
                prefix = "apps"
            elif path in ["/", "/health"]:
                prefix = "system"
            else:
                prefix = "other"
            
            routes_by_prefix[prefix].append({
                "path": path,
                "methods": methods,
                "summary": summary
            })
    
    # 打印启动信息
    logger.info("=" * 80)
    logger.info(f"🚀 {app_name} v{app_version} 启动中...")
    logger.info("=" * 80)
    
    # API 文档
    logger.info(f"\n📝 API 文档:")
    logger.info(f"   - Swagger UI: http://localhost:8000/docs")
    logger.info(f"   - ReDoc:      http://localhost:8000/redoc")
    
    # 系统接口
    if "system" in routes_by_prefix:
        logger.info(f"\n🏠 系统接口:")
        for route in sorted(routes_by_prefix["system"], key=lambda x: x["path"]):
            methods_str = ", ".join(sorted(route["methods"]))
            logger.info(f"   - {methods_str:8} {route['path']:30} - {route['summary']}")
    
    # 通用服务接口
    logger.info(f"\n📦 通用服务接口 (Common Services):")
    
    # MinerU 服务
    if "common_mineru" in routes_by_prefix:
        logger.info(f"   ┌─ MinerU 文档解析服务 (/api/v1/common/mineru)")
        mineru_routes = sorted(routes_by_prefix["common_mineru"], key=lambda x: x["path"])
        for idx, route in enumerate(mineru_routes):
            methods_str = ", ".join(sorted(route["methods"]))
            path_short = route["path"].replace("/api/v1/common/mineru", "")
            is_last = (idx == len(mineru_routes) - 1)
            prefix = "   │  └─" if is_last else "   │  ├─"
            logger.info(f"{prefix} {methods_str:8} {path_short:20} - {route['summary']}")
        logger.info(f"   │  🔧 后端: {mineru_config.get('api_url', 'Not configured')}")
        logger.info(f"   │  📑 配置: 每批{mineru_config.get('max_pages_per_request', 10)}页, 并发{mineru_config.get('max_concurrent_requests', 3)}个请求")
        logger.info(f"   │")
    
    # Storage 服务
    if "common_storage" in routes_by_prefix:
        logger.info(f"   └─ Storage 文件存储服务 (/api/v1/common/storage)")
        storage_routes = sorted(routes_by_prefix["common_storage"], key=lambda x: x["path"])
        for idx, route in enumerate(storage_routes):
            methods_str = ", ".join(sorted(route["methods"]))
            path_short = route["path"].replace("/api/v1/common/storage", "")
            is_last = (idx == len(storage_routes) - 1)
            prefix = "      └─" if is_last else "      ├─"
            logger.info(f"{prefix} {methods_str:8} {path_short:20} - {route['summary']}")
        logger.info(f"      📁 存储路径: {storage_config.get('storage_root', './upload')}")
        logger.info(f"      🗂️  分类管理: temp(1h) / session(2h) / permanent")
        logger.info(f"      📊 文件限制: 单文件{storage_config.get('max_file_size_mb', 50)}MB, 批量{storage_config.get('max_batch_size', 10)}个")
    
    # 业务应用接口
    if "apps" in routes_by_prefix:
        logger.info(f"\n🎯 业务应用接口 (Business Apps):")
        logger.info(f"   └─ Document Compliance Agent (/api/v1/apps/document-compliance)")
        apps_routes = sorted(routes_by_prefix["apps"], key=lambda x: x["path"])
        for route in apps_routes:
            methods_str = ", ".join(sorted(route["methods"]))
            path_short = route["path"].replace("/api/v1/apps/document-compliance", "")
            logger.info(f"      ├─ {methods_str:8} {path_short:20} - {route['summary']}")
    else:
        logger.info(f"\n🎯 业务应用接口 (Business Apps):")
        logger.info(f"   └─ 暂无业务应用")
    
    # 其他接口
    if "other" in routes_by_prefix:
        logger.info(f"\n📌 其他接口:")
        for route in sorted(routes_by_prefix["other"], key=lambda x: x["path"]):
            methods_str = ", ".join(sorted(route["methods"]))
            logger.info(f"   - {methods_str:8} {route['path']:30} - {route['summary']}")
    
    # 配置检查
    logger.info(f"\n🔍 配置检查:")
    if config_manager.check_health():
        logger.info(f"   ✅ 配置健康检查通过")
    else:
        logger.warning(f"   ⚠️  配置健康检查发现问题，请检查配置文件")
    
    logger.info("=" * 80)
    logger.info(f"✨ 服务启动完成！访问 http://localhost:8000/docs 查看完整 API 文档")
    logger.info("=" * 80 + "\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # ========== 启动时执行 ==========
    
    # 1. 初始化数据库
    logger.info("🗄️  正在初始化数据库...")
    try:
        from db.mysql.connection import get_mysql_manager
        
        # 获取数据库管理器
        db_manager = get_mysql_manager()
        
        # 创建数据库和表
        db_manager.init_db()
        
        # 健康检查
        if db_manager.health_check():
            logger.info("✅ 数据库初始化成功")
        else:
            logger.warning("⚠️  数据库健康检查失败，请检查配置")
            
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise
    
    # 2. 创建存储目录
    file_upload_config = config_manager.get_file_upload_config()
    storage_config = config_manager.get_storage_config()
    
    storage_path = Path(storage_config.get("storage_root", "./upload"))
    storage_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"✅ 存储目录创建成功: {storage_path}")
    
    # 3. 打印路由信息（在所有路由注册完成后）
    print_routes(app)
    
    yield  # 应用运行中
    
    # ========== 关闭时执行 ==========
    logger.info("\n" + "=" * 80)
    logger.info(f"👋 {app_name} 正在关闭...")
    
    # 关闭数据库连接
    try:
        from db.mysql.connection import MySQLManagerFactory
        MySQLManagerFactory.close_all()
        logger.info("✅ 数据库连接已关闭")
    except Exception as e:
        logger.error(f"❌ 关闭数据库连接失败: {e}")
    
    logger.info("=" * 80)


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
        port=8001,
        reload=is_debug,
        log_level="info"
    )
