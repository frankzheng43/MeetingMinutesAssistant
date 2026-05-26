# -*- coding: utf-8 -*-
"""
Excel 工具模块
提供会议纪要数据写入 Excel 文件的功能
所有会议类型写入同一个 Excel 文件的不同 Sheet：党委会、董事会、总经办
"""

import logging
import os
import re
import shutil
from datetime import datetime
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

# 配置日志
logger = logging.getLogger(__name__)

# Excel 文件名（不含时间戳，实际文件名在 get_excel_path 中动态生成）
EXCEL_FILENAME_BASE = "会议纪要汇总"

# Excel 表头定义
HEADERS = [
    "纪要编号",
    "会议日期",
    "主持人",
    "年份",
    "议题序号",
    "议题标题",
    "议题详细内容",
    "印发时间",
    "来源文件",
]

# 列宽设置
COLUMN_WIDTHS = [22, 16, 12, 8, 8, 40, 60, 18, 40]

# 样式定义
HEADER_FONT = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center", wrap_text=True)
CELL_ALIGNMENT = Alignment(vertical="top", wrap_text=True)
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)

# 会议类型对应的 Sheet 名
MEETING_SHEET_NAMES = {
    "党委会": "党委会",
    "董事会": "董事会",
    "总经办": "总经办",
    "重组整合工作领导小组": "重组整合工作领导小组",
    "党委筹建领导小组": "党委筹建领导小组",
}

# 备份目录名
BACKUP_DIR = "_excel_backup"


def get_excel_path(output_dir: str) -> str:
    """
    获取 Excel 文件路径（所有会议类型共用同一个文件）
    文件名包含生成时间，如：会议纪要汇总_20260514_144500.xlsx

    :param output_dir: 输出目录
    :return: Excel 文件完整路径
    """
    # 查找输出目录中已有的会议纪要汇总文件
    if os.path.exists(output_dir):
        for f in os.listdir(output_dir):
            if f.startswith(EXCEL_FILENAME_BASE) and f.endswith(".xlsx"):
                return os.path.join(output_dir, f)

    # 不存在则生成新的带时间戳的文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{EXCEL_FILENAME_BASE}_{timestamp}.xlsx"
    return os.path.join(output_dir, filename)


def get_backup_dir(output_dir: str) -> str:
    """
    获取备份目录路径

    :param output_dir: 输出目录
    :return: 备份目录路径
    """
    return os.path.join(output_dir, BACKUP_DIR)


def backup_excel(output_dir: str):
    """
    备份当前 Excel 文件到备份目录

    :param output_dir: 输出目录
    """
    excel_path = get_excel_path(output_dir)
    if not os.path.exists(excel_path):
        return

    backup_dir = get_backup_dir(output_dir)
    os.makedirs(backup_dir, exist_ok=True)

    # 按时间戳命名备份文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"会议纪要汇总_{timestamp}.xlsx")

    try:
        shutil.copy2(excel_path, backup_path)
        logger.info(f"Excel 已备份: {backup_path}")
    except Exception as e:
        logger.error(f"Excel 备份失败: {e}")


def restore_from_backup(output_dir: str) -> bool:
    """
    从最近的备份恢复 Excel 文件

    :param output_dir: 输出目录
    :return: 是否恢复成功
    """
    backup_dir = get_backup_dir(output_dir)
    if not os.path.exists(backup_dir):
        logger.warning(f"备份目录不存在: {backup_dir}")
        return False

    # 查找所有备份文件，按修改时间排序
    backup_files = []
    for f in os.listdir(backup_dir):
        if f.startswith("会议纪要汇总_") and f.endswith(".xlsx"):
            full_path = os.path.join(backup_dir, f)
            backup_files.append((os.path.getmtime(full_path), full_path))

    if not backup_files:
        logger.warning("没有找到备份文件")
        return False

    # 取最新的备份
    backup_files.sort(key=lambda x: x[0], reverse=True)
    latest_backup = backup_files[0][1]

    excel_path = get_excel_path(output_dir)
    try:
        shutil.copy2(latest_backup, excel_path)
        logger.info(f"已从备份恢复 Excel: {latest_backup} -> {excel_path}")
        return True
    except Exception as e:
        logger.error(f"从备份恢复 Excel 失败: {e}")
        return False


def _get_or_create_sheet(wb, sheet_name: str):
    """
    获取或创建工作表

    :param wb: 工作簿
    :param sheet_name: Sheet 名称
    :return: 工作表
    """
    if sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        # 检查表头是否匹配
        existing_headers = [cell.value for cell in ws[1]]
        if existing_headers != HEADERS:
            logger.warning(f"Sheet '{sheet_name}' 表头不匹配，将重建")
            ws.delete_rows(1, ws.max_row)
            _write_header(ws)
    else:
        ws = wb.create_sheet(title=sheet_name)
        _write_header(ws)
        logger.info(f"创建新 Sheet: {sheet_name}")

    return ws


def _write_header(ws):
    """写入表头并设置样式"""
    for col_idx, header in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGNMENT
        cell.border = THIN_BORDER

    # 设置列宽
    for col_idx, width in enumerate(COLUMN_WIDTHS, start=1):
        ws.column_dimensions[chr(64 + col_idx)].width = width

    # 冻结首行
    ws.freeze_panes = "A2"


def _write_data_row(ws, row_idx: int, data: list):
    """
    写入一行数据并设置样式

    :param ws: 工作表
    :param row_idx: 行号
    :param data: 数据列表
    """
    for col_idx, value in enumerate(data, start=1):
        cell = ws.cell(row=row_idx, column=col_idx, value=value)
        cell.alignment = CELL_ALIGNMENT
        cell.border = THIN_BORDER


