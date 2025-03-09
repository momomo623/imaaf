# core/perception/visual_engine.py
import paddleocr
import numpy as np
import cv2
import logging
import os
from datetime import datetime
from .text_matcher import TextMatcher  # 导入TextMatcher

class VisualEngine:
    """视觉感知引擎，专注OCR文本识别"""
    
    def __init__(self):
        """初始化视觉引擎"""
        self._init_ocr()
        # 创建调试输出目录
        self.debug_dir = "output/debug"
        os.makedirs(self.debug_dir, exist_ok=True)
        
        # 初始化文本匹配器实例
        self._text_matcher = TextMatcher()
    
    def _init_ocr(self):
        """初始化OCR模型"""
        self.ocr = paddleocr.PaddleOCR(use_angle_cls=True, lang="ch")
    
    def extract_text(self, image):
        """提取图像中的文本
        
        Args:
            image: 输入图像,支持OpenCV(BGR)或PIL格式
            
        Returns:
            list: 包含检测到的文字信息(文本、置信度、坐标等)的列表
        """
        # 如果是OpenCV格式(BGR)的图像,转换为RGB
        if isinstance(image, np.ndarray):
            if len(image.shape) == 3 and image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 执行OCR识别
        result = self.ocr.ocr(image, cls=True)
        
        # 处理OCR结果,提取每个文字块的信息
        text_elements = []
        for line in result:
            for item in line:
                try:
                    coordinates = item[0]  # 文字框的四个角坐标
                    text = item[1][0]      # 识别出的文字内容
                    confidence = item[1][1]  # OCR的置信度
                    
                    # 确保coordinates是列表格式的四个点坐标
                    if not isinstance(coordinates, list):
                        logging.warning(f"异常的坐标格式: {coordinates}")
                        continue
                    
                    if len(coordinates) != 4:
                        logging.warning(f"坐标点数量不正确: {len(coordinates)}")
                        continue
                    
                    # 计算文字框的中心点坐标
                    center_x = sum(point[0] for point in coordinates) / 4
                    center_y = sum(point[1] for point in coordinates) / 4
                    
                    # 计算边界框
                    x_coords = [p[0] for p in coordinates]
                    y_coords = [p[1] for p in coordinates]
                    bbox = [
                        min(x_coords),  # x1
                        min(y_coords),  # y1
                        max(x_coords),  # x2
                        max(y_coords)   # y2
                    ]
                    
                    # 保存文字块的完整信息
                    text_elements.append({
                        "text": text,
                        "confidence": confidence,
                        "coordinates": coordinates,
                        "center": (center_x, center_y),
                        "bbox": bbox
                    })
                except Exception as e:
                    logging.error(f"处理OCR结果时出错: {str(e)}")
                    logging.debug(f"问题数据: {item}")
                    continue
        
        return text_elements
    
    def save_debug_image(self, image, text_elements):
        """保存文本识别调试图像
        
        Args:
            image: 原始图像
            text_elements: 文本元素列表
        
        Returns:
            str: 保存的文件路径，如果保存失败则返回None
        """
        try:
            # 生成文件名（使用时间戳避免文件名冲突）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.debug_dir}/ocr_result_{timestamp}.png"
            
            # 转换图像格式
            if isinstance(image, np.ndarray):
                debug_image = image.copy()
                if len(debug_image.shape) == 2:  # 如果是灰度图
                    debug_image = cv2.cvtColor(debug_image, cv2.COLOR_GRAY2BGR)
            else:  # PIL Image
                debug_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # 绘制识别到的文本区域
            for elem in text_elements:
                if isinstance(elem, dict) and "bbox" in elem:
                    bbox = elem["bbox"]
                    cv2.rectangle(debug_image, 
                                (int(bbox[0]), int(bbox[1])), 
                                (int(bbox[2]), int(bbox[3])), 
                                (0, 255, 0), 
                                1)
                    
                    # 添加文本内容
                    cv2.putText(debug_image, 
                              elem["text"], 
                              (int(bbox[0]), int(bbox[1]) - 5),
                              cv2.FONT_HERSHEY_SIMPLEX, 
                              0.5, 
                              (0, 0, 255), 
                              1)
            
            # 保存图像
            cv2.imwrite(filename, debug_image)
            logging.info(f"OCR调试图像已保存: {filename}")
            
            return filename
        
        except Exception as e:
            logging.error(f"保存调试图像失败: {str(e)}")
            return None
    
    #----------- 以下是从TextMatcher代理的方法 -----------#
    
    def find_text(self, query, text_elements, exact_match=False):
        """查找匹配指定查询文本的元素
        
        Args:
            query: 查询文本
            text_elements: OCR识别的文本元素列表
            exact_match: 是否进行精确匹配，默认为模糊匹配
            
        Returns:
            list: 按相似度排序的匹配元素列表
        """
        return self._text_matcher.find_text(query, text_elements, exact_match)
    
    def find_best_match(self, query, text_elements):
        """查找最佳匹配元素
        
        Args:
            query: 查询文本
            text_elements: OCR识别的文本元素列表
            
        Returns:
            dict: 最佳匹配元素，如果没有匹配项则返回None
        """
        return self._text_matcher.find_best_match(query, text_elements)
    
    def find_closest_element(self, target_position, text_elements):
        """查找距离指定位置最近的文本元素"""
        return self._text_matcher.find_closest_element(target_position, text_elements)
    
    def find_text_in_region(self, query, text_elements, region):
        """在指定区域内查找匹配文本"""
        return self._text_matcher.find_text_in_region(query, text_elements, region)
    
    def find_element_by_content_type(self, text_elements, content_type, region=None):
        """根据内容类型查找元素（如数字、价格、日期等）"""
        return self._text_matcher.find_element_by_content_type(text_elements, content_type, region)
    
    def visualize_matches(self, image, matched_elements, query=None):
        """可视化匹配结果"""
        return self._text_matcher.visualize_matches(image, matched_elements, query)