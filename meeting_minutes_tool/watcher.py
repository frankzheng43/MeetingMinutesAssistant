# -*- coding: utf-8 -*-
"""
文件监控模块
监控指定文件夹中的 PDF 文件，自动进行 OCR 识别、LLM 提取和 Excel 写入
支持三级目录结构：监听目录/年份/会议类型/
"""

import json
import logging
import os
import queue
import re
import shutil
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# 延迟导入的模块（实际在函数中使用，提升到模块级别避免重复导入）
from llm_utils import extract_minutes
from excel_utils import append_records, delete_records_by_source, get_excel_path, restore_from_backup

# 配置日志
logger = logging.getLogger(__name__)

# Excel 写入重试配置
EXCEL_RETRY_MAX = 5       # 最大重试次数
EXCEL_RETRY_DELAY = 2     # 每次重试间隔（秒）

# 扫描记录文件名
SCAN_RECORD_FILE = "scan_record.json"
# 缓存目录名（存放 OCR 文本、LLM 结果、MD5 等缓存）
CACHE_DIR = "_cache"


# 会议类型关键词映射
MEETING_TYPE_KEYWORDS = {
    "党委会": ["党委"],
    "董事会": ["董事"],
    "总经办": ["总经办", "总经理"],
}

# 括号转换映射
BRACKET_MAP = str.maketrans({
    '【': '〔', '】': '〕',
    '[': '〔', ']': '〕',
    '（': '〔', '）': '〕',
    '(': '〔', ')': '〕',
})


@dataclass
class PDFJob:
    """PDF 处理任务的数据类"""

    file_path: str  # PDF 文件路径
    timestamp: float  # 文件创建/发现时间戳


class MonitorHandler(FileSystemEventHandler):
    """文件系统事件处理器，检测 PDF 文件创建事件"""

    def __init__(self, job_queue: queue.Queue, watch_folder: str):
        """
        初始化处理器

        :param job_queue: 任务队列，用于传递 PDF 处理任务
        :param watch_folder: 监听根目录
        """
        self.job_queue = job_queue
        self.watch_folder = os.path.normpath(watch_folder)
        super().__init__()

    def on_created(self, event):
        """
        文件创建事件处理

        :param event: 文件系统事件
        """
        if event.is_directory:
            return

        # 检测 .pdf 文件（不区分大小写）
        if event.src_path.lower().endswith(".pdf"):
            # 只处理监听目录下的文件（包括子目录）
            norm_path = os.path.normpath(event.src_path)
            if not norm_path.startswith(self.watch_folder):
                return

            logger.info(f"检测到新 PDF 文件: {event.src_path}")
            # 延迟 2 秒后放入队列，确保文件写入完成
            time.sleep(2)
            job = PDFJob(file_path=event.src_path, timestamp=time.time())
            self.job_queue.put(job)
            logger.info(f"PDF 任务已加入队列: {event.src_path}")

    def on_deleted(self, event):
        """
        文件删除事件处理

        :param event: 文件系统事件
        """
        if event.is_directory:
            return

        if event.src_path.lower().endswith(".pdf"):
            norm_path = os.path.normpath(event.src_path)
            if not norm_path.startswith(self.watch_folder):
                return

            logger.info(f"检测到 PDF 文件被删除: {event.src_path}")
            # 将删除任务放入队列（用 None 的 file_path 表示删除操作）
            job = PDFJob(file_path="__DELETE__:" + event.src_path, timestamp=time.time())
            self.job_queue.put(job)


def normalize_filename(filename: str) -> str:
    """
    规范化文件名：将各种括号统一转为〔〕

    :param filename: 原始文件名（含扩展名）
    :return: 规范化后的文件名
    """
    name_no_ext, ext = os.path.splitext(filename)
    # 转换括号
    name_no_ext = name_no_ext.translate(BRACKET_MAP)
    return name_no_ext + ext


def detect_meeting_type_from_path(file_path: str) -> str:
    """
    从文件路径中检测会议类型

    :param file_path: 文件完整路径
    :return: 会议类型（党委会/董事会/总经办）或 None
    """
    path_lower = file_path.lower()
    for meeting_type, keywords in MEETING_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in path_lower:
                return meeting_type
    return None


