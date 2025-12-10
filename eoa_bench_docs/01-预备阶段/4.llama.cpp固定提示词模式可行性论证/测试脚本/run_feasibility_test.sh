#!/bin/bash

# llama.cpp固定提示词模式可行性论证测试脚本

set -e

# 配置参数
MNN_BENCH_DIR="/home/xphi/MNN_LLM_Benchmark"
TASK_FILE="fixed_prompt_feasibility_test.yaml"
TEST_MODEL="qwen3_0_6b"
REPEAT_COUNT=10
OUTPUT_DIR="../测试结果"

# 日志函数
log_info() {
    echo "[INFO] $1"
}

log_success() {
    echo "[SUCCESS] $1"
}

log_error() {
    echo "[ERROR] $1"
}

# 检查环境
check_environment() {
    log_info "检查测试环境..."
    
    if [ ! -d "$MNN_BENCH_DIR" ]; then
        log_error "MNN_LLM_Benchmark目录不存在"
        exit 1
    fi
    
    if [ ! -f "$TASK_FILE" ]; then
        log_error "任务配置文件不存在"
        exit 1
    fi
    
    cd "$MNN_BENCH_DIR"
    if ! python framework/benchmark.py | grep -q "$TEST_MODEL"; then
        log_error "模型未配置"
        exit 1
    fi
    
    mkdir -p "$OUTPUT_DIR"
    log_success "环境检查完成"
}

# 执行测试
run_test() {
    local mode=$1
    local suit_name=$2
    
    log_info "执行 $mode 测试..."
    
    for i in $(seq 1 $REPEAT_COUNT); do
        python framework/benchmark.py -b "$TASK_FILE" 2>/dev/null
        
        # 查找最新结果
        latest_result=$(find results -name "*.json" -type f -mmin -1 | head -1)
        if [ -z "$latest_result" ]; then
            log_error "未找到测试结果"
            return 1
        fi
        
        # 保存结果
        cp "$latest_result" "$OUTPUT_DIR/${mode}_${i}.json"
    done
    
    log_success "$mode 测试完成"
}

# 主函数
main() {
    log_info "开始可行性论证测试"
    
    check_environment
    
    # 复制配置文件
    cp "$(dirname ${BASH_SOURCE[0]})/$TASK_FILE" tasks/
    
    # 执行三种模式测试
    run_test "fixed_mode" "fixed_mode_test"
    run_test "variable_mode" "variable_mode_test" 
    run_test "file_mode" "file_mode_test"
    
    log_success "所有测试执行完成！"
    log_info "结果保存在: $OUTPUT_DIR"
}

main "$@"