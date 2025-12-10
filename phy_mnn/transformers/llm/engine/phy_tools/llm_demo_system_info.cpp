//
//  llm_demo_system_info.cpp
//  Based on llm_demo.cpp with enhanced system information display
//
//  Created by MNN on 2023/03/24.
//  Modified to show NEON and system information
//  ZhaodeWang
//

#include "llm/llm.hpp"
#define MNN_OPEN_TIME_TRACE
#include <MNN/AutoTime.hpp>
#include <MNN/expr/ExecutorScope.hpp>
#include <fstream>
#include <sstream>
#include <stdlib.h>
#include <initializer_list>
#include <iostream>

// 平台相关头文件
#ifdef __linux__
#include <sys/utsname.h>
#include <unistd.h>
#endif

#if defined(__aarch64__) && defined(__linux__)
#include <asm/hwcap.h>
#include <sys/auxv.h>
// 处理不同内核版本的宏定义差异
#ifndef HWCAP_ASIMD
#define HWCAP_ASIMD (1 << 1)
#endif
#ifndef HWCAP_FP16
#define HWCAP_FP16 (1 << 23)
#endif
#ifndef HWCAP_FPHP
#define HWCAP_FPHP (1 << 10)
#endif
// SVE和SVE2在很多情况下定义在HWCAP2中
#ifndef HWCAP_SVE
#define HWCAP_SVE (1 << 22)
#endif
#ifdef HWCAP2_SVE
#define HWCAP_SVE_AVAILABLE HWCAP2_SVE
#else
#define HWCAP_SVE_AVAILABLE HWCAP_SVE
#endif
#endif

//#define LLM_SUPPORT_AUDIO
#ifdef LLM_SUPPORT_AUDIO
#include "audio/audio.hpp"
#endif

using namespace MNN::Transformer;

// 系统信息检测函数
static void print_system_info() {
    std::cout << "\n========================================\n";
    std::cout << "    MNN LLM System Information\n";
    std::cout << "========================================\n";

    // 操作系统信息
#ifdef __linux__
    struct utsname sysinfo;
    if (uname(&sysinfo) == 0) {
        std::cout << "OS: " << sysinfo.sysname << " " << sysinfo.release
                  << " (" << sysinfo.machine << ")\n";
    }
#endif

    // CPU架构信息
    std::cout << "Architecture: ";
#ifdef __aarch64__
    std::cout << "ARM64 (AArch64)\n";
#elif __arm__
    std::cout << "ARM32\n";
#elif __x86_64__
    std::cout << "x86_64\n";
#else
    std::cout << "Unknown\n";
#endif

    // NEON指令集支持情况
    std::cout << "NEON Support:\n";
    std::cout << "  Compile-time: ";
#ifdef MNN_USE_NEON
    std::cout << "YES\n";
#else
    std::cout << "NO\n";
#endif

    std::cout << "  Runtime: ";
#if defined(__aarch64__) && defined(__linux__)
    unsigned long hwcaps = getauxval(AT_HWCAP);
    if (hwcaps & HWCAP_ASIMD) {
        std::cout << "YES (ASIMD available)\n";
    } else {
        std::cout << "NO (ASIMD not available)\n";
    }

    // 检查更多ARM特性
    std::cout << "ARM Extensions:\n";
    std::cout << "  ASIMD: " << (hwcaps & HWCAP_ASIMD ? "YES" : "NO") << "\n";

    // FP16支持检查
    std::cout << "  FP16: ";
    if (hwcaps & HWCAP_FPHP) {
        std::cout << "YES (FPHP instructions)\n";
    } else if (hwcaps & HWCAP_FP16) {
        std::cout << "YES (FP16 instructions)\n";
    } else {
        std::cout << "NO\n";
    }

    // SVE支持检查
    std::cout << "  SVE: ";
    if (hwcaps & HWCAP_SVE) {
        std::cout << "YES\n";
    } else {
        std::cout << "NO\n";
    }

    // SVE2支持检查 - 需要检查HWCAP2
    std::cout << "  SVE2: ";
    unsigned long hwcaps2 = getauxval(AT_HWCAP2);
    #ifdef HWCAP2_SVE2
    if (hwcaps2 & HWCAP2_SVE2) {
        std::cout << "YES\n";
    } else {
        std::cout << "NO\n";
    }
    #else
    // 如果没有SVE2的宏定义，尝试直接使用位值
    if (hwcaps2 & (1UL << 1)) { // SVE2通常在HWCAP2的第1位
        std::cout << "YES\n";
    } else {
        std::cout << "NO (HWCAP2_SVE2 not defined)\n";
    }
    #endif

#elif defined(__aarch64__)
    // macOS/非Linux ARM64平台的处理
    std::cout << "YES (NEON assumed available on Apple Silicon)\n";
    std::cout << "ARM Extensions:\n";
    std::cout << "  ASIMD: YES (assumed on Apple Silicon)\n";
    std::cout << "  FP16: YES (assumed on Apple Silicon)\n";
    std::cout << "  SVE: NO (not supported on current Apple Silicon)\n";
    std::cout << "  SVE2: NO (not supported on current Apple Silicon)\n";

#elif defined(__arm__) && defined(__linux__)
    unsigned long hwcaps = getauxval(AT_HWCAP);
    if (hwcaps & HWCAP_NEON) {
        std::cout << "YES\n";
    } else {
        std::cout << "NO\n";
    }
#else
    std::cout << "N/A (Not ARM architecture)\n";
#endif

    // MNN构建配置信息
    std::cout << "MNN Build Configuration:\n";
#ifdef MNN_BUILD_LLM
    std::cout << "  LLM Support: YES\n";
#else
    std::cout << "  LLM Support: NO\n";
#endif

#ifdef MNN_OPENMP
    std::cout << "  OpenMP: YES\n";
#else
    std::cout << "  OpenMP: NO\n";
#endif

#ifdef MNN_USE_THREAD_POOL
    std::cout << "  Thread Pool: YES\n";
#else
    std::cout << "  Thread Pool: NO\n";
#endif

#ifdef MNN_SUPPORT_TRANSFORMER_FUSE
    std::cout << "  Transformer Fusion: YES\n";
#else
    std::cout << "  Transformer Fusion: NO\n";
#endif

#ifdef MNN_LOW_MEMORY
    std::cout << "  Low Memory Mode: YES\n";
#else
    std::cout << "  Low Memory Mode: NO\n";
#endif

    // CPU核心数
#ifdef __linux__
    long cpu_count = sysconf(_SC_NPROCESSORS_ONLN);
    std::cout << "CPU Cores: " << cpu_count << "\n";
#endif

    std::cout << "========================================\n\n";
}