def detect_year_from_path(file_path: str, watch_folder: str) -> str:
    """
    从文件路径中提取年份

    :param file_path: 文件完整路径
    :param watch_folder: 监听根目录
    :return: 年份字符串，如 "2026"
    """
    rel_path = os.path.relpath(file_path, watch_folder)
    parts = rel_path.replace("\\", "/").split("/")
    for part in parts:
        if re.match(r'^\d{4}$', part):
            return part
    return ""


def rename_all_pdfs(watch_folder: str, log_func=None) -> dict:
    """
    扫描并重命名所有 PDF 文件，将括号统一转为〔〕

    :param watch_folder: 监听根目录
    :param log_func: 日志回调函数
    :return: {重命名后的相对路径: {file_path, mtime, meeting_type, year}}
    """
    def log(message: str, level: str = "info"):
        if log_func:
            log_func(message)
        else:
            if level == "info":
                logger.info(message)
            elif level == "error":
                logger.error(message)

    watch_folder = os.path.normpath(watch_folder)
    result = {}

    for root, dirs, files in os.walk(watch_folder):
        for f in files:
            if not f.lower().endswith(".pdf"):
                continue

            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, watch_folder)

            # 跳过临时图片目录
            if "_temp_images" in rel_path:
                continue

            # 先重命名文件
            new_name = normalize_filename(f)
            if new_name != f:
                new_path = os.path.join(root, new_name)
                try:
                    # 如果目标文件已存在（括号不同但内容相同），先删除旧文件
                    if os.path.exists(new_path):
                        os.remove(new_path)
                        log(f"目标文件已存在，已删除旧文件: {new_name}")
                    os.rename(full_path, new_path)
                    log(f"文件已重命名: {f} -> {new_name}")
                    full_path = new_path
                    rel_path = os.path.relpath(full_path, watch_folder)
                except Exception as e:
                    log(f"文件重命名失败: {f} - {e}", "error")

            meeting_type = detect_meeting_type_from_path(full_path)
            year = detect_year_from_path(full_path, watch_folder)

            result[rel_path] = {
                "file_path": full_path,
                "mtime": os.path.getmtime(full_path),
                "meeting_type": meeting_type,
                "year": year,
            }

    return result



