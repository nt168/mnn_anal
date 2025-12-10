#include "llm/llm.hpp"
#include "core/MNNFileUtils.h"
#include <MNN/AutoTime.hpp>
#include <MNN/expr/ExecutorScope.hpp>
#include <fstream>
#include <sstream>
#include <regex>
#include <stdlib.h>
#include <initializer_list>
#include <rapidjson/document.h>
#include <thread>
#include <algorithm>
#include <numeric>
#include <random>


#define MNN_OPEN_TIME_TRACE

// 为了支持图片加载，我们需要包含相关头文件
#include <MNN/ImageProcess.hpp>
#include "../../../tools/cv/include/cv/imgcodecs.hpp"


using namespace MNN::Transformer;

struct RuntimeParameters {
    std::vector<std::string>         model;
    std::vector<int>                 backends;
    std::vector<int>                 threads;
    bool                             useMmap;
    std::vector<int>                 power;
    std::vector<int>                 precision;
    std::vector<int>                 memory;
    std::vector<int>                 dynamicOption;
};

struct TestParameters {
    std::vector<int>                 nPrompt;
    std::vector<int>                 nGenerate;
    std::vector<std::pair<int, int>> nPrompGen;
    std::vector<int>                 nRepeat;
    std::string                      kvCache;
    std::string                      loadTime;
    bool                             useVariablePrompt;  // 新增：可变提示词开关
    bool                             verbose;            // 新增：详细输出开关
    std::string                      promptFilePath;     // 新增：提示词文件路径
    std::string                      imageFilePath;      // 新增：图片文件路径
};

struct CommandParameters {
    std::string         model;
    int                 backend;
    int                 threads;
    bool                useMmap;
    int                 power;
    int                 precision;
    int                 memory;
    int                 dynamicOption;

    int                 nPrompt;
    int                 nGenerate;
    std::pair<int, int> nPrompGen;
    int                 nRepeat;
    std::string         kvCache;
    std::string         loadingTime;
    bool                useVariablePrompt;  // 新增：可变提示词开关
    bool                verbose;            // 新增：详细输出开关
    std::string         promptFilePath;     // 新增：提示词文件路径
    std::string         imageFilePath;      // 新增：图片文件路径

};


static const RuntimeParameters runtimeParamsDefaults = {
    /* model                */ { "./Qwen2.5-1.5B-Instruct" },
    /* backends             */ { 0 },
    /* threads            */ { 4 },
    /* useMmap             */ false,
    /* power                */ { 0 },
    /* precision            */ { 2 },
    /* memory               */ { 2 },
    /* dynamicOption       */ { 0 }
};


static const TestParameters testParamsDefaults = {
    /* nPrompt             */ { 512 },
    /* nGenerate           */ { 128 },
    /* nPrompGen           */ {std::make_pair(0, 0)},
    /* nRepeat             */ { 5 },
    /* kvCache             */ { "false" },
    /* loadingTime         */ {"false"},
    /* useVariablePrompt   */ false,  // 新增：默认使用固定提示词
    /* verbose             */ false,   // 新增：默认不显示详细输出
    /* promptFilePath      */ "",      // 新增：默认为空，表示不使用文件输入
    /* imageFilePath       */ ""       // 新增：默认为空，表示不使用图片输入
};


struct commandParametersInstance {

    CommandParameters mCmdParam;

    commandParametersInstance(CommandParameters cmdParam) {
        mCmdParam.model          = cmdParam.model;
        mCmdParam.backend        = cmdParam.backend;
        mCmdParam.threads        = cmdParam.threads;
        mCmdParam.useMmap        = cmdParam.useMmap;
        mCmdParam.power          = cmdParam.power;
        mCmdParam.precision      = cmdParam.precision;
        mCmdParam.memory         = cmdParam.memory;
        mCmdParam.dynamicOption  = cmdParam.dynamicOption;

        mCmdParam.nPrompt        = cmdParam.nPrompt;
        mCmdParam.nGenerate      = cmdParam.nGenerate;
        mCmdParam.nPrompGen      = cmdParam.nPrompGen;
        mCmdParam.nRepeat        = cmdParam.nRepeat;
        mCmdParam.kvCache        = cmdParam.kvCache;
        mCmdParam.loadingTime    = cmdParam.loadingTime;
        mCmdParam.useVariablePrompt = cmdParam.useVariablePrompt;  // 新增
        mCmdParam.verbose            = cmdParam.verbose;            // 新增
        mCmdParam.promptFilePath     = cmdParam.promptFilePath;     // 新增
        mCmdParam.imageFilePath      = cmdParam.imageFilePath;      // 新增
    }

    CommandParameters get_cmd_parameters() const {
        return mCmdParam;
    }

    bool equal_runtime_params(const commandParametersInstance & other) const {
        return mCmdParam.model == other.mCmdParam.model &&
        mCmdParam.useMmap == other.mCmdParam.useMmap &&
        mCmdParam.power == other.mCmdParam.power &&
        mCmdParam.precision == other.mCmdParam.precision &&
        mCmdParam.memory == other.mCmdParam.memory &&
        mCmdParam.dynamicOption == other.mCmdParam.dynamicOption;
    }
};

template <typename T> static T avg(const std::vector<T> & v) {
    if (v.empty()) {
        return 0;
    }
    T sum = std::accumulate(v.begin(), v.end(), T(0));
    return sum / (T) v.size();
}

template <typename T> static T stdev(const std::vector<T> & v) {
    if (v.size() <= 1) {
        return 0;
    }
    T mean   = avg(v);
    T sq_sum = std::inner_product(v.begin(), v.end(), v.begin(), T(0));
    T stdev  = std::sqrt(sq_sum / (T) (v.size() - 1) - mean * mean * (T) v.size() / (T) (v.size() - 1));
    return stdev;
}

template <class T> static std::string join(const std::vector<T> & values, const std::string & delim) {
    std::ostringstream str;
    for (size_t i = 0; i < values.size(); i++) {
        str << values[i];
        if (i < values.size() - 1) {
            str << delim;
        }
    }
    return str.str();
}

struct TestInstance {
//    static const std::string build_commit;
    std::string              model;
    std::string              modelConfigFile;
    std::string              modelType;
    uint64_t                 modelSize;
    int                      threads;
    bool                     useMmap;
    int                      nPrompt;
    int                      nGenerate;
    int                      nRepeat;              // 新增：测试重复次数
    std::string              kvCache;              // 新增：KV缓存设置
    std::string              loadingTime;          // 新增：加载时间测试
    std::vector<int64_t>     prefillUs;
    std::vector<int64_t>     decodeUs;
    std::vector<int64_t>     samplesUs;
    std::vector<double>      loadingS;
    int                      backend;
    int                      precision;
    int                      power;
    int                      memory;
    int                      dynamicOption;
    bool                     useVariablePrompt;  // 新增：可变提示词标记
    bool                     verbose;           // 新增：详细输出标记
    std::string              promptFilePath;     // 新增：提示词文件路径
    std::string              imageFilePath;      // 新增：图片文件路径
    int                      originalNPrompt;    // 新增：原始prompt参数
    int                      actualNPrompt;      // 新增：实际使用的prompt长度
    std::string              pType;              // 新增：提示词类型 (fix/variable/file/image)

