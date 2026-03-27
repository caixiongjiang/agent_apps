#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""=================================================
@PROJECT_NAME: agent_apps
@File    : service.py
@Author  : caixiongjiang
@Date    : 2026/1/19
@Function: 
    MinerU 服务层实现 - 简化版，支持智能分页
@Modify History:
    2026/1/19 - 简化架构，移除Redis，添加智能分页
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""

import asyncio
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime
import fitz  # PyMuPDF

from loguru import logger

from .client import Mineru2Client
from .schemas import ParseResult


class MinerUService:
    """
    MinerU 服务层 - 简化版
    
    功能：
    1. 同步文档解析（异步等待）
    2. 智能分页处理大文件
    3. 并行分页请求控制
    """
    
    def __init__(
        self,
        mineru_config: Dict[str, Any],
        max_pages_per_request: int = 4,
        max_concurrent_requests: int = 3,
        storage_path: Optional[Path] = None
    ):
        """
        初始化 MinerU 服务
        
        Args:
            mineru_config: MinerU 客户端配置
            max_pages_per_request: 每次请求最大页数（默认4页）
            max_concurrent_requests: 最大并发请求数（默认3个）
            storage_path: 本地存储路径（用于文件读取）
        """
        self.client = Mineru2Client(mineru_config)
        self.storage_path = storage_path or Path("./uploads")
        self.max_pages_per_request = max_pages_per_request
        self.max_concurrent_requests = max_concurrent_requests
        self.logger = logger
    
    async def parse_document(
        self,
        file_bytes: bytes,
        file_name: str,
        auto_pagination: bool = True
    ) -> ParseResult:
        """
        解析文档（主入口）
        
        Args:
            file_bytes: 文件字节内容
            file_name: 文件名
            auto_pagination: 是否自动分页（大文件自动分页并行处理）
        
        Returns:
            ParseResult: 解析结果
        
        Raises:
            Exception: 解析失败时抛出异常
        """
        start_time = datetime.now()
        self.logger.info(f"📄 开始解析文档: {file_name} ({len(file_bytes) / 1024 / 1024:.2f}MB)")
        
        try:
            if auto_pagination:
                # 智能分页模式
                result = await self._parse_with_auto_pagination(file_bytes, file_name)
            else:
                # 直接解析（不分页）
                result = await self._parse_single(file_bytes, file_name)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"✅ 解析完成: {file_name}, 耗时: {duration:.2f}秒, 页数: {result.pages}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 解析失败: {file_name}, 错误: {e}")
            raise
    
    async def _parse_single(
        self,
        file_bytes: bytes,
        file_name: str,
        start_page_id: Optional[int] = None,
        end_page_id: Optional[int] = None
    ) -> ParseResult:
        """
        单次解析（不分页或指定页码范围）
        
        Args:
            file_bytes: 文件字节内容
            file_name: 文件名
            start_page_id: 起始页码
            end_page_id: 结束页码
        
        Returns:
            ParseResult: 解析结果
        """
        # 在线程池中执行同步的 MinerU 解析
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.client.parse_file,
            file_bytes,
            file_name,
            start_page_id,
            end_page_id
        )
        
        # 转换为标准格式
        return self._convert_to_parse_result(result, file_name)
    
    async def _parse_with_auto_pagination(
        self,
        file_bytes: bytes,
        file_name: str
    ) -> ParseResult:
        """
        智能分页解析（自动检测页数，分页并行处理）
        
        工作流程：
        1. 使用 fitz 获取 PDF 真实页数
        2. 如果页数 <= max_pages_per_request，直接解析全部
        3. 否则，按 max_pages_per_request 分割成多个请求
        4. 并行执行多个分页请求（受 max_concurrent_requests 限制）
        5. 合并所有分页结果
        
        Args:
            file_bytes: 文件字节内容
            file_name: 文件名
        
        Returns:
            ParseResult: 合并后的解析结果
        """
        # 步骤1: 使用 fitz 精确获取 PDF 页数
        self.logger.info(f"🔍 检测文档页数: {file_name}")
        total_pages = self._get_pdf_page_count(file_bytes)
        self.logger.info(f"📊 文档总页数: {total_pages}")
        
        # 步骤2: 判断是否需要分页
        if total_pages <= self.max_pages_per_request:
            # 页数较少，直接解析全部
            self.logger.info(f"📄 页数较少（{total_pages}页），直接解析全部")
            return await self._parse_single(file_bytes, file_name)
        
        # 步骤3: 计算分页方案
        page_ranges = self._calculate_page_ranges(total_pages)
        self.logger.info(
            f"📑 启用分页模式: {len(page_ranges)}个分页, "
            f"每批{self.max_pages_per_request}页, "
            f"并发数{self.max_concurrent_requests}"
        )
        
        # 步骤4: 并行执行分页请求
        page_results = await self._parse_pages_concurrent(
            file_bytes,
            file_name,
            page_ranges
        )
        
        # 步骤5: 合并结果
        self.logger.info(f"🔗 合并 {len(page_results)} 个分页结果")
        merged_result = self._merge_page_results(page_results, file_name)
        
        return merged_result
    
    def _get_pdf_page_count(self, file_bytes: bytes) -> int:
        """
        使用 PyMuPDF (fitz) 获取 PDF 真实页数
        
        Args:
            file_bytes: PDF 文件字节内容
        
        Returns:
            int: PDF 页数
        
        Raises:
            Exception: PDF 读取失败时抛出异常
        """
        try:
            # 使用 fitz 打开 PDF
            pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
            page_count = pdf_document.page_count
            pdf_document.close()
            return page_count
        except Exception as e:
            raise Exception(f"获取 PDF 页数失败: {e}")
    
    def _calculate_page_ranges(self, total_pages: int) -> List[Tuple[int, int]]:
        """
        计算分页范围
        
        Args:
            total_pages: 总页数
        
        Returns:
            分页范围列表 [(start, end), ...]
        
        Example:
            total_pages=25, max_pages_per_request=10
            返回: [(0, 9), (10, 19), (20, 24)]
        """
        page_ranges = []
        for start in range(0, total_pages, self.max_pages_per_request):
            end = min(start + self.max_pages_per_request - 1, total_pages - 1)
            page_ranges.append((start, end))
        return page_ranges
    
    async def _parse_pages_concurrent(
        self,
        file_bytes: bytes,
        file_name: str,
        page_ranges: List[Tuple[int, int]]
    ) -> List[ParseResult]:
        """
        并发执行多个分页请求
        
        Args:
            file_bytes: 文件字节内容
            file_name: 文件名
            page_ranges: 分页范围列表
        
        Returns:
            解析结果列表（按页码顺序）
        """
        results = []
        
        # 使用 Semaphore 限制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        async def parse_page_range(start: int, end: int, index: int) -> Tuple[int, ParseResult]:
            """解析单个分页范围"""
            async with semaphore:
                self.logger.info(f"📖 解析分页 {index + 1}/{len(page_ranges)}: 第{start}-{end}页")
                result = await self._parse_single(file_bytes, file_name, start, end)
                return index, result
        
        # 创建所有任务
        tasks = [
            parse_page_range(start, end, i)
            for i, (start, end) in enumerate(page_ranges)
        ]
        
        # 并发执行
        indexed_results = await asyncio.gather(*tasks)
        
        # 按索引排序（保证顺序）
        indexed_results.sort(key=lambda x: x[0])
        results = [result for _, result in indexed_results]
        
        return results
    
    def _merge_page_results(
        self,
        page_results: List[ParseResult],
        file_name: str
    ) -> ParseResult:
        """
        合并多个分页结果
        
        Args:
            page_results: 分页结果列表
            file_name: 文件名
        
        Returns:
            合并后的完整结果
        """
        if not page_results:
            raise ValueError("没有分页结果可以合并")
        
        if len(page_results) == 1:
            return page_results[0]
        
        # 合并结构化内容
        merged_struct_content = {"root": []}
        for result in page_results:
            if result.struct_content and "root" in result.struct_content:
                merged_struct_content["root"].extend(result.struct_content["root"])
        
        # 合并 Markdown 内容
        merged_markdown = "\n\n---\n\n".join(
            result.markdown_content for result in page_results
            if result.markdown_content
        )
        
        # 合并坐标信息
        merged_coordinates = {}
        for result in page_results:
            if result.coordinates:
                merged_coordinates.update(result.coordinates)
        
        # 计算总页数
        total_pages = sum(result.pages for result in page_results)
        
        return ParseResult(
            file_name=file_name,
            struct_content=merged_struct_content,
            markdown_content=merged_markdown,
            pages=total_pages,
            coordinates=merged_coordinates,
            meta={
                "pagination_info": {
                    "total_chunks": len(page_results),
                    "max_pages_per_request": self.max_pages_per_request,
                    "max_concurrent_requests": self.max_concurrent_requests
                }
            }
        )
    
    def _convert_to_parse_result(
        self,
        mineru_result: Dict[str, Any],
        file_name: str
    ) -> ParseResult:
        """
        将 MinerU 客户端返回的结果转换为标准格式
        
        Args:
            mineru_result: MinerU 客户端返回的结果
            file_name: 文件名
        
        Returns:
            ParseResult: 标准化的解析结果
        """
        # 提取坐标信息
        coordinates = self._extract_coordinates(mineru_result)
        
        return ParseResult(
            file_name=file_name,
            struct_content=mineru_result.get("struct_content", {}),
            markdown_content=mineru_result.get("content", ""),
            pages=mineru_result.get("pages", 0),
            coordinates=coordinates,
            meta={}
        )
    
    def _extract_coordinates(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        从解析结果中提取坐标信息
        
        Args:
            result: MinerU 解析结果
        
        Returns:
            坐标信息字典（用于前端画框）
        """
        coordinates = {}
        struct_content = result.get("struct_content", {})
        pages = struct_content.get("root", [])
        
        for page in pages:
            page_idx = page.get("page_idx")
            page_coords = []
            
            for element in page.get("page_info", []):
                if "bbox" in element:
                    page_coords.append({
                        "id": element.get("id"),
                        "type": element.get("type"),
                        "bbox": element.get("bbox"),
                        "element_index": element.get("element_index")
                    })
            
            if page_coords:
                coordinates[f"page_{page_idx}"] = page_coords
        
        return coordinates


# ========== 批量处理支持 ==========

class BatchMinerUService:
    """批量 MinerU 服务（简化版）"""
    
    def __init__(self, service: MinerUService):
        self.service = service
        self.logger = logger
    
    async def parse_documents(
        self,
        file_list: List[Tuple[bytes, str]],
        auto_pagination: bool = True
    ) -> List[ParseResult]:
        """
        批量解析文档
        
        Args:
            file_list: 文件列表 [(file_bytes, file_name), ...]
            auto_pagination: 是否自动分页
        
        Returns:
            解析结果列表
        """
        self.logger.info(f"📦 开始批量解析 {len(file_list)} 个文档")
        
        tasks = [
            self.service.parse_document(file_bytes, file_name, auto_pagination)
            for file_bytes, file_name in file_list
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计成功和失败
        success_count = sum(1 for r in results if isinstance(r, ParseResult))
        failed_count = len(results) - success_count
        
        self.logger.info(f"✅ 批量解析完成: 成功 {success_count}/{len(file_list)}, 失败 {failed_count}")
        
        return results
