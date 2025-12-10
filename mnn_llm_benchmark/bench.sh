#!/bin/bash

# MNN LLM Bench 主入口脚本
# 统一管理基准测试和项目功能

set -euo pipefail  # 增强错误处理

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
FRAMEWORK_DIR="$SCRIPT_DIR/framework"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志级别控制
# 可选值: DEBUG, INFO, WARN, ERROR, SILENT
# 默认只显示ERROR，info和warn被过滤
LOG_LEVEL="${LOG_LEVEL:-ERROR}"

# 日志级别数值映射（用于级别比较）
# 数值越大级别越严重：DEBUG=1, INFO=2, WARN=3, ERROR=4, SILENT=5
declare -A LOG_LEVELS=([DEBUG]=1 [INFO]=2 [WARN]=3 [ERROR]=4 [SILENT]=5)

# 日志函数
should_log() {
    local level="$1"
    local current_num="${LOG_LEVELS[$LOG_LEVEL]}"
    local level_num="${LOG_LEVELS[$level]}"

    # 如果未定义级别，默认ERROR
    if [ -z "$current_num" ]; then
        current_num="${LOG_LEVELS[ERROR]}"
    fi

    # 日志级别严重性大于等于当前设置级别才输出
    # ERROR=4时，应该只输出ERROR(4)，不输出WARN(3)、INFO(2)、DEBUG(1)
    if [ "$level_num" -ge "$current_num" ]; then
        return 0
    else
        return 1
    fi
}

log_info() {
    if should_log "INFO"; then
        echo -e "${GREEN}[INFO]${NC} $1"
    fi
}

log_warn() {
    if should_log "WARN"; then
        echo -e "${YELLOW}[WARN]${NC} $1"
    fi
}

