from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import requests
from langchain_openai import OpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from fhir.resources.claim import Claim
from fhir.resources.patient import Patient
from fhir.resources.encounter import Encounter
from fhir.resources.procedure import Procedure
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="FHIR Resource Router",
    description="An intelligent FHIR resource routing system using LangChain",
    version="1.0.0"
)

# HAPI FHIR server base URL
HAPI_FHIR_BASE_URL = "https://hapi.fhir.org/baseR4"

# Initialize OpenAI
llm = OpenAI(temperature=0, openai_api_key=os.getenv("OPENAI_API_KEY"))

class ClaimBundle(BaseModel):
    resource_type: str
    requested_resource: str
    claim_data: Dict[str, Any]

class ResourceResponse(BaseModel):
    resource_type: str
    data: Dict[str, Any]

def extract_reference_id(reference: str) -> str:
    """Extract the ID from a FHIR reference string."""
    return reference.split('/')[-1] if '/' in reference else reference

def fetch_fhir_resource(resource_type: str, resource_id: str) -> Dict[str, Any]:
    """Fetch a FHIR resource from the HAPI FHIR server."""
    url = f"{HAPI_FHIR_BASE_URL}/{resource_type}/{resource_id}"
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Error fetching {resource_type}")
    return response.json()

def get_patient_info(patient_ref: str) -> Dict[str, Any]:
    """Get patient information from the reference."""
    patient_id = extract_reference_id(patient_ref)
    return fetch_fhir_resource("Patient", patient_id)

def get_encounter_info(encounter_ref: str) -> Dict[str, Any]:
    """Get encounter information from the reference."""
    try:
        # Extract just the ID from the reference
        if isinstance(encounter_ref, dict):
            encounter_ref = encounter_ref.get('id', '')
        elif isinstance(encounter_ref, str):
            # If the input contains a JSON-like string, extract just the ID
            if '{' in encounter_ref:
                encounter_ref = encounter_ref.split('{')[0].strip()
            # Remove any additional text after the ID
            encounter_ref = encounter_ref.split()[0].strip()
            # Ensure we only have the reference ID
            if '/' in encounter_ref:
                encounter_ref = encounter_ref.split('/')[-1]
        encounter_id = extract_reference_id(encounter_ref)
        return fetch_fhir_resource("Encounter", encounter_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing encounter reference: {str(e)}")

def get_procedure_info(procedure_ref: str) -> Dict[str, Any]:
    """Get procedure information from the reference."""
    procedure_id = extract_reference_id(procedure_ref)
    return fetch_fhir_resource("Procedure", procedure_id)

# Define LangChain tools with more detailed descriptions
tools = [
    Tool(
        name="get_patient",
        func=get_patient_info,
        description="""Use this tool when you need to get patient information. This includes:
        - Patient demographics
        - Personal information
        - Medical record details
        - Patient history
        - Patient profile
        Input should be the patient reference from the claim bundle."""
    ),
    Tool(
        name="get_encounter",
        func=get_encounter_info,
        description="""Use this tool when you need to get encounter information. This includes:
        - Visit details
        - Hospital stay information
        - Medical visit records
        - Treatment episodes
        - Care encounters
        - Hospital information
        Input should be just the encounter reference ID (e.g., 'Encounter/12345'). Do not include any additional data."""
    ),
    Tool(
        name="get_procedure",
        func=get_procedure_info,
        description="""Use this tool when you need to get procedure information. This includes:
        - Medical procedures
        - Surgical operations
        - Treatment procedures
        - Medical interventions
        - Clinical procedures
        Input should be the procedure reference from the claim bundle."""
    )
]

# Create a custom prompt template for the ReAct agent
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an intelligent FHIR resource routing system. Your task is to understand the user's request and determine which FHIR resource to fetch.

Available tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action (ONLY the reference ID, e.g., '598285')
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Remember:
1. For Action, use ONLY the tool name from the list [{tool_names}]
2. For Action Input, use ONLY the reference ID without any additional text
3. Do not include any explanations in the Action or Action Input fields
4. You must always choose one of the available tools
5. Never use None as an action or input
6. Never include the full resource data in the Action Input
7. For encounter references, use ONLY the ID part (e.g., '598285' instead of the full reference)

{agent_scratchpad}"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])

# Create the agent using the custom prompt
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    return_intermediate_steps=True,
    max_iterations=2  # Limit to 2 iterations to prevent infinite loops
)

