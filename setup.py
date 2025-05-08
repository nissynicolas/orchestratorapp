from setuptools import setup, find_packages

setup(
    name="fhir-resource-router",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn>=0.24.0",
        "langchain>=0.0.350",
        "langchain-community>=0.0.10",
        "python-dotenv>=1.0.0",
        "openai>=1.3.5",
        "requests>=2.31.0",
        "fhir.resources>=7.0.2",
        "pydantic>=1.9.0,<2.0.0",
        "python-multipart>=0.0.6",
    ],
    python_requires=">=3.8",
) 