log_debug() {
    if should_log "DEBUG"; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

log_error() {
    # ERROR总是输出
    echo -e "${RED}[ERROR]${NC} $1"
    echo -e "${RED}[ERROR]${NC} 脚本执行失败"
    exit 1
}

# 显示benchmark命令帮助
show_benchmark_help() {
    cat << 'EOF'
MNN LLM 基准测试工具

用法:
    ./bench.sh benchmark <模型别名> [选项]

必须参数:
    模型别名               指定要测试的模型 (如: qwen3_06b)

性能参数:
    -t, --threads NUM           线程数 (建议设为物理核心数)
    -c, --precision {0,1,2}     精度级别:
                              0=Normal(对CPU backend，Normal等于High)
                              1=High   (最高质量，速度较慢)
                              2=Low    (快速但精度降低)

序列长度控制:
    -p, --n-prompt NUM          提示词长度 (默认: 512)
    -n, --n-gen NUM             生成长度 (默认: 128)

测试配置:
    -rep, --n-repeat NUM        重复次数 (默认: 3，建议2-3次)

MNN特定选项:
    -kv, --kv-cache             启用KV缓存 (推荐，大幅加速但增加内存)
    -mmp, --mmap                启用内存映射 (0或1，适合大模型)
    -dyo, --dynamicOption NUM   动态优化选项 0-8 (默认: 0)
                              8=性能模式 (更高内存，更好解码性能)

其他选项:
    -pg, --prompt-gen FORMAT    预填充和生成长度格式 (如: 32,16)
    -vp, --variable-prompt NUM  可变提示词模式 (0或1)
                              0=固定16token, 1=使用文件实际长度
    -pf, --prompt-file FILE     提示词文件路径 (仅文件名，如: en_short.txt)
    --scan DIR                  扫描指定目录并自动添加模型
    --overwrite                 扫描时覆盖已存在的模型别名
    --help                      显示帮助信息
    --create-sample             创建批量测试示例配置

可用模型别名:
    qwen3_06b          Qwen3-0.6B-MNN (轻量级，适合快速测试)
    qwen3_vl_2b        Qwen3-VL-2B-Instruct-MNN (多模态)
    qwen3_vl_4b        Qwen3-VL-4B-Instruct-MNN (多模态)
    qwen3_vl_8b        Qwen3-VL-8B-Instruct-MNN (多模态)
    deepseek_r1_15b    DeepSeek-R1-1.5B-Qwen-MNN (推理增强)
    deepseek_r1_7b     DeepSeek-R1-7B-Qwen-MNN (推理增强)

性能调优建议:
1. 快速测试: 使用 qwen3_06b + --precision 2
2. 完整测试: 使用 --precision 0 --kv-cache true
3. 速度优先: (--precision 2 --dynamicOption 8 --kv-cache)
4. 量大模型: 考虑 --mmap 1
5. 提示词测试: 使用 --prompt-file + --variable-prompt 选项
   - --variable-prompt 0: 固定16token (快速测试)
   - --variable-prompt 1: 使用文件实际长度 (真实场景)

使用示例:
    # 基础测试 (推荐开始)
    ./bench.sh benchmark qwen3_06b

    # 自定义测试
    ./bench.sh benchmark qwen3_06b --threads 4 --precision 2

    # 生产级测试
    ./bench.sh benchmark deepseek_r1_15b --precision 0 --kv-cache true

    # 提示词测试 (新增功能)
    ./bench.sh benchmark qwen3_06b --prompt-file en_short.txt --variable-prompt 1
    ./bench.sh benchmark qwen3_06b --prompt-file zh_medium.txt --variable-prompt 0
    ./bench.sh benchmark qwen3_06b --prompt-file code_python.txt --n-prompt 32

    # 多模型测试 (框架级功能)
    uv run python framework/benchmark.py model1 model2 model3 --threads 4

    # 模型扫描功能
    ./bench.sh benchmark --scan /data/models
    ./bench.sh benchmark --scan /data/models --overwrite

    # 创建批量测试示例 (推荐先预览，再执行)
    ./bench.sh benchmark --create-sample
    ./bench.sh batch --task tasks/sample_batch_task.yaml --preview

EOF
}

# 显示批量测试命令帮助
show_batch_help() {
    cat << 'EOF'
MNN LLM 批量基准测试工具

用法:
    ./bench.sh batch <配置文件> [选项]

必须参数:
    -t, --task FILE       批量测试任务配置文件 (YAML格式)

选项:
    --preview             预览批量测试计划(不实际执行)
    --create-sample       创建示例批量测试配置文件

配置文件示例:
    task_name: "线程数对性能的影响基准测试"
    description: "基准测试不同线程数和精度下的推理性能"
    global_config:
      timeout: 300
      models: ["qwen3_06b", "qwen3_1_7b"]
    benchmark_suits:
      - suit_name: "thread_scaling"
        description: "线程数扩展性基准测试"
        variables:
          - name: "threads"
            values: [1, 2, 4]
          - name: "precision"
            values: [0, 2]
        fixed_params:
          n_prompt: 256
          n_gen: 128
          kv_cache: "true"
          variable_prompt: 1
          prompt_file: "en_short.txt"

使用示例:
    ./bench.sh batch --task tasks/my_batch_task.yaml
    ./bench.sh batch --create-sample
    ./bench.sh batch --task tasks/my_batch_task.yaml --preview

注意:
    - 批量测试使用YAML格式的任务配置文件
    - 支持**预览模式**快速验证测试计划，避免运行耗时测试
    - 配置文件存储在tasks/目录中，具体格式请参考生成的示例

EOF
}

# 显示数据分析命令帮助
show_analysis_help() {
    cat << 'EOF'
MNN LLM 数据分析工具

用法:
    ./bench.sh analyze <Suite ID> [选项]

必须参数:
    Suite ID              要分析的测试套件ID

分析选项:
    --list-suites         列出所有可用的Suite供分析
    --x-variable VAR      自变量X (如: n_prompt, threads, precision等)
    --y-variable VAR      自变量Y (可选，用于双变量分析)
    --result-types TYPES  要分析的结果类型，逗号分隔 (如: pp,tg,pp+tg)
    --list-analysis       列出所有分析报告历史记录

单变量分析选项:
    --single-variable VAR 指定要分析的单变量名称（正式分析模式）
    --fixed-params JSON   其他变量的固定值，JSON格式

分析管理:
    --delete-analysis ID  删除指定ID的分析报告（删除数据库记录和文件目录）

功能说明:
    - 自动对指定suite的所有变量进行回归分析
    - 支持线性和非线性回归拟合
    - 生成专业的分析和可视化报告
    - 输出HTML、Markdown和图表文件

使用示例:
    # 查看可用的suite
    ./bench.sh analyze --list-suites

    # 基础分析（自动检测所有变量）
    ./bench.sh analyze 1

    # 指定变量分析
    ./bench.sh analyze 1 --x-variable threads --result-types pp,tg

    # 多变量分析
    ./bench.sh analyze 1 --x-variable threads --y-variable n_prompt

    # 单变量正式分析
    ./bench.sh analyze 4 --single-variable threads --result-types pp,tg

    # 分析管理
    ./bench.sh analyze --list-analysis
    ./bench.sh --delete-analysis 1

注意:
    - 分析结果保存在web_server/static/analysis/目录
    - 启动Web服务器查看报告: ./bench.sh web
    - 每个分析生成唯一目录，避免覆盖

EOF
}

# 显示process命令帮助
show_process_help() {
    cat << 'EOF'
数据处理和报告生成工具

用法:
    ./bench.sh process [选项]

输入选项:
    -i, --input FILE      输入数据文件 (CSV/JSON格式)
    --model MODEL         按模型筛选数据
    --test-suite SUITE    按测试套件筛选数据

分析选项:
    --fit-method METHOD   拟合算法 (默认: polynomial)
                         可选: polynomial, spline, linear
输出选项:
    -o, --output DIR      输出目录 (默认: results/reports)

交互选项:
    --interactive         生成交互式图表(HTML格式)

功能说明:
    - 自动识别测试类型和变量关系
    - 生成性能曲线、拟合分析
    - 支持多种拟合算法
    - 输出HTML报告和图表

使用示例:
    ./bench.sh process --input results/csv/data.csv --interactive
    ./bench.sh process -o results/reports --model qwen3_06b
    ./bench.sh process --fit-method spline --interactive

EOF
}

# 停止Web服务器
stop_web() {
    local pid_file="logs/web_server.pid"

    if [ -f "$pid_file" ]; then
        local web_pid=$(cat "$pid_file")
        if kill -0 $web_pid 2>/dev/null; then
            log_info "停止Web服务器 (PID: $web_pid)..."
            kill $web_pid

            # 等待进程结束
            local count=0
            while kill -0 $web_pid 2>/dev/null && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done

            if kill -0 $web_pid 2>/dev/null; then
                log_warn "Web服务器未能正常停止，强制终止..."
                kill -9 $web_pid
            fi

            # 删除PID文件
            rm -f "$pid_file"
            log_info "Web服务器已停止"
        else
            log_warn "PID文件存在但进程不存在，清理PID文件"
            rm -f "$pid_file"
            log_info "Web服务器未运行"
        fi
    else
        log_info "未找到Web服务器PID文件，尝试查找进程..."
        # 尝试查找并停止可能的web服务器进程
        local found_pids=$(pgrep -f "web_server/app.py" || echo "")
        if [ -n "$found_pids" ]; then
            log_info "发现Web服务器进程，正在停止..."
            echo "$found_pids" | xargs kill
            log_info "Web服务器已停止"
        else
            log_info "Web服务器未运行"
        fi
    fi
}

# 显示web命令帮助
show_web_help() {
    cat << 'EOF'
Web可视化服务器

用法:
    ./bench.sh web [选项]           # 启动Web服务器
    ./bench.sh web stop             # 停止Web服务器

服务器选项:
    -p, --port PORT       端口号 (默认: 9998)
    -h, --host HOST       主机地址 (默认: 0.0.0.0)

功能:
    - 基准测试套件展示
    - 测试结果可视化
    - 数据检索和分析
    - 远程访问支持

使用示例:
    ./bench.sh web                          # 启动 http://0.0.0.0:9998
    ./bench.sh web --port 8080              # 启动 http://0.0.0.0:8080
    ./bench.sh web --host 127.0.0.1         # 启动仅本地访问
    ./bench.sh web stop                    # 停止Web服务器

注意:
    - 服务器后台运行，不阻塞终端
    - 日志文件: logs/web_server.log
    - PID文件: logs/web_server.pid

EOF
}

# 显示主帮助
show_help() {
    cat << EOF
MNN LLM Bench 主入口脚本

用法:
    $0 <命令> [选项]

可用命令:
    benchmark         运行基准测试 (主要功能)
    batch            运行批量基准测试 (统一预览/执行流程)
    analyze          数据分析和回归测试
    delete           删除分析报告 (输入ID)
    list             列出分析报告历史
    process          数据处理和报告 (开发中)
    web              启动Web服务器
    status           显示系统状态
    clean            清理临时文件和缓存
    clean-logs       清理日志目录(保留README.md和.gitkeep)
    clean-results    清理结果目录(保留README.md和.gitkeep)
    reset            重置项目（执行所有清理功能，需要确认）
    help             显示此帮助信息

主要功能 - 基准测试:
    $0 benchmark <模型> [参数]      # 运行单模型基准测试(推荐)

注意:
    - bench.sh专为单模型简化测试设计
    - 多模型测试请使用框架级功能:
      uv run python framework/benchmark.py model1 model2 model3

基础示例:
    $0 benchmark qwen3_06b          # 快速测试
    $0 analyze 1                    # 分析Suite 1的数据
    $0 web                          # 启动Web服务器

高级示例:
    $0 benchmark qwen3_06b --threads 4 --precision 2
    $0 analyze 1 --x-variable threads --result-types pp,tg
    $0 benchmark deepseek_r1_15b --precision 0 --kv-cache true
    $0 benchmark qwen3_06b --prompt-file en_short.txt --variable-prompt 1
    $0 benchmark --create-sample                # 创建批量测试示例
    $0 web --port 8080                         # 指定端口启动Web服务

分析管理:
    $0 delete 1                               # 删除分析报告 ID 1
    $0 list analysis                          # 列出所有分析报告

获取帮助:
    $0 benchmark --help             # 查看基准测试详细参数
    $0 batch --help                 # 查看批量测试详细参数
    $0 analyze --help               # 查看数据分析帮助
    $0 process --help               # 查看数据处理帮助
    $0 web --help                   # 查看Web服务帮助

日志控制:
    LOG_LEVEL=ERROR $0 status      # 默认：只显示错误
    LOG_LEVEL=INFO $0 status       # 显示信息和更高级别
    LOG_LEVEL=WARN $0 status       # 显示警告和错误
    LOG_LEVEL=DEBUG $0 status      # 显示所有调试信息
    LOG_LEVEL=SILENT $0 status     # 静默模式

EOF
}

# 检查系统环境
check_environment() {
    log_info "检查系统环境..."

    # 检查Python虚拟环境
    if [ ! -d "$VENV_DIR" ]; then
        log_error "Python虚拟环境不存在: $VENV_DIR"
        log_info "请运行: uv init 创建虚拟环境"
        exit 1
    fi

    
    # 检查关键配置文件
    if [ ! -f "$SCRIPT_DIR/config/models.toml" ]; then
        log_error "模型配置文件不存在: config/models.toml"
        exit 1
    fi

    if [ ! -f "$SCRIPT_DIR/config/system.toml" ]; then
        log_error "系统配置文件不存在: config/system.toml"
        exit 1
    fi

    # 检查framework目录
    if [ ! -d "$FRAMEWORK_DIR" ]; then
        log_error "Framework目录不存在: $FRAMEWORK_DIR"
        exit 1
    fi

    log_info "环境检查完成"
}

# 激活Python虚拟环境
activate_venv() {
    log_info "激活Python虚拟环境..."
    source "$VENV_DIR/bin/activate"
}

# 运行基础基准测试
run_benchmark() {
    local model=""
    local scan_dir=""
    local is_scan=false

    # 检查--scan参数
    for arg in "$@"; do
        if [ "$arg" = "--scan" ]; then
            is_scan=true
            break
        fi
    done

    # 如果是扫描模式，特殊处理
    if [ "$is_scan" = true ]; then
        log_info "运行模型扫描..."
        activate_venv
        cd "$FRAMEWORK_DIR"
        python3 benchmark.py "$@"
        exit $?
    fi

    # 常规测试模式
    if [ $# -gt 0 ]; then
        model="$1"
        shift  # 移除模型参数，剩下都是选项参数
    fi

    # 检查--help参数 (-h or --help either as model or option)
    if [ "$model" = "--help" ] || [ "$model" = "-h" ]; then
        show_benchmark_help
        exit 0
    fi

    for arg in "$@"; do
        if [ "$arg" = "--help" ] || [ "$arg" = "-h" ]; then
            show_benchmark_help
            exit 0
        fi
    done

    # 检查是否是--create-sample (作为特殊选项)
    has_create_sample=false
    for arg in "$@"; do
        if [ "$arg" = "--create-sample" ]; then
            has_create_sample=true
            break
        fi
    done

    # 如果是--create-sample且没有模型参数
    if [ "$has_create_sample" = true ] && ([ -z "$model" ] || [ "$model" = "help" ]); then
        log_info "创建批量测试示例..."
        activate_venv
        cd "$FRAMEWORK_DIR"
        python3 benchmark.py --create-sample
        exit $?
    fi

    # 如果没有参数，显示可用模型
    if [ -z "$model" ]; then
        show_benchmark_help
        exit 1
    fi

    # 如果model是--create-sample (无参数情形)
    if [ "$model" = "--create-sample" ]; then
        log_info "创建批量测试示例..."
        activate_venv
        cd "$FRAMEWORK_DIR"
        python3 benchmark.py --create-sample
        exit $?
    fi

    log_info "运行基准测试: 模型=$model"

    # 运行Python benchmark脚本
    cd "$FRAMEWORK_DIR"
    activate_venv
    python3 benchmark.py "$model" "$@"
}

# 运行批量基准测试
run_batch() {
    local task_file=""
    local is_preview=false

    # 检查--help参数
    for arg in "$@"; do
        if [ "$arg" = "--help" ] || [ "$arg" = "-h" ]; then
            show_batch_help
            exit 0
        fi
    done

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--task) task_file="$2"; shift 2 ;;
            --preview)
                is_preview=true
                shift
                ;;
            --create-sample)
                log_info "创建批量测试示例..."
                activate_venv
                cd "$FRAMEWORK_DIR"
                python3 benchmark.py --create-sample
                exit $?
                ;;
            *) log_error "未知参数: $1，使用 --help 查看可用参数" ;;
        esac
    done

    if [ -z "$task_file" ]; then
        log_error "必须指定任务文件: --task FILE"
        show_batch_help
        exit 1
    fi

    
    # 构建benchmark.py命令
    local benchmark_cmd="python3 benchmark.py -b $task_file"

    if [ "$is_preview" = true ]; then
        benchmark_cmd="$benchmark_cmd --preview"
        log_info "预览批量测试计划: $task_file"
    else
        log_info "执行批量基准测试: $task_file"
    fi

    # 调用benchmark.py执行批量测试
    activate_venv
    cd "$FRAMEWORK_DIR"
    eval "$benchmark_cmd"
}

