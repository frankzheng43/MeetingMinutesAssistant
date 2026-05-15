# -*- coding: utf-8 -*-
"""
OCR 工具模块
提供百度 OCR API 的封装，用于图片文字识别
"""

import base64
import logging
import time
import requests

# 配置日志
logger = logging.getLogger(__name__)


class BaiduOCR:
    """百度 OCR 识别类，封装了 access_token 管理和文字识别功能"""

    # 百度 OCR token 获取地址
    TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
    # 百度通用文字识别 API 地址
    OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"

    def __init__(self, api_key: str, secret_key: str):
        """
        初始化百度 OCR 实例

        :param api_key: 百度应用的 API Key
        :param secret_key: 百度应用的 Secret Key
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = None
        self.token_expire_time = 0  # token 过期时间戳
        logger.info("BaiduOCR 实例初始化完成")

    def _ensure_token(self):
        """
        确保 access_token 有效，如果过期则重新获取
        """
        # 检查当前 token 是否还有效（提前 60 秒刷新）
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
                # 默认过期时间为 30 天（2592000 秒），这里记录过期时间戳
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
        """
        识别图片中的文字

        :param image_path: 图片文件路径
        :return: 识别出的纯文本字符串，多个词条用换行符连接
        """
        # 确保 token 有效
        self._ensure_token()

        logger.info(f"开始识别图片: {image_path}")

        try:
            # 读取图片并进行 base64 编码
            with open(image_path, "rb") as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode("utf-8")

            # 调用百度 OCR API
            request_url = f"{self.OCR_URL}?access_token={self.access_token}"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {"image": image_base64}

            response = requests.post(
                request_url, headers=headers, data=data, timeout=30
            )
            response.raise_for_status()
            result = response.json()

            # 解析返回结果
            if "words_result" in result:
                words_list = result["words_result"]
                # 提取所有识别的文字，用换行符连接
                text_lines = [item["words"] for item in words_list]
                full_text = "\n".join(text_lines)
                logger.info(
                    f"图片识别完成，共识别 {len(words_list)} 个词条，"
                    f"文字长度: {len(full_text)}"
                )
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
