# from engine.agent import Agent
#
# # agent = Agent(emulator_path='/Applications/MuMuPlayer.app')
# agent = Agent(wifi_device='192.168.1.7:5555')
# agent.device._init_connection()
#
# # agent.device.adaptive_swipe("up", distance_factor=0.4)
#
# print(agent.device._get_current_activity())
#
#
# # 启动应用
# agent.device.launch_app_by_component("com.tencent.mm/com.tencent.mm.ui.LauncherUI")
#
# # # 只通过包名启动应用
# agent.device.launch_app_by_package("com.wudaokou.hippo")

# 新增代码：绘制矩形并保存图片
import cv2

# 图片路径
image_path = "/Users/chongwen/Downloads/12.jpg"

# 读取图片
image = cv2.imread(image_path)

# 定义矩形的左上角和右下角坐标
top_left = (350, 290)
bottom_right = (450, 390)

# 绘制矩形
color = (0, 255, 0)  # 绿色
thickness = 2
cv2.rectangle(image, top_left, bottom_right, color, thickness)

# 保存图片
output_path = "/Users/chongwen/Downloads/12_with_rectangle.jpg"
cv2.imwrite(output_path, image)
print(f"图片已保存到 {output_path}")