# 运行数据分析
run_analysis() {
    # 检查各种命令参数，区分分析管理和实际分析
    for arg in "$@"; do
        if [ "$arg" = "--help" ] || [ "$arg" = "-h" ]; then
            show_analysis_help
            exit 0
        fi
    done

    # 检查是否是分析管理命令
    for arg in "$@"; do
        if [ "$arg" = "--list-analysis" ]; then
            log_info "列出分析报告记录..."
            activate_venv
            cd "$FRAMEWORK_DIR"
            python3 benchmark.py --list-analysis
            return 0
        fi
    done

    log_info "运行数据分析..."

    # 激活环境并运行Python分析
    activate_venv
    cd "$FRAMEWORK_DIR"
    python3 benchmark.py --analyze "$@"
}

# 处理数据和报告 (占位符)
process_data() {
    # 检查--help参数
    for arg in "$@"; do
        if [ "$arg" = "--help" ] || [ "$arg" = "-h" ]; then
            show_process_help
            exit 0
        fi
    done

    log_info "数据处理功能开发中..."
    log_info "请使用框架级功能: cd framework && python3 src/data_processor.py"
}

# 启动Web服务器
start_web() {
    # 检查stop命令
    if [ $# -gt 0 ] && [ "$1" = "stop" ]; then
        stop_web
        exit 0
    fi

    # 检查--help参数
    for arg in "$@"; do
        if [ "$arg" = "--help" ] || [ "$arg" = "-h" ]; then
            show_web_help
            exit 0
        fi
    done

    # 设置默认参数
    local port="9998"
    local host="0.0.0.0"
    web_log_file="logs/web_server.log"

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -p|--port) port="$2"; shift 2 ;;
            -h|--host) host="$2"; shift 2 ;;
            *) log_error "未知参数: $1，使用 --help 查看可用参数" ;;
        esac
    done

    # 检查是否已有Web服务器在运行
    local pid_file="logs/web_server.pid"
    if [ -f "$pid_file" ]; then
        local existing_pid=$(cat "$pid_file" 2>/dev/null)
        if [ -n "$existing_pid" ] && kill -0 $existing_pid 2>/dev/null; then
            log_info "Web服务器已在运行 (PID: $existing_pid)"
            log_info "访问地址: http://localhost:$port"
            log_info "要重新启动，请先执行: ./bench.sh web stop"
            exit 0
        else
            log_info "清理过期的PID文件"
            rm -f "$pid_file"
        fi
    fi

    log_info "启动Web服务器: $host:$port..."
    log_info "日志文件: $web_log_file"

    # 确保日志目录存在
    mkdir -p "$(dirname "$web_log_file")"

    # 启动Web服务器（后台运行）
    log_info "Web服务器后台启动中..."
    nohup uv run python "$SCRIPT_DIR/web_server/app.py" > "$web_log_file" 2>&1 &
    local web_pid=$!

    # 等待启动并检查状态
    sleep 2
    if kill -0 $web_pid 2>/dev/null; then
        log_info "Web服务器启动成功 (PID: $web_pid)"
        log_info "访问地址: http://localhost:$port"
        log_info "网络访问: http://$host:$port"
        log_info "查看日志: tail -f $web_log_file"
        log_info "停止服务器: kill $web_pid"

        # 保存PID到文件以便管理
        echo $web_pid > "logs/web_server.pid"
    else
        log_error "Web服务器启动失败，请检查日志: $web_log_file"
        exit 1
    fi
}

