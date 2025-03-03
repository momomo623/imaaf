# core/perception/visual_engine.py
import paddleocr
import torch
import clip
from PIL import Image
import numpy as np
import cv2
from sklearn.metrics.pairwise import cosine_similarity
import logging

class VisualEngine:
    """视觉感知引擎，整合OCR和视觉模型"""
    
    def __init__(self):
        """初始化视觉引擎"""
        self._init_ocr()
        self._init_clip()
    
    def _init_ocr(self):
        """初始化OCR模型"""
        self.ocr = paddleocr.PaddleOCR(use_angle_cls=True, lang="ch")
    
    def _init_clip(self):
        """初始化CLIP模型"""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.clip_model, self.preprocess = clip.load("ViT-B/32", device=self.device)
    
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
    
    def semantic_search(self, query_text, image, text_elements=None):
        """语义搜索:在图像中查找与输入文本语义最相近的文字
        
        Args:
            query_text: 查询文本
            image: 待搜索的图像
            text_elements: 可选,预先提取好的文字信息
            
        Returns:
            list: 按相似度排序的文字元素列表
        """
        # 如果没有提供文字信息,先进行文字提取
        if text_elements is None:
            text_elements = self.extract_text(image)
        
        if not text_elements:
            return []
        
        # 将OpenCV格式图像转换为PIL格式(CLIP要求)
        if isinstance(image, np.ndarray):
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        # 准备文本数据:查询文本和识别出的所有文本
        texts = [query_text] + [item["text"] for item in text_elements]
        text_tokens = clip.tokenize(texts).to(self.device)
        
        # 使用CLIP模型计算文本特征向量
        with torch.no_grad():
            text_features = self.clip_model.encode_text(text_tokens)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        
        # 计算查询文本与各个文字块的相似度
        query_feature = text_features[0].unsqueeze(0)
        element_features = text_features[1:]
        
        similarities = torch.nn.functional.cosine_similarity(
            query_feature, element_features
        ).cpu().numpy()
        
        # 将相似度分数添加到对应的文字信息中
        for i, score in enumerate(similarities):
            text_elements[i]["similarity"] = float(score)
        
        # 按相似度降序排序
        sorted_elements = sorted(text_elements, key=lambda x: x["similarity"], reverse=True)
        
        return sorted_elements
    
    def hybrid_semantic_search(self, query_text, image, exclude_regions=[]):
        """改进的混合语义搜索，可排除指定区域"""
        # 确保图像格式正确
        if isinstance(image, np.ndarray):
            # OpenCV格式转PIL格式（如果需要）
            if len(image.shape) == 3 and image.shape[2] == 3:
                image_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            else:
                image_pil = Image.fromarray(image)
        else:
            image_pil = image
        
        # 获取图像尺寸（用于日志）
        if isinstance(image, np.ndarray):
            height, width = image.shape[:2]
        else:
            width, height = image.size
        
        logging.debug(f"处理图像尺寸: {width}x{height}")
        
        # 文本匹配结果
        text_matches = self.semantic_search(query_text, image)
        
        # 转换文本匹配结果格式
        formatted_text_matches = []
        for match in text_matches:
            try:
                formatted_text_matches.append({
                    "type": "text",
                    "score": match["similarity"],
                    "data": {
                        "text": match["text"],
                        "center": match["center"],
                        "bbox": match.get("bbox", match["coordinates"])  # 使用bbox或coordinates
                    }
                })
            except Exception as e:
                logging.error(f"格式化文本匹配结果时出错: {str(e)}")
                logging.debug(f"问题数据: {match}")
                continue
        
        # 视觉匹配结果
        visual_matches = self.visual_semantic_search(query_text, image)
        
        # 转换视觉匹配结果格式
        formatted_visual_matches = []
        for match in visual_matches:
            formatted_visual_matches.append({
                "type": "visual",
                "score": match["similarity"] * 1.2,  # 提高视觉匹配的权重
                "data": {
                    "center": match["center"],
                    "bbox": match["region"]
                }
            })
        
        # 合并结果
        combined = []
        seen_positions = set()
        
        # 先添加视觉匹配
        for match in formatted_visual_matches:
            pos = tuple(match["data"]["center"])  # 转换为元组以便用作集合元素
            if pos not in seen_positions:
                combined.append(match)
                seen_positions.add(pos)
        
        # 再添加文本匹配
        for match in formatted_text_matches:
            pos = tuple(match["data"]["center"])
            if pos not in seen_positions:
                combined.append(match)
                seen_positions.add(pos)
        
        # 过滤排除区域
        filtered_combined = []
        for match in combined:
            # 检查是否在排除区域内
            in_excluded = False
            x, y = match["data"]["center"]
            for (x1, y1, x2, y2) in exclude_regions:
                if x1 <= x <= x2 and y1 <= y <= y2:
                    in_excluded = True
                    break
            if not in_excluded:
                filtered_combined.append(match)
        
        # 按置信度排序
        filtered_combined.sort(key=lambda x: x["score"], reverse=True)
        
        # 添加调试信息
        for match in filtered_combined:
            logging.debug(f"匹配项: 类型={match['type']} "
                         f"分数={match['score']:.3f} "
                         f"位置={match['data']['center']}")
        
        return filtered_combined
    
    def visual_semantic_search(self, query_text, image, top_k=5, grid_size=(3, 3)):
        """图像语义搜索：将图像分割成网格，找出与查询文本语义最相关的图像区域
        
        Args:
            query_text: 查询文本
            image: 待搜索的图像
            top_k: 返回的最匹配区域数量
            grid_size: 图像网格划分尺寸，默认为3x3
            
        Returns:
            list: 包含最匹配区域信息的列表（位置、相似度）
        """
        # 确保图像为PIL格式
        if isinstance(image, np.ndarray):
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        # 获取图像尺寸
        width, height = image.size
        cell_width = width // grid_size[0]
        cell_height = height // grid_size[1]
        
        # 准备文本查询
        text_tokens = clip.tokenize([query_text]).to(self.device)
        
        # 预处理文本
        with torch.no_grad():
            text_features = self.clip_model.encode_text(text_tokens)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        
        # 存储每个区域的相似度和位置
        region_similarities = []
        
        # 对图像进行网格划分并计算每个区域与查询文本的相似度
        for i in range(grid_size[0]):
            for j in range(grid_size[1]):
                # 计算当前区域坐标
                left = i * cell_width
                upper = j * cell_height
                right = min((i + 1) * cell_width, width)
                lower = min((j + 1) * cell_height, height)
                
                # 裁剪区域
                region = image.crop((left, upper, right, lower))
                
                # 预处理区域图像
                region_image = self.preprocess(region).unsqueeze(0).to(self.device)
                
                # 编码图像
                with torch.no_grad():
                    region_features = self.clip_model.encode_image(region_image)
                    region_features = region_features / region_features.norm(dim=-1, keepdim=True)
                
                # 计算相似度
                similarity = torch.nn.functional.cosine_similarity(
                    text_features, region_features
                ).item()
                
                # 存储区域信息
                region_similarities.append({
                    "region": (left, upper, right, lower),
                    "center": ((left + right) // 2, (upper + lower) // 2),
                    "similarity": similarity
                })
        
        # 按相似度降序排序
        sorted_regions = sorted(region_similarities, key=lambda x: x["similarity"], reverse=True)
        
        return sorted_regions[:top_k]