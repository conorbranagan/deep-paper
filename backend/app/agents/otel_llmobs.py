import json
from typing import Any
import logging
from contextlib import contextmanager

from smolagents.agent_types import AgentText, AgentImage, AgentAudio
from smolagents import (
    CodeAgent,
    MultiStepAgent,
    FinalAnswerTool,
    UserInputTool,
    GoogleSearchTool,
    DuckDuckGoSearchTool,
    ChatMessage,
    LiteLLMModel,
)
from opentelemetry import trace
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry import context as context_api
from opentelemetry.semconv_ai import SpanAttributes, TraceloopSpanKindValues
from opentelemetry.instrumentation.openai import OpenAIInstrumentor

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

KNOWN_KWARGS = {
    "temperature",
    "vertex_credentials",
}


def _set_attribute(span: trace.Span, key: str, attribute: Any):
    if isinstance(attribute, ChatMessage):
        # the `raw` data can't be serialized so let's remove it.
        attribute.raw = None
        span.set_attribute(key, json.dumps(attribute.dict()))
    elif isinstance(attribute, (dict, list)):
        span.set_attribute(key, json.dumps(attribute))
    elif isinstance(attribute, (int, float, bool)):
        span.set_attribute(key, attribute)
    else:
        span.set_attribute(key, str(attribute))


def _start_span(name: str, kind: TraceloopSpanKindValues):
    """Create and set up a span as a context manager"""

    @contextmanager
    def span_context():
        span = tracer.start_span(f"{name}.{kind.value}")
        ctx = trace.set_span_in_context(span)
        ctx_token = context_api.attach(ctx)
        span.set_attribute(SpanAttributes.TRACELOOP_SPAN_KIND, kind.value)
        span.set_attribute(SpanAttributes.TRACELOOP_ENTITY_NAME, name)
        try:
            yield span
        finally:
            span.end()
            context_api.detach(ctx_token)

    return span_context()


def _attach_parent_span(model, span: trace.Span):
    if isinstance(model, LiteLLMModel):
        # FIXME: This could cause issues if kwargs is already set but
        # when I try to use existing kwargs it pulls in extra information
        # that causes issues.
        model.kwargs = {
            "metadata": {"litellm_parent_otel_span": span},
            **{k: v for k, v in model.kwargs.items() if k in KNOWN_KWARGS},
        }
    else:
        log.warning("unsupported model type for SmolTel: %s", type(model))


def _detach_parent_span(model):
    if isinstance(model, LiteLLMModel):
        model.kwargs = model.kwargs.pop("metadata", None)
    else:
        log.warning("unsupported model type for SmolTel: %s", type(model))


class SmolTel:
    """A utility class for providing Datadog LLM Obs wrapping for Tools and Agents from the smolagents library"""

    @staticmethod
    def wrap_tool(cls):
        original_forward = cls.forward

        def wrapped_forward(self, *args, **kwargs):
            with _start_span(self.name, TraceloopSpanKindValues.TOOL) as span:
                for k, v in kwargs.items():
                    _set_attribute(span, f"tool_input.{k}", v)
                try:
                    result = original_forward(self, *args, **kwargs)
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise e

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
            with _start_span("action", TraceloopSpanKindValues.TASK) as span:
                step_meta = memory_step.dict()
                _set_attribute(
                    span,
                    "input_data",
                    step_meta.pop("model_input_messages"),
                )
                _set_attribute(
                    span,
                    "output_data",
                    step_meta.pop("model_output_message"),
                )
                for k, v in step_meta.items():
                    _set_attribute(span, f"metadata.{k}", v)
                _attach_parent_span(self.model, span)
                try:
                    res = original_step(self, memory_step)
                finally:
                    _detach_parent_span(self.model)
                return res

        def wrapped_planning_step(self, *args, **kwargs):
            with _start_span("planning", TraceloopSpanKindValues.TASK) as span:
                _attach_parent_span(self.model, span)
                try:
                    return original_planning_step(self, *args, **kwargs)
                finally:
                    _detach_parent_span(self.model)

        def wrapped_final_answer(self, *args, **kwargs):
            with _start_span("final_answer", TraceloopSpanKindValues.TASK) as span:
                _attach_parent_span(self.model, span)
                try:
                    _set_attribute(
                        span,
                        "input_data",
                        args[0] if len(args) > 0 else "",
                    )
                    answer = original_final_answer(self, *args, **kwargs)
                    _set_attribute(span, "output_data", answer)
                    return answer
                finally:
                    _detach_parent_span(self.model)

        def wrapped_run(self, *args, **kwargs):
            llmbos_metadata = {
                "task": args[0] or kwargs.get("task") or "unset task",
                "max_steps": kwargs.get("max_steps") or 0,
                "stream": kwargs.get("stream") or False,
                "reset": kwargs.get("reset") or False,
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
                if self.name:
                    agent_name = f"{self.name} (smolagents)"

                with _start_span(agent_name, TraceloopSpanKindValues.AGENT) as span:
                    output = original_run(self, *args, **kwargs)
                    _set_attribute(span, "input_data", llmbos_metadata["task"])
                    _set_attribute(span, "output_data", output)
                    for k, v in llmbos_metadata.items():
                        _set_attribute(span, f"metadata.{k}", v)
                return output

        def _wrapped_run_stream(self, *args, llmbos_metadata, **kwargs):
            # When it's a stream we have to wrap the generator. We pick the last
            # value to come out as our potential output and cast it to str if it's a known type.
            agent_name = "smolagents_agent"
            if self.name:
                agent_name = f"{self.name} (smolagents)"
            with _start_span(agent_name, TraceloopSpanKindValues.AGENT) as span:
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
        OpenAIInstrumentor().instrument()
        SmolTel.wrap_agent(CodeAgent)
        SmolTel.wrap_agent(MultiStepAgent)
        SmolTel.wrap_tool(FinalAnswerTool)
        SmolTel.wrap_tool(UserInputTool)
        SmolTel.wrap_tool(GoogleSearchTool)
        SmolTel.wrap_tool(DuckDuckGoSearchTool)
        _otel_is_wrapped = True
