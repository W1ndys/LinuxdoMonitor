#!/bin/bash

# 定义颜色和表情符号
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # 无颜色

# 捕获 Ctrl+C 信号
trap cleanup SIGINT SIGTERM

cleanup() {
    echo -e "\n${RED}📢 脚本被终止，正在退出...${NC}"
    exit 0
}

# 显示欢迎信息
echo -e "${GREEN}🚀 RSS监控器自动运行脚本已启动${NC}"
echo -e "${BLUE}ℹ️ 将每10分钟运行一次RSS监控${NC}"
echo -e "${YELLOW}⚠️ 按 Ctrl+C 可随时终止脚本${NC}\n"

# 无限循环
while true; do
    # 获取当前时间
    current_time=$(date "+%Y-%m-%d %H:%M:%S")
    
    # 运行前输出信息
    echo -e "${GREEN}🕒 $current_time${NC}"
    echo -e "${BLUE}🔍 开始检查RSS订阅...${NC}"
    
    # 运行Python脚本
    python rss_monitor.py
    
    # 运行后输出信息
    echo -e "${GREEN}✅ RSS检查完成${NC}"
    echo -e "${YELLOW}💤 休眠10分钟后将再次运行...${NC}\n"
    
    # 休眠10分钟
    sleep 600
done