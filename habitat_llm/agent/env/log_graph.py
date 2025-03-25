import argparse
from habitat_llm.world_model import DynamicWorldGraph, WorldGraph
import datetime
import os
import json
import re

class LogSystem():
    def __init__(self):
        print("Graph logger is initialized!")
        self.output_dir = "/home/proactiveproject/ProactiveProject/WorldGraphs"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Generate the timestamp for the filename
        current_time = datetime.datetime.now()
        time_string = current_time.strftime("%d-%m-%y-%H:%M")  # Format: DD-MM-YY-HH:MM
        self.output_txt_file = os.path.join(self.output_dir, f"{time_string}.txt")
        self.output_json_file = os.path.join(self.output_dir, f"{time_string}.json")
        self.num_of_step = self._get_last_step() + 1


    def dot_to_json(self, dot_str):
        """
        Converts a DOT graph representation into a structured JSON format.

        Parameters:
            dot_str (str): The DOT format string from the world graph.

        Returns:
            dict: JSON representation of the world graph.
        """
        json_graph = {}

        # Regular expression to extract DOT relationships: "Node1" -> "Node2" [label="relationship"];
        pattern = r'"([^"]+)"\s*->\s*"([^"]+)"\s*\[label="([^"]+)"\];'

        for match in re.findall(pattern, dot_str):
            node1, node2, relation = match
            if node1 not in json_graph:
                json_graph[node1] = []
            json_graph[node1].append({"target": node2, "relation": relation})

        return json_graph

    def _get_last_step(self):
        """Retrieve the last step number from the JSON log if it exists."""
        if os.path.exists(self.output_json_file):
            try:
                with open(self.output_json_file, "r") as file:
                    data = json.load(file)
                    return max([entry["Step"] for entry in data], default=0)
            except (json.JSONDecodeError, KeyError, FileNotFoundError):
                return 0  # If file is corrupt or empty, restart from step 1
        return 0
    

    def log_world_graphs(self, world_graph, robot_world_graph, human_world_graph):
        """
        Logs the descriptions and DOT representations of the given world graphs
        into a text file.

        Parameters:
            world_graph (WorldGraph): The overall world graph.
            robot_world_graph (WorldGraph): The robot's world graph.
            human_world_graph (WorldGraph): The human's world graph.
        """

        try:
            world_descr = world_graph.get_world_descr()
            world_dot = world_graph.to_dot()
        except Exception as e:
            world_descr = f"Error retrieving world description: {str(e)}"
            world_dot = f"Error converting world graph to DOT: {str(e)}"

        try:
            robot_world_descr = robot_world_graph.get_world_descr()
            robot_world_dot = robot_world_graph.to_dot()
        except Exception as e:
            robot_world_descr = f"Error retrieving robot world description: {str(e)}"
            robot_world_dot = f"Error converting robot world graph to DOT: {str(e)}"

        try:
            human_world_descr = human_world_graph.get_world_descr(is_human_wg=True)
            human_world_dot = human_world_graph.to_dot()
        except Exception as e:
            human_world_descr = f"Error retrieving human world description: {str(e)}"
            human_world_dot = f"Error converting human world graph to DOT: {str(e)}"
        
        # Track number of steps
        step_header = f"<<<<<<<<<<<Step #{self.num_of_step}>>>>>>>>>>>>>>>>>>>\n"
        self.num_of_step += 1


        # Convert DOT to JSON
        world_json = self.dot_to_json(world_dot)
        robot_world_json = self.dot_to_json(robot_world_dot)
        human_world_json = self.dot_to_json(human_world_dot)

        # # Write to text file
        # with open(output_txt_file, "w") as f:
        #     f.write(step_header)
        #     f.write("=== World Graph ===\n")
        #     f.write("Description:\n")
        #     f.write(world_descr + "\n\n")
        #     f.write("DOT Representation:\n")
        #     f.write(world_dot + "\n\n")

        #     f.write("=== Robot World Graph ===\n")
        #     f.write("Description:\n")
        #     f.write(robot_world_descr + "\n\n")
        #     f.write("DOT Representation:\n")
        #     f.write(robot_world_dot + "\n\n")

        #     f.write("=== Human World Graph ===\n")
        #     f.write("Description:\n")
        #     f.write(human_world_descr + "\n\n")
        #     f.write("DOT Representation:\n")
        #     f.write(human_world_dot + "\n\n")

        # Write to JSON file
        json_data = {
            "Step": self.num_of_step - 1,
            "WorldGraph": world_json,
            "RobotWorldGraph": robot_world_json,
            "HumanWorldGraph": human_world_json,
        }


        if os.path.exists(self.output_json_file):
            try:
                with open(self.output_json_file, "r") as file:
                    existing_data = json.load(file)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_data = []
        else:
            existing_data = []
        existing_data.append(json_data)

        with open(self.output_json_file, "w") as json_file:
            json.dump(existing_data, json_file, indent=4)

        # Append descriptions to the text log
        with open(self.output_txt_file, "a") as txt_file:
            txt_file.write(step_header)
            txt_file.write("=== World Graph Description ===\n")
            txt_file.write(world_descr + "\n\n")
            txt_file.write("=== Robot World Graph Description ===\n")
            txt_file.write(robot_world_descr + "\n\n")
            txt_file.write("=== Human World Graph Description ===\n")
            txt_file.write(human_world_descr + "\n\n")
            txt_file.write("=" * 50 + "\n\n")
        
        # print(f"Step #{self.num_of_step} recorded in {self.output_json_file} and {self.output_txt_file}")