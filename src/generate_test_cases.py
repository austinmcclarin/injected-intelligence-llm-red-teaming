# Adapted from the Center for AI Safety HarmBench project.
# See THIRD_PARTY_NOTICES.md for upstream attribution and MIT license text.

import argparse
import csv
import os

import torch
import transformers
import yaml

from baselines import get_method_class, init_method
from eval_utils import get_experiment_config

# Disable warning messages during generation.
transformers.utils.logging.set_verbosity_error()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate HarmBench red-teaming test cases."
    )
    parser.add_argument(
        "--method_name",
        type=str,
        default="DirectRequest",
        help="Red-teaming method to use. This project used DirectRequest.",
    )
    parser.add_argument(
        "--experiment_name",
        type=str,
        default="default",
        help="Experiment name from the selected HarmBench method configuration.",
    )
    parser.add_argument(
        "--method_config_file",
        type=str,
        default=None,
        help="Optional path to a HarmBench method configuration file.",
    )
    parser.add_argument(
        "--models_config_file",
        type=str,
        default="./configs/model_configs/models.yaml",
        help="Path to the HarmBench model configuration file.",
    )
    parser.add_argument(
        "--behaviors_path",
        type=str,
        default="./data/behavior_datasets/harmbench_behaviors_text_all.csv",
        help="Path to the HarmBench behavior dataset.",
    )
    parser.add_argument(
        "--save_dir",
        type=str,
        default="./test_cases",
        help="Directory used to save generated test cases.",
    )
    parser.add_argument(
        "--behavior_start_idx",
        type=int,
        default=None,
        help="Start index for a behavior subset, inclusive.",
    )
    parser.add_argument(
        "--behavior_end_idx",
        type=int,
        default=None,
        help="End index for a behavior subset, exclusive.",
    )
    parser.add_argument(
        "--behavior_ids_subset",
        type=str,
        default="",
        help=(
            "Comma-separated behavior IDs or a path to a newline-separated ID file. "
            "Overrides behavior_start_idx and behavior_end_idx."
        ),
    )
    parser.add_argument(
        "--run_id",
        type=str,
        default=None,
        help="Optional integer run ID appended to output filenames.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing saved test cases.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print intermediate generation details.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print(args)

    method_name = args.method_name
    experiment_name = args.experiment_name
    save_dir = os.path.abspath(args.save_dir)

    with open(args.models_config_file, encoding="utf-8") as file:
        model_configs = yaml.full_load(file)

    method_config_file = (
        args.method_config_file
        or f"configs/method_configs/{method_name}_config.yaml"
    )
    with open(method_config_file, encoding="utf-8") as file:
        method_configs = yaml.full_load(file)

    if "default_method_hyperparameters" not in method_configs:
        raise ValueError(
            f"Default method hyperparameters not found in {method_config_file}"
        )

    method_config = method_configs.get("default_method_hyperparameters") or {}
    experiment_config = get_experiment_config(
        experiment_name, model_configs, method_configs
    )
    method_config.update(experiment_config)

    if args.run_id:
        assert args.run_id.isdigit(), (
            f"Expected run_id to be an integer; got {args.run_id}"
        )

    with open(args.behaviors_path, "r", encoding="utf-8") as file:
        behaviors = list(csv.DictReader(file))

    if args.behavior_ids_subset:
        print(f"Selecting subset from behavior IDs: {args.behavior_ids_subset}")
        if os.path.exists(args.behavior_ids_subset):
            with open(args.behavior_ids_subset, "r", encoding="utf-8") as file:
                behavior_ids_subset = file.read().splitlines()
        else:
            behavior_ids_subset = args.behavior_ids_subset.split(",")

        behaviors = [
            behavior
            for behavior in behaviors
            if behavior["BehaviorID"] in behavior_ids_subset
        ]
    elif args.behavior_start_idx is not None or args.behavior_end_idx is not None:
        print(
            "Selecting behavior index range: "
            f"[{args.behavior_start_idx}, {args.behavior_end_idx}]"
        )
        behaviors = behaviors[
            args.behavior_start_idx : args.behavior_end_idx
        ]

    world_size = torch.cuda.device_count()

    print(f"============= {method_name}, {experiment_name} Config =============")
    print("\n".join(f"{key}: {value}" for key, value in method_config.items()))
    print("============= GPU Allocation Configs =============")
    print(f"Total GPUs: {world_size}")
    print("=============")

    method_class = get_method_class(method_name)

    if not args.overwrite:
        filtered_behaviors = []
        for behavior in behaviors:
            behavior_id = behavior["BehaviorID"]
            test_case_file = method_class.get_output_file_path(
                save_dir,
                behavior_id,
                file_type="test_cases",
                run_id=args.run_id,
            )
            if not os.path.exists(test_case_file):
                filtered_behaviors.append(behavior)
            else:
                print(f"===> Skipping {behavior_id}")

        behaviors = filtered_behaviors
        if not behaviors:
            print("Found existing test cases for all selected behaviors. Exiting.")
            return

    method = init_method(method_class, method_config)

    print("# Behaviors to run:", len(behaviors))
    test_cases, logs = method.generate_test_cases(
        behaviors=behaviors,
        verbose=args.verbose,
    )

    print("Saving outputs to:", save_dir)
    method.save_test_cases(
        save_dir,
        test_cases,
        logs,
        method_config=method_config,
        run_id=args.run_id,
    )
    print("Finished")


if __name__ == "__main__":
    main()
