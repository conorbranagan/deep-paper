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

from opentelemetry import trace
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry import context as context_api
from opentelemetry.semconv_ai import SpanAttributes, TraceloopSpanKindValues

from app.config import OtelClient


class SmolTel:
    """A utility class for providing Datadog LLM Obs wrapping for Tools and Agents from the smolagents library"""

    @staticmethod
    def _serialize_output_data(output_data):
        if isinstance(output_data, ChatMessage):
            # the `raw` data can't be serialized so let's remove it.
            output_data.raw = None
            return output_data.dict()
        return output_data

    @staticmethod
    def _setup_span(name: str, kind: TraceloopSpanKindValues):
        """Create and set up a span"""
        tracer = OtelClient.get_tracer()
        span = tracer.start_span(f"{name}.{kind.value}")
        span.set_attribute(SpanAttributes.TRACELOOP_SPAN_KIND, kind.value)
        ctx = trace.set_span_in_context(span)
        ctx_token = context_api.attach(ctx)
        return span, ctx, ctx_token

    def wrap_tool(cls):
        original_forward = cls.forward

        def wrapped_forward(self, *args, **kwargs):
            span, ctx, ctx_token = SmolTel._setup_span(
                self.name, TraceloopSpanKindValues.TOOL
            )
            for k, v in kwargs.items():
                span.set_attribute(f"tool_input.{k}", v)
            try:
                result = original_forward(self, *args, **kwargs)
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise e
            finally:
                context_api.detach(ctx_token)
                span.end()

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
            span, ctx, ctx_token = SmolTel._setup_span(
                "action", TraceloopSpanKindValues.TASK
            )

            res = original_step(self, memory_step)
            step_meta = memory_step.dict()
            span.set_attribute("input_data", step_meta.pop("model_input_messages"))
            span.set_attribute(
                "output_data",
                SmolTel._serialize_output_data(step_meta.pop("model_output_message")),
            )
            for k, v in step_meta.items():
                span.set_attribute(f"metadata.{k}", v)
            context_api.detach(ctx_token)
            span.end()
            return res

        def wrapped_planning_step(self, *args, **kwargs):
            span, ctx, ctx_token = SmolTel._setup_span(
                "planning", TraceloopSpanKindValues.TASK
            )
            return original_planning_step(self, *args, **kwargs)

        def wrapped_final_answer(self, *args, **kwargs):
            span, ctx, ctx_token = SmolTel._setup_span(
                "final_answer", TraceloopSpanKindValues.TASK
            )
            answer = original_final_answer(self, *args, **kwargs)
            span.set_attribute("input_data", args[0] if len(args) > 0 else "")
            span.set_attribute("output_data", answer)
            context_api.detach(ctx_token)
            span.end()
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

                span, ctx, ctx_token = SmolTel._setup_span(
                    agent_name, TraceloopSpanKindValues.AGENT
                )
                output = original_run(self, *args, **kwargs)
                span.set_attribute("input_data", llmbos_metadata["task"])
                span.set_attribute("output_data", output)
                for k, v in llmbos_metadata.items():
                    span.set_attribute(f"metadata.{k}", v)
                context_api.detach(ctx_token)
                span.end()
                return output

        def _wrapped_run_stream(self, *args, llmbos_metadata, **kwargs):
            # When it's a stream we have to wrap the generator. We pick the last
            # value to come out as our potential output and cast it to str if it's a known type.
            agent_name = "smolagents_agent"
            if hasattr(self, "name"):
                agent_name = f"{self.name} (smolagents)"
            span, ctx, ctx_token = SmolTel._setup_span(
                agent_name, TraceloopSpanKindValues.AGENT
            )
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
                    span.set_attribute("input_data", llmbos_metadata["task"])
                    span.set_attribute("output_data", output)
                    for k, v in llmbos_metadata.items():
                        span.set_attribute(f"metadata.{k}", v)

            context_api.detach(ctx_token)
            span.end()

        cls.step = wrapped_step
        cls.planning_step = wrapped_planning_step
        cls.provide_final_answer = wrapped_final_answer
        cls.run = wrapped_run
        return cls

    @classmethod
    def wrapped_tool(cls, base_class):
        """Class decorator to create a monitored tool."""
        return cls.wrap_tool(base_class)


_otel_is_wrapped = False


def wrap_otel_llmobs():
    global _otel_is_wrapped
    if not _otel_is_wrapped:
        SmolTel.wrap_agent(CodeAgent)
        SmolTel.wrap_agent(MultiStepAgent)
        SmolTel.wrap_tool(FinalAnswerTool)
        SmolTel.wrap_tool(UserInputTool)
        SmolTel.wrap_tool(GoogleSearchTool)
        SmolTel.wrap_tool(DuckDuckGoSearchTool)
        _otel_is_wrapped = True
