from typing import List
import torch
import random

from habitat_llm.tools.motor_skills.skill import SkillPolicy

class DiscreteNavSkill(SkillPolicy):
    def __init__(self, config, observation_space, action_space, batch_size, env, agent_uid):
        super().__init__(
            config,
            action_space,
            batch_size,
            should_keep_hold_state=False,
            agent_uid=agent_uid,
        )
        self.env = env
        # Define the discrete commands available.
        self.commands = ["turn right", "turn left", "move forward", "move backward", "wait"]
        # Map each command to (linear_velocity, angular_velocity) tuples.
        # Adjust these values to suit your robot's dynamics.
        self.action_mapping = {
            "move forward": (1.0, 0.0),
            "move backward": (-1.0, 0.0),
            "turn left": (0.0, 1.0),
            "turn right": (0.0, -1.0),
            "wait": (0.0, 0.0)
        }

    def reset(self, batch_idxs):
        super().reset(batch_idxs)
        return

    def _is_skill_done(
        self,
        observations,
        rnn_hidden_states,
        prev_actions,
        masks,
        batch_idx,
    ) -> torch.BoolTensor:
        # For a discrete command, we assume one execution step is sufficient.
        return torch.ones(self._batch_size, dtype=torch.bool, device=masks.device)

    def get_state_description(self):
        return "Discrete Navigation Skill"

    def _internal_act(
        self,
        observations,
        rnn_hidden_states,
        prev_actions,
        masks,
        cur_batch_idx,
        deterministic=False,
    ):
        # Randomly select one command from the available discrete commands.
        # Alternatively, you might want to use a command provided by the planner.
        command = random.choice(self.commands)
        linear, angular = self.action_mapping[command]
        # Create an action tensor matching the shape of prev_actions.
        # Here, we assume the action tensor has two elements: [linear_velocity, angular_velocity].
        action = torch.tensor([linear, angular], device=masks.device).unsqueeze(0).repeat(self._batch_size, 1)
        return action, None

    @property
    def argument_types(self) -> List[str]:
        return []