static void tuning_prepare(Llm* llm) {
    MNN_PRINT("Prepare for tuning opt Begin\n");
    llm->tuning(OP_ENCODER_NUMBER, {1, 5, 10, 20, 30, 50, 100});
    MNN_PRINT("Prepare for tuning opt End\n");
}

std::vector<std::vector<std::string>> parse_csv(const std::vector<std::string>& lines) {
    std::vector<std::vector<std::string>> csv_data;
    std::string line;
    std::vector<std::string> row;
    std::string cell;
    bool insideQuotes = false;
    bool startCollecting = false;

    // content to stream
    std::string content = "";
    for (auto line : lines) {
        content = content + line + "\n";
    }
    std::istringstream stream(content);

    while (stream.peek() != EOF) {
        char c = stream.get();
        if (c == '"') {
            if (insideQuotes && stream.peek() == '"') { // quote
                cell += '"';
                stream.get(); // skip quote
            } else {
                insideQuotes = !insideQuotes; // start or end text in quote
            }
            startCollecting = true;
        } else if (c == ',' && !insideQuotes) { // end element, start new element
            row.push_back(cell);
            cell.clear();
            startCollecting = false;
        } else if ((c == '\n' || stream.peek() == EOF) && !insideQuotes) { // end line
            row.push_back(cell);
            csv_data.push_back(row);
            cell.clear();
            row.clear();
            startCollecting = false;
        } else {
            cell += c;
            startCollecting = true;
        }
    }
    return csv_data;
}

