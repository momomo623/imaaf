# tools/ecommerce/hema_crawler.py
import os
import time
import json
import csv
import logging
from ..base_tool import BaseTool

class HemaCrawler(BaseTool):
    """盒马商品数据采集工具"""
    
    # 定义为类属性
    required_app = "盒马"
    
    def __init__(self, agent):
        """初始化盒马爬取工具"""
        super().__init__(agent)
        self.name = "HemaCrawler"
        self.description = "盒马APP商品数据采集工具，可提取商品名称和价格"
        self.version = "1.0.0"
        
        # 工具特定属性
        self.categories = []
        self.products = []
        self.output_dir = "output/hema"
    
    def setup(self):
        """设置工具"""
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"盒马商品爬取工具已设置，将保存数据到 {self.output_dir}")
        return True
    
    def navigate_to_category(self, category_name):
        """导航到指定商品类别
        
        Args:
            category_name: 类别名称，如"海鲜水产"
            
        Returns:
            bool: 是否成功导航到指定类别
        """
        # 先回到首页
        self.agent.execute_action({"action_type": "home"})
        time.sleep(1)
        
        # 尝试在主页面上找到分类入口
        screen = self.agent.capture_and_analyze()
        matches = self.agent.vision.semantic_search(
            category_name, 
            screen["screenshot"],
            screen["text_elements"]
        )
        
        # 如果找到类别，直接点击
        if matches:
            self.agent.execute_action({
                "action_type": "click",
                "target": category_name
            })
            return True
            
        # 如果没找到，可能需要先进入分类页
        self.agent.execute_action({
            "action_type": "click",
            "target": "分类",
            "use_visual_search": True
        })
        
        time.sleep(1)
        
        # 在分类页面查找目标类别
        screen = self.agent.capture_and_analyze()
        matches = self.agent.vision.semantic_search(
            category_name, 
            screen["screenshot"],
            screen["text_elements"]
        )
        
        if matches:
            self.agent.execute_action({
                "action_type": "click",
                "target": category_name
            })
            return True
            
        print(f"未找到类别: {category_name}")
        return False
    
    def collect_current_page_products(self):
        """采集当前页面的商品信息
        
        Returns:
            list: 商品信息列表
        """
        # 识别并提取商品信息
        screen_data = self.agent.capture_and_analyze()
        
        # 解析商品信息
        products = self._extract_product_info(screen_data)
        
        return products
    
    def _extract_product_info(self, screen_data):
        """从屏幕数据中提取商品信息
        
        Args:
            screen_data: 屏幕数据，包含截图和文本元素
            
        Returns:
            list: 商品信息列表
        """
        products = []
        text_elements = screen_data["text_elements"]
        
        # 识别价格元素（通常包含¥符号）
        price_elements = [e for e in text_elements if "¥" in e["text"]]
        
        for price_elem in price_elements:
            price_x, price_y = price_elem["center"]
            
            # 查找与价格在同一区域的商品名称
            # 通常商品名在价格上方
            nearby_elements = [
                e for e in text_elements 
                if abs(e["center"][0] - price_x) < 200  # x轴偏差不大
                and price_y - 200 < e["center"][1] < price_y  # 在价格上方
                and e["text"] != price_elem["text"]  # 不是价格本身
                and "¥" not in e["text"]  # 不是其他价格
            ]
            
            if nearby_elements:
                # 找距离价格最近的元素作为商品名
                name_elem = min(nearby_elements, 
                              key=lambda e: abs(e["center"][1] - price_y))
                
                products.append({
                    "name": name_elem["text"],
                    "price": price_elem["text"],
                    "position": {
                        "name": name_elem["center"],
                        "price": price_elem["center"]
                    }
                })
        
        return products
    
    def scroll_for_more(self):
        """滑动查看更多商品"""
        self.agent.execute_action({
            "action_type": "swipe",
            "direction": "up"
        })
    
    def save_data(self, format="csv"):
        """保存采集的数据
        
        Args:
            format: 保存格式，支持"csv"和"json"
        """
        if format == "csv":
            self._save_to_csv()
        elif format == "json":
            self._save_to_json()
    
    def _save_to_csv(self):
        """保存为CSV格式"""
        filepath = os.path.join(self.output_dir, "hema_products.csv")
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['商品名称', '价格', '类别', '子类别'])
            for product in self.products:
                writer.writerow([
                    product["name"],
                    product["price"],
                    product.get("category", ""),
                    product.get("subcategory", "")
                ])
        print(f"数据已保存到: {filepath}")
    
    def _save_to_json(self):
        """保存为JSON格式"""
        filepath = os.path.join(self.output_dir, "hema_products.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.products, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到: {filepath}")
    
    def run(self, params=None):
        """运行盒马商品爬取任务
        
        Args:
            params: 参数字典，可包含以下键:
                - category: 要爬取的类别，默认为"海鲜水产"
                - max_pages: 最大页数，默认为5
                
        Returns:
            dict: 执行结果
        """
        params = params or {}
        category = params.get("category", "海鲜水产")
        max_pages = params.get("max_pages", 5)
        
        # 1. 启动盒马APP
        print(f"开始采集盒马APP '{category}' 类别的商品信息...")
        
        # 2. 导航到目标类别
        if not self.navigate_to_category(category):
            return {"success": False, "message": f"无法导航到类别: {category}"}
        
        # 3. 采集商品数据
        all_products = []
        seen_products = set()  # 用于去重
        
        for page in range(max_pages):
            print(f"采集第 {page+1} 页商品...")
            
            # 等待页面加载
            time.sleep(1.5)
            
            # 采集当前页商品
            products = self.collect_current_page_products()
            
            # 去重处理
            new_products = []
            for product in products:
                product_key = f"{product['name']}_{product['price']}"
                if product_key not in seen_products:
                    seen_products.add(product_key)
                    product["category"] = category
                    new_products.append(product)
            
            if new_products:
                all_products.extend(new_products)
                print(f"发现 {len(new_products)} 个新商品")
            else:
                print("未发现新商品，可能已到底部")
                break
            
            # 滑动到下一页
            if page < max_pages - 1:
                self.scroll_for_more()
                time.sleep(1.5)
        
        # 4. 保存数据
        self.products = all_products
        self.save_data(format="csv")
        self.save_data(format="json")
        
        return {
            "success": True,
            "message": f"成功采集 {len(all_products)} 个商品信息",
            "product_count": len(all_products)
        }
    
    def cleanup(self):
        """清理工具"""
        self.products = []
        print(f"工具清理完成: {self.name}")
        return True

    @staticmethod
    def check_app_launched(agent):
        """检查盒马是否成功启动
        
        通过以下方式验证当前页面是否属于盒马APP：
        1. OCR识别特征文本
        2. 大模型分析页面内容
        """
        # 获取屏幕截图和文本内容
        screenshot = agent.device.capture_screenshot()
        text_elements = agent.vision.extract_text(screenshot)
        
        # 1. 特征文本检查
        text_content = ' '.join([elem["text"] for elem in text_elements])
        feature_keywords = [
            "盒马", "分类", "果蔬", "海鲜水产",
            "购物车", "我的", "首页"
        ]
        keyword_matches = [kw for kw in feature_keywords if kw in text_content]
        
        # 2. 使用大模型分析页面内容
        prompt = f"""
        分析以下页面文本内容，判断是否是盒马APP的界面：
        
        页面文本：{text_content}
        
        特征匹配：以下是盒马APP特征关键词：{', '.join(keyword_matches)}
        
        请分析这是否是盒马APP的界面？只需回答：是或否？
        """
        
        try:
            messages = [
                {"role": "user", "content": prompt}
            ]
            analysis = agent.brain._make_request(messages)
            # 添加调试日志
            # 解析响应
            is_hema = "是" in analysis
        except Exception as e:
            logging.warning(f"大模型分析失败: {e}")
            logging.debug(f"错误详情:", exc_info=True)
            is_hema = False
        
        # 综合判断：关键词匹配数量 + 大模型判断
        launch_success = len(keyword_matches) >= 3 and is_hema
        print("关键词匹配数量：", len(keyword_matches))

        # 记录详细日志
        logging.info(f"盒马APP启动检查结果：")
        logging.info(f"- 关键词匹配：找到 {len(keyword_matches)} 个 ({', '.join(keyword_matches)})")
        logging.info(f"- 大模型分析：{'是' if is_hema else '否'}")
        logging.info(f"- 最终判断：{'成功' if launch_success else '失败'}")
        
        return launch_success

def _is_float(value):
    """检查字符串是否可以转换为浮点数"""
    try:
        float(value)
        return True
    except ValueError:
        return False