def load_scan_record(watch_folder: str) -> dict:
    """
    加载上次扫描记录

    :param watch_folder: 监听根目录
    :return: 记录字典
    """
    record_path = os.path.normpath(os.path.join(watch_folder, SCAN_RECORD_FILE))
    if os.path.exists(record_path):
        try:
            with open(record_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载扫描记录失败: {e}")
    return {}


def save_scan_record(watch_folder: str, record: dict):
    """
    保存扫描记录

    :param watch_folder: 监听根目录
    :param record: 记录字典
    """
    record_path = os.path.normpath(os.path.join(watch_folder, SCAN_RECORD_FILE))
    try:
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存扫描记录失败: {e}")


def _get_cache_paths(watch_folder: str, pdf_rel_path: str) -> dict:
    """
    获取缓存文件路径（所有缓存放在监听目录下的 _cache 目录中）

    :param watch_folder: 监听根目录
    :param pdf_rel_path: PDF 文件的相对路径（如 "2026/党委会/党委会〔2026〕4号.pdf"）
    :return: {"md5": ..., "ocr": ..., "result": ...}
    """
    cache_dir = os.path.normpath(os.path.join(watch_folder, CACHE_DIR))
    # 保持相同的子目录结构
    rel_dir = os.path.dirname(pdf_rel_path)
    base_name = os.path.basename(pdf_rel_path)
    target_dir = os.path.join(cache_dir, rel_dir)
    return {
        "md5": os.path.join(target_dir, base_name + ".md5"),
        "ocr": os.path.join(target_dir, base_name + ".ocr.txt"),
        "result": os.path.join(target_dir, base_name + ".result.json"),
    }


def _compute_file_md5(file_path: str) -> str:
    """
    计算文件的 MD5 值

    :param file_path: 文件路径
    :return: MD5 十六进制字符串
    """
    import hashlib
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def _load_cache_md5(cache_paths: dict) -> str:
    """加载缓存的 MD5 值"""
    try:
        with open(cache_paths["md5"], "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _save_cache_md5(cache_paths: dict, md5_value: str):
    """保存 MD5 值到缓存"""
    os.makedirs(os.path.dirname(cache_paths["md5"]), exist_ok=True)
    with open(cache_paths["md5"], "w", encoding="utf-8") as f:
        f.write(md5_value)


def _load_cache_ocr(cache_paths: dict) -> str:
    """加载缓存的 OCR 文本"""
    try:
        with open(cache_paths["ocr"], "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _save_cache_ocr(cache_paths: dict, ocr_text: str):
    """保存 OCR 文本到缓存"""
    os.makedirs(os.path.dirname(cache_paths["ocr"]), exist_ok=True)
    with open(cache_paths["ocr"], "w", encoding="utf-8") as f:
        f.write(ocr_text)


def _load_cache_result(cache_paths: dict) -> dict:
    """加载缓存的 LLM 提取结果"""
    try:
        with open(cache_paths["result"], "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache_result(cache_paths: dict, result: dict):
    """保存 LLM 提取结果到缓存"""
    os.makedirs(os.path.dirname(cache_paths["result"]), exist_ok=True)
    with open(cache_paths["result"], "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def _delete_cache(cache_paths: dict):
    """删除所有缓存文件"""
    for key in ("md5", "ocr", "result"):
        path = cache_paths[key]
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


def pdf_to_images(pdf_path: str, output_folder: str) -> list:
    """
    将 PDF 文件的每一页转换为 PNG 图片

    :param pdf_path: PDF 文件路径
    :param output_folder: 输出图片的文件夹路径
    :return: 生成的图片路径列表
    """
    import fitz  # PyMuPDF

    logger.info(f"开始转换 PDF 为图片: {pdf_path}")

    # 确保输出文件夹存在
    os.makedirs(output_folder, exist_ok=True)

    image_paths = []
    try:
        # 打开 PDF 文件
        pdf_document = fitz.open(pdf_path)
        logger.info(f"PDF 共 {len(pdf_document)} 页")

        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            # 设置 300 DPI 进行渲染
            zoom_matrix = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=zoom_matrix)

            # 生成图片文件名
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            image_name = f"{base_name}_page_{page_num + 1}.png"
            image_path = os.path.join(output_folder, image_name)

            # 保存图片
            pix.save(image_path)
            image_paths.append(image_path)
            logger.info(f"第 {page_num + 1} 页已转换为图片: {image_path}")

        pdf_document.close()
        logger.info(f"PDF 转换完成，共生成 {len(image_paths)} 张图片")
        return image_paths

    except Exception as e:
        logger.error(f"PDF 转图片失败: {e}")
        raise


def _write_excel_with_retry(output_dir: str, record_number: str, items: list,
                             meeting_type_name: str, meeting_info: dict,
                             pdf_filename: str, year: str, publish_date: str,
                             log_func) -> bool:
    """
    写入 Excel 并自动重试（解决文件被占用问题）

    :return: 是否写入成功
    """
    for attempt in range(1, EXCEL_RETRY_MAX + 1):
        try:
            saved_path = append_records(
                output_dir=output_dir,
                record_number=record_number,
                items=items,
                meeting_type=meeting_type_name,
                meeting_info=meeting_info,
                source_file=pdf_filename,
                year=year,
                publish_date=publish_date,
            )
            log_func(f"Excel 写入完成 [{meeting_type_name}]: {saved_path}")
            return True
        except PermissionError as e:
            if attempt < EXCEL_RETRY_MAX:
                log_func(
                    f"Excel 文件被占用，{EXCEL_RETRY_DELAY}秒后重试 ({attempt}/{EXCEL_RETRY_MAX})...",
                    "warning",
                )
                time.sleep(EXCEL_RETRY_DELAY)
            else:
                log_func(
                    f"Excel 文件被占用，已重试 {EXCEL_RETRY_MAX} 次仍失败，请关闭 Excel 文件后重新处理",
                    "error",
                )
        except Exception as e:
            log_func(f"写入 Excel 失败: {e}", "error")
            return False

    return False


def _delete_excel_with_retry(output_dir: str, meeting_type_name: str,
                              source_file: str, log_func) -> bool:
    """
    从 Excel 删除记录并自动重试

    :return: 是否删除成功
    """
    for attempt in range(1, EXCEL_RETRY_MAX + 1):
        try:
            deleted = delete_records_by_source(
                output_dir=output_dir,
                meeting_type=meeting_type_name,
                source_file=source_file,
            )
            if deleted:
                log_func(f"已从 Excel [{meeting_type_name}] 删除来源文件 '{source_file}' 的记录")
            return True
        except PermissionError as e:
            if attempt < EXCEL_RETRY_MAX:
                log_func(
                    f"Excel 文件被占用，{EXCEL_RETRY_DELAY}秒后重试 ({attempt}/{EXCEL_RETRY_MAX})...",
                    "warning",
                )
                time.sleep(EXCEL_RETRY_DELAY)
            else:
                log_func(
                    f"Excel 文件被占用，已重试 {EXCEL_RETRY_MAX} 次仍失败，请手动删除",
                    "error",
                )
        except Exception as e:
            log_func(f"删除 Excel 记录失败: {e}", "error")
            return False

    return False


def process_single_pdf(pdf_path: str, config: dict, ocr_client, log_func,
                       temp_image_dir: str, output_dir: str, watch_folder: str,
                       force_reprocess: bool = False) -> bool:
    """
    处理单个 PDF 文件（OCR + LLM + Excel 写入）
    支持缓存机制：如果缓存命中且内容未变，跳过 OCR 和 LLM 步骤

    :param force_reprocess: 是否强制重新处理（忽略缓存）
    :return: 是否处理成功
    """
    def log(message: str, level: str = "info"):
        if log_func:
            log_func(message)
        else:
            if level == "info":
                logger.info(message)
            elif level == "error":
                logger.error(message)
            elif level == "warning":
                logger.warning(message)

    deepseek_key = config.get("deepseek_key", "")
    image_paths = []

    try:
        # 检测会议类型和年份
        meeting_type_name = detect_meeting_type_from_path(pdf_path)
        year = detect_year_from_path(pdf_path, watch_folder)

        if not meeting_type_name:
            log(f"无法从路径检测会议类型，跳过: {pdf_path}", "warning")
            return False

        log(f"检测到会议类型: {meeting_type_name}, 年份: {year or '未知'}")

        # 计算 PDF 相对路径和缓存路径
        pdf_rel_path = os.path.relpath(pdf_path, watch_folder)
        cache_paths = _get_cache_paths(watch_folder, pdf_rel_path)
        pdf_filename = os.path.basename(pdf_path)

        # 检查缓存是否有效（MD5 匹配）
        cached_md5 = _load_cache_md5(cache_paths)
        current_md5 = _compute_file_md5(pdf_path)
        cache_hit = (cached_md5 == current_md5) and not force_reprocess

        if cache_hit:
            # 缓存命中：尝试从缓存加载 OCR 文本和 LLM 结果
            cached_ocr = _load_cache_ocr(cache_paths)
            cached_result = _load_cache_result(cache_paths)

            if cached_ocr and cached_result:
                log(f"缓存命中，跳过 OCR 和 LLM 步骤")
                full_text = cached_ocr
                minutes_data = cached_result
                record_number = minutes_data.get("record_number", "")
                meeting_info = minutes_data.get("meeting_info", {})
                items = minutes_data.get("items", [])
                publish_date = minutes_data.get("publish_date", "")
                log(
                    f"从缓存加载完成，纪要号: {record_number or '未找到'}, "
                    f"议题数: {len(items)}, "
                    f"印发时间: {publish_date or '未找到'}"
                )
            else:
                # 缓存文件不完整，降级为重新处理
                log("缓存文件不完整，将重新处理", "warning")
                cache_hit = False

        if not cache_hit:
            # 步骤 1：PDF 转图片
            log("步骤 1/4：正在将 PDF 转换为图片...")
            image_paths = pdf_to_images(pdf_path, temp_image_dir)
            log(f"PDF 转换完成，共 {len(image_paths)} 页")

            # 步骤 2：逐页 OCR 识别
            log("步骤 2/4：正在进行 OCR 文字识别...")
            full_text_parts = []
            for img_path in image_paths:
                try:
                    text = ocr_client.recognize(img_path)
                    full_text_parts.append(text)
                    log(f"页面识别完成: {os.path.basename(img_path)}")
                except Exception as e:
                    log(f"页面识别失败: {e}", "error")

            full_text = "\n".join(full_text_parts)
            log(f"OCR 识别完成，总文字长度: {len(full_text)}")

            # 缓存 OCR 文本
            _save_cache_ocr(cache_paths, full_text)

            # 步骤 3：LLM 提取会议纪要
            log("步骤 3/4：正在调用 DeepSeek API 提取会议纪要...")
            minutes_data = extract_minutes(full_text, deepseek_key, filename=pdf_filename)
            record_number = minutes_data.get("record_number", "")
            meeting_info = minutes_data.get("meeting_info", {})
            items = minutes_data.get("items", [])
            publish_date = minutes_data.get("publish_date", "")
            log(
                f"提取完成，纪要号: {record_number or '未找到'}, "
                f"议题数: {len(items)}, "
                f"印发时间: {publish_date or '未找到'}"
            )

            # 缓存 LLM 结果和 MD5
            _save_cache_result(cache_paths, minutes_data)
            _save_cache_md5(cache_paths, current_md5)

        # 步骤 4：写入 Excel（带重试机制）
        if items:
            log("步骤 4/4：正在写入 Excel 文件...")
            excel_ok = _write_excel_with_retry(
                output_dir=output_dir,
                record_number=record_number,
                items=items,
                meeting_type_name=meeting_type_name,
                meeting_info=meeting_info,
                pdf_filename=pdf_filename,
                year=year,
                publish_date=publish_date,
                log_func=log,
            )
            if not excel_ok:
                log("Excel 写入失败，PDF 文件将保留在原位置等待重新处理", "warning")
                return False
        else:
            log("未提取到议题内容，跳过 Excel 写入", "warning")

        log(f"文件处理完成: {os.path.basename(pdf_path)}")
        return True

    except Exception as e:
        log(f"处理 PDF 文件时发生错误: {e}", "error")
        return False

    finally:
        # 清理临时图片
        try:
            for img_path in image_paths:
                if os.path.exists(img_path):
                    os.remove(img_path)
        except Exception:
            pass


def initial_scan_and_process(watch_folder: str, config: dict, ocr_client,
                              log_func, temp_image_dir: str, output_dir: str,
                              stop_event: threading.Event = None):
    """
    启动时全量扫描目录，对比上次记录，处理新增/删除的文件
    支持通过 stop_event 中断（用于退出时快速响应）

    :param watch_folder: 监听根目录
    :param config: 配置字典
    :param ocr_client: 百度 OCR 客户端
    :param log_func: 日志回调函数
    :param temp_image_dir: 临时图片目录
    :param output_dir: Excel 输出目录
    :param stop_event: 停止事件，设置后尽快退出
    """
    def log(message: str, level: str = "info"):
        if log_func:
            log_func(message)
        else:
            if level == "info":
                logger.info(message)
            elif level == "error":
                logger.error(message)
            elif level == "warning":
                logger.warning(message)

    def should_stop() -> bool:
        """检查是否需要停止"""
        return stop_event and stop_event.is_set()

    log("开始全量扫描目录...")

    # 先重命名所有文件，再扫描（确保文件名统一为〔〕格式）
    current_files = rename_all_pdfs(watch_folder, log_func=log_func)
    log(f"扫描到 {len(current_files)} 个 PDF 文件")

    if should_stop():
        log("全量扫描被中断")
        return

    # 检查 Excel 文件是否存在，如果不存在则尝试从缓存重建
    excel_path = get_excel_path(output_dir)
    if not os.path.exists(excel_path):
        log("Excel 文件不存在，尝试从缓存重建...")
        # 先尝试从备份恢复
        restored = restore_from_backup(output_dir)
        if restored:
            log("Excel 已从备份恢复，跳过重新处理")
            # 恢复后保存扫描记录（标记所有文件为已处理）
            record_to_save = {}
            for rel_path, info in current_files.items():
                record_to_save[rel_path] = {
                    "mtime": info["mtime"],
                    "meeting_type": info["meeting_type"],
                    "year": info["year"],
                }
            save_scan_record(watch_folder, record_to_save)
            log("全量扫描完成（从备份恢复，无需处理）")
            return
        else:
            # 备份也没有，尝试从缓存（.result.json）重建
            log("没有找到备份，尝试从缓存重建 Excel...", "warning")
            rebuilt_count = 0
            for rel_path, info in sorted(current_files.items()):
                if should_stop():
                    log("全量扫描被中断")
                    return
                cache_paths = _get_cache_paths(watch_folder, rel_path)
                cached_result = _load_cache_result(cache_paths)
                if cached_result and cached_result.get("items"):
                    try:
                        append_records(
                            output_dir=output_dir,
                            record_number=cached_result.get("record_number", ""),
                            items=cached_result.get("items", []),
                            meeting_type=info["meeting_type"] or "未知",
                            meeting_info=cached_result.get("meeting_info", {}),
                            source_file=os.path.basename(rel_path),
                            year=info["year"] or "",
                            publish_date=cached_result.get("publish_date", ""),
                        )
                        rebuilt_count += 1
                    except Exception as e:
                        log(f"从缓存重建记录失败: {rel_path} - {e}", "error")
            if rebuilt_count > 0:
                log(f"从缓存成功重建 {rebuilt_count} 条记录")
                record_to_save = {}
                for rel_path, info in current_files.items():
                    record_to_save[rel_path] = {
                        "mtime": info["mtime"],
                        "meeting_type": info["meeting_type"],
                        "year": info["year"],
                    }
                save_scan_record(watch_folder, record_to_save)
                log("全量扫描完成（从缓存重建，无需重新处理）")
                return
            else:
                log("缓存中没有有效数据，将全部重新处理", "warning")

    if should_stop():
        log("全量扫描被中断")
        return

    # 加载上次扫描记录
    last_record = load_scan_record(watch_folder)

    # 找出新增的文件（上次没有的）和修改的文件（mtime 变化的）
    new_files = {}
    modified_files = {}
    for rel_path, info in current_files.items():
        if rel_path not in last_record:
            new_files[rel_path] = info
        elif last_record[rel_path].get("mtime") != info["mtime"]:
            modified_files[rel_path] = info

    # 找出删除的文件（上次有但这次没有的）
    deleted_files = {}
    for rel_path, info in last_record.items():
        if rel_path not in current_files:
            deleted_files[rel_path] = info

    # 处理修改的文件（同名替换）：先判断内容是否真正变化，再决定是否重新处理
    if modified_files:
        actual_changed = 0
        skipped_md5 = 0
        for rel_path, info in sorted(modified_files.items()):
            if should_stop():
                log("全量扫描被中断")
                return

            # 检查 MD5 缓存：如果文件内容未变，跳过重新处理
            cache_paths = _get_cache_paths(watch_folder, rel_path)
            cached_md5 = _load_cache_md5(cache_paths)
            current_md5 = _compute_file_md5(info["file_path"])
            if cached_md5 and cached_md5 == current_md5:
                log(f"文件内容未变化（MD5 相同），跳过重新处理: {rel_path}")
                skipped_md5 += 1
                continue

            meeting_type_name = info["meeting_type"]
            source_file = os.path.basename(rel_path)

            if not meeting_type_name:
                log(f"无法检测会议类型，跳过: {rel_path}", "warning")
                continue

            log(f"文件内容已变化（替换），重新处理: {rel_path}")

            # 先删除旧的 Excel 记录
            _delete_excel_with_retry(
                output_dir=output_dir,
                meeting_type_name=meeting_type_name,
                source_file=source_file,
                log_func=log,
            )

            # 删除旧缓存（强制重新处理）
            _delete_cache(cache_paths)

            # 重新处理 PDF
            success = process_single_pdf(
                pdf_path=info["file_path"],
                config=config,
                ocr_client=ocr_client,
                log_func=log_func,
                temp_image_dir=temp_image_dir,
                output_dir=output_dir,
                watch_folder=watch_folder,
            )

            if success:
                log(f"修改文件重新处理完成: {rel_path}")
                actual_changed += 1
            else:
                log(f"修改文件重新处理失败: {rel_path}", "error")

        if skipped_md5 > 0:
            log(f"修改文件中 {skipped_md5} 个内容未变（MD5 相同），已跳过")

    if should_stop():
        log("全量扫描被中断")
        return

    # 处理新增的文件
    if new_files:
        log(f"发现 {len(new_files)} 个新增文件，开始处理...")
        for rel_path, info in sorted(new_files.items()):
            if should_stop():
                log("全量扫描被中断")
                return
            pdf_path = info["file_path"]
            meeting_type_name = info["meeting_type"]
            year = info["year"]

            if not meeting_type_name:
                log(f"无法检测会议类型，跳过: {rel_path}", "warning")
                continue

            log(f"处理新增文件: {rel_path}")

            # 处理 PDF（文件已在 rename_all_pdfs 中重命名过了）
            success = process_single_pdf(
                pdf_path=pdf_path,
                config=config,
                ocr_client=ocr_client,
                log_func=log_func,
                temp_image_dir=temp_image_dir,
                output_dir=output_dir,
                watch_folder=watch_folder,
            )

            if success:
                log(f"新增文件处理完成: {rel_path}")
            else:
                log(f"新增文件处理失败: {rel_path}", "error")
    else:
        log("没有新增文件")

    if should_stop():
        log("全量扫描被中断")
        return

    # 处理删除的文件
    if deleted_files:
        log(f"发现 {len(deleted_files)} 个已删除文件，开始清理 Excel...")
        for rel_path, info in sorted(deleted_files.items()):
            if should_stop():
                log("全量扫描被中断")
                return
            meeting_type_name = info.get("meeting_type")
            source_file = os.path.basename(rel_path)

            if not meeting_type_name:
                continue

            log(f"文件已删除，清理 Excel 记录和缓存: {rel_path}")
            _delete_excel_with_retry(
                output_dir=output_dir,
                meeting_type_name=meeting_type_name,
                source_file=source_file,
                log_func=log,
            )
            # 删除对应的缓存
            cache_paths = _get_cache_paths(watch_folder, rel_path)
            _delete_cache(cache_paths)
    else:
        log("没有删除的文件")

    if should_stop():
        log("全量扫描被中断")
        return

    # 保存当前扫描记录
    record_to_save = {}
    for rel_path, info in current_files.items():
        record_to_save[rel_path] = {
            "mtime": info["mtime"],
            "meeting_type": info["meeting_type"],
            "year": info["year"],
        }
    save_scan_record(watch_folder, record_to_save)
    log("全量扫描完成")


def worker_loop(job_queue: queue.Queue, config: dict, log_func=None,
                stop_event: threading.Event = None):
    """
    工作线程主循环，从队列获取 PDF 任务并处理

    :param job_queue: 任务队列
    :param config: 配置字典
    :param log_func: 日志回调函数
    :param stop_event: 停止事件
    """
    from ocr_utils import create_ocr_engine

    def log(message: str, level: str = "info"):
        if log_func:
            log_func(message)
        else:
            if level == "info":
                logger.info(message)
            elif level == "error":
                logger.error(message)
            elif level == "warning":
                logger.warning(message)

    # 读取配置
    api_key = config.get("api_key", "")
    secret_key = config.get("secret_key", "")
    deepseek_key = config.get("deepseek_key", "")
    output_dir = config.get("output_dir", "")
    watch_folder = config.get("watch_folder", "")

    if not all([api_key, secret_key, deepseek_key, output_dir, watch_folder]):
        log("配置不完整，请检查所有配置项", "error")
        return

    try:
        ocr_client = create_ocr_engine(config, log_func=log)
        engine_name = config.get("ocr_engine", "baidu")
        log(f"OCR 引擎初始化成功（{engine_name}）")
    except Exception as e:
        log(f"OCR 引擎初始化失败: {e}", "error")
        return

    # 创建临时图片输出目录
    temp_image_dir = os.path.normpath(os.path.join(watch_folder, "_temp_images"))
    os.makedirs(temp_image_dir, exist_ok=True)

    # ===== 启动时全量扫描 =====
    initial_scan_and_process(
        watch_folder=watch_folder,
        config=config,
        ocr_client=ocr_client,
        log_func=log_func,
        temp_image_dir=temp_image_dir,
        output_dir=output_dir,
        stop_event=stop_event,
    )

    log("工作线程已启动，等待 PDF 任务...")

    while True:
        # 检查是否收到停止信号
        if stop_event and stop_event.is_set():
            log("工作线程收到停止信号，正在停止...")
            break

        try:
            # 从队列获取任务，超时 1 秒以便检查退出信号
            job = job_queue.get(timeout=1)
        except queue.Empty:
            continue

        # 检查退出信号
        if job is None:
            log("工作线程收到退出信号，正在停止...")
            break

        pdf_path = job.file_path

        # 检查是否为删除任务
        if pdf_path.startswith("__DELETE__:"):
            deleted_path = pdf_path[len("__DELETE__:"):]
            log(f"处理文件删除: {deleted_path}")

            try:
                # 计算相对路径
                rel_path = os.path.relpath(deleted_path, watch_folder)
                meeting_type_name = detect_meeting_type_from_path(deleted_path)
                source_file = os.path.basename(deleted_path)

                if meeting_type_name:
                    # 从 Excel 删除记录
                    _delete_excel_with_retry(
                        output_dir=output_dir,
                        meeting_type_name=meeting_type_name,
                        source_file=source_file,
                        log_func=log,
                    )

                # 删除缓存
                cache_paths = _get_cache_paths(watch_folder, rel_path)
                _delete_cache(cache_paths)

                # 更新扫描记录
                record = load_scan_record(watch_folder)
                if rel_path in record:
                    del record[rel_path]
                    save_scan_record(watch_folder, record)

                log(f"文件删除处理完成: {source_file}")
            except Exception as e:
                log(f"处理文件删除时出错: {e}", "error")

            job_queue.task_done()
            continue

        log(f"开始处理 PDF 文件: {pdf_path}")

        # 先重命名文件，统一括号格式
        dir_name = os.path.dirname(pdf_path)
        old_name = os.path.basename(pdf_path)
        new_name = normalize_filename(old_name)
        if new_name != old_name:
            new_path = os.path.join(dir_name, new_name)
            try:
                if os.path.exists(new_path):
                    os.remove(new_path)
                os.rename(pdf_path, new_path)
                log(f"实时文件已重命名: {old_name} -> {new_name}")
                pdf_path = new_path
            except Exception as e:
                log(f"实时文件重命名失败: {old_name} - {e}", "error")
                # 继续使用原路径处理

        # 处理 PDF
        success = process_single_pdf(
            pdf_path=pdf_path,
            config=config,
            ocr_client=ocr_client,
            log_func=log_func,
            temp_image_dir=temp_image_dir,
            output_dir=output_dir,
            watch_folder=watch_folder,
        )

        if success:
            log(f"文件处理完成: {os.path.basename(pdf_path)}")

        job_queue.task_done()

    # 清理临时目录
    try:
        if os.path.exists(temp_image_dir):
            shutil.rmtree(temp_image_dir)
    except Exception:
        pass


class WatcherService:
    """文件监控服务，管理文件监听和工作线程"""

    def __init__(self, folder: str, config: dict, log_func=None):
        """
        初始化监控服务

        :param folder: 要监听的文件夹路径
        :param config: 配置字典
        :param log_func: 日志回调函数
        """
        self.folder = folder
        self.config = config
        self.log_func = log_func
        self.observer = None
        self.worker_thread = None
        self.job_queue = queue.Queue()
        self._running = False
        self._stop_event = threading.Event()

    def start(self):
        """启动监控服务"""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()

        # 确保监听文件夹存在
        os.makedirs(self.folder, exist_ok=True)

        # 创建并启动文件系统监听器（递归监听子目录）
        event_handler = MonitorHandler(self.job_queue, self.folder)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.folder, recursive=True)
        self.observer.start()

        if self.log_func:
            self.log_func(f"文件监听已启动，监听文件夹: {self.folder}")

        # 创建并启动工作线程（非 daemon，确保能正确退出）
        self.worker_thread = threading.Thread(
            target=worker_loop,
            args=(self.job_queue, self.config, self.log_func, self._stop_event),
            daemon=False,
        )
        self.worker_thread.start()

        logger.info("WatcherService 已启动")

    def stop(self):
        """停止监控服务"""
        if not self._running:
            return

        self._running = False

        # 先设置停止事件，让工作线程尽快退出
        self._stop_event.set()

        # 发送退出信号给工作线程
        self.job_queue.put(None)

        # 等待工作线程结束（最多等 5 秒）
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
            self.worker_thread = None

        # 停止文件系统监听器
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None

        if self.log_func:
            self.log_func("文件监听已停止")

        logger.info("WatcherService 已停止")
