"""
Agent Engine Wrappers
------------------------
Wraps each pipeline stage as a LangchainAgent, matching the pattern in
the hackathon-provided notebook (intro_agent_engine.ipynb). This is
what you'd deploy individually to Vertex AI Agent Engine if the
hackathon judging wants to see agents running as actual deployed
Agent Engine resources rather than local function calls.

For the demo itself, running orchestrator.py locally/on Replit is
likely simpler and faster to iterate on — reach for these wrappers
once the pipeline logic is solid and you're ready to show it deployed
on Google Cloud.
"""

from vertexai import agent_engines
from vertexai.preview.reasoning_engines import LangchainAgent

from interpreter import sketch_to_spec
from generator import spec_to_svg
from critic import critique_render

MODEL_NAME = "gemini-3.6-flash"  # confirm current valid model name in Vertex AI Studio

interpreter_agent = LangchainAgent(
    model=MODEL_NAME,
    tools=[sketch_to_spec],
    agent_executor_kwargs={"return_intermediate_steps": True},
)

generator_agent = LangchainAgent(
    model=MODEL_NAME,
    tools=[spec_to_svg],
    agent_executor_kwargs={"return_intermediate_steps": True},
)

critic_agent = LangchainAgent(
    model=MODEL_NAME,
    tools=[critique_render],
    agent_executor_kwargs={"return_intermediate_steps": True},
)


def deploy_all():
    """
    Deploys all three agents to Vertex AI Agent Engine. Run this once
    you've tested each agent locally with .query() and are ready to
    show them as real deployed Agent Engine resources.
    """
    requirements = [
        "google-cloud-aiplatform[agent_engines,langchain]",
        "cloudpickle==3.0.0",
        "pydantic>=2.10",
        "cairosvg",
    ]

    remote_interpreter = agent_engines.create(
        interpreter_agent, requirements=requirements
    )
    remote_generator = agent_engines.create(
        generator_agent, requirements=requirements
    )
    remote_critic = agent_engines.create(critic_agent, requirements=requirements)

    return {
        "interpreter": remote_interpreter,
        "generator": remote_generator,
        "critic": remote_critic,
    }


if __name__ == "__main__":
    deployed = deploy_all()
    for name, remote_agent in deployed.items():
        print(f"{name} deployed: {remote_agent.resource_name}")
