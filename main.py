from fastapi import FastAPI, Request
import requests
from typing import Dict
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
import os
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

# Set your OpenAI API key (ensure this is set in your environment for production)
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "sk-proj-1234")

# LLM-based intent classification using LangChain
prompt = PromptTemplate(
    input_variables=["input"],
    template="""
    Classify the following request into one of the following categories: name, address, medication, employment, salary.
    Only return the category name.
    Request: {input}
    """
)
llm = OpenAI(temperature=0)

def classify_intent_llm(input_text: str) -> str:
    chain = prompt | llm
    result = chain.invoke({"input": input_text})
    return result.strip().lower()

# Routing function (uses LLM if 'query' is present)
def classify_intent(input_data: Dict) -> str:
    if "type" in input_data:
        return input_data["type"].lower()
    elif "query" in input_data:
        # Use LLM for intent classification
        return classify_intent_llm(input_data["query"])
    return "unknown"

# Dummy downstream endpoints
@app.post("/get-name")
def get_name(data: Dict):
    return {"name": "John Doe"}

@app.post("/get-address")
def get_address(data: Dict):
    return {"address": "123 Main St"}

@app.post("/get-medication")
def get_medication(data: Dict):
    return {"medication": "Aspirin"}

@app.post("/get-employment-details")
def get_employment_details(data: Dict):
    return {"employment": "Engineer"}

@app.post("/get-salary-bracket")
def get_salary_bracket(data: Dict):
    return {"salary_bracket": "50k-60k"}

class PersonInfoRequest(BaseModel):
    type: Optional[str] = None
    query: Optional[str] = None
    person_id: Optional[str] = None

@app.post("/person-info")
async def person_info(data: PersonInfoRequest):
    data_dict = data.dict(exclude_none=True)
    intent = classify_intent(data_dict)
    endpoint_map = {
        "name": "get-name",
        "address": "get-address",
        "medication": "get-medication",
        "employment": "get-employment-details",
        "salary": "get-salary-bracket"
    }
    endpoint = endpoint_map.get(intent)
    if not endpoint:
        return {"error": "Unknown intent"}
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.post(f"/{endpoint}", json=data_dict)
    return response.json() 
