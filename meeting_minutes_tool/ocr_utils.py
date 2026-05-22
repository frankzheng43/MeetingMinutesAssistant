# -*- coding: utf-8 -*-
"""
OCR 引擎模块
提供百度 OCR 和 PaddleOCR（本地）两种引擎的统一接口
"""

import base64
import logging
import os
import subprocess
import sys
import time
from abc import ABC, abstractmethod

import requests

logger = logging.getLogger(__name__)

# ========== 抽象基类 ==========

class OcrEngine(ABC):
    """OCR 引擎抽象基类"""

    @abstractmethod
    def recognize(self, image_path: str) -> str:
        ...


# ========== 百度 OCR ==========

class BaiduOCR(OcrEngine):
    """百度 OCR 识别类，封装了 access_token 管理和文字识别功能"""

    TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
    OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"

    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = None
        self.token_expire_time = 0
        logger.info("BaiduOCR 实例初始化完成")

    def _ensure_token(self):
        if self.access_token and time.time() < self.token_expire_time - 60:
            return
        logger.info("正在获取百度 OCR access_token...")
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key,
        }
        try:
            response = requests.post(self.TOKEN_URL, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            if "access_token" in result:
                self.access_token = result["access_token"]
                expires_in = result.get("expires_in", 2592000)
                self.token_expire_time = time.time() + expires_in
                logger.info("百度 OCR access_token 获取成功")
            else:
                error_msg = result.get("error_description", "未知错误")
                logger.error(f"获取 access_token 失败: {error_msg}")
                raise RuntimeError(f"获取 access_token 失败: {error_msg}")
        except requests.RequestException as e:
            logger.error(f"请求百度 token 接口异常: {e}")
            raise

    def recognize(self, image_path: str) -> str:
        self._ensure_token()
        logger.info(f"开始识别图片: {image_path}")
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode("utf-8")
            request_url = f"{self.OCR_URL}?access_token={self.access_token}"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {"image": image_base64}
            response = requests.post(request_url, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            if "words_result" in result:
                words_list = result["words_result"]
                text_lines = [item["words"] for item in words_list]
                full_text = "\n".join(text_lines)
                logger.info(f"图片识别完成，共识别 {len(words_list)} 个词条，文字长度: {len(full_text)}")
                return full_text
            else:
                error_msg = result.get("error_msg", "未知错误")
                logger.error(f"OCR 识别失败: {error_msg}")
                raise RuntimeError(f"OCR 识别失败: {error_msg}")
        except FileNotFoundError:
            logger.error(f"图片文件不存在: {image_path}")
            raise
        except requests.RequestException as e:
            logger.error(f"请求 OCR API 异常: {e}")
            raise
        except Exception as e:
            logger.error(f"OCR 识别过程发生未知错误: {e}")
            raise


# ========== PaddleOCR（本地） ==========

PADDLE_DIRNAME = "paddle_deps"


class PaddleOCREngine(OcrEngine):
    """PaddleOCR 本地识别类"""

    def __init__(self, log_func=None):
        from paddleocr import PaddleOCR as _PaddleOCR
        self._log(f"正在加载 PaddleOCR 模型（首次加载需下载模型文件）...")
        # use_angle_cls=True 启用文字方向分类，lang='ch' 中文模型
        self._engine = _PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
        self._log("PaddleOCR 加载完成")

    def _log(self, msg):
        logger.info(msg)

    def recognize(self, image_path: str) -> str:
        logger.info(f"开始 PaddleOCR 识别: {image_path}")
        result = self._engine.ocr(image_path, cls=True)
        if not result or not result[0]:
            logger.warning(f"PaddleOCR 未识别到文字: {image_path}")
            return ""

        # result 格式：[[[bbox, (text, confidence)], ...], ...]
        lines = []
        for page in result:
            for line in page:
                text = line[1][0]  # (text, confidence)
                if text and text.strip():
                    lines.append(text.strip())

        full_text = "\n".join(lines)
        logger.info(f"PaddleOCR 识别完成，共 {len(lines)} 行，文字长度: {len(full_text)}")
        return full_text


# ========== 下载管理 ==========

def _get_program_dir() -> str:
    """获取程序所在目录（EXE 或源码目录）"""
    if hasattr(sys, 'frozen') and getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    # 源码模式：ocr_engine.py 所在目录的父目录
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ensure_paddle_downloaded(program_dir: str = None, log_func=None) -> bool:
    """
    确保 PaddleOCR 已下载到本地目录
    如果不存在则自动 pip install --target

    :param program_dir: 程序根目录（默认自动检测）
    :param log_func: 日志回调
    :return: 是否就绪
    """
    if log_func is None:
        log_func = logger.info

    if program_dir is None:
        program_dir = _get_program_dir()

    target_dir = os.path.join(program_dir, PADDLE_DIRNAME)

    # 检查是否已下载（通过检查 paddleocr 包是否存在）
    marker = os.path.join(target_dir, "paddleocr", "__init__.py")
    if os.path.exists(marker):
        if target_dir not in sys.path:
            sys.path.insert(0, target_dir)
        log_func("PaddleOCR 依赖已就绪")
        return True

    log_func("正在下载 PaddleOCR（首次使用需下载约 200MB 依赖，请耐心等待）...")
    log_func(f"下载目标：{target_dir}")

    try:
        # 使用 Popen 实时输出下载进度
        process = subprocess.Popen(
            [sys.executable, "-m", "pip", "install", "paddleocr",
             "--target", str(target_dir), "--no-warn-script-location"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace",
        )

        # 逐行读取并输出到日志
        returncode = None
        last_line = ""
        while True:
            line = process.stdout.readline()
            if line:
                line = line.rstrip()
                if line:
                    log_func(f"  {line}")
                    last_line = line
            if process.poll() is not None:
                # 进程结束，读取剩余输出
                for leftover in process.stdout.readlines():
                    leftover = leftover.rstrip()
                    if leftover:
                        log_func(f"  {leftover}")
                        last_line = leftover
                returncode = process.returncode
                break

        if returncode != 0:
            log_func(f"[ERR]  PaddleOCR 下载失败（退出码 {returncode}），请检查网络后重试")
            return False

        if target_dir not in sys.path:
            sys.path.insert(0, target_dir)

        # 验证能导入
        try:
            import paddleocr
            log_func(f"[OK]  PaddleOCR 下载完成（{_dir_size(target_dir)} MB）")
            return True
        except ImportError as e:
            log_func(f"[ERR]  PaddleOCR 下载后导入失败：{e}")
            return False

    except subprocess.TimeoutExpired:
        log_func("[ERR]  PaddleOCR 下载超时（超过 10 分钟），请检查网络后重试")
        return False
    except Exception as e:
        log_func(f"[ERR]  PaddleOCR 下载异常：{e}")
        return False


def _dir_size(path: str) -> str:
    """计算目录大小（MB）"""
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return f"{total / 1024 / 1024:.0f}"


# ========== 工厂函数 ==========

def create_ocr_engine(config: dict, log_func=None) -> OcrEngine:
    """
    根据配置创建 OCR 引擎

    :param config: 配置字典，需包含 ocr_engine（baidu/paddle）
    :param log_func: 日志回调
    :return: OcrEngine 实例
    """
    engine_type = config.get("ocr_engine", "baidu")

    if engine_type == "paddle":
        if not ensure_paddle_downloaded(log_func=log_func):
            raise RuntimeError("PaddleOCR 未就绪，请检查日志")
        return PaddleOCREngine(log_func=log_func)

    # 默认百度 OCR
    api_key = config.get("api_key", "")
    secret_key = config.get("secret_key", "")
    if not api_key or not secret_key:
        raise RuntimeError("百度 OCR 未配置 API Key 和 Secret Key")
    return BaiduOCR(api_key, secret_key)