# 显示系统状态
show_status() {
    log_info "系统状态检查..."

    echo "=== 基本信息 ==="
    echo "脚本目录: $SCRIPT_DIR"
    echo "虚拟环境: $VENV_DIR"
    echo "框架目录: $FRAMEWORK_DIR"

    echo "=== 环境检查 ==="
    if command -v uv &> /dev/null; then
        echo "✓ uv 工具可用 ($(uv --version 2>/dev/null || echo 'version unknown'))"
    else
        echo "✗ uv 工具不可用"
    fi
    if [ -d "$VENV_DIR" ]; then
        echo "✓ 虚拟环境存在"
    else
        echo "✗ 虚拟环境不存在"
    fi

    if [ -f "$SCRIPT_DIR/config/models.toml" ]; then
        echo "✓ 模型配置文件存在"
    else
        echo "✗ 模型配置文件不存在"
    fi

    if [ -f "$SCRIPT_DIR/config/system.toml" ]; then
        echo "✓ 系统配置文件存在"
    else
        echo "✗ 系统配置文件不存在"
    fi

    if [ -d "$FRAMEWORK_DIR" ]; then
        echo "✓ Framework目录存在"
    else
        echo "✗ Framework目录不存在"
    fi

    echo "=== MNN 工具检查 ==="
    # 检查llm_bench工具 - 直接从配置文件读取路径
    if [ -f "$SCRIPT_DIR/config/system.toml" ]; then
        # 提取路径配置
        llm_bench_path=$(grep 'path.*=' "$SCRIPT_DIR/config/system.toml" | sed 's/.*"\([^"]*\)".*/\1/' | sed 's|~|'"$HOME"'|' | head -1)

        if [ -n "$llm_bench_path" ]; then
            if [ -f "$llm_bench_path" ]; then
                echo "✓ llm_bench 工具存在 ($llm_bench_path)"
                if [ -x "$llm_bench_path" ]; then
                    echo "✓ llm_bench 工具可执行"
                else
                    echo "✗ llm_bench 工具不可执行"
                fi
            else
                echo "✗ llm_bench 工具不存在 ($llm_bench_path)"
                log_info "请检查MNN编译安装，或更新config/system.toml中的path配置"
            fi
        else
            echo "✗ llm_bench 路径配置缺失"
            log_info "请在config/system.toml的[llm_bench]部分设置path参数"
        fi
    else
        echo "✗ 系统配置文件不存在 ($SCRIPT_DIR/config/system.toml)"
        log_info "缺少必要的配置文件"
    fi

    echo "=== 可用模型 ==="
    # 检查uv和Python环境
    if command -v uv &> /dev/null && [ -f "$FRAMEWORK_DIR/benchmark.py" ]; then
        cd "$FRAMEWORK_DIR"
        log_info "通过uv获取可用模型列表..."
        uv run python benchmark.py 2>/dev/null || {
            log_warn "uv运行模型列表失败，尝试直接Python..."
            if command -v python3 &> /dev/null; then
                if [ -d "$VENV_DIR" ]; then
                    source "$VENV_DIR/bin/activate"
                    python3 benchmark.py
                else
                    log_warn "虚拟环境不存在，无法获取模型列表"
                fi
            else
                log_warn "Python3不可用，无法获取模型列表"
            fi
        }
    elif command -v python3 &> /dev/null && [ -f "$FRAMEWORK_DIR/benchmark.py" ]; then
        cd "$FRAMEWORK_DIR"
        log_info "通过直接Python获取可用模型列表..."
        if [ -d "$VENV_DIR" ]; then
            source "$VENV_DIR/bin/activate"
            python3 benchmark.py
        else
            log_warn "虚拟环境不存在，无法获取模型列表"
        fi
    else
        log_warn "Python环境不可用，无法获取模型列表"
    fi

    echo "=== 结果目录 ==="
    if [ -d "$SCRIPT_DIR/results" ]; then
        echo "✓ 结果目录存在"
        du -sh "$SCRIPT_DIR/results" 2>/dev/null || echo "  目录为空"
    else
        echo "✗ 结果目录不存在"
    fi
}

