# -*- coding: utf-8 -*-
"""
LLM 工具模块
提供 DeepSeek API 的封装，用于从 OCR 文本中提取会议纪要信息
支持三种会议类型：党委会、董事会、总经办
"""

import json
import logging
import os
import re
import requests

# 配置日志
logger = logging.getLogger(__name__)

# ========== 三种会议类型的专用提示词 ==========

SYSTEM_PROMPT_PARTY = (
    "你是一个专业的会议纪要解析助手。以下是一份【党委会会议纪要】的OCR识别文本，请从中提取结构化信息，返回严格的JSON格式。\n\n"
    "格式要求：\n"
    "1. record_number: 纪要号，例如\"〔2026〕10号\"，从文档标题附近提取\n"
    "2. meeting_info: 会议基本信息对象，包含：\n"
    "   - date: 会议日期（如\"2026年4月10日\"）\n"
    "   - presider: 主持人（如\"李文杰\"）\n"
    "   - meeting_name: 会议名称（如\"集团党委会议\"）\n"
    "3. items: 议题列表，每个议题包含：\n"
    "   - title: 议题标题（去除编号的纯标题）\n"
    "   - content: 该议题的完整内容\n\n"
    "识别规则：\n"
    "- 党委会纪要通常在\"二、议定事项\"或\"议定事项\"标题下列出编号议题（一）（二）（三）...\n"
    "- 每个编号对应一个议题，提取其标题和完整内容\n"
    "- 注意\"一、传达学习\"部分通常是一个单独的议题，也需要提取\n"
    "- 如果OCR文本中有明显的识别错误（如错字、漏字），请根据上下文合理纠正\n\n"
    '返回格式：{"record_number": "〔2026〕10号", "meeting_info": {"date": "2026年4月10日", "presider": "李文杰", "meeting_name": "集团党委会议"}, "items": [{"title": "...", "content": "..."}, ...]}\n'
    "如果没有找到，record_number 为空字符串，meeting_info 为空对象，items 为空数组。"
)

SYSTEM_PROMPT_BOARD = (
    "你是一个专业的会议纪要解析助手。以下是一份【董事会决议】的OCR识别文本，请从中提取结构化信息，返回严格的JSON格式。\n\n"
    "格式要求：\n"
    "1. record_number: 决议编号，例如\"〔2026〕2号\"，从文档标题附近提取\n"
    "2. meeting_info: 会议基本信息对象，包含：\n"
    "   - date: 会议日期（如\"2026年1月23日\"）\n"
    "   - presider: 主持人（如\"李文杰\"）\n"
    "   - meeting_name: 会议名称（如\"2026年第2次董事会\"）\n"
    "3. items: 议题列表，每个议题包含：\n"
    "   - title: 议题标题（去除编号的纯标题，如\"研究2025年度考核工作方案的议案\"）\n"
    "   - content: 该议题的完整内容，包括党委会议意见和投票结果\n\n"
    "识别规则：\n"
    "- 董事会决议的议题通常以\"一、\"\"二、\"\"三、\"等中文数字编号\n"
    "- 每个议题标题通常是\"研究...的议案\"或\"研究...有关事宜\"格式\n"
    "- 每个议题内容包括：党委会议意见、投票结果（如\"同意7票，反对0票，弃权0票\"）\n"
    "- 请将党委会议意见和投票结果都包含在content中\n"
    "- 如果OCR文本中有明显的识别错误（如错字、漏字），请根据上下文合理纠正\n\n"
    '返回格式：{"record_number": "〔2026〕2号", "meeting_info": {"date": "2026年1月23日", "presider": "李文杰", "meeting_name": "2026年第2次董事会"}, "items": [{"title": "研究...的议案", "content": "党委会议意见：...\\n投票结果：同意7票..."}, ...]}\n'
    "如果没有找到，record_number 为空字符串，meeting_info 为空对象，items 为空数组。"
)

SYSTEM_PROMPT_GM = (
    "你是一个专业的会议纪要解析助手。以下是一份【总经理办公会议纪要】的OCR识别文本，请从中提取结构化信息，返回严格的JSON格式。\n\n"
    "格式要求：\n"
    "1. record_number: 纪要编号，例如\"〔2026〕4号\"，从文档标题附近提取\n"
    "2. meeting_info: 会议基本信息对象，包含：\n"
    "   - date: 会议日期（如\"2026年3月31日\"）\n"
    "   - presider: 主持人（如\"蔡风飞\"）\n"
    "   - meeting_name: 会议名称（如\"集团总经理办公会议\"）\n"
    "3. items: 议题列表，每个议题包含：\n"
    "   - title: 议题标题（去除编号的纯标题）\n"
    "   - content: 该议题的完整内容\n\n"
    "识别规则：\n"
    "- 总经办纪要分为两大部分：\"一、督查落实 贯彻落实董事会决议\"和\"二、研究事项\"\n"
    "- 在\"一、督查落实\"部分，每个子项用（一）（二）（三）...编号，内容通常是\"会议指出，请XX部门根据...文件精神，按程序办理\"\n"
    "- 在\"二、研究事项\"部分，每个子项用（一）（二）（三）...编号，每个议题包含汇报和会议研究决定的内容\n"
    "- 请提取所有编号的议题（包括督查落实和研究事项两部分）\n"
    "- 如果OCR文本中有明显的识别错误（如错字、漏字），请根据上下文合理纠正\n\n"
    '返回格式：{"record_number": "〔2026〕4号", "meeting_info": {"date": "2026年3月31日", "presider": "蔡风飞", "meeting_name": "集团总经理办公会议"}, "items": [{"title": "...", "content": "..."}, ...]}\n'
    "如果没有找到，record_number 为空字符串，meeting_info 为空对象，items 为空数组。"
)


