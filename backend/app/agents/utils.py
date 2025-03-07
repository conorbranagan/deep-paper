from smolagents import ActionStep, PlanningStep, TaskStep, SystemPromptStep, AgentText
import json

def step_as_json(step) -> dict:
    if isinstance(step, ActionStep):
        return {
            "type": "action",
            "content": step.model_output,
        }
    elif isinstance(step, PlanningStep):
        return {
            "type": "thinking",
            "content": step.plan,
        }
    elif isinstance(step, TaskStep):
        return {
            "type": "task",
            "content": step.task,
        }
    elif isinstance(step, SystemPromptStep):
        return {
            "type": "system",
            "content": step.system_prompt,
        }
    elif isinstance(step, AgentText):
        return {
            "type": "agent-answer",
            "content": step.to_string(),
        }
    elif isinstance(step, (dict, list)):
        return {
            "type": "agent-answer",
            "content": json.dumps(step),
        }
    else:
        raise Exception(f"Unknown step type: {type(step)}")
