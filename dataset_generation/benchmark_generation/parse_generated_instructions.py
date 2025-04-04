#!/usr/bin/env python3

# Copyright (c) Meta Platforms, Inc. and affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree

import copy
import glob
import json
import os
import random
import re

import hydra
import omegaconf
from omegaconf import OmegaConf


def extract_task_number(filename):
    match = re.search(r"gen_(\d+)_(\d+).json$", filename)
    if match:
        return int(match.group(1)), int(match.group(2))
    else:
        return None


conversion_dict = {
    "plant": "plant_container",
    "watering_can": "pitcher",
    "reading_lamp": "lamp",
    "phone": "cellphone",
    "ball": "basketball",
    "towel": "hand_towel",
    "washcloth": "hand_towel",
    "laundry": "bath_towel",
    "laundry_basket": "basket",
    "hamper": "basket",
    "toy_car": "toy_vehicle",
    "stuffed_animal": "stuffed_toy",
    "dish": "plate",
    "shoes": "shoe",
    "cutlery": "fork",
    "dishes": "plate",
    "mug": "cup",
    "cups": "cup",
    "bat": "baseballbat",
    "dirty_dishes": "plate",
    "clean_dishes": "plate",
    "dirty_laundry": "bath_towel",
}


class InstructionParser:
    def parse_instruction_folders(
        self,
        folder_names,
        save_output=False,
        per_call_generation=5,
        add_clutter=False,
    ):
        dict_total = {
            "total_theoretically_possible": 0,
            "total_obtained": 0,
            "good_parsing": 0,
        }
        for folder_name in folder_names:
            dict_res = self.parse_instructions(
                folder_name,
                save_output,
                per_call_generation,
                add_clutter,
            )
            for elem in dict_res:
                dict_total[elem] += dict_res[elem]
        return dict_total

    def parse_instructions(
        self,
        folder_name,
        save_output=False,
        per_call_generation=5,
        add_clutter=False,
    ):
        """
        Read a folder of episodes generated by the LLM, parses them and makes sure that
        objects exist
        """
        # TODO: this should be generated somewhere else
        good_parsing = 0
        total = 0
        missing_objects = 0
        missing_furniture = 0
        all_missing = []
        total_theo = 0

        scenes = [
            scene
            for scene in glob.glob(f"{folder_name}/*")
            if "yaml" not in scene and "json" not in scene and "csv" not in scene
        ]
        for scene_path in scenes:
            scene_info = self.load_scene_info(f"{scene_path}/scene_info.json")
            parsed_folder = f"{scene_path}/output_parsed"
            gen_folder = f"{scene_path}/output_gen"

            if save_output and not os.path.isdir(parsed_folder):
                os.makedirs(parsed_folder)
            files = glob.glob(f"{gen_folder}/*")
            total_theo = len(files) * per_call_generation

            for file_path in files:
                template_task_number = extract_task_number(file_path)
                with open(file_path, "r") as f:
                    content = f.read()
                fi = content.find("[")
                ei = content.rfind("]")
                print("Parsing: ", file_path)
                content = content[fi : ei + 1]
                content_parsed = self.parse_to_json(content)

                for ind, episode_init in enumerate(content_parsed):
                    total += 1
                    dest_file = file_path.replace("output_gen", "output_parsed")
                    dest_file = dest_file.replace(".json", f"_{ind}.json")

                    (
                        is_valid,
                        content_parsed,
                        missing_objects,
                        missing_furniture,
                        missing_room,
                    ) = self.episode_init_valid(
                        episode_init, scene_info, add_clutter, template_task_number
                    )

                    print(
                        "is_valid:",
                        is_valid,
                        "missing_objects:",
                        missing_objects,
                        "missing_furniture:",
                        missing_furniture,
                        "missing_room:",
                        missing_room,
                    )
                    # breakpoint()

                    if is_valid:
                        good_parsing += 1

                        if save_output:
                            with open(dest_file, "w+") as f:
                                f.write(json.dumps(content_parsed, indent=4))
                    else:
                        all_missing += missing_objects

        return {
            "total_theoretically_possible": total_theo,
            "total_obtained": total,
            "good_parsing": good_parsing,
        }

    def episode_init_valid(
        self, init_episode, scene_info, add_clutter=False, template_task_number=None
    ):
        """
        Check if the episode initialization is valid
        """
        missing_objects = []
        missing_furniture = []
        missing_room = []
        missing_spatial_anchor = []
        parsed_init_state = []
        task_relevant_objects = []
        necessary_fields = [
            "object_classes",
            "furniture_names",
            "allowed_regions",
            "number",
        ]

        init_state_key = "initial_state"
        if init_state_key not in init_episode:
            return False, [], [], [], []

        # check hallucinations in initial state
        for init_obj in init_episode[init_state_key]:
            # ensure all init fields are present
            if not all(x in init_obj for x in necessary_fields):
                continue

            try:
                init_obj["object_classes"] = init_obj["object_classes"][0]
                init_obj["furniture_names"] = init_obj["furniture_names"][0]
                init_obj["allowed_regions"] = init_obj["allowed_regions"][0]
            except BaseException:
                continue

            # Convert object
            init_obj["object_classes"] = (
                init_obj["object_classes"].lower().strip().replace(" ", "_")
            )

            if init_obj["object_classes"] in conversion_dict:
                init_obj["object_classes"] = conversion_dict[init_obj["object_classes"]]

            if init_obj["object_classes"] not in scene_info["objects"]:
                missing_objects.append(init_obj["object_classes"])
            else:
                task_relevant_objects.append(init_obj["object_classes"])

            if (
                init_obj["furniture_names"] not in scene_info["all_furniture"]
                and init_obj["furniture_names"] != "floor"
            ):
                missing_furniture.append(init_obj["furniture_names"])

            if (
                init_obj["allowed_regions"] not in scene_info["furniture"].keys()
                and init_obj["allowed_regions"] not in scene_info["all_rooms"]
            ):
                missing_room.append(init_obj["allowed_regions"])

            parsed_init_state.append(
                {
                    "number": init_obj["number"],
                    "object_classes": [init_obj["object_classes"]],
                    "furniture_names": [init_obj["furniture_names"]],
                    "allowed_regions": [init_obj["allowed_regions"]],
                }
            )

        if add_clutter:
            clutter_num = random.randint(1, 5)
            clutter_num = str(clutter_num)
            ##use the task_relevant_objects list above to control clutter gen
            parsed_init_state.append(
                {
                    "name": "common sense",
                    "excluded_object_classes": task_relevant_objects,
                    "exclude_existing_objects": True,
                    "number": clutter_num,
                    "common_sense_object_classes": True,  # this specifies region->object metadata is used for sampling
                    "location": "on",
                    "furniture_names": [],
                },
            )

        if template_task_number is not None:
            parsed_init_state.append(
                {
                    "template_task_number": template_task_number,
                }
            )

        new_init = copy.deepcopy(init_episode)
        del new_init[init_state_key]
        new_init["initial_state"] = parsed_init_state

        if (
            len(missing_objects) > 0
            or len(missing_furniture) > 0
            or len(missing_spatial_anchor) > 0
        ):
            return False, new_init, missing_objects, missing_furniture, missing_room
        else:
            return True, new_init, [], [], []

    def parse_to_json(self, content_parsed):
        """
        Modifies json string so that it can be parsed
        """
        try:
            res = json.loads(content_parsed)
            return res
        except BaseException:
            print("generated content was not a json, trying alternate parsing.")

        # break by JSON_OUTPUT
        def check_braces(s):
            return any(s[i] == "{" for i in range(min(5, len(s))))

        using_parts = False
        content_parsed = str(content_parsed)
        parsed = content_parsed.split("assistant\n\nJSON_OUTPUT: ")
        parts = re.split("assistant|JSON_OUTPUT", content_parsed)
        if len(parsed) == 1:
            using_parts = True
            parsed = parts
        content_parsed = []
        res = []
        for parse in parsed:
            parse = str(parse)
            parse = parse.replace(",,", ",")
            parse = parse.replace("\n},\n]", "\n}\n]")
            if not check_braces(parse) and using_parts:
                print("not json ", parse)
                continue
            try:
                res += json.loads(parse)
            except Exception:
                break
        if len(res):
            return res

        print("Empty json")
        return {}

    def load_scene_info(self, sceneinfo_file):
        """
        Loads scene information
        """
        if not os.path.exists(sceneinfo_file):
            print("scene info does not exist. Tried this path: ", sceneinfo_file)
        with open(sceneinfo_file, "r") as f:
            scene_info = json.load(f)
        scene_info["all_furniture"] = []
        scene_info["all_rooms"] = []
        for room, furniture_room in scene_info["furniture"].items():
            scene_info["all_furniture"] += furniture_room
            if room not in scene_info["all_rooms"]:
                scene_info["all_rooms"].append(room)
        scene_info["all_furniture"] = list(set(scene_info["all_furniture"]))
        return scene_info


@hydra.main(
    version_base=None,
    config_path="../conf/",
    config_name="benchmark_gen.yaml",
)
def main(cfg: omegaconf.DictConfig):
    inst_gen_config = OmegaConf.create(cfg)

    instr_parser = InstructionParser()
    res = instr_parser.parse_instruction_folders(
        [cfg.generator.output_path],
        save_output=True,
        per_call_generation=inst_gen_config.generator.generations_per_call,
        add_clutter=inst_gen_config.generator.add_clutter,
    )
    print(res)


if __name__ == "__main__":
    main()
