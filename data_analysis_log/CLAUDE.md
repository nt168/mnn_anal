# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains benchmark performance data comparing two language models:
- **model_0.6B_Qwen**: Qwen model with 0.6 billion parameters
- **model_0.5B_Hunyuan**: Hunyuan model with 0.5 billion parameters

## Data Structure

The repository contains two main data files:

- `phy.txt`: Physical hardware benchmark results with detailed performance metrics including token counts, processing times, and speed measurements
- `sim.txt`: Simulated hardware benchmark results with similar performance metrics

Both files contain benchmark results for the same test queries:
1. "2+3=？" (mathematical calculation)
2. "春眠不觉晓"下一句？ (classical Chinese poetry)
3. "中国首都是哪？" (geographical knowledge)
4. "人民币符号？" (currency symbol)
5. "光速是多少？" (scientific knowledge)

## Performance Metrics

Each benchmark entry includes:
- **Total processing time**: Overall cost time in milliseconds
- **Token statistics**: prompt and decode token counts
- **Timing breakdown**: prefill, decode, sample, vision, and audio processing times
- **Speed metrics**: tokens per second for prefill and decode phases

## File Naming Convention

- `phy.txt`: Physical hardware measurements
- `sim.txt`: Simulated/hardware-accelerated measurements
- Format: Each entry starts with `*******` separator and includes model name and query

## Working with the Data

When analyzing or comparing performance:
- Compare corresponding entries between phy.txt and sim.txt to understand hardware vs simulation differences
- Focus on decode speed as the primary performance indicator for text generation
- Note token count differences between models for the same queries
- Consider prefill vs decode time ratios for understanding bottleneck characteristics

## Data Quality Considerations

**IMPORTANT**: Before any analysis, check for data quality issues:
- **Token truncation**: Hunyuan model shows exactly 512 tokens for "人民币符号" and "光速是多少" queries - likely output limit enforcement
- **Sample size**: Only 5 query types per model/environment combination (small sample)
- **Complete data**: Only 16/20 samples are complete (80% completeness)
- Use `select_data.sh` or similar filtering criteria to analyze only complete data

## Analysis Methods

For reliable conclusions:
1. **Descriptive analysis**: Basic comparison with awareness of limitations
2. **Statistical testing**: Use inferential statistics (ANOVA) due to small sample sizes
3. **Effect size evaluation**: Report effect sizes (η²) alongside p-values
4. **Conservative interpretation**: Acknowledge data limitations and provide ranges rather than point estimates

## Available Analysis Tools

- `anova_data.csv`: Structured data format for statistical analysis
- `corrected_anova.py`: Python script for two-way ANOVA analysis
- Requires virtual environment setup (found `.venv/`)
- Dependencies: numpy, scipy, pandas

## Key Findings (from Statistical Analysis)

- **Model effect**: Hunyuan 0.5B shows significantly faster decode speeds (p=0.002, η²=0.413)
- **Environment effect**: Simulated hardware outperforms physical (p=0.018, η²=0.201)
- **No significant interaction**: Models perform consistently across environments
- **Caveat**: 20% of data truncated, potentially underestimating Hunyuan performance

## Analysis Documentation

- `interaction_log.md`: Complete analysis process and decision history
- `reliable_conclusion.md`: Conservative interpretation considering data quality
- `anova_conclusion.md`: Statistical analysis with formal hypothesis testing

**Recommendation**: Always prioritize statistical significance testing over simple numeric comparisons with this dataset.