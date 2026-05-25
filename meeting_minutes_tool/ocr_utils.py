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


# ========== 下载目录 ==========

_DEPS_DIRNAME = "ocr_deps"


def _get_program_dir() -> str:
    """获取程序所在目录（EXE 或源码目录）"""
    if hasattr(sys, 'frozen') and getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ========== RapidOCR（本地，ONNX 推理） ==========

class RapidOCREngine(OcrEngine):
    """RapidOCR 本地识别类（基于 ONNX Runtime，轻量快速）"""

    def __init__(self, log_func=None):
        import importlib
        import time
        t0 = time.time()

        self._log = log_func or logger.info

        self._log("[DEBUG] 开始导入 rapidocr 模块...")
        _RapidOCR = importlib.import_module("rapidocr").RapidOCR
        self._log(f"[DEBUG] rapidocr 模块导入完成（{time.time()-t0:.1f}s）")

        self._log("正在加载 RapidOCR 模型（首次自动下载约 15MB 模型文件）...")
        t1 = time.time()
        self._engine = _RapidOCR()
        self._log(f"RapidOCR 模型加载完成（耗时 {time.time()-t1:.1f}s）")

    def recognize(self, image_path: str) -> str:
        import time
        t0 = time.time()
        logger.info(f"开始 RapidOCR 识别: {image_path}")
        result = self._engine(image_path)
        elapsed = time.time() - t0
        if result.txts:
            text = "\n".join(result.txts)
            logger.info(f"RapidOCR 识别完成（耗时 {elapsed:.1f}s），{len(result.txts)} 行")
            return text
        logger.warning(f"RapidOCR 未识别到文字: {image_path}")
        return ""


# ========== 下载管理 ==========

def _ensure_rapidocr_downloaded(program_dir: str = None, log_func=None) -> bool:
    """确保 RapidOCR + onnxruntime 已安装（轻量，约 30MB）"""
    if log_func is None:
        log_func = logger.info

    if program_dir is None:
        program_dir = _get_program_dir()

    target_dir = os.path.join(program_dir, _DEPS_DIRNAME)

    # 检查是否已下载
    marker = os.path.join(target_dir, "rapidocr", "__init__.py")
    if os.path.exists(marker):
        if target_dir not in sys.path:
            sys.path.insert(0, target_dir)
        log_func("RapidOCR 依赖已就绪")
        return True

    log_func("正在下载 RapidOCR + onnxruntime（约 30MB）...")
    log_func(f"下载目标：{target_dir}")

    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "pip", "install",
             "rapidocr", "onnxruntime",
             "--target", str(target_dir), "--no-warn-script-location"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace",
        )

        returncode = None
        while True:
            line = process.stdout.readline()
            if line:
                line = line.rstrip()
                if line:
                    log_func(f"  {line}")
            if process.poll() is not None:
                for leftover in process.stdout.readlines():
                    leftover = leftover.rstrip()
                    if leftover:
                        log_func(f"  {leftover}")
                returncode = process.returncode
                break

        if returncode != 0:
            log_func(f"[ERR]  RapidOCR 下载失败（退出码 {returncode}）")
            return False

        if target_dir not in sys.path:
            sys.path.insert(0, target_dir)

        try:
            import rapidocr
            log_func(f"[OK]  RapidOCR 下载完成（{_dir_size(target_dir)} MB）")
            return True
        except ImportError as e:
            log_func(f"[ERR]  RapidOCR 下载后导入失败：{e}")
            return False

    except Exception as e:
        log_func(f"[ERR]  RapidOCR 下载异常：{e}")
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

    if engine_type == "rapidocr":
        if not _ensure_rapidocr_downloaded(log_func=log_func):
            raise RuntimeError("RapidOCR 未就绪，请检查日志")
        return RapidOCREngine(log_func=log_func)

    # 默认百度 OCR
    api_key = config.get("api_key", "")
    secret_key = config.get("secret_key", "")
    if not api_key or not secret_key:
        raise RuntimeError("百度 OCR 未配置 API Key 和 Secret Key")
    return BaiduOCR(api_key, secret_key)
