#!/bin/bash
# MNN LLM Stdio Backend - 综合演示测试脚本
# 依次执行单次、批量、交互式对话测试

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_msg() {
    local color=$1
    local msg=$2
    echo -e "${color}${msg}${NC}"
}

print_separator() {
    echo "=================================================================="
}

# 检查backend是否存在
check_backend() {
    local backend_path="$1"
    if [ ! -f "$backend_path" ]; then
        print_msg $RED "错误: backend可执行文件不存在: $backend_path"
        print_msg $YELLOW "请先编译backend: cd ~/mnn/build && make -j12 mnn_llm_stdio_backend"
        exit 1
    fi
    print_msg $GREEN "Backend可执行文件检查通过: $backend_path"
}

# 检查是否需要等待
NO_WAIT=false
if [ "$1" == "--no-wait" ]; then
    NO_WAIT=true
    print_msg $YELLOW "跳过用户确认模式"
fi

# 等待用户确认
wait_user() {
    if [ "$NO_WAIT" == "true" ]; then
        print_msg $CYAN "自动继续执行..."
        sleep 1
    else
        print_msg $CYAN "按Enter继续，或Ctrl+C退出..."
        read -r
    fi
}

# 进入正确的工作目录
cd "$(dirname "$0")"
SCRIPT_DIR=$(pwd)
PYTHON_DEMO_DIR="$SCRIPT_DIR/python_demo"

print_msg $BLUE "MNN LLM Stdio Backend - 综合演示测试"
print_msg $BLUE "工作目录: $SCRIPT_DIR"
print_separator

# 配置路径
BACKEND_PATH="$HOME/mnn/build/mnn_llm_stdio_backend"
MODEL_CONFIG="$HOME/models/Qwen3-0.6B-MNN/config.json"

print_msg $YELLOW "配置信息:"
echo "- Backend路径: $BACKEND_PATH"
echo "- 模型配置: $MODEL_CONFIG"
echo "- Python演示目录: $PYTHON_DEMO_DIR"
print_separator

# 检查文件
check_backend "$BACKEND_PATH"

if [ ! -f "$MODEL_CONFIG" ]; then
    print_msg $RED "警告: 模型配置文件不存在: $MODEL_CONFIG"
    print_msg $YELLOW "将使用config.toml中的默认配置"
fi

# 进入Python演示目录
cd "$PYTHON_DEMO_DIR"

# 1. 单次对话测试
print_msg $PURPLE "1. 单次对话测试"
print_separator
print_msg $CYAN "执行命令: python3 demo.py single --backend <backend> --model <model>"
wait_user

python3 demo.py single --backend "$BACKEND_PATH" --model "$MODEL_CONFIG"

print_separator
print_msg $GREEN "单次对话测试完成"
wait_user

# 2. 批量对话测试
print_msg $PURPLE "2. 批量对话测试"
print_separator
print_msg $CYAN "执行命令: python3 demo.py batch --backend <backend> --model <model>"
print_msg $YELLOW "批量文件内容:"
cat example_commands.txt
print_separator
wait_user

python3 demo.py batch --backend "$BACKEND_PATH" --model "$MODEL_CONFIG"

print_separator
print_msg $GREEN "批量对话测试完成"
wait_user

# 3. 交互式对话测试
print_msg $PURPLE "3. 交互式对话测试"
print_separator
print_msg $CYAN "执行命令: python3 demo.py chat --backend <backend> --model <model>"
print_msg $YELLOW "启动交互式对话模式，可手动输入对话测试"
print_separator
wait_user

python3 demo.py chat --backend "$BACKEND_PATH" --model "$MODEL_CONFIG"

print_separator
print_msg $GREEN "交互式对话测试完成"

# 总结
print_separator
print_msg $BLUE "所有测试完成！"
print_msg $GREEN "MNN LLM Stdio Backend 综合演示测试成功执行"
print_msg $YELLOW "如有问题，请检查日志文件: mnn_llm_demo.log"

# 添加使用说明
echo
print_msg $CYAN "脚本使用方法:"
echo "  交互执行: ./run_demo_tests.sh"
echo "  跳过确认: ./run_demo_tests.sh --no-wait"
echo
print_msg $CYAN "单独运行演示:"
echo "  单次对话: cd python_demo && python3 demo.py single --backend <backend> --model <model>"
echo "  批量对话: cd python_demo && python3 demo.py batch --backend <backend> --model <model>"
echo "  交互对话: cd python_demo && python3 demo.py chat --backend <backend> --model <model>"