    TestInstance(const commandParametersInstance & instance) {

        model             = instance.mCmdParam.model;
        modelConfigFile   = instance.mCmdParam.model;  // 保留向后兼容
        threads           = instance.mCmdParam.threads;
        useMmap           = instance.mCmdParam.useMmap;
        nPrompt           = instance.mCmdParam.nPrompt;
        nGenerate         = instance.mCmdParam.nGenerate;
        nRepeat           = instance.mCmdParam.nRepeat;
        kvCache           = instance.mCmdParam.kvCache;
        loadingTime       = instance.mCmdParam.loadingTime;
        backend           = instance.mCmdParam.backend;
        precision         = instance.mCmdParam.precision;
        memory            = instance.mCmdParam.memory;
        power             = instance.mCmdParam.power;
        dynamicOption     = instance.mCmdParam.dynamicOption;
        useVariablePrompt = instance.mCmdParam.useVariablePrompt;  // 新增
        verbose           = instance.mCmdParam.verbose;            // 新增
        promptFilePath    = instance.mCmdParam.promptFilePath;     // 新增
        imageFilePath     = instance.mCmdParam.imageFilePath;      // 新增
        originalNPrompt   = instance.mCmdParam.nPrompt;           // 新增：保存原始值
        actualNPrompt     = instance.mCmdParam.nPrompt;           // 新增：默认等于原始值

        // 新增：判断pType类型，优先级：图片 > 文件 > 变量 > 固定
        if (!instance.mCmdParam.imageFilePath.empty()) {
            pType = "image";
        } else if (!instance.mCmdParam.promptFilePath.empty()) {
            pType = "file";
        } else if (instance.mCmdParam.useVariablePrompt) {
            pType = "variable";
        } else {
            pType = "fix";
        }
    }

    std::vector<double> getTokensPerSecond(int n_tokens, std::vector<int64_t> cost_us) const {
        std::vector<double> ts;
        std::transform(cost_us.begin(), cost_us.end(), std::back_inserter(ts), [n_tokens](int64_t t) { return 1e6 * n_tokens / t; });
        return ts;
    }

    double getAvgUs(std::vector<double> v) const { return ::avg(v); }
    double getStdevUs(std::vector<double> v) const { return ::stdev(v); }
    enum fieldType { STRING, BOOL, INT, FLOAT };

    static fieldType getFieldType(const std::string & field) {
        if (field == "threads") {
            return INT;
        }
        if (field == "useMmap") {
            return BOOL;
        }
        if (field == "t/s" || field == "modelSize" || field == "prefill&decode speed (tok/s)") {
            return FLOAT;
        }
        return STRING;
    }
};

static std::string pairString(const std::pair<int, int> & p) {
    static char buf[32];
    snprintf(buf, sizeof(buf), "%d,%d", p.first, p.second);
    return buf;
}

template <typename T, typename F> static std::vector<std::string> transform2String(const std::vector<T> & values, F f) {
    std::vector<std::string> str_values;
    std::transform(values.begin(), values.end(), std::back_inserter(str_values), f);
    return str_values;
}

template<class T>
static std::vector<T> splitString(const std::string & str, char delim) {
    std::vector<T> values;
    std::istringstream str_stream(str);
    std::string token;
    while (std::getline(str_stream, token, delim)) {
        T value;
        std::istringstream tokenStream(token);
        tokenStream >> value;
        values.push_back(value);
    }
    return values;
}

struct Printer {
    virtual ~Printer() {}

    FILE * fout;

    virtual void printHeader(const RuntimeParameters & rp, const TestParameters & tp) { (void) rp; (void) tp; }

    virtual void printPerformance(const TestInstance & t) = 0;

//    virtual void print_footer() {}
};

struct markdownPrinter : public Printer {
    std::vector<std::string> fields;

    static int getFieldWidth(const std::string & field) {
        if (field == "model") {
            return -30;
        }
        if (field == "prefill&decode speed (tok/s)") {
            return 20;
        }
        if (field == "threads") {
            return 5;
        }
        if (field == "useMmap") {
            return 4;
        }
        if (field == "test") {
            return -13;
        }
        if (field == "loadingTime(s)") {
            return 13;
        }

        int width = std::max((int) field.length(), 10);

        if (TestInstance::getFieldType(field) == TestInstance::STRING) {
            return -width;
        }
        return width;
    }

    static std::string getFieldDisplayName(const std::string & field) {
        if (field == "useMmap") {
            return "mmap";
        }
        return field;
    }

    void printHeader(const RuntimeParameters & rp, const TestParameters & tp) override {
        // select fields to print
        fields.emplace_back("model");
        fields.emplace_back("modelSize");
        fields.emplace_back("backend");
        fields.emplace_back("threads");

        if (rp.precision.size() > 0) {
            fields.emplace_back("precision");
        }
        if (rp.memory.size() > 1) {
            fields.emplace_back("memory");
        }
        if (rp.dynamicOption.size() > 1) {
            fields.emplace_back("dynamicOption");
        }

        if (rp.useMmap) {
            fields.emplace_back("useMmap");
        }

        // 显示提示词类型
        fields.emplace_back("pType");

        if (tp.kvCache == "false") {
            fields.emplace_back("test");
            fields.emplace_back("t/s");
        } else {
            fields.emplace_back("llm_demo");
            fields.emplace_back("speed(tok/s)");
        }
        if (tp.loadTime == "true") {
            fields.emplace_back("loadingTime(s)");
        }

        fprintf(fout, "|");
        for (const auto & field : fields) {
            fprintf(fout, " %*s |", getFieldWidth(field), getFieldDisplayName(field).c_str());
        }
        fprintf(fout, "\n");
        fprintf(fout, "|");
        for (const auto & field : fields) {
            int width = getFieldWidth(field);
            fprintf(fout, " %s%s |", std::string(std::abs(width) - 1, '-').c_str(), width > 0 ? ":" : "-");
        }
        fprintf(fout, "\n");
    }

