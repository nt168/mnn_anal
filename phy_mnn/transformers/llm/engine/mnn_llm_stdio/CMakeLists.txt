# MNN LLM Stdio Backend CMakeLists.txt
#
# 配置基于三管道通信的LLM服务后端 (stdin/stdout/stderr)

include_directories(${CMAKE_CURRENT_LIST_DIR}/include/)
include_directories(${CMAKE_CURRENT_LIST_DIR}/../include/)

# 后端核心源文件
set(LLM_STDIO_CORE_SOURCES
    ${CMAKE_CURRENT_LIST_DIR}/src/llm_stdio_core.cpp
)

# 后端应用程序源文件
set(BACKEND_SOURCES
    ${CMAKE_CURRENT_LIST_DIR}/backend/main.cpp
    ${LLM_STDIO_CORE_SOURCES}
)

# 创建核心静态库
add_library(llm_stdio_core STATIC ${LLM_STDIO_CORE_SOURCES})
target_compile_options(llm_stdio_core PRIVATE -fno-exceptions)
target_compile_definitions(llm_stdio_core PRIVATE MNN_LOW_MEMORY)
target_link_libraries(llm_stdio_core ${LLM_DEPS})

# 创建后端可执行文件
add_executable(mnn_llm_stdio_backend ${BACKEND_SOURCES})

# 设置编译选项
target_compile_options(mnn_llm_stdio_backend PRIVATE -fno-exceptions)
target_compile_definitions(mnn_llm_stdio_backend PRIVATE MNN_LOW_MEMORY)

# 链接依赖
target_link_libraries(mnn_llm_stdio_backend ${LLM_DEPS})

# 安装规则
install(FILES ${CMAKE_CURRENT_LIST_DIR}/include/llm_stdio_core.hpp
        DESTINATION include/transformers/llm/mnn_llm_stdio)

install(TARGETS mnn_llm_stdio_backend llm_stdio_core
        RUNTIME DESTINATION bin
        ARCHIVE DESTINATION lib)