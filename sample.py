'''
This is just a sample using OCI Response API with API key authentication. It is not intended for production use.
.env file example for local testing of the sample_response_api_key_auth.py script.
OCI_REGION is the OCI region where your Generative AI project is located.
OCI_GENAI_PROJECT_OCID is the OCID of your Generative AI project.
OCI_GENAI_API_KEY is the API key for your Generative AI project. Do not commit
OCI_CHAT_MODEL is the model to use for chat responses. Optional; defaults to openai.gpt-oss-120b.
'''

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

region = os.environ.get("OCI_REGION", "ap-osaka-1")
client = OpenAI(
    base_url=f"https://inference.generativeai.{region}.oci.oraclecloud.com/openai/v1",
    api_key=os.environ["OCI_GENAI_API_KEY"],
    project=os.environ["OCI_GENAI_PROJECT_OCID"],
)
response = client.responses.create(
    model=os.environ.get("OCI_CHAT_MODEL", "openai.gpt-oss-120b"),
    input="Capital of Canada?",
)
print(response.output_text)
