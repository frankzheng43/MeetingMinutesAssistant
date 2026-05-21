# -*- coding: utf-8 -*-
"""
导出视图模块
提供按年份和会议类型筛选导出 Excel 的功能
"""

import logging
import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

logger = logging.getLogger(__name__)

# 所有支持的会议类型
ALL_MEETING_TYPES = ["党委会", "董事会", "总经办"]

# 表头定义（与 excel_utils.py 保持一致）
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


class ExportView(tk.Frame):
    """导出标签页视图"""

    def __init__(self, parent, config_callback):
        """
        初始化导出视图

        :param parent: 父容器
        :param config_callback: 获取配置的回调函数
        """
        super().__init__(parent)
        self.config_callback = config_callback

        # 年份和会议类型的选中状态
        self.year_vars = {}       # { "2025": tk.BooleanVar, ... }
        self.type_vars = {}       # { "党委会": tk.BooleanVar, ... }

        self.source_excel_path = None  # 源 Excel 文件路径

        self._build_ui()

    def _build_ui(self):
        """构建界面"""
        main_frame = tk.Frame(self, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ========== 标题 ==========
        title_label = tk.Label(
            main_frame,
            text="📤 导出会议纪要",
            font=("微软雅黑", 14, "bold"),
            anchor="w",
        )
        title_label.pack(fill=tk.X, pady=(0, 10))

        # ========== 源文件信息 ==========
        source_frame = tk.LabelFrame(
            main_frame, text="源数据文件", padx=10, pady=8
        )
        source_frame.pack(fill=tk.X, pady=(0, 10))

        self.source_label = tk.Label(
            source_frame,
            text="（请先保存配置，并确保已生成汇总 Excel）",
            fg="#888888",
            anchor="w",
            wraplength=700,
        )
        self.source_label.pack(fill=tk.X)

        # ========== 过滤条件 ==========
        filter_frame = tk.LabelFrame(
            main_frame, text="筛选条件", padx=10, pady=10
        )
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        # -- 年份选择 --
        year_label = tk.Label(filter_frame, text="选择年份：", font=("", 10, "bold"))
        year_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(0, 5))

        self.year_container = tk.Frame(filter_frame)
        self.year_container.grid(row=0, column=1, sticky="nw", pady=(0, 5))

        # -- 会议类型选择 --
        type_label = tk.Label(filter_frame, text="选择类型：", font=("", 10, "bold"))
        type_label.grid(row=1, column=0, sticky="nw", padx=(0, 10), pady=(0, 5))

        self.type_container = tk.Frame(filter_frame)
        self.type_container.grid(row=1, column=1, sticky="nw", pady=(0, 5))

        # 初始化类型复选框
        self._init_type_checkboxes()

        # 全选/取消按钮行
        btn_row = tk.Frame(filter_frame)
        btn_row.grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))

        tk.Button(btn_row, text="全选年份", command=self._select_all_years,
                  width=10).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_row, text="取消年份", command=self._deselect_all_years,
                  width=10).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_row, text="全选类型", command=self._select_all_types,
                  width=10).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_row, text="取消类型", command=self._deselect_all_types,
                  width=10).pack(side=tk.LEFT, padx=(0, 5))

        # ========== 导出路径 ==========
        path_frame = tk.LabelFrame(
            main_frame, text="导出位置", padx=10, pady=8
        )
        path_frame.pack(fill=tk.X, pady=(0, 10))

        path_row = tk.Frame(path_frame)
        path_row.pack(fill=tk.X)

        self.export_path_var = tk.StringVar()
        self.export_path_entry = tk.Entry(
            path_row, textvariable=self.export_path_var, width=60
        )
        self.export_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        tk.Button(
            path_row, text="选择...", command=self._select_export_dir, width=8
        ).pack(side=tk.RIGHT)

        # ========== 导出按钮 ==========
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        # 刷新按钮
        tk.Button(
            btn_frame,
            text="🔄 刷新数据",
            command=self.refresh_data,
            width=12,
        ).pack(side=tk.LEFT, padx=(0, 10))

        # 导出按钮
        self.export_btn = tk.Button(
            btn_frame,
            text="📤 开始导出",
            command=self._do_export,
            width=14,
            bg="#4472C4",
            fg="white",
            font=("", 10, "bold"),
        )
        self.export_btn.pack(side=tk.LEFT, padx=(0, 5))

        # ========== 日志区域 ==========
        log_frame = tk.LabelFrame(
            main_frame, text="导出日志", padx=5, pady=5
        )
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            log_frame,
            wrap=tk.WORD,
            state="disabled",
            font=("Consolas", 9),
            bg="#1E1E1E",
            fg="#D4D4D4",
            height=10,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 加载数据
        self.refresh_data()

    def _init_type_checkboxes(self):
        """初始化会议类型复选框"""
        for mt in ALL_MEETING_TYPES:
            var = tk.BooleanVar(value=True)  # 默认全选
            self.type_vars[mt] = var
            cb = tk.Checkbutton(
                self.type_container,
                text=mt,
                variable=var,
            )
            cb.pack(side=tk.LEFT, padx=(0, 15))

    def _log(self, message: str, level: str = "info"):
        """输出日志到文本框"""
        self.log_text.configure(state="normal")
        prefix = {"info": "", "warning": "⚠️ ", "error": "❌ "}.get(level, "")
        self.log_text.insert(tk.END, f"{prefix}{message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _select_export_dir(self):
        """选择导出目录"""
        folder = filedialog.askdirectory(title="选择导出目录")
        if folder:
            self.export_path_var.set(folder)

    def refresh_data(self):
        """刷新数据：从源 Excel 读取可用的年份和类型"""
        config = self.config_callback()
        output_dir = config.get("output_dir", "")

        if not output_dir or not os.path.isdir(output_dir):
            self.source_label.config(
                text="⚠️ 输出目录不存在，请先在配置页填写并保存配置",
                fg="#CC6600",
            )
            return

        # 查找源 Excel 文件
        from excel_utils import get_excel_path
        excel_path = get_excel_path(output_dir)

        if not os.path.exists(excel_path):
            self.source_label.config(
                text=f"❌ 未找到汇总 Excel 文件：{excel_path}",
                fg="#CC0000",
            )
            return

        self.source_excel_path = excel_path
        self.source_label.config(
            text=f"✅ 源文件：{excel_path}",
            fg="#006600",
        )

        # 默认导出路径 = 输出目录
        if not self.export_path_var.get():
            self.export_path_var.get()
        if not self.export_path_var.get():
            self.export_path_var.set(output_dir)

        # 读取可用的年份
        try:
            years = self._read_available_years(excel_path)
            self._update_year_checkboxes(years)
            self._log(f"已加载数据，可用年份：{', '.join(sorted(years, reverse=True))}")
        except Exception as e:
            self._log(f"读取年份失败：{e}", "error")

    def _read_available_years(self, excel_path: str) -> set:
        """
        从 Excel 文件中读取所有可用的年份

        :param excel_path: Excel 文件路径
        :return: 年份字符串集合
        """
        years = set()
        wb = load_workbook(excel_path, read_only=True, data_only=True)

        for sheet_name in wb.sheetnames:
            if sheet_name not in ALL_MEETING_TYPES:
                continue

            ws = wb[sheet_name]
            # 第一行是表头，从第二行开始读
            for row in ws.iter_rows(min_row=2, values_only=True):
                if len(row) >= 4 and row[3]:  # 年份在第4列（索引3）
                    year_str = str(row[3]).strip()
                    if re.match(r'^\d{4}$', year_str):
                        years.add(year_str)

        wb.close()
        return years

    def _update_year_checkboxes(self, years: set):
        """
        更新年份复选框

        :param years: 可用年份集合
        """
        # 清空旧的年份复选框
        for widget in self.year_container.winfo_children():
            widget.destroy()
        self.year_vars.clear()

        if not years:
            tk.Label(
                self.year_container,
                text="（无数据）",
                fg="#888888",
            ).pack(side=tk.LEFT)
            return

        # 按年份降序排列（最新的在最前面）
        for year in sorted(years, reverse=True):
            var = tk.BooleanVar(value=True)  # 默认选中
            self.year_vars[year] = var
            cb = tk.Checkbutton(
                self.year_container,
                text=year,
                variable=var,
            )
            cb.pack(side=tk.LEFT, padx=(0, 10))

    def _select_all_years(self):
        """全选年份"""
        for var in self.year_vars.values():
            var.set(True)

    def _deselect_all_years(self):
        """取消全选年份"""
        for var in self.year_vars.values():
            var.set(False)

    def _select_all_types(self):
        """全选类型"""
        for var in self.type_vars.values():
            var.set(True)

    def _deselect_all_types(self):
        """取消全选类型"""
        for var in self.type_vars.values():
            var.set(False)

    def _build_export_filename(self, selected_years: list, selected_types: list) -> str:
        """
        生成导出文件名

        :param selected_years: 选中的年份列表（已排序）
        :param selected_types: 选中的会议类型列表
        :return: 文件名，如 "（2025年、2026年）董事会、党委会纪要.xlsx"
        """
        # 年份部分
        if len(selected_years) == 1:
            year_part = f"（{selected_years[0]}年）"
        else:
            years_str = "、".join(f"{y}年" for y in selected_years)
            year_part = f"（{years_str}）"

        # 类型部分
        types_str = "、".join(selected_types)
        name_part = f"{types_str}纪要"

        return f"{year_part}{name_part}.xlsx"

    def _do_export(self):
        """执行导出"""
        if not self.source_excel_path:
            messagebox.showwarning("提示", "没有源数据文件，请先保存配置并生成汇总 Excel。")
            return

        # 获取选中的年份
        selected_years = sorted([y for y, v in self.year_vars.items() if v.get()])
        if not selected_years:
            messagebox.showwarning("提示", "请至少选择一个年份。")
            return

        # 获取选中的类型
        selected_types = [t for t, v in self.type_vars.items() if v.get()]
        if not selected_types:
            messagebox.showwarning("提示", "请至少选择一个会议类型。")
            return

        # 获取导出目录
        export_dir = self.export_path_var.get().strip()
        if not export_dir or not os.path.isdir(export_dir):
            messagebox.showwarning("提示", "请选择有效的导出目录。")
            return

        # 生成文件名
        filename = self._build_export_filename(selected_years, selected_types)
        export_path = os.path.join(export_dir, filename)

        # 执行导出
        try:
            self.export_btn.configure(state="disabled", text="⏳ 导出中...")
            self._log(f"开始导出：{filename}")
            self._log(f"筛选条件：{'、'.join(selected_years)}年，{'、'.join(selected_types)}")

            # 核心导出逻辑
            result_path = self._export_filtered(
                self.source_excel_path,
                export_path,
                selected_years,
                selected_types,
            )

            self._log(f"✅ 导出完成：{result_path}")
            messagebox.showinfo("导出成功", f"文件已保存到：\n{result_path}")

        except Exception as e:
            self._log(f"导出失败：{e}", "error")
            messagebox.showerror("导出失败", str(e))
        finally:
            self.export_btn.configure(state="normal", text="📤 开始导出")

    def _export_filtered(self, source_path: str, export_path: str,
                        selected_years: list, selected_types: list) -> str:
        """
        按年份和类型筛选数据，导出为新 Excel

        :param source_path: 源 Excel 路径
        :param export_path: 导出目标路径
        :param selected_years: 选中的年份列表
        :param selected_types: 选中的会议类型列表
        :return: 导出的文件路径
        """
        wb_source = load_workbook(source_path, data_only=True)
        wb_export = Workbook()

        # 删除默认 Sheet
        if "Sheet" in wb_export.sheetnames:
            del wb_export["Sheet"]

        total_rows = 0

        for sheet_name in wb_source.sheetnames:
            # 只处理选中且存在的类型
            if sheet_name not in selected_types:
                continue

            ws_source = wb_source[sheet_name]

            # 检查是否有数据
            if ws_source.max_row < 2:
                self._log(f"  Sheet「{sheet_name}」无数据，跳过")
                continue

            # 创建同名 Sheet
            ws_export = wb_export.create_sheet(title=sheet_name)

            # 写入表头
            self._write_header(ws_export)

            # 筛选并写入数据行
            row_count = 0
            for row_idx in range(2, ws_source.max_row + 1):
                row_data = []
                for col_idx in range(1, len(HEADERS) + 1):
                    row_data.append(ws_source.cell(row=row_idx, column=col_idx).value)

                # 年份在第4列（索引3）
                year_val = str(row_data[3] or "").strip() if len(row_data) > 3 else ""
                if year_val in selected_years:
                    self._write_data_row(ws_export, ws_export.max_row + 1, row_data)
                    row_count += 1

            self._log(f"  Sheet「{sheet_name}」：导出 {row_count} 条记录")
            total_rows += row_count

            # 设置列宽
            for col_idx, width in enumerate(COLUMN_WIDTHS, start=1):
                col_letter = chr(64 + col_idx)
                ws_export.column_dimensions[col_letter].width = width

            # 冻结首行
            ws_export.freeze_panes = "A2"

        if total_rows == 0:
            raise RuntimeError("没有符合筛选条件的数据，请检查筛选条件。")

        # 确保目录存在
        os.makedirs(os.path.dirname(export_path), exist_ok=True)

        wb_export.save(export_path)
        wb_source.close()
        wb_export.close()

        self._log(f"  总计导出 {total_rows} 条记录")
        return export_path

    def _write_header(self, ws):
        """写入表头并设置样式（与 excel_utils.py 保持一致）"""
        for col_idx, header in enumerate(HEADERS, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.alignment = HEADER_ALIGNMENT
            cell.border = THIN_BORDER

    def _write_data_row(self, ws, row_idx: int, data: list):
        """写入一行数据并设置样式（与 excel_utils.py 保持一致）"""
        for col_idx, value in enumerate(data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = CELL_ALIGNMENT
            cell.border = THIN_BORDER