    void printPerformance(const TestInstance & t) override {
        fprintf(fout, "|");
        for (const auto & field : fields) {
            std::string value;
            char        buf[128];
            if (field == "model") {
                value = t.modelType;
            } else if (field == "modelSize") {
                if (t.modelSize < 1024 * 1024 * 1024) {
                    snprintf(buf, sizeof(buf), "%.2f MiB", t.modelSize / 1024.0 / 1024.0);
                } else {
                    snprintf(buf, sizeof(buf), "%.2f GiB", t.modelSize / 1024.0 / 1024.0 / 1024.0);
                }
                value = buf;
            }  else if (field == "backend") {
                if (t.backend == 1) value = "METAL";
                else if (t.backend == 3) value = "OPENCL";
                else value = "CPU";
            } else if (field == "test") {
                // 按照原始设计意图，但考虑文件覆盖
                // 使用实际存储的值
                if (t.originalNPrompt > 0 && t.nGenerate == 0) {
                    snprintf(buf, sizeof(buf), "pp%d", t.actualNPrompt);
                } else if (t.originalNPrompt == 0 && t.nGenerate > 0) {
                    // 纯generate测试：不显示prompt
                    snprintf(buf, sizeof(buf), "tg%d", t.nGenerate);
                } else if (t.originalNPrompt > 0 && t.nGenerate > 0) {
                    // 组合测试
                    snprintf(buf, sizeof(buf), "pp%d+tg%d", t.actualNPrompt, t.nGenerate);
                } else {
                    snprintf(buf, sizeof(buf), "unknown");
                }
                value = buf;
            } else if (field == "llm_demo") {
                snprintf(buf, sizeof(buf), "prompt=%d<br>decode=%d", t.actualNPrompt, t.nGenerate);
                value = buf;
            } else if (field == "t/s") {
                auto spd = t.getTokensPerSecond(t.actualNPrompt + t.nGenerate, t.samplesUs);
                snprintf(buf, sizeof(buf), "%.2f ± %.2f", t.getAvgUs(spd), t.getStdevUs(spd));
                value = buf;
            } else if (field == "speed(tok/s)") {
                auto decode_speed = t.getTokensPerSecond(t.nGenerate, t.decodeUs);
                auto prefill_speed = t.getTokensPerSecond(t.nPrompt, t.prefillUs);
                snprintf(buf, sizeof(buf), "%.2f ± %.2f<br>%.2f ± %.2f", t.getAvgUs(prefill_speed), t.getStdevUs(prefill_speed), t.getAvgUs(decode_speed), t.getStdevUs(decode_speed));
                value = buf;
            } else if (field == "precision") {
                if (t.precision == 2) value = "Low";
                else if (t.precision == 0) value = "Normal";
                else value = "High";
            } else if (field == "memory") {
                if (t.memory == 2) value = "Low";
                else if (t.memory == 0) value = "Normal";
                else value = "High";
            } else if (field == "power") {
                if (t.power == 2) value = "Low";
                else if (t.power == 0) value = "Normal";
                else value = "High";
            } else if (field == "threads") {
                snprintf(buf, sizeof(buf), "%d", t.threads);
                value = buf;
            } else if (field == "loadingTime(s)") {
                snprintf(buf, sizeof(buf), "%.2f ± %.2f", t.getAvgUs(t.loadingS), t.getStdevUs(t.loadingS));
                value = buf;
            } else if (field == "useMmap") {
                if (t.useMmap) value = "true";
                else value = "false";
            } else if (field == "pType") {  // 新增
                value = t.pType;
            }
            else {
                assert(false);
                MNN_ERROR("llm bench print fields error\n");
                return;
            }

            int width = getFieldWidth(field);
            if (field == "prefill&decode speed (tok/s)" || field == "t/s") {
                // HACK: the utf-8 character is 2 bytes
                width += 1;
            }
            fprintf(fout, " %*s |", width, value.c_str());
        }
        fprintf(fout, "\n");
    }
};

static FILE* openFile(const char* file, bool read) {
#if defined(_MSC_VER)
    wchar_t wFilename[1024];
    if (0 == MultiByteToWideChar(CP_ACP, 0, file, -1, wFilename, sizeof(wFilename))) {
        return nullptr;
    }
#if _MSC_VER >= 1400
    FILE* mFile = nullptr;
    if (read) {
        if (0 != _wfopen_s(&mFile, wFilename, L"r")) {
            return nullptr;
        }
    } else {
        if (0 != _wfopen_s(&mFile, wFilename, L"a")) {
            return nullptr;
        }
    }
    return mFile;
#else
    if (read) {
        return _wfopen(wFilename, L"r");
    } else {
        return _wfopen(wFilename, L"a");
    }
#endif
#else
    if (read) {
        return fopen(file, "r");
    } else {
        return fopen(file, "a");
    }
#endif
    return nullptr;
}


// 新增：从图片文件加载并转换为PromptImagePart
static PromptImagePart loadImageFromFile(const std::string& filePath) {
    PromptImagePart imagePart;
    imagePart.width = 0;
    imagePart.height = 0;

    // 检查文件是否存在
    std::ifstream file(filePath);
    if (!file.is_open()) {
        MNN_ERROR("Error: Cannot open image file: %s\n", filePath.c_str());
        return imagePart;
    }
    file.close();

    // 使用MNN CV模块加载图片，与Python cv.imread保持一致
    auto imageData = MNN::CV::imread(filePath, MNN::CV::IMREAD_COLOR);

    if (imageData.get() == nullptr || imageData->getInfo() == nullptr) {
        MNN_ERROR("Error: Failed to load image file: %s\n", filePath.c_str());
        MNN_ERROR("       Please check image format and file integrity.\n");
        return imagePart;
    }

    // 获取图片尺寸信息
    auto dims = imageData->getInfo()->dim;

    // 打印调试信息
    MNN_PRINT("DEBUG: Image tensor dimensions count: %zd\n", dims.size());
    for (size_t i = 0; i < dims.size() && i < 10; i++) {
        MNN_PRINT("DEBUG: Dimension %zd: %d\n", i, dims[i]);
    }

    if (dims.size() < 3) {
        MNN_ERROR("Error: Invalid image tensor dimensions: %zd\n", dims.size());
        return imagePart;
    }

    // 尝试不同的维度格式来获取尺寸
    if (dims.size() == 3) {
        // 可能是 [height, width, channels]
        imagePart.height = dims[0];
        imagePart.width = dims[1];
    } else if (dims.size() == 4) {
        // 可能是 [batch, height, width, channels]
        imagePart.height = dims[1];
        imagePart.width = dims[2];
    } else {
        MNN_ERROR("Error: Unsupported image tensor dimensions: %zd\n", dims.size());
        return imagePart;
    }
    imagePart.image_data = imageData;

    MNN_PRINT("Successfully loaded image: %s (%dx%d)\n", filePath.c_str(), imagePart.width, imagePart.height);

    return imagePart;
}

