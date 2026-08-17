# Adapted from the Center for AI Safety HarmBench project.
# See THIRD_PARTY_NOTICES.md for upstream attribution and MIT license text.

import argparse
import csv
import json
import os

import numpy as np
import transformers
from tqdm import tqdm
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams

from eval_utils import (
    compute_results_advbench,
    compute_results_classifier,
    compute_results_hashing,
)

# Disable warning messages during evaluation.
transformers.utils.logging.set_verbosity_error()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate HarmBench model completions and report classifier-based ASR."
    )
    parser.add_argument(
        "--cls_path",
        type=str,
        default="cais/HarmBench-Llama-2-13b-cls",
        help="Classifier model used to compute HarmBench success labels.",
    )
    parser.add_argument(
        "--behaviors_path",
        type=str,
        default="./data/behavior_datasets/harmbench_behaviors_text_all.csv",
        help="Path to the HarmBench behavior dataset.",
    )
    parser.add_argument(
        "--completions_path",
        type=str,
        required=True,
        help="Path to the model completions JSON file.",
    )
    parser.add_argument(
        "--save_path",
        type=str,
        required=True,
        help="Path used to save evaluation results.",
    )
    parser.add_argument(
        "--include_advbench_metric",
        action="store_true",
        help=(
            "Also attach the optional AdvBench keyword-refusal label to each result. "
            "The reported Average ASR is still computed from HarmBench classifier labels."
        ),
    )
    parser.add_argument(
        "--num_tokens",
        type=int,
        default=512,
        help="Maximum number of generation tokens passed to the classifier.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print(args)

    with open(args.behaviors_path, "r", encoding="utf-8") as file:
        behaviors = {
            behavior["BehaviorID"]: behavior
            for behavior in csv.DictReader(file)
        }

    with open(args.completions_path, "r", encoding="utf-8") as file:
        completions = json.load(file)

    tokenizer = AutoTokenizer.from_pretrained(args.cls_path)
    tokenizer.truncation_side = "right"

    for completion_list in completions.values():
        for completion in completion_list:
            tokenized_text = tokenizer.encode(
                completion["generation"],
                max_length=args.num_tokens,
                truncation=True,
            )
            completion["generation"] = tokenizer.decode(
                tokenized_text,
                skip_special_tokens=True,
            )

    classifier = LLM(model=args.cls_path, tensor_parallel_size=1)
    classifier.llm_engine.tokenizer.tokenizer.truncation_side = "left"
    classifier_params = SamplingParams(temperature=0.0, max_tokens=1)

    results = {}
    for behavior_id, data in tqdm(completions.items()):
        if behavior_id not in behaviors:
            print(f"Behavior {behavior_id} not found in behaviors file; skipping")
            continue

        behavior_dict = behaviors[behavior_id]
        tags = behavior_dict["Tags"].split(", ")

        if "hash_check" in tags:
            current_results = compute_results_hashing(behavior_dict, data)
        else:
            current_results = compute_results_classifier(
                behavior_dict,
                data,
                classifier,
                classifier_params,
            )

        if args.include_advbench_metric:
            current_results = compute_results_advbench(current_results, data)

        results[behavior_id] = current_results

    success_rates = []
    for index, (behavior_id, data) in enumerate(results.items()):
        success_mean = np.mean([result["label"] == 1 for result in data])
        print(f"{index}. {behavior_id} === classifier ASR: {success_mean}")
        success_rates.append(success_mean)

    average_asr = np.mean(success_rates) if success_rates else float("nan")
    print("Average classifier ASR:", average_asr)

    output_dir = os.path.dirname(args.save_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.save_path, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=4)


if __name__ == "__main__":
    main()
