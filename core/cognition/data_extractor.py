import json
import logging
from typing import Dict, List, Any, Optional
from .llm_client import LLMClient
from .prompt_templates import PromptTemplates

class DataExtractor:
    """数据提取器，从OCR结果中提取结构化数据"""
    
    def __init__(self, model="gpt-4o-mini"):
        """初始化数据提取器"""
        self.llm = LLMClient(model=model)
        self.templates = PromptTemplates()
    
    def extract_product_info(self, text_elements):
        """从文本元素中提取商品信息
        
        Args:
            text_elements: OCR识别的文本元素列表
            
        Returns:
            dict: 提取的商品信息
        """
        # 使用文本提取模板
        system_message = self.templates.text_extraction()
        
        # 构建OCR结果表示
        ocr_text = "OCR识别结果:\n"
        for i, elem in enumerate(text_elements, 1):
            ocr_text += f"{i}. '{elem['text']}' 位置:({elem['center'][0]},{elem['center'][1]})\n"
        
        user_message = {
            "role": "user",
            "content": f"""
            {ocr_text}
            
            请从上述文本中提取商品信息，包括:
            - title: 商品标题
            - price: 价格(仅数字部分)
            - original_price: 原价(如有)
            - discount: 折扣信息(如有)
            - specifications: 规格信息(如有)
            - tags: 标签列表(如有)
            
            以JSON格式返回结果。对于未找到的字段，使用null值。
            """
        }
        
        messages = [system_message, user_message]
        response = self.llm.chat_completion(messages)
        
        try:
            # 尝试解析JSON响应
            product_info = json.loads(response)
            return product_info
        except:
            logging.warning("无法解析商品提取结果")
            return {"error": "提取失败", "raw_response": response}
    
    def extract_list_items(self, text_elements, item_type="product"):
        """从列表页提取多个项目
        
        Args:
            text_elements: OCR识别的文本元素列表
            item_type: 项目类型(商品/评论等)
            
        Returns:
            list: 提取的项目列表
        """
        system_message = self.templates.text_extraction()
        
        # 构建OCR结果表示
        ocr_text = "OCR识别结果:\n"
        for i, elem in enumerate(text_elements, 1):
            ocr_text += f"{i}. '{elem['text']}' 位置:({elem['center'][0]},{elem['center'][1]})\n"
        
        user_message = {
            "role": "user",
            "content": f"""
            {ocr_text}
            
            请从上述文本中提取{item_type}列表，将页面上的多个{item_type}识别并分组。
            每个{item_type}应包含:
            - name: 名称/标题
            - description: 描述(如有)
            - price: 价格(如有)
            - position: 大致位置描述(顶部/中部/底部/左侧/右侧等)
            
            以JSON格式返回结果，使用items作为列表键名。
            """
        }
        
        messages = [system_message, user_message]
        response = self.llm.chat_completion(messages)
        
        try:
            # 尝试解析JSON响应
            result = json.loads(response)
            return result.get("items", [])
        except:
            logging.warning(f"无法解析{item_type}列表提取结果")
            return []
    
    def extract_form_fields(self, text_elements):
        """提取表单字段信息"""
        system_message = self.templates.text_extraction()
        
        # 构建OCR结果表示
        ocr_text = "OCR识别结果:\n"
        for i, elem in enumerate(text_elements, 1):
            ocr_text += f"{i}. '{elem['text']}' 位置:({elem['center'][0]},{elem['center'][1]})\n"
        
        user_message = {
            "role": "user",
            "content": f"""
            {ocr_text}
            
            请识别页面上的表单字段，包括:
            - labels: 字段标签列表
            - inputs: 输入框位置列表
            - required: 必填字段列表
            - buttons: 表单按钮列表
            
            以JSON格式返回结果。
            """
        }
        
        messages = [system_message, user_message]
        response = self.llm.chat_completion(messages)
        
        try:
            # 尝试解析JSON响应
            form_info = json.loads(response)
            return form_info
        except:
            logging.warning("无法解析表单字段提取结果")
            return {"error": "表单提取失败"}
    
    def extract_product_info_with_vision(self, screenshot, text_elements):
        """使用多模态模型从屏幕提取商品信息
        
        Args:
            screenshot: 屏幕截图
            text_elements: OCR识别的文本元素列表
            
        Returns:
            dict: 提取的商品信息
        """
        # 构建OCR结果表示
        ocr_text = "OCR识别结果:\n"
        for i, elem in enumerate(text_elements, 1):
            ocr_text += f"{i}. '{elem['text']}' 位置:({elem['center'][0]},{elem['center'][1]})\n"
        
        prompt = f"""
        {ocr_text}
        
        请分析这个屏幕截图，提取商品信息，包括:
        - title: 商品标题
        - price: 价格(仅数字部分)
        - original_price: 原价(如有)
        - discount: 折扣信息(如有)
        - specifications: 规格信息(如有)
        - tags: 标签列表(如有)
        - images: 商品图片描述(如有)
        
        以JSON格式返回结果。对于未找到的字段，使用null值。
        请同时考虑图像中可能未被OCR识别到的视觉信息。
        """
        
        try:
            response = self.llm.multimodal_chat_completion(prompt, screenshot)
            
            # 尝试解析JSON响应
            try:
                product_info = json.loads(response)
                return product_info
            except:
                logging.warning("无法解析多模态商品提取结果")
                return {"error": "提取失败", "raw_response": response}
        except Exception as e:
            logging.error(f"多模态提取失败: {str(e)}")
            return {"error": f"多模态提取失败: {str(e)}"} 