// 新增：从文本文件读取并使用MNN正式tokenizer进行token化
static std::vector<int> loadTokensFromFile(const std::string& filePath, const std::string& modelConfig, Llm* llm) {
    std::ifstream file(filePath.c_str());
    if (!file.is_open()) {
        MNN_ERROR("Cannot open prompt file: %s\n", filePath.c_str());
        return {};
    }

    // 读取文件内容
    std::string content((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    file.close();

    if (content.empty()) {
        MNN_ERROR("Empty prompt file: %s\n", filePath.c_str());
        return {};
    }

    // 使用MNN正式的tokenizer进行token化
    auto tokens = llm->tokenizer_encode(content);

    if (tokens.empty()) {
        MNN_ERROR("Failed to tokenize content from file: %s\n", filePath.c_str());
        return {};
    }

    // 简化调试信息输出
    // printf("DEBUG: Tokenized %zd characters to %d tokens using MNN tokenizer\n",
    //        content.length(), (int)tokens.size());

    return tokens;
}

// 新增：构建多模态提示词
static MultimodalPrompt buildMultimodalPrompt(const std::string& textPrompt, const std::string& imageFile) {
    MultimodalPrompt multimodal;
    multimodal.prompt_template = textPrompt;

    if (!imageFile.empty()) {
        // 加载图片
        PromptImagePart imagePart = loadImageFromFile(imageFile);
        if (imagePart.image_data.get() != nullptr && imagePart.width > 0 && imagePart.height > 0) {
            multimodal.images["image_0"] = imagePart;
            // 直接使用文件中的提示词，不强制修改格式
        }
    }

    return multimodal;
}

// 显示测试配置信息（命令行参数等）
static void displayTestConfiguration(const TestInstance& t, const std::string& kvCache, const std::string& promptFilePath, const std::string& imageFilePath) {
    printf("\n=== Test Configuration ===\n");
    printf("Model: %s\n", t.model.c_str());
    printf("Backend: %d\n", t.backend);
    printf("Threads: %d\n", t.threads);
    printf("Power: %d\n", t.power);
    printf("Memory: %d\n", t.memory);
    printf("Precision: %d\n", t.precision);
    printf("Test Mode: %s\n", (!imageFilePath.empty()) ? "Image Prompt" :
                            (!promptFilePath.empty()) ? "File Prompt" :
                            (t.useVariablePrompt ? "Variable Prompt" : "Fixed Prompt"));
    printf("Prompt File: %s\n", promptFilePath.empty() ? "None" : promptFilePath.c_str());
    printf("Image File: %s\n", imageFilePath.empty() ? "None" : imageFilePath.c_str());
    printf("Verbose Mode: %s\n", t.verbose ? "Enabled" : "Disabled");
    printf("KV Cache: %s\n", kvCache.c_str());
    printf("==========================\n");
}

// 基础函数：显示token向量数组（统一显示前10个）
static void displayTokenVector(const std::vector<int>& tokens, const std::string& label) {
    if (tokens.empty()) {
        printf("%s: [] (empty vector)\n", label.c_str());
        return;
    }

    printf("%s Vector [size=%zd]: [", label.c_str(), tokens.size());
    for (size_t i = 0; i < std::min((size_t)10, tokens.size()); ++i) {
        if (i > 0) printf(", ");
        printf("%d", tokens[i]);
    }
    if (tokens.size() > 10) {
        printf(" ... %zd more", tokens.size() - 10);
    }
    printf("]\n");
}


// 显示生成的token以及解码后的实际文字内容
static void displayDecodeTokens(const std::vector<int>& decodeTokens, Llm* llm, int maxDisplay = 50) {
    if (decodeTokens.empty() || !llm) {
        return;
    }

    printf("--- Generated Content ---\n");
    displayTokenVector(decodeTokens, "Decode Tokens");

    // 解码并显示实际文字
    printf("Decoded Text: ");
    int displayCount = 0;
    for (size_t i = 0; i < decodeTokens.size() && displayCount < maxDisplay; ++i) {
        {
            std::string decodedText = llm->tokenizer_decode(decodeTokens[i]);
            // 直接输出原始解码文本，支持UTF-8（包括中文）
            printf("%s", decodedText.c_str());
            displayCount++;
        }
    }

    printf("\n");
    if (decodeTokens.size() > maxDisplay) {
        printf("... (showing first %d tokens, total %d)\n", maxDisplay, (int)decodeTokens.size());
    }
}

// 显示prefill阶段的token向量信息
static void displayPrefillTokenVector(const std::vector<int>& tokens) {
    printf("--- Prompt Content ---\n");
    displayTokenVector(tokens, "Prefill Tokens");
    printf("Prompt Length: %d tokens\n", (int)tokens.size());
}

// 根据目标长度调整token数组（截断或重复填充）
static std::vector<int> adjustTokensToLength(const std::vector<int>& sourceTokens, int targetLength) {
    std::vector<int> adjustedTokens;

    if (sourceTokens.empty() || targetLength <= 0) {
        return adjustedTokens; // 返回空数组
    }

    // 如果源token数量等于目标长度，直接返回
    if (sourceTokens.size() == (size_t)targetLength) {
        return sourceTokens;
    }

    // 如果源token数量大于目标长度，截断
    if (sourceTokens.size() > (size_t)targetLength) {
        adjustedTokens.assign(sourceTokens.begin(), sourceTokens.begin() + targetLength);
    }
    // 如果源token数量小于目标长度，重复填充
    else {
        int fullCycles = targetLength / sourceTokens.size();
        int remainder = targetLength % sourceTokens.size();

        // 重复完整的循环
        for (int i = 0; i < fullCycles; ++i) {
            adjustedTokens.insert(adjustedTokens.end(), sourceTokens.begin(), sourceTokens.end());
        }

        // 添加剩余部分
        if (remainder > 0) {
            adjustedTokens.insert(adjustedTokens.end(), sourceTokens.begin(), sourceTokens.begin() + remainder);
        }
    }
    return adjustedTokens;
}

// 统一的token准备函数
static std::vector<int> prepareTokens(const TestInstance& t, const std::vector<int>& fileTokens,
                                     int nPrompt, bool verbose, const std::string& testType) {
    std::vector<int> tokens;

    if (!t.promptFilePath.empty() && nPrompt > 0) {
        // 根据参数长度调整文件tokens
        tokens = adjustTokensToLength(fileTokens, nPrompt);
        if (verbose) {
            printf("DEBUG: Using file tokens for %s\n", testType.c_str());
        }
    } else if (nPrompt > 0) {
        // 使用生成的tokens，基于指定的prompt长度
        if (t.useVariablePrompt) {
            for (int i = 0; i < nPrompt; ++i) {
                tokens.push_back(20 + (i % 20)); // 20-39范围的循环
            }
        } else {
            tokens = std::vector<int>(nPrompt, 16);
        }
    }

    return tokens;
}

static std::vector<commandParametersInstance> get_cmd_params_instances(const RuntimeParameters & rp, const TestParameters& tp) {
    std::vector<commandParametersInstance> instances;

    // this ordering minimizes the number of times that each model needs to be reloaded
    // clang-format off
    for (const auto & m : rp.model)
    for (const auto & backend : rp.backends)
    for (const auto & precision : rp.precision)
    for (const auto & memory : rp.memory)
    for (const auto & power : rp.power)
    for (const auto & nt : rp.threads)
    for (const auto & dyop : rp.dynamicOption)
        if (tp.kvCache == "true") { // MNN llm_demo test standard
            for (const auto & nPrompt : tp.nPrompt) {
                if (nPrompt == 0) {
                    continue;
                }
                for (const auto & nGenerate: tp.nGenerate) {
                    if (nGenerate == 0) {
                        continue;
                    }
                    CommandParameters tmpParam;
                    tmpParam.model = m;
                    tmpParam.backend = backend;
                    tmpParam.threads = nt;
                    tmpParam.power = power;
                    tmpParam.precision = precision;
                    tmpParam.memory = memory;
                    tmpParam.nPrompt = nPrompt;
                    tmpParam.nGenerate = nGenerate;
                    tmpParam.useMmap = rp.useMmap;
                    tmpParam.dynamicOption = dyop;
                    tmpParam.nRepeat = tp.nRepeat[0];
                    tmpParam.kvCache = "true";
                    tmpParam.loadingTime = tp.loadTime;
                    tmpParam.useVariablePrompt = tp.useVariablePrompt;  // 新增
                    tmpParam.verbose = tp.verbose;                    // 新增
                    tmpParam.promptFilePath = tp.promptFilePath;       // 新增 - 遗漏的关键参数
                    tmpParam.imageFilePath = tp.imageFilePath;        // 新增 - 遗漏的关键参数
                    auto instance = commandParametersInstance(tmpParam);
                    instances.push_back(instance);
                }
            }
        } else { // llama.cpp llama-bench's test standard
            for (const auto & nPrompt : tp.nPrompt) {
                if (nPrompt == 0) {
                    continue;
                }
                CommandParameters tmpParam;
                tmpParam.model = m;
                tmpParam.nPrompt = nPrompt;
                tmpParam.nGenerate = 0;
                tmpParam.threads = nt;
                tmpParam.useMmap = rp.useMmap;
                tmpParam.backend = backend;
                tmpParam.power = power;
                tmpParam.precision = precision;
                tmpParam.memory = memory;
                tmpParam.dynamicOption = dyop;
                tmpParam.nRepeat = tp.nRepeat[0];
                tmpParam.kvCache = "false";
                tmpParam.loadingTime = tp.loadTime;
                tmpParam.useVariablePrompt = tp.useVariablePrompt;  // 新增
                tmpParam.verbose = tp.verbose;                    // 新增
                tmpParam.promptFilePath = tp.promptFilePath;       // 新增 - 遗漏的关键参数
                tmpParam.imageFilePath = tp.imageFilePath;        // 新增 - 遗漏的关键参数
                auto instance = commandParametersInstance(tmpParam);
                instances.push_back(instance);
            }
            for (const auto & nGenerate: tp.nGenerate) {
                CommandParameters tmpParam;
                tmpParam.model = m;
                tmpParam.nPrompt = 0;
                tmpParam.nGenerate = nGenerate;
                tmpParam.threads = nt;
                tmpParam.useMmap = rp.useMmap;
                tmpParam.backend = backend;
                tmpParam.power = power;
                tmpParam.precision = precision;
                tmpParam.memory = memory;
                tmpParam.dynamicOption = dyop;
                tmpParam.nRepeat = tp.nRepeat[0];
                tmpParam.kvCache = "false";
                tmpParam.loadingTime = tp.loadTime;
                tmpParam.useVariablePrompt = tp.useVariablePrompt;  // 新增
                tmpParam.verbose = tp.verbose;                    // 新增
                tmpParam.promptFilePath = tp.promptFilePath;       // 新增 - 遗漏的关键参数
                tmpParam.imageFilePath = tp.imageFilePath;        // 新增 - 遗漏的关键参数
                auto instance = commandParametersInstance(tmpParam);
                instances.push_back(instance);
            }
            for (const auto & nPrompGen : tp.nPrompGen) {
                if (nPrompGen.first == 0 && nPrompGen.second == 0) {
                    continue;
                }
                CommandParameters tmpParam;
                tmpParam.model = m;
                tmpParam.nPrompt = nPrompGen.first;
                tmpParam.nGenerate = nPrompGen.second;
                tmpParam.threads = nt;
                tmpParam.useMmap = rp.useMmap;
                tmpParam.backend = backend;
                tmpParam.power = power;
                tmpParam.precision = precision;
                tmpParam.memory = memory;
                tmpParam.dynamicOption = dyop;
                tmpParam.nRepeat = tp.nRepeat[0];
                tmpParam.kvCache = "false";
                tmpParam.loadingTime = tp.loadTime;
                tmpParam.useVariablePrompt = tp.useVariablePrompt;  // 新增
                tmpParam.verbose = tp.verbose;                    // 新增
                tmpParam.promptFilePath = tp.promptFilePath;       // 新增 - 遗漏的关键参数
                tmpParam.imageFilePath = tp.imageFilePath;        // 新增 - 遗漏的关键参数
                auto instance = commandParametersInstance(tmpParam);
                instances.push_back(instance);
            }
        }

    return instances;
}

std::string getDirectoryOf(const std::string& file_path, std::string& modelname) {
    // weight filename
    std::string weight_name = "llm.mnn.weight";
    std::ifstream file(file_path.c_str());
    std::string json_str((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());

    rapidjson::Document doc;
    doc.Parse(json_str.c_str());

    if (doc.HasMember("llm_weight") && doc["llm_weight"].IsString()) {
        weight_name = doc["llm_weight"].GetString();
    }

    size_t pos = file_path.find_last_of("/\\");
    if (pos == std::string::npos) {
        MNN_ERROR("Invalid model config path\n");
        return "";
    }
    auto dir = file_path.substr(0, pos);
    pos = dir.find_last_of("/\\");
    modelname = dir.substr(pos + 1, -1);
    return MNNFilePathConcat(dir, weight_name);
}

static void printUsage(int /* argc */, char ** argv) {
    printf("usage: %s [options]\n", argv[0]);
    printf("\n");
    printf("options:\n");
    printf("  -h, --help\n");
    printf("  -m, --model <filename>                    (default: ./Qwen2.5-1.5B-Instruct/config.json)\n");
    printf("  -a, --backends <cpu,opencl,metal>         (default: %s)\n", "cpu");
    printf("  -c, --precision <n>                       (default: %s) | Note: (0:Normal(for cpu bakend, 'Nornal' is 'High'),1:High,2:Low)\n", join(runtimeParamsDefaults.precision, ",").c_str());
    printf("  -t, --threads <n>                         (default: %s)\n", join(runtimeParamsDefaults.threads, ",").c_str());
    printf("  -p, --n-prompt <n>                        (default: %s)\n", join(testParamsDefaults.nPrompt, ",").c_str());
    printf("  -n, --n-gen <n>                           (default: %s)\n", join(testParamsDefaults.nGenerate, ",").c_str());
    printf("  -pg <pp,tg>                               (default: %s)\n", join(transform2String(testParamsDefaults.nPrompGen, pairString), ",").c_str());
    printf("  -mmp, --mmap <0|1>                        (default: %s)\n", "0");
    printf("  -rep, --n-repeat <n>                      (default: %s)\n", join(testParamsDefaults.nRepeat, ",").c_str());
    printf("  -kv, --kv-cache <true|false>              (default: %s) | Note: if true: Every time the LLM model generates a new word, it utilizes the cached KV-cache\n", "false");
    printf("  -fp, --file-print <stdout|filename>       (default: %s)\n", "stdout");
    printf("  -load, --loading-time <true|false>        (default: %s)\n", "true");
    printf("  -dyo, --dynamicOption <n>                 (default: 0) | Note: if set 8, trades higher memory usage for better decoding performance\n");
    printf("  -vp, --variable-prompt <0|1>              (default: 0) | Note: if 1, use variable prompt tokens instead of fixed token 16\n");
    printf("  -v, --verbose <0|1>                       (default: 0) | Note: if 1, display detailed test information including token vectors\n");
    printf("  -pf, --prompt-file <filename>             (default: none) | Note: if provided, use file content as prompt and override -p and -pg settings\n");
    printf("  -ipf, --image-file <filename>            (default: none) | Note: if provided, use image as multimodal prompt with <img>image_0</img> marker\n");
}

static bool parseCmdParams(int argc, char ** argv, RuntimeParameters & runtimeParams, TestParameters & testParams, FILE** outfile, bool& helpInfo) {
    std::string       arg;
    bool              invalidParam = false;
    const std::string argPrefix    = "--";
    const char        splitDelim   = ',';

    runtimeParams.useMmap = runtimeParamsDefaults.useMmap;
    testParams.kvCache = testParamsDefaults.kvCache;
    testParams.loadTime = testParamsDefaults.loadTime;
    testParams.useVariablePrompt = testParamsDefaults.useVariablePrompt;  // 新增
    testParams.verbose = testParamsDefaults.verbose;                   // 新增

    for (int i = 1; i < argc; i++) {
        arg = argv[i];
        if (arg.compare(0, argPrefix.size(), argPrefix) == 0) {
            std::replace(arg.begin(), arg.end(), '_', '-');
        }

        if (arg == "-h" || arg == "--help") {
            printUsage(argc, argv);
            helpInfo = true;
            return true;
        } else if (arg == "-m" || arg == "--model") {
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto p = splitString<std::string>(argv[i], splitDelim);
            runtimeParams.model.insert(runtimeParams.model.end(), p.begin(), p.end());
        } else if (arg == "-p" || arg == "--n-prompt") {
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto p = splitString<int>(argv[i], splitDelim);
            testParams.nPrompt.insert(testParams.nPrompt.end(), p.begin(), p.end());
        } else if (arg == "-n" || arg == "--n-gen") {
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto p = splitString<int>(argv[i], splitDelim);
            testParams.nGenerate.insert(testParams.nGenerate.end(), p.begin(), p.end());
        } else if (arg == "-pg") {
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto p = splitString<std::string>(argv[i], ',');
            if (p.size() != 2) {
                invalidParam = true;
                break;
            }
            testParams.nPrompGen.push_back({ std::stoi(p[0]), std::stoi(p[1]) });
        } else if (arg == "-a" || arg == "--backends") {
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto ba = splitString<std::string>(argv[i], splitDelim);
            std::vector<int> p;
            for (auto& type: ba) {
                if (type == "metal") {
                    p.emplace_back(1);
                } else if (type == "opencl") {
                    p.emplace_back(3);
                } else {
                    p.emplace_back(0);
                }
            }
            runtimeParams.backends.insert(runtimeParams.backends.end(), p.begin(), p.end());
        } else if (arg == "-t" || arg == "--threads") {
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto p = splitString<int>(argv[i], splitDelim);
            std::sort(p.begin(), p.end(), std::greater<int>());
            runtimeParams.threads.insert(runtimeParams.threads.end(), p.begin(), p.end());
        } else if (arg == "-mmp" || arg == "--mmap") {
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto p = splitString<bool>(argv[i], splitDelim);
            runtimeParams.useMmap = p[0];
        } else if (arg == "-c" || arg == "--precision") {
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto p = splitString<int>(argv[i], splitDelim);
            runtimeParams.precision.insert(runtimeParams.precision.end(), p.begin(), p.end());
        } else if (arg == "--memory") {
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto p = splitString<int>(argv[i], splitDelim);
            runtimeParams.memory.insert(runtimeParams.memory.end(), p.begin(), p.end());
        } else if (arg == "--power") {
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto p = splitString<int>(argv[i], splitDelim);
            runtimeParams.power.insert(runtimeParams.power.end(), p.begin(), p.end());
        } else if (arg == "-dyo" || arg == "--dynamicOption") {
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto p = splitString<int>(argv[i], splitDelim);
            runtimeParams.dynamicOption.insert(runtimeParams.dynamicOption.end(), p.begin(), p.end());
        } else if (arg == "-rep" || arg == "--n-repeat") {
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto p = splitString<int>(argv[i], splitDelim);
            testParams.nRepeat.insert(testParams.nRepeat.end(), p.begin(), p.end());
        } else if (arg == "-vp" || arg == "--variable-prompt") {  // 新增
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto p = splitString<bool>(argv[i], splitDelim);
            testParams.useVariablePrompt = p[0];
        } else if (arg == "-v" || arg == "--verbose") {  // 新增
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto p = splitString<bool>(argv[i], splitDelim);
            testParams.verbose = p[0];
        } else if (arg == "-pf" || arg == "--prompt-file") {  // 新增
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            testParams.promptFilePath = argv[i];
        } else if (arg == "-ipf" || arg == "--image-file") {  // 新增
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            testParams.imageFilePath = argv[i];
        } else if (arg == "-kv" || arg == "--kv-cache") {
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto p = splitString<std::string>(argv[i], splitDelim);
            testParams.kvCache = p[0];
        } else if (arg == "-fp" || arg == "--file-print") {
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto p = splitString<std::string>(argv[i], splitDelim);
            if (!MNNFileExist(p[0].c_str())) {
                MNNCreateFile(p[0].c_str());
            }
            *outfile = openFile(p[0].c_str(), false);
        } else if (arg == "-load" || arg == "--loading-time") {
            if (++i >= argc) {
                invalidParam = true;
                break;
            }
            auto p = splitString<std::string>(argv[i], splitDelim);
            testParams.loadTime = p[0];
        }
        else {
            invalidParam = true;
            break;
        }
    } // parse end


    if (invalidParam) {
        fprintf(stderr, "error: invalid parameter for argument: %s\n", arg.c_str());
        printUsage(argc, argv);
        return false;
    }

    // set defaults
    if (runtimeParams.model.empty()) {
        runtimeParams.model = runtimeParamsDefaults.model;
    }
    if (testParams.nPrompt.empty()) {
        testParams.nPrompt = testParamsDefaults.nPrompt;
    }
    if (testParams.nGenerate.empty()) {
        testParams.nGenerate = testParamsDefaults.nGenerate;
    }
    if (testParams.nPrompGen.empty()) {
        testParams.nPrompGen = testParamsDefaults.nPrompGen;
    }
    if (runtimeParams.backends.empty()) {
        runtimeParams.backends = runtimeParamsDefaults.backends;
    }
    if (runtimeParams.memory.empty()) {
        runtimeParams.memory = runtimeParamsDefaults.memory;
    }
    if (runtimeParams.precision.empty()) {
        runtimeParams.precision = runtimeParamsDefaults.precision;
    }
    if (runtimeParams.power.empty()) {
        runtimeParams.power = runtimeParamsDefaults.power;
    }
    if (runtimeParams.threads.empty()) {
        runtimeParams.threads = runtimeParamsDefaults.threads;
    }
    if (runtimeParams.dynamicOption.empty()) {
        runtimeParams.dynamicOption = runtimeParamsDefaults.dynamicOption;
    }
    if (testParams.nRepeat.empty()) {
        testParams.nRepeat = testParamsDefaults.nRepeat;
    }

    return true;
}

static Llm* buildLLM(const std::string& config_path, int backend, int memory, int precision, int threads, int power, int dynamic_option, bool use_mmap) {
    auto llmPtr = Llm::createLLM(config_path);
    llmPtr->set_config(R"({
        "async":false
    })");
    std::map<int, std::string> lever = {{0,"normal"}, {1, "high"}, {2, "low"}};
    std::map<int, std::string> backend_type = {{0, "cpu"}, {1, "metal"}, {3, "opencl"}};
    std::map<bool, std::string> mmap = {{true,"true"}, {false,"false"}};

    bool setSuccess = true;
    setSuccess &= llmPtr->set_config("{\"precision\":\"" + lever[precision] + "\"}");
    if (!setSuccess) {
        MNN_ERROR("precison for LLM config set error\n");
        return nullptr;
    }
    setSuccess &= llmPtr->set_config("{\"memory\":\"" + lever[memory] + "\"}");
    if (!setSuccess) {
        MNN_ERROR("memory for LLM config set error\n");
        return nullptr;
    }
    setSuccess &= llmPtr->set_config("{\"power\":\"" + lever[power] + "\"}");
    if (!setSuccess) {
        MNN_ERROR("power for LLM config set error\n");
        return nullptr;
    }
    setSuccess &= llmPtr->set_config("{\"backend_type\":\"" + backend_type[backend] + "\"}");
    if (!setSuccess) {
        MNN_ERROR("backend_type for LLM config set error\n");
        return nullptr;
    }
    setSuccess &= llmPtr->set_config("{\"thread_num\":" + std::to_string(threads) + "}");
    if (!setSuccess) {
        MNN_ERROR("thread_num for LLM config set error\n");
        return nullptr;
    }
    setSuccess &= llmPtr->set_config("{\"dynamic_option\":" + std::to_string(dynamic_option) + "}");
    if (!setSuccess) {
        MNN_ERROR("dynamic_option for LLM config set error\n");
        return nullptr;
    }
    setSuccess &= llmPtr->set_config("{\"use_mmap\":" + mmap[use_mmap] + "}");
    if (!setSuccess) {
        MNN_ERROR("use_mmap for LLM config set error\n");
        return nullptr;
    }
    setSuccess &= llmPtr->set_config("{\"tmp_path\":\"tmp\"}");
    if (!setSuccess) {
        MNN_ERROR("tmp_path for LLM config set error\n");
        return nullptr;
    }
    setSuccess &= llmPtr->set_config("{\"prefer_decode\": false}"); // llm_bench use dynamic_option(-dyo) to control whether to use 'prefer_decode'
    if (!setSuccess) {
        MNN_ERROR("prefer_decode for LLM config set error\n");
        return nullptr;
    }

    
    return llmPtr;
}

static void tuning_prepare(Llm* llm, bool verbose = false) {
    if (verbose) {
        printf("Prepare for performance tuning...\n");
    }
    llm->tuning(OP_ENCODER_NUMBER, {1, 5, 10, 20, 30, 50, 100});
    if (verbose) {
        printf("Performance tuning completed.\n");
    }
}

int main(int argc, char ** argv) {
    RuntimeParameters runtimeParams;
    TestParameters testParams;
    FILE* outfile = stdout;
    bool helpInfo = false;
    bool parseSuccess = parseCmdParams(argc, argv, runtimeParams, testParams, &outfile, helpInfo);
    if (!parseSuccess) {
        MNN_ERROR("Parse arguments error\n");
        return -1;
    }
    if (parseSuccess && helpInfo) {
        return 0;
    }
    std::vector<commandParametersInstance> paramsInstances = get_cmd_params_instances(runtimeParams, testParams);
    std::unique_ptr<Printer> printer_(new markdownPrinter());
    bool printHeader = true;

    // 显示测试配置信息（只显示一次，因为所有测试实例使用相同配置）
    if (!paramsInstances.empty() && paramsInstances[0].mCmdParam.verbose) {
        TestInstance firstInstance(paramsInstances[0]);
        displayTestConfiguration(firstInstance, paramsInstances[0].mCmdParam.kvCache, paramsInstances[0].mCmdParam.promptFilePath, paramsInstances[0].mCmdParam.imageFilePath);
    }

    for (const auto & instance: paramsInstances) {
        TestInstance t(instance);

        auto llmWeightPath = getDirectoryOf(t.model, t.modelType); // To check path

        file_t file = MNNOpenFile(llmWeightPath.c_str(), MNN_FILE_READ);
        t.modelSize = MNNGetFileSize(file);

        MNN::BackendConfig backendConfig;
        auto executor = MNN::Express::Executor::newExecutor(MNN_FORWARD_CPU, backendConfig, 1);
        MNN::Express::ExecutorScope scope(executor);

        auto llmPtr = buildLLM(t.model, t.backend, t.memory, t.precision, t.threads, t.power, t.dynamicOption, t.useMmap);
        std::unique_ptr<Llm> llm(llmPtr);
        if (t.loadingTime == "true") {
            for (int k = 0; k < 3; ++k) {
                Timer loadingCost;
                llm->load();
                t.loadingS.push_back((double)loadingCost.durationInUs() / 1e6);
            }
        } else {
            llm->load();
        }
        tuning_prepare(llm.get(), t.verbose);
        auto context = llm->getContext();

        // 准备多模态提示词
        MultimodalPrompt multimodalPrompt;
        std::vector<int> fileTokens;

        if (!t.imageFilePath.empty()) {
            // 图片模式：先验证图片加载
            PromptImagePart testImagePart = loadImageFromFile(t.imageFilePath);

            // 如果图片加载失败（width或height为0），直接退出
            if (testImagePart.width == 0 || testImagePart.height == 0) {
                MNN_ERROR("Error: Image loading failed. Cannot proceed with image-based testing.\n");
                MNN_ERROR("       Please check image file format and availability.\n");
                return -1;
            }

            // 确定文本提示词逻辑：优先级：文件内容 > 默认文本
            std::string textPrompt = "介绍一下这张图";  // 默认文本内容

            if (!t.promptFilePath.empty()) {
                // 如果有提示词文件，使用文件内容作为文本部分
                MNN_PRINT("Info: Using file content as text part of multimodal prompt.\n");
                std::ifstream file(t.promptFilePath);
                std::string content((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
                file.close();
                if (!content.empty()) {
                    textPrompt = content;
                    MNN_PRINT("    Loaded %zd characters from file as text prompt.\n", content.length());
                }
            }

            // 构建多模态提示词
            multimodalPrompt = buildMultimodalPrompt(textPrompt, t.imageFilePath);

            // 验证多模态提示词是否成功构建
            if (multimodalPrompt.images.empty() || multimodalPrompt.images.find("image_0") == multimodalPrompt.images.end()) {
                MNN_ERROR("Error: Failed to construct multimodal prompt.\n");
                return -1;
            }
        } else if (!t.promptFilePath.empty()) {
            // 文件模式：加载文本文件的tokens
            fileTokens = loadTokensFromFile(t.promptFilePath, t.model, llm.get());
            if (fileTokens.empty()) {
                MNN_ERROR("Failed to load prompt tokens from file: %s\n", t.promptFilePath.c_str());
                return -1;
            }
            // 文件tokens作为原料，实际长度由参数控制，不在这里覆盖
        }

        if (t.nGenerate > 0) {
            llm->set_config("{\"max_new_tokens\":1}");
        }

        auto prompt_tokens = t.nPrompt;
        auto decodeTokens = t.nGenerate;

        // llm_demo test
        if (t.kvCache == "true") {
            // 如果开启verbose，显示测试模式信息
            if (t.verbose) {
                if (!t.imageFilePath.empty()) {
                    printf("\n=== Branch 1: llm_demo test with image ===\n");
                } else {
                    printf("\n=== Branch 1: llm_demo test ===\n");
                }
            }

            for (int i = 0; i < t.nRepeat + 1; ++i) {
                if (t.verbose) {
                    printf("\n****** Round %d : ******\n", i+1);
                    if (!t.imageFilePath.empty()) {
                        printf("Image File: %s\n", t.imageFilePath.c_str());
                        printf("Image Size: %dx%d\n", 420, 420); // 与loadImageFromFile中的尺寸一致
                        printf("Multimodal Prompt: %s\n", multimodalPrompt.prompt_template.c_str());
                        printf("Image References: %zu\n", multimodalPrompt.images.size());
                        for (const auto& imgPair : multimodalPrompt.images) {
                            printf("  - %s: %dx%d\n", imgPair.first.c_str(), imgPair.second.width, imgPair.second.height);
                        }
                    } else {
                        // 显示token信息和文件内容
                        std::vector<int> tokens = prepareTokens(t, fileTokens, prompt_tokens, false, "llm_demo test");
                        displayPrefillTokenVector(tokens);
                        if (!t.promptFilePath.empty()) {
                            // 显示原始文件内容
                            std::ifstream file(t.promptFilePath);
                            std::string content((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
                            printf("File Content: %s\n", content.c_str());
                        }
                    }
                }

                if (!t.imageFilePath.empty()) {
                    // 多模态调用
                    if (t.verbose) {
                        printf("--- Multimodal Prefill Tokens ---\n");
                        printf("Prompt Template: %s\n", multimodalPrompt.prompt_template.c_str());
                        printf("Image Keys: %zu\n", multimodalPrompt.images.size());
                        for (const auto& imgPair : multimodalPrompt.images) {
                            printf("  - %s: %dx%d\n", imgPair.first.c_str(), imgPair.second.width, imgPair.second.height);
                        }
                        printf("*********************************\n");
                    }
                    llm->response(multimodalPrompt, nullptr, nullptr, decodeTokens);
                } else {
                    // 传统token调用
                    std::vector<int> tokens = prepareTokens(t, fileTokens, prompt_tokens, t.verbose, "llm_demo test");
                    llm->response(tokens, nullptr, nullptr, decodeTokens);
                }

                auto prefillTime = context->prefill_us;
                auto decodeTime = context->decode_us;

                if (i > 0) { // Exclude the first performance value.
                    t.prefillUs.push_back(prefillTime);
                    t.decodeUs.push_back(decodeTime);
                }

                if (t.verbose) {
                    auto outputTokens = context->output_tokens;
                    if (!outputTokens.empty()) {
                        displayDecodeTokens(outputTokens, llm.get());
                    }
                    printf("Performance: Prefill=%.2f ms, Decode=%.2f ms\n",
                         prefillTime/1000.0, decodeTime/1000.0);
                    printf("************************\n");
                }

                // 轮间休眠
                if (i < t.nRepeat) {
                    std::this_thread::sleep_for(std::chrono::milliseconds(10));
                }
            }
            if (printHeader) {
                printer_->fout = outfile;
                printer_->printHeader(runtimeParams, testParams);
                printHeader = false;
            }
            printer_->printPerformance(t);
            // Cool
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
        }

        // llama.cpp llama-bench test
        if (t.kvCache == "false") {
            // llama.cpp模式不支持图片测试，因为它是token级别的性能测试
            if (!t.imageFilePath.empty()) {
                MNN_PRINT("Warning: Image file is not supported in llama.cpp benchmark mode (kv-cache=false).\n");
                MNN_PRINT("         Skipping image file and using token-based test instead.\n");
            }

            // 使用统一的token准备函数
            std::vector<int> tokens = prepareTokens(t, fileTokens, prompt_tokens, t.verbose, "llama.cpp prompt test");
            int testToken = tokens.empty() ? 16 : tokens[0];  // 用于显示的测试token
            std::vector<int> decodeVectors(1, testToken);

            // 如果开启verbose，显示token信息
            if (t.verbose) {
                if (prompt_tokens > 0 && decodeTokens > 0) {
                    printf("\n=== Branch 4: llama.cpp prompt+generate test ===\n");
                    displayTokenVector(tokens, "Actual Prompt Tokens");
                } else if (prompt_tokens > 0) {
                    printf("\n=== Branch 2: llama.cpp prompt test ===\n");
                    displayTokenVector(tokens, "Actual Prompt Tokens");
                } else if (decodeTokens > 0) {
                    printf("\n=== Branch 3: llama.cpp generate test ===\n");
                    displayTokenVector(std::vector<int>(), "Actual Prompt Tokens"); // Empty tokens for generate-only test
                }
            }

            for (int i = 0; i < t.nRepeat + 1; ++i) {
                int64_t sampler_us = 0;
                int64_t prefillTime = 0;
                int64_t decodeTime = 0;

                if (t.verbose) {
                    printf("\n****** Round %d : ******\n", i+1);
                    // 如果开启verbose，显示prefill阶段的token向量信息
                    if (prompt_tokens > 0) {
                        // 直接显示已准备好的tokens（与实际传入模型的一致）
                        displayPrefillTokenVector(tokens);
                    }
                }
                if (prompt_tokens > 0) {
                    llm->response(tokens, nullptr, nullptr, 1);
                    prefillTime = context->prefill_us;
                    sampler_us += prefillTime;
                }
                if (decodeTokens > 0) {
                    llm->response(decodeVectors, nullptr, nullptr, decodeTokens);
                    decodeTime = context->decode_us;
                    sampler_us += decodeTime;
                }

                if (i > 0) {
                    t.samplesUs.push_back(sampler_us);
                }

                if (t.verbose) {
                    if (decodeTokens > 0) {
                        std::vector<int> actualOutputTokens;
                        actualOutputTokens = context->output_tokens;
                        displayDecodeTokens(actualOutputTokens, llm.get());
                    }
                    if (prompt_tokens > 0 && decodeTokens > 0) {
                        printf("Performance: Prefill=%.2f ms, Decode=%.2f ms\n",
                               prefillTime/1000.0, decodeTime/1000.0);
                    } else if (prompt_tokens > 0) {
                        printf("Performance: Prefill=%.2f ms\n", prefillTime/1000.0);
                    } else if (decodeTokens > 0) {
                        printf("Performance: Decode=%.2f ms\n", decodeTime/1000.0);
                    }
                    printf("************************\n");
                }

                // 轮间休眠
                if (i < t.nRepeat) {
                    std::this_thread::sleep_for(std::chrono::milliseconds(10));
                }
            }

            if (printHeader) {
                printer_->fout = outfile;
                printer_->printHeader(runtimeParams, testParams);
                printHeader = false;
            }
            printer_->printPerformance(t);
            // Cool
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
        }
    }

    fprintf(printer_->fout, "\n");
    if (printer_->fout != stdout) {
        fclose(printer_->fout);
    }
    return 0;
}