@app.post("/claim-bundle", response_model=ResourceResponse)
async def process_claim_bundle(bundle: ClaimBundle):
    """
    Process a FHIR Claim bundle and route to appropriate resource endpoint based on requested_resource.
    The requested_resource can be in natural language, and the system will intelligently determine the correct endpoint.
    """
    try:
        # Extract references from the claim bundle
        patient_ref = bundle.claim_data.get('patient', {}).get('reference', 'Not found')
        encounter_ref = bundle.claim_data.get('item', [{}])[0].get('encounter', [{}])[0].get('reference', 'Not found')
        procedure_ref = bundle.claim_data.get('procedure', [{}])[0].get('procedureReference', {}).get('reference', 'Not found')
        
        # Prepare the input for the agent
        agent_input = {
            "input": f"""
            Based on the following request, determine which FHIR resource to fetch and extract the appropriate reference from the claim bundle.
            
            Request: {bundle.requested_resource}
            
            Available references in the claim bundle:
            - Patient: {patient_ref}
            - Encounter: {encounter_ref}
            - Procedure: {procedure_ref}
            
            You must choose one of the following tools to fetch the resource:
            - get_patient: for patient information
            - get_encounter: for encounter/hospital information
            - get_procedure: for procedure information
            
            Use the appropriate tool to fetch the resource. Only use the reference ID as input (e.g., '598285' for Encounter/598285).
            Do not include any additional data or the full resource in the input.
            After getting the resource, provide a final answer.
            """,
            "chat_history": [],
            "agent_scratchpad": ""
        }
        
        # Run the agent
        result = agent_executor.invoke(agent_input)
        
        # Check if we have intermediate steps
        if "intermediate_steps" in result and result["intermediate_steps"]:
            # Get the last action and its result
            last_action, last_result = result["intermediate_steps"][-1]
            if last_result:
                return ResourceResponse(
                    resource_type=last_action.tool,
                    data=last_result
                )
        
        # If no intermediate steps or result, try to determine resource type from output
        resource_type = None
        output = result.get("output", "").lower()
        
        # More sophisticated resource type detection
        if any(term in output for term in ["patient", "demographic", "personal information", "medical record", "patient history", "patient profile"]):
            resource_type = "patient"
        elif any(term in output for term in ["encounter", "visit", "hospital stay", "medical visit", "treatment episode", "care encounter", "hospital"]):
            resource_type = "encounter"
        elif any(term in output for term in ["procedure", "surgical", "operation", "treatment procedure", "medical intervention", "clinical procedure"]):
            resource_type = "procedure"
            
        if not resource_type:
            raise HTTPException(status_code=400, detail="Could not determine resource type from request. Please be more specific about what information you need.")
            
        # Extract the appropriate reference based on the resource type
        if resource_type == "patient":
            if patient_ref == "Not found":
                raise HTTPException(status_code=400, detail="Patient reference not found in claim")
            resource_data = get_patient_info(patient_ref)
            
        elif resource_type == "encounter":
            if encounter_ref == "Not found":
                raise HTTPException(status_code=400, detail="Encounter reference not found in claim")
            resource_data = get_encounter_info(encounter_ref)
            
        elif resource_type == "procedure":
            if procedure_ref == "Not found":
                raise HTTPException(status_code=400, detail="Procedure reference not found in claim")
            resource_data = get_procedure_info(procedure_ref)
            
        return ResourceResponse(
            resource_type=resource_type,
            data=resource_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
