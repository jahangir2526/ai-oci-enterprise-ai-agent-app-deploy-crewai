# OCI Generative AI Hosted Deployment — Minimal CrewAI Multi-Agent Responses Agent

This is a minimal, stateless FastAPI and CrewAI multi-agent service for an
**existing** OCI Generative AI hosted application. It follows the API-key
authentication pattern in `sample.py` and calls OCI's OpenAI-compatible
Responses API. A **Solution Scout** drafts the answer and a **Clarity Editor**
reviews it before the service returns the final response.

## OCI requirement checklist

| OCI requirement | Implementation |
| ----------------------------- | -------------------------------------------------------- |
| HTTP service | FastAPI `POST /invoke` |
| Host and port | Uvicorn listens on `0.0.0.0:8080` |
| Readiness probe | `GET /ready` returns `200` |
| Liveness probe | `GET /health` returns `200` |
| Normal response | JSON response from `POST /invoke` |
| Streaming response | One completed SSE event when `Accept: text/event-stream` is supplied |
| Supported image architecture | Build with `--platform linux/amd64` |
| Image entry command | Defined by `CMD` in `Dockerfile` |
| Container writes | The crew is stateless; CrewAI internal mutable state is directed to `/tmp` |

## Files

| File | Purpose |
| ------------------------------ | ------------------------------------------------------- |
| `sample.py` | Supplied working OCI API-key reference code |
| `src/ai_oci_enterprise_ai_hosted_deployment_crewai/main.py` | Hosted FastAPI service |
| `src/ai_oci_enterprise_ai_hosted_deployment_crewai/crews/content_crew/content_crew.py` | Two-agent CrewAI orchestration |
| `src/ai_oci_enterprise_ai_hosted_deployment_crewai/crews/content_crew/config/agents.yaml` | Solution Scout and Clarity Editor definitions |
| `src/ai_oci_enterprise_ai_hosted_deployment_crewai/crews/content_crew/config/tasks.yaml` | Draft and review task definitions |
| `requirements.txt` | Runtime dependencies |
| `Dockerfile` | OCI-compatible container image |
| `.dockerignore` | Prevents credentials and local files entering the image |
| `.env.example` | Local configuration template |

## 1. Obtain the OCI Generative AI API key

Create an OCI Generative AI API key for the Generative AI project used by this
crew and give the key only the permissions it needs. Keep the key secret.

The deployment needs these variables:

```text
OCI_REGION=us-ashburn-1
OCI_GENAI_PROJECT_OCID=ocid1.generativeaiproject.oc1.<region>.<unique-id>
OCI_GENAI_API_KEY=<oci-generative-ai-api-key>
OCI_CHAT_MODEL=xai.grok-4.3
```

`OCI_CHAT_MODEL` is optional and defaults to `xai.grok-4.3`. `OCI_REGION`
defaults to `us-ashburn-1`. Use a model available to the specified project and
region. Do not place `OCI_GENAI_API_KEY` in source code, an image tag, the
Dockerfile, or a Docker build argument. Store the API-key value in your approved
secrets manager and enter it only through the application's protected
configuration workflow.

For local testing, copy the template and replace its placeholders:

```bash
cp .env.example .env
```

The real `.env` file is excluded from Git and from the container image.

## 2. Build the amd64 container image

OCI Hosted Deployments accept `linux/amd64` images. From this directory:

```bash
docker buildx build \
  --platform linux/amd64 \
  --load \
  -t crewai-answer-studio:v1 .
```

The image uses Oracle Linux 9 Slim, runs as a non-root user, and starts the
service on `0.0.0.0:8080` through the Dockerfile `CMD`.

## 3. Test the container locally

Run the image by passing configuration at runtime. Substitute actual values
only in your local `.env`; never add the key to a command history shared with
others.

```bash
docker run --rm \
  -p 8080:8080 \
  --env-file .env \
  crewai-answer-studio:v1
```

In another terminal, check OCI's required probes:

```bash
curl -i http://localhost:8080/ready
curl -i http://localhost:8080/health
```

Make a standard JSON request:

```bash
curl -sS -X POST http://localhost:8080/invoke \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is OCI Generative AI?"}'
```

Request a Server-Sent Events response:

```bash
curl -N -X POST http://localhost:8080/invoke \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d '{"question":"Explain OCI in one paragraph."}'
```

This minimal implementation completes the two CrewAI tasks first and then
returns the final answer as one SSE event; it does not stream intermediate agent
tokens.

### Ready-to-use sample prompts

Use any of these request bodies with the local `curl` command or the deployed
`oci raw-request` command:

```bash
--request-body '{"question":"Explain vector databases using a coffee shop analogy."}'

--request-body '{"question":"Why do multi-agent systems use specialized roles? Give one practical example."}'

--request-body '{"question":"Suggest three OCI Generative AI use cases for a regional bank, including the benefit and main risk of each."}'

--request-body '{"question":"Compare containers and serverless functions for hosting an AI agent in five concise points."}'

--request-body '{"question":"Create a troubleshooting checklist for an AI API that has suddenly become slow."}'

--request-body '{"question":"Write a 60-second executive explanation of why reviewed AI answers can be more reliable than a single model response."}'
```

For `curl`, place the selected JSON value after `-d` instead of using the
`--request-body` option.

## 4. Push the image to Oracle Container Registry

Replace the placeholders with the registry region key, tenancy namespace,
repository, and tag:

```bash
docker login <region-key>.ocir.io
docker tag crewai-answer-studio:v1 \
  <region-key>.ocir.io/<tenancy-namespace>/<repository>:v1
docker push <region-key>.ocir.io/<tenancy-namespace>/<repository>:v1
```

For the Ashburn region, the registry host is `iad.ocir.io`. If the target
registry is in another region, use that region's OCIR key.

## 5. Create a deployment for the existing application

1. In OCI Console, go to **Generative AI > Applications** and select the
   existing application.
2. Open **Deployments** and create a deployment using the OCIR image pushed in
   step 4.
3. In the application **Environment** section, add `OCI_REGION`,
   `OCI_GENAI_PROJECT_OCID`, `OCI_GENAI_API_KEY`, and optionally
   `OCI_CHAT_MODEL` as environment-variable key/value pairs. Enter the API-key
   value from your approved secrets manager; do not commit it to this
   repository.
4. Verify that the deployment has outbound network access to the OCI Generative
   AI inference endpoint. The default service-managed network provides public
   egress.
5. Create the deployment and wait until its lifecycle state is **Active**. OCI
   calls `/ready` before sending traffic and monitors `/health`.
6. Copy the application endpoint, append `/invoke`, and invoke it using the
   inbound authentication configured for the existing application:

   ```bash
   oci raw-request \
     --profile DEFAULT \
     --auth api_key \
     --http-method POST \
     --target-uri '<deployment-endpoint>/invoke' \
     --request-headers '{"content-type":"application/json"}' \
     --request-body '{"question":"What is the capital of Bhutan?"}'
   ```

   Replace the value passed to `--request-body` with any example from
   **Ready-to-use sample prompts** in section 3, or supply your own question
   using the same `{"question":"..."}` JSON structure.

OCI provisions an endpoint for the active deployment. Its console-provided base
URL is authoritative; append the agent route `/invoke` to that base URL.

## References

- [Preparing Container Images](https://docs.oracle.com/en-us/iaas/Content/generative-ai/prepare-artifacts.htm)
- [Hosted Applications and Deployments](https://docs.oracle.com/en-us/iaas/Content/generative-ai/applications-deployments.htm)