def detect_meeting_type(filename: str) -> str:
    """
    根据文件名检测会议类型

    :param filename: PDF文件名
    :return: "party"（党委会）, "board"（董事会）, "gm"（总经办）, 或 "unknown"
    """
    name_lower = filename.lower()
    if "党委" in name_lower:
        return "party"
    elif "董事" in name_lower:
        return "board"
    elif "总经办" in name_lower or "总经理" in name_lower:
        return "gm"
    else:
        return "unknown"


def get_system_prompt(meeting_type: str) -> str:
    """
    根据会议类型获取对应的系统提示词

    :param meeting_type: 会议类型
    :return: 系统提示词
    """
    prompts = {
        "party": SYSTEM_PROMPT_PARTY,
        "board": SYSTEM_PROMPT_BOARD,
        "gm": SYSTEM_PROMPT_GM,
    }
    return prompts.get(meeting_type, SYSTEM_PROMPT_PARTY)


def get_meeting_type_name(meeting_type: str) -> str:
    """获取会议类型的中文名称"""
    names = {
        "party": "党委会",
        "board": "董事会",
        "gm": "总经办",
        "unknown": "未知类型",
    }
    return names.get(meeting_type, "未知类型")


def extract_record_number_from_filename(filename: str) -> str:
    """
    从文件名中正则提取纪要编号
    优先从文件名解析，失败则返回空字符串（后续由 AI 从内容提取）

    支持的格式：
    - 党委会〔2026〕4号.pdf
    - 党委会【2026】4号.pdf
    - 董事会[2026]4号.pdf
    - 总经办（2026）4号.pdf
    - 党委会〔2018〕9期.pdf           （期 = 号）
    - 总经办〔2021〕第10期.pdf         （自动去掉"第"）

    :param filename: 文件名（不含路径）
    :return: 纪要编号，如 "党委会〔2026〕4号" 或 "党委会〔2018〕9期"
    """
    # 去掉扩展名
    name_no_ext = os.path.splitext(filename)[0]

    # 匹配模式：会议类型 + 括号 + 年份 + 括号 + 可选"第" + 序号 + 号/期
    # 支持各种括号：〔〕【】[]（）()
    # 期和号视为等价
    pattern = r'^(.+?)[〔【\[（(]\s*(\d{4})\s*[〕】\]）)]\s*(第)?\s*(\d+)\s*(号|期)$'
    match = re.match(pattern, name_no_ext)
    if match:
        prefix = match.group(1)  # 党委会/董事会/总经办
        year = match.group(2)    # 2026
        number = match.group(4)  # 4（跳过第3组"第"）
        suffix = match.group(5)  # 号 或 期
        return f"{prefix}〔{year}〕{number}{suffix}"

    return ""


def extract_publish_date_from_text(ocr_text: str, meeting_type: str) -> str:
    """
    从 OCR 文本中正则提取印发时间

    党委会格式：XXXX年XX月XX日印发
    董事会/总经办格式：XXXX年XX月XX日

    :param ocr_text: OCR 识别文本
    :param meeting_type: 会议类型（party/board/gm）
    :return: 印发时间字符串，如 "2026年5月14日"
    """
    if meeting_type == "party":
        # 党委会：匹配 "XXXX年XX月XX日印发"
        pattern = r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*印发'
        match = re.search(pattern, ocr_text)
        if match:
            return f"{match.group(1)}年{match.group(2)}月{match.group(3)}日"
    else:
        # 董事会/总经办：匹配 "XXXX年XX月XX日"
        pattern = r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日'
        matches = list(re.finditer(pattern, ocr_text))
        if matches:
            # 取最后一个匹配（印发时间通常在文件末尾）
            last = matches[-1]
            return f"{last.group(1)}年{last.group(2)}月{last.group(3)}日"

    return ""


