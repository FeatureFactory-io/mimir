# Activity: Create Helm Chart & Values

**Activity ID**: 82
**Order**: 2
**Phase**: Elaboration
**Dependencies**: Predecessor: Activity 81 (Review SAO & Define CICD Requirements)

## Description

Create Helm Chart & Values

## Guidance

# Create Deployment Manifest

## Objective

Create a versioned, per-environment deployment artifact that CI/CD uses to deploy the application. The artifact format depends on your deployment style (from Activity #74): Helm chart for Kubernetes/EKS, or Docker Compose template for Elastic Beanstalk.

---

## Process

### Path Selection

Refer to `docs/architecture/INFRA_REQUIREMENTS.md` § Deployment Style. Follow the path for your chosen style.

---

## Kubernetes / EKS Path

**Skill**: K8s in EKS Deployment Patterns (#23)

### 1. Create Helm Chart Structure

```bash
mkdir -p deploy/helm/{project}/templates
```

### 2. Create Chart.yaml

```yaml
# deploy/helm/{project}/Chart.yaml
apiVersion: v2
name: {project}
description: Helm chart for {project} application
type: application
version: 0.1.0
appVersion: "0.1.0"
```

### 3. Create Templates

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
  namespace: {{ .Values.namespace | default .Release.Namespace }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app: {{ .Release.Name }}
    spec:
      containers:
        - name: app
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - containerPort: {{ .Values.service.targetPort }}
          envFrom:
            - configMapRef:
                name: {{ .Release.Name }}-config
          livenessProbe:
            httpGet:
              path: /health
              port: {{ .Values.service.targetPort }}
            initialDelaySeconds: 15
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: {{ .Values.service.targetPort }}
            initialDelaySeconds: 5
            periodSeconds: 5
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
```

**service.yaml:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ .Release.Name }}
  namespace: {{ .Values.namespace | default .Release.Namespace }}
spec:
  type: {{ .Values.service.type }}
  selector:
    app: {{ .Release.Name }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
```

**configmap.yaml:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Release.Name }}-config
  namespace: {{ .Values.namespace | default .Release.Namespace }}
data:
  {{- range $key, $value := .Values.config }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}
```

### 4. Create Values Files

**values.yaml** (defaults):
```yaml
replicaCount: 2
image:
  repository: "{account}.dkr.ecr.{region}.amazonaws.com/{project}"
  tag: "latest"
  pullPolicy: IfNotPresent
service:
  type: ClusterIP
  port: 80
  targetPort: 8000
resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi
config:
  LOG_LEVEL: "INFO"
  ENVIRONMENT: "production"
```

**values-local.yaml**, **values-blue.yaml**, **values-green.yaml** (per-environment overrides).

### 5. Verify Helm Template

```bash
helm lint deploy/helm/{project}
helm template {project} deploy/helm/{project} -f deploy/helm/{project}/values-local.yaml
```

---

## Elastic Beanstalk Path

**Skill**: AWS EB Blue/Green Deployment

### 1. Create Docker Compose Template

EB uses a `docker-compose.yml` file to define the container. Create a template with environment variable substitution:

```yaml
# deploy/docker-compose.tmpl.yml
version: "3.8"
services:
  web:
    image: ${IMAGE_WEB}
    ports:
      - "80:8000"
    environment:
      - MIMIR_ENV=production
      - DJANGO_SETTINGS_MODULE=mimir.settings
    restart: always
```

### 2. Create Render Script

CI/CD will substitute `IMAGE_WEB` at deploy time:

```bash
# In .github/workflows/build-and-deploy.yml
env:
  IMAGE_WEB: ${{ steps.ecr-login.outputs.registry }}/mimir:${{ steps.version.outputs.suffix }}
run: |
  envsubst '$IMAGE_WEB' < deploy/docker-compose.tmpl.yml > docker-compose.yml
  cat docker-compose.yml
```

### 3. Create Deployment Bundle

EB requires a `.zip` bundle containing `docker-compose.yml`:

```bash
# In CI/CD
zip -j deploy-bundle.zip docker-compose.yml
```

This bundle is uploaded to S3 and referenced when creating an EB application version. See AWS EB Blue/Green Deployment skill Pattern 1 for full `deploy-idle.sh` script.

### 4. Document Deployment Flow

Add to `README.md` or `docs/deployment.md`:

```markdown
## EB Deployment Flow

1. CI builds Docker image, pushes to ECR
2. Render `docker-compose.yml` from template with `IMAGE_WEB={ecr-uri}:{tag}`
3. Zip `docker-compose.yml` → `deploy-bundle.zip`
4. Upload bundle to S3: `s3://{EB_BUCKET}/mimir/{VERSION_LABEL}/deploy-bundle.zip`
5. Create EB application version: `aws elasticbeanstalk create-application-version --version-label {VERSION_LABEL} --source-bundle S3Bucket={EB_BUCKET},S3Key=mimir/{VERSION_LABEL}/deploy-bundle.zip`
6. Deploy to idle: `aws elasticbeanstalk update-environment --environment-name {IDLE_ENV} --version-label {VERSION_LABEL}`
7. Smoke test idle, then swap: `aws elasticbeanstalk swap-environment-cnames --source-environment-name {IDLE_ENV} --destination-environment-name {LIVE_ENV}`
```

---

## Commit (Both Paths)

```bash
git add deploy/
git commit -m "feat(deploy): add deployment manifest ({Helm chart|EB docker-compose template})"
```

---

## Deliverables (Style-Agnostic)

- ✅ **Deployment manifest created** (Helm chart OR docker-compose template)
- ✅ **Per-environment values/overrides** defined
- ✅ **Rendering verified** (`helm template` OR `envsubst` test)
- ✅ **`make deploy ENV=<env>`** works locally (after Activity #83)

## Inputs

Read these before starting this activity. They are produced earlier in the playbook and are authoritative — raise a drift event instead of deviating.

- **SAO.md** (Document, Required) — produced by Write SAO.md (#59).
- **INFRA_REQUIREMENTS.md** (Document, Required) — produced by Review SAO & Define Infra Requirements (#74).

## Agent

None

## Skill

**Title**: AWS Elastic Beanstalk Blue/Green Deployment

**Title**: K8s in EKS Deployment Patterns
**Capability Domain**: CONTAINER_ORCHESTRATION
**Technology Stack**: Kubernetes + AWS EKS

## Rules

None

## Artifacts Produced

- **Helm Chart Template** (Template) - Required

## Artifacts Consumed

- **CICD Requirements (Release-Gated EB Reference)** (Document) - Required

## Notes

No additional notes.
