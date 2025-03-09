import os
import json
import time
import httpx
import base64
from io import BytesIO
import numpy as np
import cv2
from typing import Dict, List, Any, Optional, Union
from openai import OpenAI

class LLMClient:
    """LLM客户端，处理与大模型的基础通信，包括文本和多模态"""
    
    def __init__(self, model="gpt-4o-mini", api_key=None, base_url="https://api.openai-proxy.org/v1",
                 mm_model="qwen2.5-vl-72b-instruct", mm_api_key=None, mm_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"):
        """初始化LLM客户端
        
        Args:
            model: 使用的文本模型名称
            api_key: 文本模型API密钥
            base_url: 文本模型API基础URL
            mm_model: 使用的多模态模型名称
            mm_api_key: 多模态模型API密钥
            mm_base_url: 多模态模型API基础URL
        """
        # 文本模型配置
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or "sk-aVnMX4wIWhH0KQS2iaFKULUFJ8Zh1ZAxn2QEb8Op60FjCz0b"
        self.model = model
        self.base_url = base_url
        
        # 多模态模型配置
        self.mm_api_key = mm_api_key or os.environ.get("DASHSCOPE_API_KEY") or "sk-cef474fb2a4e4dfda3e657ec98e4f7e3"
        self.mm_model = mm_model
        self.mm_base_url = mm_base_url
        
        # 初始化客户端
        self._init_client()
        self._init_mm_client()
        
        # 重试相关参数
        self.max_retries = 3
        self.base_wait_time = 2  # seconds
    
    def _init_client(self):
        """初始化文本OpenAI客户端"""
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=httpx.Client(
                timeout=60.0,
                follow_redirects=True
            )
        )
    
    def _init_mm_client(self):
        """初始化多模态客户端"""
        self.mm_client = OpenAI(
            api_key=self.mm_api_key,
            base_url=self.mm_base_url,
            http_client=httpx.Client(
                timeout=60.0,
                follow_redirects=True
            )
        )
    
    def chat_completion(self, messages, **kwargs):
        """发送文本聊天请求
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数，如temperature等
            
        Returns:
            str: 模型返回的内容
        """
        attempt = 0
        while attempt < self.max_retries:
            try:
                temperature = kwargs.get("temperature", 0.7)
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature
                )
                
                # 提取回复文本
                reply = response.choices[0].message.content
                return reply
                
            except Exception as e:
                attempt += 1
                wait_time = self.base_wait_time * (2 ** attempt)  # 指数退避
                
                print(f"API请求失败 (尝试 {attempt}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries:
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print("已达到最大重试次数，请求失败")
                    raise
    
    def _encode_image(self, image):
        """将图像编码为base64字符串
        
        Args:
            image: numpy数组(OpenCV格式)或文件路径
            
        Returns:
            str: base64编码的图像
        """
        if isinstance(image, str):
            # 如果是文件路径，读取图像
            image = cv2.imread(image)
        
        # 确保图像是numpy数组
        if not isinstance(image, np.ndarray):
            raise ValueError("图像必须是numpy数组或有效的文件路径")
        
        # 将OpenCV BGR格式转换为RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 将图像编码为JPEG
        is_success, buffer = cv2.imencode(".jpg", image_rgb)
        if not is_success:
            raise ValueError("图像编码失败")
        
        # 转换为base64字符串
        image_bytes = BytesIO(buffer).getvalue()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        
        return base64_image
    
    def multimodal_chat_completion(self, prompt=None, images=None, messages=None, **kwargs):
        """发送多模态聊天请求
        
        Args:
            prompt: 文本提示 (如果messages为None则使用)
            images: 单个图像(numpy数组或路径)或图像列表
            messages: 消息列表，格式为[{"role": "system", "content": "..."},
                                    {"role": "user", "content": "..."}]
            **kwargs: 其他参数，如temperature等
            
        Returns:
            str: 模型返回的内容
        """
        if not messages and not prompt:
            raise ValueError("必须提供prompt或messages参数")
            
        
        # 如果直接提供了messages，使用它
        if messages:
            # 处理图片：将图片添加到第一个user消息的content中
            if images is not None:
                for i, msg in enumerate(messages):
                    if msg["role"] == "user":
                        # 将内容转换为列表格式
                        if isinstance(msg["content"], str):
                            content = [{"type": "text", "text": msg["content"]}]
                        elif isinstance(msg["content"], list):
                            content = msg["content"]
                        else:
                            content = [{"type": "text", "text": str(msg["content"])}]
                        
                        # 添加图像
                        if not isinstance(images, list):
                            images = [images]
                            
                        for img in images:
                            try:
                                if isinstance(img, str) and (img.startswith("http") or img.startswith("data:")):
                                    content.append({
                                        "type": "image_url",
                                        "image_url": {"url": img}
                                    })
                                else:
                                    base64_img = self._encode_image(img)
                                    content.append({
                                        "type": "image_url",
                                        "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                                    })
                            except Exception as e:
                                print(f"图像处理失败: {str(e)}")
                                continue
                        
                        # 更新消息内容
                        messages[i]["content"] = content
                        break
            
            # 构建完整消息
            openai_messages = messages
        else:
            # 如果没有提供messages，使用prompt构建
            content = []
            
            # 添加文本部分
            content.append({"type": "text", "text": prompt})
            
            # 添加图像部分
            if images:
                if not isinstance(images, list):
                    images = [images]
                
                for img in images:
                    try:
                        if isinstance(img, str) and (img.startswith("http") or img.startswith("data:")):
                            content.append({
                                "type": "image_url",
                                "image_url": {"url": img}
                            })
                        else:
                            base64_img = self._encode_image(img)
                            content.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                            })
                    except Exception as e:
                        print(f"图像处理失败: {str(e)}")
                        continue
            
            # 构建完整消息
            openai_messages = [{"role": "user", "content": content}]
        
        # 发送请求
        attempt = 0
        while attempt < self.max_retries:
            try:
                temperature = kwargs.get("temperature", 0.7)
                response = self.mm_client.chat.completions.create(
                    model=self.mm_model,
                    messages=openai_messages,
                    temperature=temperature
                )
                
                # 提取回复文本
                reply = response.choices[0].message.content
                return reply
                
            except Exception as e:
                attempt += 1
                wait_time = self.base_wait_time * (2 ** attempt)  # 指数退避
                
                print(f"多模态API请求失败 (尝试 {attempt}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries:
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print("已达到最大重试次数，多模态请求失败")
                    raise
    
    def set_model(self, model):
        """设置使用的文本模型"""
        self.model = model
    
    def set_mm_model(self, model):
        """设置使用的多模态模型"""
        self.mm_model = model
    
    def set_api_key(self, api_key):
        """设置文本API密钥"""
        self.api_key = api_key
        self._init_client()
    
    def set_mm_api_key(self, api_key):
        """设置多模态API密钥"""
        self.mm_api_key = api_key
        self._init_mm_client() 