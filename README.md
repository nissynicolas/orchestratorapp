# Person Info Orchestrator API

This project provides a single POST endpoint that intelligently routes requests to the appropriate person information endpoint (name, address, medication, employment details, or salary bracket).

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the app:**
   ```bash
   uvicorn main:app --reload
   ```

## Endpoints

- `POST /person-info` — Main orchestrator endpoint
- `POST /get-name`
- `POST /get-address`
- `POST /get-medication`
- `POST /get-employment-details`
- `POST /get-salary-bracket`

## Example Request

### By type
```json
{
  "type": "address",
  "person_id": "123"
}
```

### By query
```json
{
  "query": "What is the salary bracket for John Doe?"
}
```

## How it works
- The `/person-info` endpoint analyzes the request and routes it to the correct downstream endpoint based on the `type` field or by analyzing the `query` text. 