# 从配置文件中读取目录路径
get_config_paths() {
    local config_file="$SCRIPT_DIR/config/system.toml"

    # 设置默认值
    LOGS_DIR="logs"
    TEMP_DIR="temp"
    RESULTS_DIR="results"

    # 如果配置文件存在，从中读取路径
    if [ -f "$config_file" ]; then
        # 读取log_dir
        local log_dir_val=$(grep -A1 "\[logging\]" "$config_file" | grep "log_dir" | cut -d'"' -f2 2>/dev/null || echo "")
        if [ -n "$log_dir_val" ]; then
            LOGS_DIR="$log_dir_val"
        fi

        # 读取temp_dir
        local temp_dir_val=$(grep -A1 "\[temp\]" "$config_file" | grep "temp_dir" | cut -d'"' -f2 2>/dev/null || echo "")
        if [ -n "$temp_dir_val" ]; then
            TEMP_DIR="$temp_dir_val"
        fi

        # 读取output_dir
        local output_dir_val=$(grep -A1 "\[results\]" "$config_file" | grep "output_dir" | cut -d'"' -f2 2>/dev/null || echo "")
        if [ -n "$output_dir_val" ]; then
            RESULTS_DIR="$output_dir_val"
        fi
    fi

    # 构建完整路径
    LOGS_PATH="$SCRIPT_DIR/$LOGS_DIR"
    TEMP_PATH="$SCRIPT_DIR/$TEMP_DIR"
    RESULTS_PATH="$SCRIPT_DIR/$RESULTS_DIR"
}

