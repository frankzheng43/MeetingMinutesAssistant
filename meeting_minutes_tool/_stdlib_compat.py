# -*- coding: utf-8 -*-
"""
标准库兼容模块
仅用于 PyInstaller 打包时让分析器检测到所有可能需要的 stdlib 模块。
运行时不会被实际调用。
"""
# 这些导入确保 PyInstaller 将相关模块打包进 EXE
# 防止 PaddleOCR 等动态加载的包在运行时报 "No module named 'xxx'"

# ---- 基础模块 ----
import uuid
import zoneinfo
import symtable
import ast
import token
import tokenize
import compileall
import py_compile
import genericpath
import stat
import filecmp
import gettext
import locale
import calendar
import datetime

# ---- 标记语言 ----
import html
import html.parser
import html.entities

# ---- 网络协议 ----
import http
import http.client
import http.server
import http.cookies
import http.cookiejar

# ---- XML ----
import xml
import xml.parsers
import xml.parsers.expat
import xml.etree
import xml.etree.ElementTree
import xml.etree.ElementInclude
import xml.dom
import xml.dom.minidom
import xml.sax
import xml.sax.handler

# ---- 压缩归档 ----
import tarfile
import zipfile
import zipimport
import gzip
import bz2
import lzma

# ---- 配置/文件格式 ----
import configparser
import mailbox
import mimetypes
import quopri
import base64
import wave
import csv
import fileinput
import linecache

# ---- 邮件 ----
import email
import email.mime
import email.mime.text
import email.mime.multipart
import email.mime.base
import email.header
import email.charset
import email.encoders
import email.utils

# ---- 数值计算 ----
import numbers
import decimal
import fractions
import random
import statistics
import hashlib
import hmac
import secrets

# ---- IO ----
import io
import codecs

# ---- 网络底层 ----
import socket
import ssl
import selectors
import ftplib
import imaplib
import poplib
import smtplib

# ---- 并发 ----
import _thread
import threading
import asyncio
import concurrent
import concurrent.futures
import multiprocessing
import multiprocessing.connection
import multiprocessing.managers
import multiprocessing.pool
import multiprocessing.sharedctypes

# ---- C 交互 ----
import ctypes
import struct

# ---- 文本处理 ----
import difflib
import pprint
import textwrap
import string
import re

# ---- 其他 ----
import netrc
