# Adapted from the Center for AI Safety HarmBench project.
# See THIRD_PARTY_NOTICES.md for upstream attribution and MIT license text.

import argparse
import json
import os
from functools import partial

import torch
import transformers
import yaml
from accelerate.utils import find_executable_batch_size
from tqdm import tqdm
from vllm import SamplingParams

from api_models import api_models_map
from baselines import get_template, load_model_and_tokenizer, load_vllm_model
import multimodalmodels

# Disable warning messages during generation.
transformers.utils.logging.set_verbosity_error()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate model completions for HarmBench test cases."
    )
    parser.add_argument(
        "--model_name",
        type=str,
        required=True,
        help="Model key from the HarmBench model configuration file.",
    )
    parser.add_argument(
        "--models_config_file",
        type=str,
        default="./configs/model_configs/models.yaml",
        help="Path to the HarmBench model configuration file.",
    )
    parser.add_argument(
        "--test_cases_path",
        type=str,
        required=True,
        help="Path to generated test cases.",
    )
    parser.add_argument(
        "--save_path",
        type=str,
        required=True,
        help="Path used to save generated completions.",
    )
    parser.add_argument(
        "--max_new_tokens",
        type=int,
        default=256,
        help="Maximum number of new tokens generated per completion.",
    )
    parser.add_argument(
        "--generate_with_vllm",
        action="store_true",
        help="Use vLLM generation when supported by the configured model.",
    )
    parser.add_argument(
        "--incremental_update",
        action="store_true",
        help="Reuse complete entries in an existing completions file.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print(args)

    with open(args.models_config_file, encoding="utf-8") as file:
        model_configs = yaml.full_load(file)

    if args.model_name not in model_configs:
        raise ValueError(f"Model '{args.model_name}' not found in model configuration")

    configured_gpus = model_configs[args.model_name].get("num_gpus", 0)
    available_gpus = torch.cuda.device_count()
    if available_gpus != configured_gpus:
        print(
            f"Warning: configured GPUs ({configured_gpus}) do not match available "
            f"GPUs ({available_gpus}). Using {available_gpus}."
        )

    model_config = dict(model_configs[args.model_name]["model"])
    model_config["num_gpus"] = available_gpus
    print("model_config", model_config)

    with open(args.test_cases_path, "r", encoding="utf-8") as file:
        test_cases_data = json.load(file)

    generation_function = load_generation_function(
        model_config,
        args.max_new_tokens,
        test_cases_path=args.test_cases_path,
        generate_with_vllm=args.generate_with_vllm,
    )

    returned_data = {}
    if args.incremental_update and os.path.exists(args.save_path):
        with open(args.save_path, "r", encoding="utf-8") as file:
            returned_data = json.load(file)

        pending_test_cases = {}
        for behavior_id, behavior_test_cases in test_cases_data.items():
            if (
                behavior_id in returned_data
                and len(returned_data[behavior_id]) == len(behavior_test_cases)
            ):
                continue

            print(behavior_id, len(behavior_test_cases))
            pending_test_cases[behavior_id] = behavior_test_cases

        test_cases_data = pending_test_cases

    test_cases = []
    for behavior_id, behavior_test_cases in test_cases_data.items():
        test_cases.extend(
            {
                "behavior_id": behavior_id,
                "test_case": test_case,
            }
            for test_case in behavior_test_cases
        )

    if not test_cases:
        print("No test cases to generate completions for")
        return

    print(f"Generating completions for {len(test_cases)} test cases")
    generations = generation_function(
        test_cases=[test_case["test_case"] for test_case in test_cases]
    )
    print("Done")

    for test_case, generation in zip(test_cases, generations):
        behavior_id = test_case["behavior_id"]
        returned_data.setdefault(behavior_id, [])
        returned_data[behavior_id].append(
            {
                "test_case": test_case["test_case"],
                "generation": generation,
            }
        )

    output_dir = os.path.dirname(args.save_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    print(f"Saving completions to {args.save_path}...")
    with open(args.save_path, "w", encoding="utf-8") as file:
        json.dump(returned_data, file, indent=4)
    print("Saved")


def _vllm_generate(model, test_cases, template, **generation_kwargs):
    inputs = [template["prompt"].format(instruction=test_case) for test_case in test_cases]
    outputs = model.generate(inputs, **generation_kwargs)
    return [output.outputs[0].text.strip() for output in outputs]


def _hf_generate_with_batching(
    model,
    tokenizer,
    test_cases,
    template,
    **generation_kwargs,
):
    @find_executable_batch_size(starting_batch_size=len(test_cases))
    def inner_generation_loop(batch_size):
        generations = []

        for index in tqdm(range(0, len(test_cases), batch_size)):
            batch = test_cases[index : index + batch_size]
            inputs = [template["prompt"].format(instruction=item) for item in batch]
            inputs = tokenizer(inputs, return_tensors="pt", padding=True).to(model.device)

            with torch.no_grad():
                outputs = model.generate(
                    inputs=inputs["input_ids"],
                    attention_mask=inputs["attention_mask"],
                    **generation_kwargs,
                ).cpu()

            generated_tokens = outputs[:, inputs["input_ids"].shape[1] :]
            generations.extend(
                tokenizer.decode(output, skip_special_tokens=True).strip()
                for output in generated_tokens
            )

        return generations

    return inner_generation_loop()


def _api_model_generate(model, test_cases, **generation_kwargs):
    if isinstance(test_cases[0], (tuple, list)):
        images, prompts = zip(*test_cases)
        return model.generate(
            prompts=list(prompts),
            images=list(images),
            **generation_kwargs,
        )

    return model.generate(prompts=test_cases, **generation_kwargs)


def load_generation_function(
    model_config,
    max_new_tokens,
    test_cases_path,
    generate_with_vllm=False,
):
    model_name_or_path = model_config["model_name_or_path"]

    if model_name_or_path in dir(multimodalmodels):
        model = getattr(multimodalmodels, model_name_or_path)()
        generation_kwargs = {
            "max_new_tokens": max_new_tokens,
            "do_sample": False,
            "num_beams": 1,
        }
        image_dir = os.path.join(os.path.dirname(test_cases_path), "images")
        return partial(
            model.generate,
            image_dir=image_dir,
            **generation_kwargs,
        )

    api_model = api_models_map(**model_config)
    if api_model:
        generation_kwargs = {
            "max_new_tokens": max_new_tokens,
            "temperature": 0.0,
            "use_tqdm": True,
        }
        return partial(
            _api_model_generate,
            model=api_model,
            **generation_kwargs,
        )

    template = get_template(
        model_name_or_path,
        chat_template=model_config.get("chat_template"),
    )

    if generate_with_vllm:
        print("Using vLLM generation")
        model = load_vllm_model(**model_config)
        sampling_params = SamplingParams(temperature=0, max_tokens=max_new_tokens)
        return partial(
            _vllm_generate,
            model=model,
            template=template,
            sampling_params=sampling_params,
            use_tqdm=True,
        )

    print("Using Hugging Face generation")
    model, tokenizer = load_model_and_tokenizer(**model_config)
    return partial(
        _hf_generate_with_batching,
        model=model,
        tokenizer=tokenizer,
        template=template,
        max_new_tokens=max_new_tokens,
        do_sample=False,
    )


if __name__ == "__main__":
    main()