# 清理临时文件
clean_temp() {
    get_config_paths

    log_info "清理临时文件和缓存..."

    # 清理Python缓存
    find "$SCRIPT_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$SCRIPT_DIR" -name "*.pyc" -delete 2>/dev/null || true

    # 清理临时测试文件
    find "$RESULTS_PATH" -name "*.tmp" -delete 2>/dev/null || true
    find "$RESULTS_PATH" -name "temp_*" -type d -exec rm -rf {} + 2>/dev/null || true

    # 清理整个temp目录
    if [ -d "$TEMP_PATH" ]; then
        log_info "清理 temp 目录: $TEMP_PATH"
        rm -rf "$TEMP_PATH"
        if [ $? -eq 0 ]; then
            log_info "temp 目录清理完成"
        else
            log_warn "清理 temp 目录时遇到错误"
        fi
    else
        log_info "temp 目录不存在，跳过清理"
    fi

    # 注意：日志文件和结果文件保留，不在这里清理

    log_info "清理完成"
}

# 清理日志目录（保留README.md和.gitkeep）
clean_logs() {
    get_config_paths

    if [ ! -d "$LOGS_PATH" ]; then
        log_info "日志目录不存在，跳过清理"
        return 0
    fi

    log_info "清理 logs 目录..."

    # 删除除保留文件外的所有内容
    # 使用find命令，排除README.md和.gitkeep
    find "$LOGS_PATH" -mindepth 1 -not -name "README.md" -not -name ".gitkeep" -print0 2>/dev/null | while IFS= read -r -d $'\0' file; do
        if [ -e "$file" ]; then
            rm -rf "$file" 2>/dev/null || true
        fi
    done

    log_info "logs 目录清理完成"
}

