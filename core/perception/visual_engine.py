# core/perception/visual_engine.py
import paddleocr
import torch
import clip
from PIL import Image
import numpy as np
import cv2
from sklearn.metrics.pairwise import cosine_similarity

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
                coordinates = item[0]  # 文字框的四个角坐标
                text = item[1][0]      # 识别出的文字内容
                confidence = item[1][1]  # OCR的置信度
                
                # 计算文字框的中心点坐标
                center_x = sum(point[0] for point in coordinates) / 4
                center_y = sum(point[1] for point in coordinates) / 4
                
                # 保存文字块的完整信息
                text_elements.append({
                    "text": text,
                    "confidence": confidence,
                    "coordinates": coordinates,
                    "center": (center_x, center_y)
                })
        
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
    
    def hybrid_semantic_search(self, query_text, image, text_elements=None, grid_size=(3, 3)):
        """混合语义搜索：结合文本和图像区域的双路径搜索
        
        Args:
            query_text: 查询文本
            image: 待搜索的图像
            text_elements: 可选，预先提取好的文字信息
            grid_size: 图像网格划分尺寸
            
        Returns:
            list: 综合排序后的匹配元素列表
        """
        # 获取基于文本的匹配结果
        text_matches = self.semantic_search(query_text, image, text_elements)
        
        # 获取基于图像区域的匹配结果
        visual_matches = self.visual_semantic_search(query_text, image, grid_size=grid_size)
        
        # 文本匹配为空的情况，直接返回视觉匹配结果
        if not text_matches:
            return [{"type": "visual", "data": item} for item in visual_matches]
        
        # 综合两种结果
        # 为每种匹配添加类型标识
        typed_text_matches = [{"type": "text", "data": item} for item in text_matches]
        typed_visual_matches = [{"type": "visual", "data": item} for item in visual_matches]
        
        # 对匹配项进行综合评分
        all_matches = []
        
        # 处理文本匹配
        for match in typed_text_matches:
            # 文本匹配时，保留原始相似度但稍微提高权重
            match["final_score"] = match["data"]["similarity"] * 1.2
            all_matches.append(match)
        
        # 处理视觉匹配
        for match in typed_visual_matches:
            # 检查该视觉区域是否与文本区域重叠，如果重叠则提高分数
            visual_region = match["data"]["region"]
            match["final_score"] = match["data"]["similarity"]
            
            # 检查与文本区域的重叠
            for text_match in text_matches:
                text_center = text_match["center"]
                if (visual_region[0] <= text_center[0] <= visual_region[2] and 
                    visual_region[1] <= text_center[1] <= visual_region[3]):
                    # 如果视觉区域包含文本中心点，则提高分数
                    match["final_score"] *= 1.5
                    match["overlapped_text"] = text_match["text"]
                    break
            
            all_matches.append(match)
        
        # 按最终分数排序
        sorted_matches = sorted(all_matches, key=lambda x: x["final_score"], reverse=True)
        
        return sorted_matches
    
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