def _extract_sort_key(record_number: str, year: str) -> tuple:
    """
    从纪要编号中提取排序键（年份, 序号）

    :param record_number: 纪要编号，如 "党委会〔2026〕4号"
    :param year: 年份，如 "2026"
    :return: (年份数字, 序号数字)
    """
    year_num = int(year) if year else 0

    # 从纪要编号中提取序号，如 "党委会〔2026〕4号" -> 4
    number = 0
    if record_number:
        match = re.search(r'〔\d+〕(\d+)号', record_number)
        if match:
            number = int(match.group(1))

    return (year_num, number)


def _sort_and_rewrite(ws):
    """
    对工作表按年份和纪要号从小到大排序并重写

    :param ws: 工作表
    """
    # 读取所有数据行
    rows = []
    for row_idx in range(2, ws.max_row + 1):
        row_data = []
        for col_idx in range(1, len(HEADERS) + 1):
            row_data.append(ws.cell(row=row_idx, column=col_idx).value)
        rows.append(row_data)

    if not rows:
        return

    # 按年份和纪要号排序
    # 年份在第4列（索引3），纪要编号在第1列（索引0）
    rows.sort(key=lambda r: _extract_sort_key(r[0] or "", r[3] or ""))

    # 清空原有数据（保留表头）
    ws.delete_rows(2, ws.max_row)

    # 重新写入排序后的数据
    for idx, row_data in enumerate(rows, start=2):
        _write_data_row(ws, idx, row_data)


def append_records(
    output_dir: str,
    record_number: str,
    items: list,
    meeting_type: str = "",
    meeting_info: dict = None,
    source_file: str = "",
    year: str = "",
    publish_date: str = "",
) -> str:
    """
    将数据写入对应会议类型的 Sheet

    :param output_dir: 输出目录
    :param record_number: 纪要编号
    :param items: 议题列表
    :param meeting_type: 会议类型（党委会/董事会/总经办）
    :param meeting_info: 会议基本信息
    :param source_file: 来源文件名
    :param year: 年份
    :param publish_date: 印发时间
    :return: 写入的 Excel 文件路径
    """
    if meeting_info is None:
        meeting_info = {}

    excel_path = get_excel_path(output_dir)
    sheet_name = MEETING_SHEET_NAMES.get(meeting_type, meeting_type)
    logger.info(f"开始写入 Excel [{sheet_name}]: {excel_path}")

    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 打开或创建工作簿
        if os.path.exists(excel_path):
            wb = load_workbook(excel_path)
        else:
            wb = Workbook()
            # 删除默认的 Sheet
            if "Sheet" in wb.sheetnames:
                del wb["Sheet"]

        # 获取或创建 Sheet
        ws = _get_or_create_sheet(wb, sheet_name)

        # 获取当前最大行号
        current_max_row = ws.max_row

        # 追加数据
        for idx, item in enumerate(items, start=1):
            title = item.get("title", "")
            content = item.get("content", "")
            row_data = [
                record_number,
                meeting_info.get("date", ""),
                meeting_info.get("presider", ""),
                year,
                idx,
                title,
                content,
                publish_date,
                source_file,
            ]
            _write_data_row(ws, current_max_row + idx, row_data)
            logger.info(f"写入议题 {idx}: {title}")

        # 排序：按年份和纪要号从小到大
        _sort_and_rewrite(ws)

        # 保存前先备份
        backup_excel(output_dir)

        # 保存文件
        wb.save(excel_path)
        logger.info(
            f"Excel 文件保存成功 [{sheet_name}], "
            f"共写入 {len(items)} 条议题记录"
        )
        return excel_path

    except PermissionError:
        logger.error(f"无法写入 Excel 文件（文件可能被占用）: {excel_path}")
        raise
    except Exception as e:
        logger.error(f"写入 Excel 文件时发生错误: {e}")
        raise


def delete_records_by_source(output_dir: str, meeting_type: str, source_file: str) -> bool:
    """
    根据来源文件名删除 Excel 中对应的所有行

    :param output_dir: 输出目录
    :param meeting_type: 会议类型（党委会/董事会/总经办）
    :param source_file: 来源文件名
    :return: 是否删除成功
    """
    excel_path = get_excel_path(output_dir)
    sheet_name = MEETING_SHEET_NAMES.get(meeting_type, meeting_type)

    if not os.path.exists(excel_path):
        logger.warning(f"Excel 文件不存在，跳过删除: {excel_path}")
        return False

    try:
        wb = load_workbook(excel_path)

        if sheet_name not in wb.sheetnames:
            logger.warning(f"Sheet '{sheet_name}' 不存在，跳过删除")
            wb.close()
            return False

        ws = wb[sheet_name]

        # 找到"来源文件"列的索引（第9列）
        source_col_idx = HEADERS.index("来源文件") + 1  # = 9

        # 从最后一行往前遍历删除
        rows_to_delete = []
        for row_idx in range(2, ws.max_row + 1):
            cell_value = ws.cell(row=row_idx, column=source_col_idx).value
            if cell_value == source_file:
                rows_to_delete.append(row_idx)

        if not rows_to_delete:
            logger.info(f"未找到来源文件 '{source_file}' 的记录，无需删除")
            wb.close()
            return False

        # 从后往前删除
        for row_idx in reversed(rows_to_delete):
            ws.delete_rows(row_idx)
            logger.info(f"已删除第 {row_idx} 行（来源文件: {source_file}）")

        wb.save(excel_path)
        logger.info(f"共删除 {len(rows_to_delete)} 条记录（来源文件: {source_file}）")
        return True

    except PermissionError:
        logger.error(f"无法写入 Excel 文件（文件可能被占用）: {excel_path}")
        raise
    except Exception as e:
        logger.error(f"删除 Excel 记录时发生错误: {e}")
        raise
