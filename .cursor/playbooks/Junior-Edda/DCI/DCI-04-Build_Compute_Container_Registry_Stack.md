# Activity: Build Compute & Container Registry Stack

**Activity ID**: 77
**Order**: 4
**Phase**: Elaboration
**Dependencies**: Predecessor: Activity 76 (Build VPC & Networking Stack)

## Description

Build Compute & Container Registry Stack

## Guidance

# Build Compute & Container Registry Stack

## Objective

Provision the compute environment and container registry matching your chosen deployment style (from Activity #74). This activity forks into two implementation paths—EKS or Elastic Beanstalk—both delivering the same outcome: a running compute platform and accessible ECR repository.

---

## Process

### Path Selection

Refer to `docs/architecture/INFRA_REQUIREMENTS.md` § Deployment Style. Follow the path for your chosen style.

---

## EKS Path

**Skill**: K8s in EKS Deployment Patterns (#23)

### 1. Implement `stacks/eks_stack.py`

Key constructs:
- **EKS Cluster** with managed node group (2-3 `t3.medium` nodes)
- **ECR Repository** for application container images
- **OIDC Provider** for IAM Roles for Service Accounts (IRSA)
- **kubectl layer** for CDK to interact with cluster
- **Blue/green namespaces** created on cluster

```python
from aws_cdk import Stack, RemovalPolicy, aws_eks as eks, aws_ec2 as ec2, aws_ecr as ecr, aws_iam as iam
from constructs import Construct

class EksStack(Stack):
    def __init__(self, scope: Construct, id: str, vpc: ec2.Vpc, **kwargs):
        super().__init__(scope, id, **kwargs)

        # EKS Cluster
        self.cluster = eks.Cluster(
            self, "Cluster",
            vpc=vpc,
            version=eks.KubernetesVersion.V1_29,
            default_capacity=0,
            endpoint_access=eks.EndpointAccess.PUBLIC_AND_PRIVATE,
        )

        # Managed Node Group
        self.cluster.add_nodegroup_capacity(
            "WorkerNodes",
            instance_types=[ec2.InstanceType("t3.medium")],
            min_size=2,
            max_size=4,
            desired_size=2,
            disk_size=50,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )

        # ECR Repository
        self.ecr_repo = ecr.Repository(
            self, "AppRepo",
            repository_name="{project}",
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                ecr.LifecycleRule(max_image_count=20, description="Keep last 20 images")
            ],
        )

        # Create blue/green namespaces
        for ns in ["blue", "green"]:
            self.cluster.add_manifest(
                f"{ns}-namespace",
                {
                    "apiVersion": "v1",
                    "kind": "Namespace",
                    "metadata": {"name": ns},
                },
            )
```

### 2. Configure kubectl Access

```bash
aws eks update-kubeconfig --name {cluster-name} --region {region}
kubectl get nodes  # Should show 2 worker nodes
kubectl get ns     # Should show blue and green namespaces
```

### 3. Test ECR Push

```bash
aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {account}.dkr.ecr.{region}.amazonaws.com
docker pull nginx:alpine
docker tag nginx:alpine {account}.dkr.ecr.{region}.amazonaws.com/{project}:test
docker push {account}.dkr.ecr.{region}.amazonaws.com/{project}:test
```

---

## Elastic Beanstalk Path

**Skill**: AWS EB Blue/Green Deployment

### 1. Implement `stacks/eb_stack.py`

Key constructs:
- **EB Application** resource
- **Two EB Environments**: `{project}-prod` (physical A), `{project}-idle` (physical B)
- **ECR Repository** for Docker images
- **S3 Bucket** for deployment bundles (use existing `elasticbeanstalk-{region}-{account}` bucket)

```python
from aws_cdk import Stack, RemovalPolicy, aws_elasticbeanstalk as eb, aws_ec2 as ec2, aws_ecr as ecr, aws_iam as iam
from constructs import Construct

class EbStack(Stack):
    def __init__(self, scope: Construct, id: str, vpc: ec2.Vpc, **kwargs):
        super().__init__(scope, id, **kwargs)

        # EB Application
        self.app = eb.CfnApplication(
            self, "App",
            application_name="{project}",
        )

        # ECR Repository
        self.ecr_repo = ecr.Repository(
            self, "AppRepo",
            repository_name="{project}",
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                ecr.LifecycleRule(max_image_count=20, description="Keep last 20 images")
            ],
        )

        # Service Role for EB
        service_role = iam.Role(
            self, "EBServiceRole",
            assumed_by=iam.ServicePrincipal("elasticbeanstalk.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSElasticBeanstalkEnhancedHealth"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSElasticBeanstalkManagedUpdatesCustomerRolePolicy"),
            ],
        )

        # Instance Profile
        instance_role = iam.Role(
            self, "EBInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSElasticBeanstalkWebTier"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly"),
            ],
        )
        instance_profile = iam.CfnInstanceProfile(
            self, "EBInstanceProfile",
            roles=[instance_role.role_name],
        )

        # Environment A ({project}-prod initially)
        self.env_a = eb.CfnEnvironment(
            self, "EnvA",
            application_name=self.app.application_name,
            environment_name="{project}-prod",
            solution_stack_name="64bit Amazon Linux 2023 v4.3.0 running Docker",
            option_settings=[
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:autoscaling:launchconfiguration",
                    option_name="IamInstanceProfile",
                    value=instance_profile.ref,
                ),
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:environment",
                    option_name="ServiceRole",
                    value=service_role.role_arn,
                ),
            ],
        )
        self.env_a.add_dependency(self.app)

        # Environment B ({project}-idle initially)
        self.env_b = eb.CfnEnvironment(
            self, "EnvB",
            application_name=self.app.application_name,
            environment_name="{project}-idle",
            solution_stack_name="64bit Amazon Linux 2023 v4.3.0 running Docker",
            option_settings=[
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:autoscaling:launchconfiguration",
                    option_name="IamInstanceProfile",
                    value=instance_profile.ref,
                ),
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:environment",
                    option_name="ServiceRole",
                    value=service_role.role_arn,
                ),
            ],
        )
        self.env_b.add_dependency(self.app)
```

### 2. Document EB Variables

Add to `INFRA_REQUIREMENTS.md`:

```markdown
## EB Environment Variables (for CI/CD)

- `EB_APP`: {project}
- `EB_ENV_A`: {project}-prod
- `EB_ENV_B`: {project}-idle
- `EB_BUCKET`: elasticbeanstalk-{region}-{account}
```

### 3. Verify EB Environments

```bash
aws elasticbeanstalk describe-environments \
  --application-name {project} \
  --query 'Environments[].{Name:EnvironmentName,Status:Status,Health:Health,CNAME:CNAME}' \
  --output table
```

Both environments should show `Status=Ready`.

### 4. Test ECR Push

```bash
aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {account}.dkr.ecr.{region}.amazonaws.com
docker pull nginx:alpine
docker tag nginx:alpine {account}.dkr.ecr.{region}.amazonaws.com/{project}:test
docker push {account}.dkr.ecr.{region}.amazonaws.com/{project}:test
```

---

## Commit (Both Paths)

```bash
git add stacks/
git commit -m "infra: implement compute and container registry stack ({EKS|EB})"
```

---

## Deliverables (Style-Agnostic)

- ✅ **Compute environment running** (EKS cluster with nodes OR two EB environments)
- ✅ **ECR repository accessible** (push/pull verified)
- ✅ **Blue/green substrate in place** (K8s namespaces OR EB environment pair)
- ✅ **Chosen style recorded** in `INFRA_REQUIREMENTS.md`
- ✅ **CDK stack committed**

## Inputs

Read these before starting this activity. They are produced earlier in the playbook and are authoritative — raise a drift event instead of deviating.

- **Infra Repo Scaffold** (Template, Required) — produced by Scaffold Infra Repo & CDK Project (#75).
- **VPC Stack** (Code, Required) — produced by Build VPC & Networking Stack (#76).
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

None

## Artifacts Consumed

- **Infra Repo Scaffold** (Template) - Required
- **CDK Stack Templates** (Code) - Required

## Notes

No additional notes.
