# Injected Intelligence: Prompt Attacks on LLMs

A cybersecurity research project evaluating how open-source large language models respond to harmful direct requests using the HarmBench red-teaming framework.

**Authors:** Austin McClarin and Abigail Amiscosa  
**Course:** CSEC 4483 - Advanced Penetration Testing, Texas A&M University-San Antonio  
**Completed:** May 2026

> This repository is a portfolio-focused version of the completed school project. Administrative milestone documents, student IDs, duplicate document formats, and the raw third-party HarmBench behavior dataset are intentionally excluded.

## Project Overview

Large language models introduce security and safety risks that are not fully addressed by traditional application-security controls. This project established a repeatable baseline for evaluating model behavior under harmful inputs and comparing refusal behavior across multiple open-source LLMs.

The experiment used:

- **HarmBench** as the evaluation framework
- **400 harmful behavior prompts** from the HarmBench behavior dataset
- **DirectRequest** as the baseline attack method
- Three open-source 7B instruction/chat models
- **Attack Success Rate (ASR)** as the primary comparison metric

A higher ASR indicates that a model responded to more harmful requests instead of refusing them.

## Models and Results

| Model | Attack Success Rate | Interpretation |
| --- | ---: | --- |
| Llama-2-7B-Chat | **2.2%** | Strongest refusal behavior in this experiment |
| Vicuna-7B-v1.5 | **50.2%** | Responded to roughly half of tested harmful prompts |
| Mistral-7B-Instruct-v0.2 | **65.8%** | Highest observed vulnerability in this experiment |

![Three-model ASR comparison](results/three_model_comparison.png)

These results are specific to the tested model versions, DirectRequest baseline, HarmBench behavior set, and evaluation method. They should not be interpreted as a complete security assessment of any model family.

## Evaluation Pipeline

The experiment followed a three-stage workflow:

```text
HarmBench Behaviors
        |
        v
1. Generate Test Cases
   generate_test_cases.py
        |
        v
2. Generate Model Completions
   generate_completions.py
        |
        v
3. Evaluate Completions
   evaluate_completions.py
        |
        v
Attack Success Rate (ASR)
```

### 1. Generate Test Cases

`src/generate_test_cases.py` loads the HarmBench behavior dataset, applies the selected red-teaming method/configuration, generates model-ready test cases, and saves the resulting test cases and logs.

### 2. Generate Model Completions

`src/generate_completions.py` loads the configured target model, sends each generated test case to the model, and stores the resulting generations in JSON format. The script supports Hugging Face generation and vLLM-based generation where applicable.

### 3. Evaluate Completions

`src/evaluate_completions.py` evaluates saved generations and calculates attack-success results. The project used the AdvBench-style refusal metric for its final baseline comparison.

## Experimental Environment

The completed project documented the following software and compute environment:

### Local system

- AMD Ryzen 9 5900X
- 32 GB DDR4
- AMD Radeon RX 9070 XT with 16 GB VRAM
- Docker
- ROCm 6.4

### School HPC environment

- TAMU HPRC Launch cluster
- Slurm workload manager
- NVIDIA A30 GPU resources

The final experiment was completed primarily on the local system after storage/quota constraints made the school HPC environment difficult to use for the workflow.

### Software stack

- Python 3.10
- PyTorch 2.5.1
- Transformers 4.40
- vLLM 0.4.3
- ROCm 6.4
- HarmBench

## Repository Structure

```text
.
├── README.md
├── .gitignore
├── THIRD_PARTY_NOTICES.md
├── src/
│   ├── generate_test_cases.py
│   ├── generate_completions.py
│   └── evaluate_completions.py
├── results/
│   ├── llama2_results.png
│   ├── vicuna_results.png
│   ├── mistral_results.png
│   └── three_model_comparison.png
└── docs/
    ├── final-report.pdf
    └── presentation.pdf
```

## Reproducing the Workflow

The scripts in `src/` were used within the HarmBench project environment and rely on HarmBench modules such as `baselines` and `eval_utils`. They are included to document the implementation used for the project rather than as a standalone replacement for HarmBench.

To reproduce the experiment:

1. Clone the upstream [HarmBench](https://github.com/centerforaisafety/HarmBench) repository and follow its environment setup instructions.
2. Obtain the HarmBench behavior dataset from the upstream project. The raw dataset is **not redistributed in this repository**.
3. Configure the target model in HarmBench's model configuration.
4. Use the scripts in `src/` for the test-case, completion-generation, and evaluation stages.
5. Compare the resulting ASR values across models under the same test configuration.

Exact commands depend on the HarmBench configuration and hardware environment being used.

## Results and Documentation

Individual model-result visualizations are available in [`results/`](results/).

The complete academic deliverables are retained as portfolio documentation:

- [`docs/final-report.pdf`](docs/final-report.pdf)
- [`docs/presentation.pdf`](docs/presentation.pdf)

## Limitations

This project was designed as a baseline evaluation rather than a comprehensive LLM security benchmark. Important limitations include:

- Only the **DirectRequest** attack method was used for the final comparison.
- All three evaluated models were approximately 7B parameters.
- The project relied on a refusal-oriented automated scoring method, which can misclassify nuanced responses.
- More advanced multi-turn, obfuscated, multimodal, and adaptive attacks were outside the completed experiment's scope.

## Future Work

Potential extensions identified during the project include:

- Prompt obfuscation and transformation attacks
- Multi-turn jailbreak techniques
- Multimodal/image-based prompt attacks
- Newer model families such as Llama, Gemma, and Qwen
- Larger-scale testing using HPC resources
- More advanced response classifiers and evaluation metrics

## Responsible Use

This project was performed for academic cybersecurity research and AI red-teaming education. The purpose is to understand model safety weaknesses, improve evaluation practices, and support stronger safeguards. Testing should only be performed on systems and models you are authorized to evaluate.

## Third-Party Attribution

The workflow and included scripts are based on the open-source **HarmBench** project from the Center for AI Safety. HarmBench is distributed under the MIT License. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for attribution and license information.
