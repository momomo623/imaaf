import numpy as np
import logging
import difflib
from typing import List, Dict, Any, Tuple, Optional
import cv2

class TextMatcher:
    """文本匹配器，提供基于OCR结果的文本检索和匹配功能"""
    
    def __init__(self):
        """初始化文本匹配器"""
        self.similarity_threshold = 0.6  # 相似度阈值
    
    def find_text(self, query: str, text_elements: List[Dict], exact_match=False) -> List[Dict]:
        """查找匹配指定查询文本的元素
        
        Args:
            query: 查询文本
            text_elements: OCR识别的文本元素列表
            exact_match: 是否进行精确匹配，默认为模糊匹配
            
        Returns:
            list: 按相似度排序的匹配元素列表
        """
        if not text_elements:
            return []
        
        matches = []
        
        for element in text_elements:
            text = element.get("text", "")
            
            if exact_match:
                # 精确匹配
                if query == text:
                    element["similarity"] = 1.0
                    matches.append(element)
            else:
                # 模糊匹配，计算相似度
                similarity = self._calculate_similarity(query, text)
                if similarity >= self.similarity_threshold:
                    element_copy = element.copy()
                    element_copy["similarity"] = similarity
                    matches.append(element_copy)
        
        # 按相似度降序排序
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return matches
    
    def find_best_match(self, query: str, text_elements: List[Dict]) -> Optional[Dict]:
        """查找最佳匹配元素
        
        Args:
            query: 查询文本
            text_elements: OCR识别的文本元素列表
            
        Returns:
            dict: 最佳匹配元素，如果没有匹配项则返回None
        """
        matches = self.find_text(query, text_elements)
        return matches[0] if matches else None
    
    def find_closest_element(self, target_position: Tuple[float, float], text_elements: List[Dict]) -> Optional[Dict]:
        """查找距离指定位置最近的文本元素
        
        Args:
            target_position: 目标位置 (x, y)
            text_elements: OCR识别的文本元素列表
            
        Returns:
            dict: 距离最近的元素，如果列表为空则返回None
        """
        if not text_elements:
            return None
        
        closest_element = None
        min_distance = float('inf')
        
        target_x, target_y = target_position
        
        for element in text_elements:
            center = element.get("center")
            if not center:
                continue
            
            center_x, center_y = center
            distance = np.sqrt((center_x - target_x) ** 2 + (center_y - target_y) ** 2)
            
            if distance < min_distance:
                min_distance = distance
                closest_element = element
        
        return closest_element
    
    def find_text_in_region(self, query: str, text_elements: List[Dict], region: Tuple[float, float, float, float]) -> List[Dict]:
        """在指定区域内查找匹配文本
        
        Args:
            query: 查询文本
            text_elements: OCR识别的文本元素列表
            region: 区域范围 (x1, y1, x2, y2)
            
        Returns:
            list: 区域内匹配的元素列表
        """
        x1, y1, x2, y2 = region
        
        # 过滤出区域内的元素
        elements_in_region = []
        for element in text_elements:
            center = element.get("center")
            if not center:
                continue
            
            center_x, center_y = center
            if x1 <= center_x <= x2 and y1 <= center_y <= y2:
                elements_in_region.append(element)
        
        # 在区域内的元素中查找匹配项
        return self.find_text(query, elements_in_region)
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """计算两个字符串的相似度
        
        Args:
            str1: 第一个字符串
            str2: 第二个字符串
            
        Returns:
            float: 相似度分数 (0-1)
        """
        # 使用difflib计算相似度
        return difflib.SequenceMatcher(None, str1, str2).ratio()
    
    def find_element_by_content_type(self, 
                                     text_elements: List[Dict], 
                                     content_type: str, 
                                     region: Optional[Tuple[float, float, float, float]] = None) -> List[Dict]:
        """根据内容类型查找元素（如数字、价格、日期等）
        
        Args:
            text_elements: OCR识别的文本元素列表
            content_type: 内容类型，支持"number"、"price"、"date"等
            region: 可选的搜索区域 (x1, y1, x2, y2)
            
        Returns:
            list: 匹配的元素列表
        """
        # 首先根据区域过滤
        if region:
            x1, y1, x2, y2 = region
            filtered_elements = [e for e in text_elements if e.get("center") and
                               x1 <= e["center"][0] <= x2 and
                               y1 <= e["center"][1] <= y2]
        else:
            filtered_elements = text_elements
        
        results = []
        
        # 根据不同的内容类型进行匹配
        if content_type == "number":
            # 匹配纯数字
            for element in filtered_elements:
                text = element.get("text", "")
                if text.isdigit():
                    results.append(element)
                    
        elif content_type == "price":
            # 匹配价格格式 (包含¥或数字+小数点)
            for element in filtered_elements:
                text = element.get("text", "")
                if "¥" in text or "￥" in text or \
                   (any(c.isdigit() for c in text) and "." in text):
                    results.append(element)
                    
        elif content_type == "date":
            # 匹配日期格式
            for element in filtered_elements:
                text = element.get("text", "")
                if "-" in text and any(c.isdigit() for c in text):
                    results.append(element)
        
        return results
    
    def visualize_matches(self, image, matched_elements, query=None):
        """可视化匹配结果
        
        Args:
            image: 原始图像
            matched_elements: 匹配的元素列表
            query: 可选的查询文本
            
        Returns:
            numpy.ndarray: 带有可视化标记的图像
        """
        # 转换图像格式
        if not isinstance(image, np.ndarray):
            image = np.array(image)
        
        debug_image = image.copy()
        if len(debug_image.shape) == 2:  # 如果是灰度图
            debug_image = cv2.cvtColor(debug_image, cv2.COLOR_GRAY2BGR)
        
        # 绘制匹配元素
        for i, element in enumerate(matched_elements):
            if "bbox" not in element:
                continue
                
            bbox = element["bbox"]
            similarity = element.get("similarity", 1.0)
            
            # 使用不同的颜色表示相似度
            color = (0, int(255 * similarity), int(255 * (1-similarity)))
            
            # 绘制边界框
            cv2.rectangle(debug_image, 
                        (int(bbox[0]), int(bbox[1])), 
                        (int(bbox[2]), int(bbox[3])), 
                        color, 
                        2)
            
            # 添加文本和相似度
            text = f"{element['text']} ({similarity:.2f})"
            cv2.putText(debug_image, 
                      text, 
                      (int(bbox[0]), int(bbox[1]) - 5),
                      cv2.FONT_HERSHEY_SIMPLEX, 
                      0.5, 
                      color, 
                      1)
        
        # 添加查询信息
        if query:
            cv2.putText(debug_image, 
                      f"Query: {query}", 
                      (10, 30),
                      cv2.FONT_HERSHEY_SIMPLEX, 
                      1, 
                      (0, 255, 255), 
                      2)
        
        return debug_image 