def extract_publish_date_via_ai(ocr_text: str, api_key: str, meeting_type_name: str) -> str:
    """
    调用 DeepSeek API 从 OCR 文本中提取印发时间（正则失败时的兜底方案）

    :param ocr_text: OCR 识别文本
    :param api_key: DeepSeek API 密钥
    :param meeting_type_name: 会议类型中文名
    :return: 印发时间字符串
    """
    system_prompt = (
        f"你是一个文档解析助手。以下是一份【{meeting_type_name}】文档的OCR识别文本，"
        f"请从中提取【印发时间】或【印发日期】。\n"
        f"印发时间通常在文档末尾附近。\n"
        f"请只返回日期，格式如\"2026年5月14日\"，不要返回其他内容。\n"
        f"如果找不到，请返回空字符串。"
    )

    # 取文本末尾 2000 字符（印发时间通常在末尾）
    tail_text = ocr_text[-2000:] if len(ocr_text) > 2000 else ocr_text

    payload = {
        "model": "deepseek-v4-flash",
        "temperature": 0.1,
        "max_tokens": 128,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请提取印发时间：\n\n{tail_text}"},
        ],
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()

        # 验证返回的是否是日期格式
        if re.match(r'\d{4}年\d{1,2}月\d{1,2}日', content):
            return content
        return ""
    except Exception as e:
        logger.warning(f"AI 提取印发时间失败: {e}")
        return ""


def extract_minutes(ocr_text: str, api_key: str, filename: str = "") -> dict:
    """
    调用 DeepSeek API 从 OCR 文本中提取会议纪要信息

    :param ocr_text: OCR 识别出的完整文本
    :param api_key: DeepSeek API 密钥
    :param filename: PDF文件名，用于自动检测会议类型
    :return: 包含 record_number, meeting_info, items, publish_date 的字典
    """
    # 检测会议类型
    meeting_type = detect_meeting_type(filename)
    meeting_type_name = get_meeting_type_name(meeting_type)
    logger.info(f"检测到会议类型: {meeting_type_name} (类型代码: {meeting_type})")

    # 优先从文件名正则提取纪要编号
    record_number = extract_record_number_from_filename(filename)
    if record_number:
        logger.info(f"从文件名正则提取到纪要编号: {record_number}")
    else:
        logger.info("文件名正则未提取到纪要编号，将由 AI 从内容提取")

    # 优先从 OCR 文本正则提取印发时间
    publish_date = extract_publish_date_from_text(ocr_text, meeting_type)
    if publish_date:
        logger.info(f"从 OCR 文本正则提取到印发时间: {publish_date}")
    else:
        logger.info("正则未提取到印发时间，将由 AI 提取")

    # 获取对应的系统提示词
    system_prompt = get_system_prompt(meeting_type)

    logger.info(f"开始调用 DeepSeek API 提取会议纪要信息 (类型: {meeting_type_name})")

    # 拼接系统提示词和用户文本
    user_message = f"请从以下OCR文本中提取会议纪要信息：\n\n{ocr_text}"

    # 构建请求数据
    payload = {
        "model": "deepseek-v4-flash",
        "temperature": 0.1,
        "max_tokens": 8192,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        # 调用 DeepSeek API
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        result = response.json()

        # 提取返回的文本内容
        if "choices" not in result or len(result["choices"]) == 0:
            logger.error("DeepSeek API 返回结果中没有 choices")
            return {"record_number": "", "meeting_info": {}, "items": [], "meeting_type": meeting_type}

        content = result["choices"][0]["message"]["content"]
        logger.info(f"DeepSeek API 返回原始内容长度: {len(content)}")

        # 尝试解析 JSON
        parsed_result = _parse_json_response(content)

        # 如果文件名正则没提取到纪要编号，用 AI 提取的结果
        if not record_number:
            record_number = parsed_result.get("record_number", "")

        # 如果正则没提取到印发时间，用 AI 提取
        if not publish_date:
            publish_date = extract_publish_date_via_ai(ocr_text, api_key, meeting_type_name)

        # 添加会议类型信息
        parsed_result["meeting_type"] = meeting_type
        parsed_result["meeting_type_name"] = meeting_type_name
        parsed_result["record_number"] = record_number
        parsed_result["publish_date"] = publish_date

        return parsed_result

    except requests.RequestException as e:
        logger.error(f"请求 DeepSeek API 异常: {e}")
        return {"record_number": "", "meeting_info": {}, "items": [], "meeting_type": meeting_type}
    except json.JSONDecodeError as e:
        logger.error(f"解析 DeepSeek 返回 JSON 失败: {e}")
        return {"record_number": "", "meeting_info": {}, "items": [], "meeting_type": meeting_type}
    except Exception as e:
        logger.error(f"调用 DeepSeek API 发生未知错误: {e}")
        return {"record_number": "", "meeting_info": {}, "items": [], "meeting_type": meeting_type}


def _parse_json_response(content: str) -> dict:
    """
    解析 LLM 返回的文本，尝试提取 JSON 内容

    :param content: LLM 返回的原始文本
    :return: 解析后的字典
    """
    # 尝试直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 尝试提取 markdown 代码块中的 JSON
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
    if json_match:
        json_str = json_match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # 尝试查找最外层的大括号
    brace_match = re.search(r"\{[\s\S]*\}", content)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass

    logger.error("无法从 LLM 返回内容中解析出有效的 JSON")
    return {"record_number": "", "meeting_info": {}, "items": []}
