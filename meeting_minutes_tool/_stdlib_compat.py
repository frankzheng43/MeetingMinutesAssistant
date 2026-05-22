# -*- coding: utf-8 -*-
"""
标准库兼容模块
仅用于 PyInstaller 打包时让分析器检测到所有可能需要的 stdlib 模块。
运行时不会被实际调用。
"""
# 这些导入确保 PyInstaller 将相关模块打包进 EXE
# 防止 PaddleOCR 等动态加载的包在运行时报 "No module named 'xxx'"
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
import html
import http
import xml
import tarfile
import zipfile
import gzip
import bz2
import lzma
import configparser
import mailbox
import mimetypes
import quopri
import base64
import wave
import imaplib
import poplib
import smtplib
import ftplib
import fileinput
import linecache
import numbers
import decimal
import fractions
import random
import statistics
import hashlib
import hmac
import secrets
import io
import codecs
import socket
import ssl
import selectors
import ctypes
import struct
import difflib
import pprint
import textwrap
import email
import asyncio
import concurrent
import multiprocessing
