#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : constants.py
@Author  : caixiongjiang
@Date    : 2026/1/21
@Function: 
    文件存储服务常量定义
@Modify History:
    2026/1/21 - 初始版本
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

from enum import Enum


# ========== 文件分类 ==========

class FileCategory(str, Enum):
    """
    文件分类枚举
    
    - TEMP: 临时文件（1小时自动清理）
    - SESSION: 会话文件（2小时自动清理）
    - PERMANENT: 永久文件（手动删除）
    """
    TEMP = "temp"
    SESSION = "session"
    PERMANENT = "permanent"


# ========== 文件处理状态 ==========

class FileStatus(str, Enum):
    """
    文件处理状态枚举
    
    - UPLOADED: 已上传（初始状态）
    - PARSING: 解析中（MinerU处理中）
    - COMPLETED: 解析完成
    - FAILED: 解析失败
    """
    UPLOADED = "uploaded"
    PARSING = "parsing"
    COMPLETED = "completed"
    FAILED = "failed"


# ========== 允许的文件类型 ==========

# MIME 类型白名单
ALLOWED_MIME_TYPES = {
    # PDF
    "application/pdf",
    
    # 图片
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/tiff",
    
    # Office 文档
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # pptx
    "application/msword",  # doc
    "application/vnd.ms-excel",  # xls
    "application/vnd.ms-powerpoint",  # ppt
    
    # 文本
    "text/plain",
    "text/markdown",
    "text/csv",
    
    # 其他
    "application/json",
    "application/xml",
}

# 文件扩展名白名单
ALLOWED_EXTENSIONS = {
    # PDF
    ".pdf",
    
    # 图片
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif",
    
    # Office 文档
    ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt",
    
    # 文本
    ".txt", ".md", ".csv", ".json", ".xml",
}

# MIME 类型到扩展名的映射（用于默认扩展名）
MIME_TO_EXTENSION = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/csv": ".csv",
    "application/json": ".json",
}


# ========== 文件大小限制 ==========

# 单文件最大大小（字节）
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# 批量上传最大文件数
MAX_BATCH_SIZE = 10


# ========== 过期时间配置 ==========

# 临时文件过期时间（小时）
TEMP_FILE_EXPIRE_HOURS = 1

# 会话文件过期时间（小时）
SESSION_FILE_EXPIRE_HOURS = 2


# ========== 错误消息 ==========

ERROR_MESSAGES = {
    "file_not_found": "文件不存在: {file_id}",
    "file_expired": "文件已过期: {file_id}",
    "file_too_large": "文件大小超过限制（最大{max_size}MB）",
    "invalid_file_type": "不支持的文件类型: {mime_type}",
    "invalid_extension": "不支持的文件扩展名: {extension}",
    "batch_too_large": "批量上传文件数超过限制（最大{max_count}个）",
    "upload_failed": "文件上传失败: {reason}",
    "delete_failed": "文件删除失败: {reason}",
    "storage_error": "存储操作失败: {reason}",
}