static int benchmark(Llm* llm, const std::vector<std::string>& prompts, int max_token_number) {
    int prompt_len = 0;
    int decode_len = 0;
    int64_t prefill_time = 0;
    int64_t decode_time = 0;
    int64_t sample_time = 0;
    // llm->warmup();
    auto context = llm->getContext();
    if (max_token_number > 0) {
        llm->set_config("{\"max_new_tokens\":1}");
    }
#ifdef LLM_SUPPORT_AUDIO
    std::vector<float> waveform;
    llm->setWavformCallback([&](const float* ptr, size_t size, bool last_chunk) {
        waveform.reserve(waveform.size() + size);
        waveform.insert(waveform.end(), ptr, ptr + size);
        if (last_chunk) {
            auto waveform_var = MNN::Express::_Const(waveform.data(), {(int)waveform.size()}, MNN::Express::NCHW, halide_type_of<float>());
            MNN::AUDIO::save("output.wav", waveform_var, 24000);
            waveform.clear();
        }
        return true;
    });
#endif
    for (int i = 0; i < prompts.size(); i++) {
        auto prompt = prompts[i];
     // #define MIMO_NO_THINKING
     #ifdef MIMO_NO_THINKING
        // update config.json and llm_config.json if need. example:
        llm->set_config("{\"assistant_prompt_template\":\"<|im_start|>assistant\n\n\n%s<|im_end|>\n\"}");
        prompt = prompt + "\n\n";
     #endif

        // prompt start with '#' will be ignored
        if (prompt.substr(0, 1) == "#") {
            continue;
        }
        if (max_token_number >= 0) {
            llm->response(prompt, &std::cout, nullptr, 0);
            while (!llm->stoped() && context->gen_seq_len < max_token_number) {
                llm->generate(1);
            }
        } else {
            llm->response(prompt);
        }
        prompt_len += context->prompt_len;
        decode_len += context->gen_seq_len;
        prefill_time += context->prefill_us;
        decode_time += context->decode_us;
        sample_time += context->sample_us;
    }
    llm->generateWavform();

    float vision_s = context->vision_us / 1e6;
    float audio_s = context->audio_us / 1e6;
    float prefill_s = prefill_time / 1e6;
    float decode_s = decode_time / 1e6;
    float sample_s = sample_time / 1e6;
    float vision_speed = 0.0f;
    if (context->pixels_mp > 0.0f) {
        vision_speed = context->pixels_mp / vision_s;
    }
    float audio_speed = 0.0f;
    if (context->audio_input_s > 0.0f) {
        audio_speed = context->audio_input_s / audio_s;
    }
    printf("\n#################################\n");
    printf("prompt tokens num = %d\n", prompt_len);
    printf("decode tokens num = %d\n", decode_len);
    printf(" vision time = %.2f s\n", vision_s);
    printf(" pixels_mp = %.2f MP\n", context->pixels_mp);
    printf("  audio process time = %.2f s\n", audio_s);
    printf("  audio input time = %.2f s\n", context->audio_input_s);
    printf("prefill time = %.2f s\n", prefill_s);
    printf(" decode time = %.2f s\n", decode_s);
    printf(" sample time = %.2f s\n", sample_s);
    printf("prefill speed = %.2f tok/s\n", prompt_len / prefill_s);
    printf(" decode speed = %.2f tok/s\n", decode_len / decode_s);
    printf(" vision speed = %.3f MP/s\n", vision_speed);
    printf(" audio RTF = %.3f \n", audio_s / context->audio_input_s);
    printf("##################################\n");
    return 0;
}

static int ceval(Llm* llm, const std::vector<std::string>& lines, std::string filename) {
    auto csv_data = parse_csv(lines);
    int right = 0, wrong = 0;
    std::vector<std::string> answers;
    for (int i = 1; i < csv_data.size(); i++) {
        const auto& elements = csv_data[i];
        std::string prompt = elements[1];
        prompt += "\n\nA. " + elements[2];
        prompt += "\nB. " + elements[3];
        prompt += "\nC. " + elements[4];
        prompt += "\nD. " + elements[5];
        prompt += "\n\n";
        printf("%s", prompt.c_str());
        printf("## 进度: %d / %lu\n", i, lines.size() - 1);
        std::ostringstream lineOs;
        llm->response(prompt.c_str(), &lineOs);
        auto line = lineOs.str();
        printf("%s", line.c_str());
        answers.push_back(line);
    }
    {
        auto position = filename.rfind("/");
        if (position != std::string::npos) {
            filename = filename.substr(position + 1, -1);
        }
        position = filename.find("_val");
        if (position != std::string::npos) {
            filename.replace(position, 4, "_res");
        }
        std::cout << "store to " << filename << std::endl;
    }
    std::ofstream ofp(filename);
    ofp << "id,answer" << std::endl;
    for (int i = 0; i < answers.size(); i++) {
        auto& answer = answers[i];
        ofp << i << ",\"" << answer << "\"" << std::endl;
    }
    ofp.close();
    return 0;
}