# 清理results目录（保留README.md和.gitkeep）
clean_results() {
    get_config_paths

    if [ ! -d "$RESULTS_PATH" ]; then
        log_info "results 目录不存在，跳过清理"
        return 0
    fi

    log_info "清理 results 目录..."

    # 删除除保留文件外的所有内容
    # 使用find命令，排除README.md和.gitkeep
    find "$RESULTS_PATH" -mindepth 1 -not -name "README.md" -not -name ".gitkeep" -print0 2>/dev/null | while IFS= read -r -d $'\0' file; do
        if [ -e "$file" ]; then
            rm -rf "$file" 2>/dev/null || true
        fi
    done

    log_info "results 目录清理完成"
}

# 重置项目状态（包含所有清理功能）
reset_project() {
    echo -e "${YELLOW}[警告]${NC} 此命令将删除以下内容："
    echo "  • 所有临时文件和temp目录"
    echo "  • 所有日志文件（保留README.md和.gitkeep）"
    echo "  • 所有测试结果目录和文件（保留README.md和.gitkeep）"
    echo ""
    read -p "确认要继续吗？(输入 'yes' 继续，其他任何输入取消): " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "用户取消操作"
        return 0
    fi

    log_info "重置项目状态，清理所有临时文件和结果..."

    # 执行所有清理功能
    clean_temp
    clean_logs
    clean_results

    log_info "项目重置完成"
}

