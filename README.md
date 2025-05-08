# FHIR Resource Router with LangChain

An intelligent FHIR resource routing system that uses LangChain to process FHIR Claim bundles and fetch related resources from a HAPI FHIR server.

## Features

- Intelligent routing using LangChain
- Support for FHIR resources:
  - Patient
  - Encounter
  - Procedure
- Automatic reference extraction from Claim bundles
- Integration with HAPI FHIR server

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- Windows:
```bash
.\venv\Scripts\activate
```
- Unix/MacOS:
```bash
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Running the Application

```bash
uvicorn main:app --reload
```

The application will be available at `http://localhost:8000`

## API Usage

### POST /claim-bundle

Process a FHIR Claim bundle and retrieve related resources.

Example request:
```json
{
    "resource_type": "Claim",
    "requested_resource": "Patient",
    "claim_data": {
        "patient": {
            "reference": "Patient/12345",
            "display": "John Doe"
        },
        "encounter": [
            {
                "reference": "Encounter/67890"
            }
        ],
        "procedure": [
            {
                "sequence": 1,
                "procedureReference": {
                    "reference": "Procedure/11111"
                }
            }
        ]
    }
}
```

The application will:
1. Use LangChain to determine the appropriate routing based on the requested_resource
2. Extract the relevant reference from the claim_data
3. Fetch the requested resource from the HAPI FHIR server
4. Return the resource data

## API Documentation

Access the Swagger UI documentation at `http://localhost:8000/docs` 