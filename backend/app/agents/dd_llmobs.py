from smolagents.agent_types import AgentText, AgentImage, AgentAudio
from smolagents import (
    CodeAgent,
    MultiStepAgent,
    FinalAnswerTool,
    UserInputTool,
    GoogleSearchTool,
    DuckDuckGoSearchTool,
    ChatMessage,
)
from ddtrace.llmobs import LLMObs


class SmolLLMObs:
    """A utility class for providing Datadog LLM Obs wrapping for Tools and Agents from the smolagents library"""

    @staticmethod
    def _serialize_output_data(output_data):
        if isinstance(output_data, ChatMessage):
            # the `raw` data can't be serialized so let's remove it.
            output_data.raw = None
            return output_data.dict()
        return output_data

    def wrap_tool(cls):
        original_forward = cls.forward

        def wrapped_forward(self, *args, **kwargs):
            with LLMObs.tool(self.name):
                tool_args = {k: v for k, v in kwargs.items()}
                result = original_forward(self, *args, **kwargs)
                LLMObs.annotate(
                    input_data=tool_args,
                    output_data=result,
                )
                return result

        cls.skip_forward_signature_validation = True
        cls.forward = wrapped_forward
        return cls

    def wrap_agent(cls):
        original_step = cls.step
        original_planning_step = cls.planning_step
        original_final_answer = cls.provide_final_answer
        original_run = cls.run

        def wrapped_step(self, memory_step):
            with LLMObs.task(name="action"):
                res = original_step(self, memory_step)
                step_meta = memory_step.dict()
                annotate_args = dict(
                    input_data=step_meta.pop("model_input_messages"),
                    output_data=SmolLLMObs._serialize_output_data(
                        step_meta.pop("model_output_message")
                    ),
                    metadata=step_meta,
                )
                LLMObs.annotate(**annotate_args)
                return res

        def wrapped_planning_step(self, *args, **kwargs):
            with LLMObs.task(name="planning"):
                return original_planning_step(self, *args, **kwargs)

        def wrapped_final_answer(self, *args, **kwargs):
            with LLMObs.task(name="final_answer"):
                answer = original_final_answer(self, *args, **kwargs)
                LLMObs.annotate(
                    input_data=args[0] if len(args) > 0 else "",
                    output_data=answer,
                )
                return answer

        def wrapped_run(self, *args, **kwargs):
            llmbos_metadata = {
                "task": args[0] or kwargs.get("task") or "unset task",
                "max_steps": kwargs.get("max_steps"),
                "stream": kwargs.get("stream"),
                "reset": kwargs.get("reset"),
                # other options: images, additional_args
            }
            is_stream = kwargs.get("stream", False)
            if is_stream:
                return _wrapped_run_stream(
                    self, *args, llmbos_metadata=llmbos_metadata, **kwargs
                )
            else:
                # For non-stream we simply return that's provided.
                agent_name = "smolagents_agent"
                if hasattr(self, "name"):
                    agent_name = f"{self.name} (smolagents)"

                with LLMObs.agent(agent_name):
                    output = original_run(self, *args, **kwargs)
                    LLMObs.annotate(
                        input_data=llmbos_metadata["task"],
                        output_data=output,
                        metadata=llmbos_metadata,
                    )
                    return output

        def _wrapped_run_stream(self, *args, llmbos_metadata, **kwargs):
            # When it's a stream we have to wrap the generator. We pick the last
            # value to come out as our potential output and cast it to str if it's a known type.
            agent_name = "smolagents_agent"
            if hasattr(self, "name"):
                    agent_name = f"{self.name} (smolagents)"
            with LLMObs.agent(agent_name):
                r_gen = original_run(self, *args, **kwargs)
                output = "unknown"
                last_val = None
                for val in r_gen:
                    last_val = val
                    yield val

                # Handle specific types for now.
                if last_val and isinstance(
                    last_val, (AgentText, AgentImage, AgentAudio)
                ):
                    output = last_val.to_string()
                    LLMObs.annotate(
                        input_data=llmbos_metadata["task"],
                        output_data=output,
                        metadata=llmbos_metadata,
                    )

        cls.step = wrapped_step
        cls.planning_step = wrapped_planning_step
        cls.provide_final_answer = wrapped_final_answer
        cls.run = wrapped_run
        return cls

    @classmethod
    def wrapped_tool(cls, base_class):
        """Class decorator to create a monitored tool."""
        return cls.wrap_tool(base_class)


_llmobs_is_wrapped = False


def wrap_llmobs():
    global _llmobs_is_wrapped
    if not _llmobs_is_wrapped:
        SmolLLMObs.wrap_agent(CodeAgent)
        SmolLLMObs.wrap_agent(MultiStepAgent)
        SmolLLMObs.wrap_tool(FinalAnswerTool)
        SmolLLMObs.wrap_tool(UserInputTool)
        SmolLLMObs.wrap_tool(GoogleSearchTool)
        SmolLLMObs.wrap_tool(DuckDuckGoSearchTool)
        _llmobs_is_wrapped = True
