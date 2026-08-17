# Project Report: Injected Intelligence - Prompt Attacks on LLMs

**Authors:** Austin McClarin and Abigail Amiscosa  
**Institution:** Texas A&M University-San Antonio  
**Course:** CSEC 4483 - Advanced Penetration Testing  
**Completed:** May 2026

## Introduction

Large language models are being adopted across many industries because they can automate tasks and generate human-like responses. These systems also introduce security and safety risks that are not fully addressed by traditional cybersecurity frameworks. One concern is prompt-based manipulation, where crafted user input can influence model behavior in unsafe or unintended ways.

This project evaluated how three open-source LLMs responded to harmful inputs. The goal was to measure differences in model behavior under the same baseline test conditions and demonstrate why AI systems require continuous security evaluation.

## Methodology

### Dataset

The experiment used the **HarmBench behavior dataset**, which provides a standardized collection of harmful behaviors for evaluating LLM safety. The project tested **400 prompts** spanning multiple harmful-content categories.

Using the same behavior set for each model allowed the experiment to compare model responses under consistent conditions.

### Attack Method

The selected baseline was **DirectRequest**. Harmful requests were sent directly to each model without additional jailbreak transformations, prompt obfuscation, or multi-turn attack techniques.

This method established a baseline for how readily each model would produce generations that HarmBench's evaluator classified as successful instances of the tested harmful behaviors.

### Models Tested

Three open-source 7B models were evaluated:

- **Llama-2-7B-Chat**
- **Vicuna-7B-v1.5**
- **Mistral-7B-Instruct-v0.2**

The models were selected to compare systems with similar parameter counts but different instruction-tuning and alignment approaches.

## Experimental Pipeline

The project used a three-stage workflow.

### 1. Generate Test Cases

`generate_test_cases.py` loaded HarmBench behavior entries and generated model-ready test cases using the DirectRequest baseline.

### 2. Generate Model Completions

`generate_completions.py` loaded the selected target model and generated responses for each test case. Responses were stored for later evaluation.

### 3. Evaluate Model Completions

`evaluate_completions.py` evaluated the generated responses using HarmBench's classifier-based scoring path. For non-hash-check behaviors, the script used the `cais/HarmBench-Llama-2-13b-cls` classifier and stored the result in each completion's `label` field.

The primary comparison metric was **Attack Success Rate (ASR)**. The script calculated ASR from the percentage of evaluated results where `label == 1`. A higher ASR therefore means the HarmBench evaluator classified a larger percentage of generations as successful instances of the tested harmful behavior.

The script can optionally attach HarmBench's AdvBench keyword-refusal metric. That optional result is stored separately as `advbench_label` and is not used to calculate the Average ASR reported by the script.

## Compute Environment

### Local System

- AMD Ryzen 9 5900X
- 32 GB DDR4 memory
- AMD Radeon RX 9070 XT, 16 GB VRAM
- Docker
- ROCm 6.4

### HPC Environment

The project also attempted to use the Texas A&M HPRC Launch environment with Slurm and NVIDIA A30 GPU resources. Persistent user storage/quota constraints made the HPC workflow difficult to complete, so the final experiment was conducted primarily on the local system.

### Software Stack

- HarmBench
- Python 3.10
- PyTorch 2.5.1
- Transformers 4.40
- vLLM 0.4.3
- Docker
- ROCm 6.4

## Results

| Model | Attack Success Rate |
| --- | ---: |
| Llama-2-7B-Chat | **2.2%** |
| Vicuna-7B-v1.5 | **50.2%** |
| Mistral-7B-Instruct-v0.2 | **65.8%** |

Llama-2-7B-Chat produced the lowest classifier-based ASR in the experiment, while Mistral-7B-Instruct-v0.2 produced the highest. Vicuna-7B-v1.5 fell between the two.

These results show that models with similar parameter counts can behave very differently under the same harmful-input evaluation. The experiment suggests that model training and alignment choices can substantially affect how frequently generated responses are classified as successful harmful behaviors.

The percentages should be interpreted as results from this HarmBench configuration rather than universal safety scores for the broader model families.

## Cybersecurity Relevance

Prompt-based attacks represent an input-driven security problem unique to systems that interpret natural language. Unlike many traditional vulnerabilities, the attacker does not necessarily exploit a memory-safety flaw or software bug. Instead, the attack attempts to manipulate the model's learned behavior through chosen input.

As LLMs are integrated into chatbots, automation systems, agents, and decision-support tools, organizations need methods for repeatedly testing model behavior. AI red teaming provides a way to identify weaknesses before deployment and after model, prompt, policy, or application changes.

## Limitations

The experiment was intentionally narrow and should be treated as a baseline rather than a complete security benchmark.

- Only DirectRequest was used for the final comparison.
- The experiment tested three approximately 7B models.
- Automated classifier-based evaluation can misclassify nuanced responses.
- Multi-turn, obfuscated, multimodal, and adaptive attacks were not included in the final experiment.
- Results apply to the tested model versions and evaluation configuration, not to every version of the model families.
- The reported ASR values reflect the HarmBench classifier's labels and should not be interpreted as a universal measurement of model safety.

## Future Work

Potential project extensions include:

- Prompt obfuscation and transformation
- Multi-turn jailbreak methods
- Multimodal and image-based attacks
- Newer model families such as Llama, Gemma, and Qwen
- Larger-scale testing using HPC resources
- Comparing multiple classifiers and scoring methods

## References

- Center for AI Safety. **HarmBench: A Standardized Evaluation Framework for Automated Red Teaming and Robust Refusal.** https://github.com/centerforaisafety/HarmBench
- LMSYS. **Vicuna-7B-v1.5.** https://huggingface.co/lmsys/vicuna-7b-v1.5
- Meta. **Llama-2-7B-Chat-HF.** https://huggingface.co/meta-llama/Llama-2-7b-chat-hf
- Mistral AI. **Mistral-7B-Instruct-v0.2.** https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2

## Attribution Note

The experiment used HarmBench's open-source evaluation framework and scripts. See the repository's [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) for licensing and attribution information.
