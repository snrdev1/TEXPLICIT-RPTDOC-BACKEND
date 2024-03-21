# libraries
from __future__ import annotations

import json
import logging
from typing import List, Optional

from colorama import Fore, Style
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.utils.validator import Subtopics

from ..config.config import Config
from ..master.prompts import auto_agent_instructions

CFG = Config()


async def create_chat_completion(
    messages: list,  # type: ignore
    model: Optional[str] = None,
    temperature: float = 1.0,
    max_tokens: Optional[int] = None,
    llm_provider: Optional[str] = None,
    stream: Optional[bool] = False,
    websocket=None,
) -> str:
    """Create a chat completion using the OpenAI API
    Args:
        messages (list[dict[str, str]]): The messages to send to the chat completion
        model (str, optional): The model to use. Defaults to None.
        temperature (float, optional): The temperature to use. Defaults to 0.9.
        max_tokens (int, optional): The max tokens to use. Defaults to None.
        stream (bool, optional): Whether to stream the response. Defaults to False.
        llm_provider (str, optional): The LLM Provider to use.
        webocket (WebSocket): The websocket used in the currect request
    Returns:
        str: The response from the chat completion
    """

    # validate input
    if model is None:
        raise ValueError("Model cannot be None")
    if max_tokens is not None and max_tokens > 8001:
        raise ValueError(
            f"Max tokens cannot be more than 8001, but got {max_tokens}")

    # create response
    for _ in range(10):  # maximum of 10 attempts
        if llm_provider == "Google":
            response = await send_google_chat_completion_request(
                messages, model, temperature, max_tokens, stream, llm_provider, websocket
            )
        else:
            response = await send_oepnai_chat_completion_request(
                messages, model, temperature, max_tokens, stream, llm_provider, websocket
            )

        return response

    logging.error("Failed to get response from OpenAI API")
    raise RuntimeError("Failed to get response from OpenAI API")


def convert_messages(messages):
    """
    The function `convert_messages` converts messages based on their role into either SystemMessage or
    HumanMessage objects.

    :param messages: It seems like the code snippet you provided is a function called `convert_messages`
    that takes a list of messages as input and converts each message based on its role into either a
    `SystemMessage` or a `HumanMessage`. However, the definition of `SystemMessage` and `HumanMessage`
    classes
    :return: The `convert_messages` function is returning a list of converted messages where each
    message is an instance of either `SystemMessage` or `HumanMessage` based on the role specified in
    the input messages.
    """
    converted_messages = []
    for message in messages:
        if message["role"] == "system":
            converted_messages.append(
                SystemMessage(content=message["content"]))
        elif message["role"] == "user":
            converted_messages.append(HumanMessage(content=message["content"]))

    return converted_messages


async def send_google_chat_completion_request(
    messages, model, temperature, max_tokens, stream, llm_provider, websocket=None
):
    print(f"🤖 Calling {model}...")

    llm = ChatGoogleGenerativeAI(
        model=model, 
        convert_system_message_to_human=True,
        temperature=temperature, 
        max_output_tokens=max_tokens
    )
    
    converted_messages = convert_messages(messages)
    result = llm.invoke(converted_messages)

    return result.content

async def send_oepnai_chat_completion_request(
    messages, model, temperature, max_tokens, stream, llm_provider, websocket=None
):
    print(f"\n🤖 Calling {model}...\n")
    
    if not stream:        
        chat = ChatOpenAI(
            model=model, 
            temperature=temperature,
            max_tokens=max_tokens
        )

        output = await chat.ainvoke(messages)
        
        return output.content
        
    else:
        return await stream_response(
            model, messages, temperature, max_tokens, llm_provider, websocket
        )

async def stream_response(
    model, messages, temperature, max_tokens, llm_provider, websocket=None
):
    print(f"\n🤖 Calling {model}...\n")
    
    chat = ChatOpenAI(
        model=model, 
        temperature=temperature,
        max_tokens=max_tokens
    )

    paragraph = ""
    response = ""
    
    async for chunk in chat.astream(messages):
        content = chunk.content
        if content is not None:
            response += content
            paragraph += content
            if "\n" in paragraph:
                if websocket is not None:
                    await websocket.send_json({"type": "report", "output": paragraph})
                else:
                    print(f"{Fore.GREEN}{paragraph}{Style.RESET_ALL}")
                paragraph = ""
                
    return response


async def choose_agent(query, cfg):
    """
    Chooses the agent automatically
    Args:
        query: original query
        cfg: Config

    Returns:
        agent: Agent name
        agent_role_prompt: Agent role prompt
    """
    try:
        response = await create_chat_completion(
            model=cfg.smart_llm_model,
            messages=[
                {"role": "system", "content": f"{auto_agent_instructions()}"},
                {"role": "user", "content": f"task: {query}"}],
            temperature=0,
            llm_provider=cfg.llm_provider
        )
        agent_dict = json.loads(response)

        return agent_dict["agent"], agent_dict["agent_role_prompt"]
    except Exception as e:
        print("Exception : ", e)
        return "Default Agent", "You are an AI critical thinker research assistant. Your sole purpose is to write well written, critically acclaimed, objective and structured reports on given text."


async def construct_subtopics(task: str, data: str, source: str, subtopics: list = []) -> list:
    try:
        parser = PydanticOutputParser(pydantic_object=Subtopics)

        prompt = PromptTemplate(
            template="""
                Provided the main topic:
                
                {task}
                
                and research data:
                
                {data}
                
                - Construct a list of subtopics which indicate the headers of a report document to be generated on the task. 
                - Default value of source: {source}
                - You MUST retain these subtopics along with their sources : {subtopics}.
                - There should NOT be any duplicate subtopics.
                - Limit the number of subtopics to a maximum of 10 (can be lower)
                - Finally order the subtopics by their tasks, in a relevant and meaningful order which is presentable in a detailed report
                
                {format_instructions}
            """,
            input_variables=["task", "data", "source", "subtopics"],
            partial_variables={
                "format_instructions": parser.get_format_instructions()},
        )

        print(f"\n🤖 Calling {CFG.smart_llm_model}...\n")

        model = ChatOpenAI(model=CFG.smart_llm_model)

        chain = prompt | model | parser

        output = chain.invoke({
            "task": task,
            "data": data,
            "source": source,
            "subtopics": subtopics
        })

        return output

    except Exception as e:
        print("Exception in parsing subtopics : ", e)
        return subtopics