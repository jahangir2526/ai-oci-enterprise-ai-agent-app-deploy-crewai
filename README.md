# OCI Hosted Deployment — Minimal CrewAI Multi-Agent

A stateless FastAPI service that runs a two-agent CrewAI workflow against OCI Generative AI's OpenAI-compatible Responses API. OCI hosts the container and generates the answers. A **Solution Scout** drafts an answer, then a **Clarity Editor** reviews it. Each request creates a fresh crew, with no stored conversation history. The agents have no tools or live-data access.

## Service and files

| Item | Implementation |
| --- | --- |
| API | `POST /chat` with `{"question":"..."}`; JSON answer in `answer` |
| SSE | `Accept: text/event-stream` returns one data event after both agents finish |
| Readiness | `GET /ready`: `200` when the HTTP service is running |
| Liveness | `GET /health`: `200` |
| Probes | Empty body, `Content-Type: application/json`; no model call or credential validation |
| Runtime | Uvicorn on `0.0.0.0:8080`; entry command defined in the Dockerfile |
| Container | `python:3.13-slim`, Linux x86_64 (`linux/amd64`), non-root UID 1000 |
| Filesystem | CrewAI application data uses `/tmp/crewai`; its internal credential-store key is prepared at image build time |

| File | Purpose |
| --- | --- |
| `main.py` | Local launcher for `python main.py` |
| `requirements.txt` | Direct runtime dependencies |
| `src/ai_oci_enterprise_ai_hosted_deployment_crewai/main.py` | HTTP API, probes, JSON/SSE responses, and local entry point |
| `src/ai_oci_enterprise_ai_hosted_deployment_crewai/crews/content_crew/content_crew.py` | Two-agent orchestration and OCI Responses API configuration |
| `src/ai_oci_enterprise_ai_hosted_deployment_crewai/crews/content_crew/config/agents.yaml` | Solution Scout and Clarity Editor roles |
| `src/ai_oci_enterprise_ai_hosted_deployment_crewai/crews/content_crew/config/tasks.yaml` | Draft and review instructions |
| `Dockerfile`, `.dockerignore` | Image definition and build-context exclusions |
| `.env.example` | Local configuration template |
| `tests/test_api.py`, `tests/conftest.py` | Probe, validation, JSON/SSE, crew workflow, and OCI configuration checks |

## 1. Configure the OCI Generative AI API key

Create a Generative AI API key for the OCI project used by the crew, then copy the template (or edit your existing `.env`):

```bash
cp .env.example .env
```

```dotenv
OCI_REGION=us-ashburn-1
OCI_GENAI_PROJECT_OCID=ocid1.generativeaiproject.oc1.<region>.<unique-id>
OCI_GENAI_API_KEY=your-oci-generative-ai-api-key
OCI_CHAT_MODEL=xai.grok-4.3
```

`OCI_GENAI_API_KEY` and `OCI_GENAI_PROJECT_OCID` are required to answer questions. `OCI_REGION` defaults to `us-ashburn-1`; `OCI_CHAT_MODEL` defaults to `xai.grok-4.3`. Choose a model available to the specified project and region. Local `.env` values do not override existing environment variables.

The real `.env` is excluded from Git and the image. Supply credentials at runtime, keeping them out of source code, build arguments, and image tags. Probe success confirms that the HTTP service is running; it does not confirm that the model or API key works.

For `docker run --env-file .env`, use unquoted values such as
`OCI_GENAI_API_KEY=your-key`. Surrounding quotes become part of the value passed
to the container and can cause OCI authentication errors. After editing `.env`,
recreate the container; restarting an existing container keeps its old environment.

### Optional: run locally without Docker

With Python 3.13, from the project root:

CrewAI does not support Python 3.14 in this version. An existing `.venv` keeps
the Python version it was created with. If it uses 3.14, deactivate it and
rename it as a backup before creating the Python 3.13 environment below.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python --version  # Must report Python 3.13.x
python -m pip install -r requirements.txt
python main.py
```

In another terminal:

```bash
curl -i http://localhost:8080/ready
curl -i http://localhost:8080/health

curl -sS -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is the capital of Spain?"}'
```

Interactive API documentation: <http://localhost:8080/docs>.

For automated checks, use the activated environment:

```bash
python -m pip install 'pytest>=8,<9'
python -m pytest -q
```

Tests use stub model responses, disable telemetry and tracing, and do not call OCI.

## 2. Docker | Build the container

```bash
docker buildx build --platform linux/amd64 --provenance=false --sbom=false \
  --load -t crewai-answer-studio:v1 .