# 主函数
main() {
    # 检查是否有参数
    if [ $# -eq 0 ]; then
        show_help
        exit 1
    fi

    # 获取命令
    local command="$1"
    shift

    case "$command" in
        benchmark|bench|test)
            check_environment
            run_benchmark "$@"
            ;;
        batch|orchestrated|orch|orchestrate)
            check_environment
            run_batch "$@"
            ;;
        analyze|analysis|regression)
            check_environment
            run_analysis "$@"
            ;;
        delete|del|remove)
            check_environment
            activate_venv
            cd "$FRAMEWORK_DIR"
            python3 benchmark.py --delete-analysis "$@"
            ;;
        list|ls)
            # 分析列表命令
            if [ $# -eq 0 ] || [ "$1" = "analysis" ] || [ "$1" = "analyses" ]; then
                check_environment
                activate_venv
                cd "$FRAMEWORK_DIR"
                python3 benchmark.py --list-analysis "$@"
            else
                log_error "仅支持分析列表: $0 list analysis"
                exit 1
            fi
            ;;
        process|proc|data)
            check_environment
            process_data "$@"
            ;;
        web|serve|server)
            # 简化环境检查，仅检查必要的组件
            if ! command -v uv &> /dev/null; then
                log_error "uv工具不可用，请安装uv工具"
                exit 1
            fi
            if [ ! -d "$VENV_DIR" ]; then
                log_error "Python虚拟环境不存在: $VENV_DIR"
                log_info "请运行: uv init 创建虚拟环境"
                exit 1
            fi
            if [ ! -f "$SCRIPT_DIR/web_server/app.py" ]; then
                log_error "Web服务器文件不存在: $SCRIPT_DIR/web_server/app.py"
                exit 1
            fi
            start_web "$@"
            ;;
        status|stat)
            show_status
            ;;
        clean|cleanup)
            clean_temp
            ;;
        clean-logs)
            clean_logs
            ;;
        clean-results)
            clean_results
            ;;
        reset|reinit)
            reset_project
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 脚本主入口
main "$@"