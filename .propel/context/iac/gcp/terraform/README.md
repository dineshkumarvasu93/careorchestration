# Unified Patient Access & Clinical Intelligence Platform — GCP Terraform IaC

HIPAA-compliant, production-ready GCP infrastructure for the Patient Access Platform.

## Directory Structure

```
terraform/
├── modules/
│   ├── networking/     # VPC, subnets, PSC, VPC connector, NAT, firewall
│   ├── compute/        # Cloud Run v2 (API) + Compute Engine VM (Ollama)
│   ├── database/       # Cloud SQL PostgreSQL 16 + Memorystore Redis 7
│   ├── storage/        # GCS SPA bucket + uploads bucket + CDN/LB
│   ├── security/       # KMS, Secret Manager, Cloud Armor WAF, service accounts
│   └── monitoring/     # Uptime checks, alert policies, log metrics
└── environments/
    ├── dev/
    ├── qa/
    ├── staging/
    └── prod/
```

## Prerequisites

| Tool | Minimum Version |
|------|----------------|
| Terraform | >= 1.5.0 |
| Google Provider | ~> 5.0 |
| gcloud CLI | >= 450.0.0 |

### Required GCP APIs

Enable these APIs in every project before applying:

```bash
gcloud services enable \
  cloudresourcemanager.googleapis.com \
  compute.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  run.googleapis.com \
  vpcaccess.googleapis.com \
  servicenetworking.googleapis.com \
  secretmanager.googleapis.com \
  cloudkms.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  storage.googleapis.com
```

## Environment Sizing Matrix

| Variable | dev | qa | staging | prod |
|----------|-----|----|---------|------|
| Cloud Run min_instances | 0 | 1 | 1 | 2 |
| Cloud Run max_instances | 2 | 5 | 10 | 20 |
| Cloud SQL tier | db-f1-micro | db-g1-small | db-n1-standard-2 | db-n1-standard-4 |
| Cloud SQL HA | false | false | true | true |
| Redis tier | BASIC | BASIC | STANDARD_HA | STANDARD_HA |
| Redis memory_gb | 1 | 1 | 4 | 8 |
| Ollama VM | e2-medium | e2-standard-2 | e2-standard-4 | e2-standard-4 |
| deletion_protection | false | false | true | true |

## Deployment

### First-time setup

1. **Create the GCS bucket for Terraform state** (once per organization):

```bash
gsutil mb -p patient-access-prod -l us-central1 gs://patient-access-tfstate
gsutil versioning set on gs://patient-access-tfstate
```

2. **Authenticate**:

```bash
gcloud auth application-default login
```

3. **Deploy an environment**:

```bash
cd environments/dev
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

### Updating secrets (out-of-band — never in .tf files)

```bash
# JWT signing key (generate a strong random key)
openssl rand -base64 64 | gcloud secrets versions add \
  patient-access-dev-jwt-signing-key --data-file=-

# DB password
gcloud secrets versions add patient-access-dev-db-password \
  --data-file=<(echo -n "YOUR_DB_PASSWORD")
```

## HIPAA Compliance Controls

| Control | Implementation |
|---------|---------------|
| PHI boundary (NFR-005) | Ollama VM on internal VPC; no external AI API calls |
| TLS 1.2+ (NFR-006) | Cloud SQL `ENCRYPTED_ONLY`; Redis `SERVER_AUTHENTICATION`; Cloud Run HTTPS |
| AES-256 at rest (NFR-007) | Cloud KMS CMEK on Cloud SQL and GCS uploads bucket |
| RBAC (NFR-008) | Least-privilege service accounts; Cloud Armor WAF |
| Audit retention (NFR-017) | GCS uploads retention 6 years; log-based metric alert on gaps |
| No PHI to 3rd party (NFR-010) | Ollama runs locally; Secret Manager for credentials |

## Security Architecture

- **Network**: Custom VPC, private subnets, deny-all ingress default, Cloud NAT for egress
- **Compute**: No external IPs on VMs; Cloud Run HTTPS-only; IAP for SSH
- **Data**: Cloud SQL private IP only; Redis auth + TLS; CMEK encryption
- **WAF**: Cloud Armor with XSS, SQLi, RFI preconfigured rules + rate limiting
- **Secrets**: All credentials in Secret Manager; no secrets in Terraform state

## Naming Convention

```
{project_name}-{environment}-{resource_type}-{identifier}
```

Examples:
- `patient-access-prod-sql-main` — Cloud SQL instance
- `patient-access-dev-run-api` — Cloud Run service
- `patient-access-staging-vm-ollama` — Ollama VM

## Module Dependencies

```
networking → security → database
                     → storage
                     → compute → monitoring
```

## Linting & Validation

```bash
# Format check
terraform fmt -recursive -check

# Validate
terraform validate

# Security scan (install tfsec)
tfsec .

# Policy scan (install checkov)
checkov -d .
```