static int eval(Llm* llm, std::string prompt_file, int max_token_number) {
    std::cout << "prompt file is " << prompt_file << std::endl;
    std::ifstream prompt_fs(prompt_file);
    std::vector<std::string> prompts;
    std::string prompt;
//#define LLM_DEMO_ONELINE
#ifdef LLM_DEMO_ONELINE
    std::ostringstream tempOs;
    tempOs << prompt_fs.rdbuf();
    prompt = tempOs.str();
    prompts = {prompt};
#else
    while (std::getline(prompt_fs, prompt)) {
        if (prompt.empty()) {
            continue;
        }
        if (prompt.back() == '\r') {
            prompt.pop_back();
        }
        prompts.push_back(prompt);
    }
#endif
    prompt_fs.close();
    if (prompts.empty()) {
        return 1;
    }
    // ceval
    if (prompts[0] == "id,question,A,B,C,D,answer") {
        return ceval(llm, prompts, prompt_file);
    }
    return benchmark(llm, prompts, max_token_number);
}

void chat(Llm* llm) {
    ChatMessages messages;
    messages.emplace_back("system", "You are a helpful assistant.");
    auto context = llm->getContext();
    while (true) {
        std::cout << "\nUser: ";
        std::string user_str;
        std::getline(std::cin, user_str);
        if (user_str == "/exit") {
            return;
        }
        if (user_str == "/reset") {
            llm->reset();
            std::cout << "\nA: reset done." << std::endl;
            continue;
        }
        messages.emplace_back("user", user_str);
        std::cout << "\nA: " << std::flush;
        llm->response(messages);
        auto assistant_str = context->generate_str;
        messages.emplace_back("assistant", assistant_str);
    }
}

static void print_runtime_info(Llm* llm) {
    auto context = llm->getContext();
    std::cout << "\n========================================\n";
    std::cout << "      LLM Runtime Configuration\n";
    std::cout << "========================================\n";
    std::cout << "Backend Type: CPU\n";

    // 显示配置信息（通过dump_config获取JSON配置）
    std::cout << "Current Configuration:\n";
    std::string config_str = llm->dump_config();
    std::cout << config_str << std::endl;

    std::cout << "========================================\n\n";
}

int main(int argc, const char* argv[]) {
    if (argc < 2) {
        std::cout << "Usage: " << argv[0] << " config.json <prompt.txt>" << std::endl;
        return 0;
    }

    // 显示系统信息（在任何MNN操作之前）
    print_system_info();

    MNN::BackendConfig backendConfig;
    auto executor = MNN::Express::Executor::newExecutor(MNN_FORWARD_CPU, backendConfig, 1);
    MNN::Express::ExecutorScope s(executor);

    std::string config_path = argv[1];
    std::cout << "config path is " << config_path << std::endl;
    std::unique_ptr<Llm> llm(Llm::createLLM(config_path));

    // 显示运行时配置信息
    print_runtime_info(llm.get());

    llm->set_config("{\"tmp_path\":\"tmp\"}");
    {
        AUTOTIME;
        bool res = llm->load();
        if (!res) {
            MNN_ERROR("LLM init error\n");
            return 0;
        }
    }
    if (true) {
        AUTOTIME;
        tuning_prepare(llm.get());
    }
    if (argc < 3) {
        chat(llm.get());
        return 0;
    }
    int max_token_number = -1;
    if (argc >= 4) {
        std::istringstream os(argv[3]);
        os >> max_token_number;
    }
    if (argc >= 5) {
        MNN_PRINT("Set not thinking, only valid for Qwen3\n");
        llm->set_config(R"({
            "jinja": {
                "context": {
                    "enable_thinking":false
                }
            }
        })");
    }
    std::string prompt_file = argv[2];
    llm->set_config(R"({
        "async":false
    })");
    return eval(llm.get(), prompt_file, max_token_number);
}