```

The build disables provenance and SBOM attestations for this example. Omit those two flags if your image publication workflow requires attestations. See [Docker build attestations](https://docs.docker.com/build/metadata/attestations/).

The official Python Slim base includes Python 3.13 and pip, so the Dockerfile does not install a separate Python runtime or run an OS package update. Dependencies are installed with `python -m pip install -r requirements.txt`; the application source and YAML configuration are copied into the image. The entry command is `python main.py`. CrewAI brings its own transitive dependencies, so the complete image is larger than the base image alone.

Keep direct dependency versions in `requirements.txt`. Both local development and Docker use this file; uv and a package installation of this project are not required. After dependency changes, reinstall, test, and rebuild the image. Docker can reuse its dependency layer when only application code changes.

The image runs as a non-root user, disables bytecode writes and pip caching, and directs CrewAI application data to `/tmp`. Its build-time internal credential-store key is separate from your OCI API key. OCI uses the HTTP probes; no Docker `HEALTHCHECK` or persistent conversation storage is needed.

## 3. Docker | Test locally

```bash
docker run --rm -p 8080:8080 --env-file .env crewai-answer-studio:v1
```

In another terminal:

```bash
curl -i http://localhost:8080/ready
curl -i http://localhost:8080/health

curl -sS -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is the capital of Malaysia?"}'
```

Example answer (wording may vary):

```json
{"answer":"The capital of Malaysia is Kuala Lumpur."}
```

For SSE:

```bash
curl -N -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d '{"question":"What is the capital of Bhutan?"}'
```

```text
data: {"answer": "The capital of Bhutan is Thimphu."}

```

JSON and SSE return the same reviewed answer. SSE sends the full answer as one data event after generation, without intermediate agent tokens or a named `completed` event. Questions must contain between 1 and 4,000 characters; missing, empty, or overlong questions return HTTP `422`.

### Ready-to-use sample prompts

Use these JSON bodies with local `curl -d` or deployed `oci raw-request --request-body`:

```json
{"question":"Explain vector databases using a coffee shop analogy."}
{"question":"Why do multi-agent systems use specialized roles? Give one practical example."}
{"question":"Suggest three OCI Generative AI use cases for a regional bank, including the benefit and main risk of each."}
{"question":"Compare containers and serverless functions for hosting an AI agent in five concise points."}
```

Send one JSON object per request.

## 4. Push to Oracle Container Registry

Create a repository in OCI Console, for example `repo-oci-crewai-agent`, then replace the registry, namespace, and repository placeholders:

```bash
docker login <region-key>.ocir.io
docker tag crewai-answer-studio:v1 <region-key>.ocir.io/<tenancy-namespace>/<repository>:v1
docker push <region-key>.ocir.io/<tenancy-namespace>/<repository>:v1
```

For Ashburn, use `iad.ocir.io`. Example image path: `iad.ocir.io/<tenancy-namespace>/repo-oci-crewai-agent:v1`. Supply the Generative AI API key separately at runtime.

## 5. Deploy and invoke on OCI

1. In **Generative AI > Applications**, select an existing application or create one.
2. In the application's environment configuration, set `OCI_GENAI_API_KEY`, `OCI_GENAI_PROJECT_OCID`, `OCI_REGION`, and optionally `OCI_CHAT_MODEL`.
3. Create a deployment using the OCIR image from section 4.
4. Allow outbound HTTPS to `inference.generativeai.<region>.oci.oraclecloud.com`, use port `8080`, and confirm `/ready` and `/health` succeed.
5. Wait for the deployment to become active. Copy the Console-provided application endpoint and append `/chat`; the final path ends in `/actions/invoke/chat`.

Match requests to the application's authentication setting. Use the Console endpoint without changing its resource type. [OCI invocation guidance](https://docs.oracle.com/en-us/iaas/Content/generative-ai/use-applications.htm) explains the supported authentication methods.

### 5.1 Test

The Console application endpoint ends in `/actions/invoke`. Append the container route: `/health`, `/ready`, or `/chat`.

#### 5.1.1 No authentication

If the application has **Authentication type: No Authentication**:

```bash
curl -i '<console-application-endpoint-ending-in-actions/invoke>/health'

curl -N -X POST '<console-application-endpoint-ending-in-actions/invoke>/chat' \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d '{"question":"What is the capital of Luxembourg?"}'
```

#### 5.1.2 OCI IAM authentication

For an OCI IAM application with API-key request signing:

```bash
oci raw-request \
  --profile DEFAULT \
  --auth api_key \
  --http-method POST \
  --target-uri '<console-application-endpoint-ending-in-actions/invoke>/chat' \
  --request-headers '{"content-type":"application/json"}' \
  --request-body '{"question":"What is the capital of Bangladesh?"}'
```

OCI IAM endpoints contain `hostedApplicationsIam`. Identity-domain bearer-token endpoints contain `hostedApplications`; use a valid OAuth bearer token for those requests. Inbound application authentication is separate from the outbound `OCI_GENAI_API_KEY` used for model calls.

**HTTP 404 (`{"detail":"Not Found"}`):** check that the request URL ends in `/actions/invoke/chat`. After changing a route, rebuild, push a new image tag, and activate its deployment. The deployed `/actions/invoke/docs` route shows the API schema, subject to the application's authentication settings.

## References

- [CrewAI documentation](https://docs.crewai.com/)
- [Official Python container image](https://hub.docker.com/_/python)
- [OCI container requirements](https://docs.oracle.com/en-us/iaas/Content/generative-ai/prepare-artifacts.htm)
- [OCI hosted applications and deployments](https://docs.oracle.com/en-us/iaas/Content/generative-ai/applications-deployments.htm)
- [OCI application invocation](https://docs.oracle.com/en-us/iaas/Content/generative-ai/use-applications.htm)
