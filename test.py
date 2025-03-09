from engine.agent import Agent

# agent = Agent(emulator_path='/Applications/MuMuPlayer.app')
agent = Agent(wifi_device='192.168.1.7:5555')
agent.device._init_connection()

# agent.device.adaptive_swipe("up", distance_factor=0.4)

print(agent.device._get_current_activity())


# 启动应用
agent.device.launch_app_by_component("com.tencent.mm/com.tencent.mm.ui.LauncherUI")

# # 只通过包名启动应用
agent.device.launch_app_by_package("com.wudaokou.hippo")