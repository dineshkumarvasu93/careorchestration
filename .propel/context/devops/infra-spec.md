---
title: "Infrastructure Specification — Unified Patient Access & Clinical Intelligence Platform"
version: "1.0.0"
date: "2026-04-26"
status: "Active"
owner: "platform-team"
classification: "Internal"
---

# Infrastructure Specification

**Platform**: Google Cloud Platform (GCP)
**Application**: Unified Patient Access & Clinical Intelligence Platform
**Compliance**: HIPAA, SOC 2 Type II (target)
**Terraform**: `>= 1.5.0` | Google Provider `~> 5.0`

---

## Platform Summary

The platform runs entirely within GCP using managed services and private networking. All PHI processing occurs within the deployment boundary — no PHI is sent to external third-party APIs.

| App Component | GCP Service | Notes |
|--------------|-------------|-------|
| .NET 9 API | Cloud Run v2 | Serverless, auto-scaling |
| PostgreSQL 16 + pgvector | Cloud SQL for PostgreSQL 16 | Private IP only, CMEK |
| Redis 7 | Memorystore for Redis | Auth + TLS |
| Ollama AI (Llama 3.2 3B) | Compute Engine VM | In-boundary HIPAA; no external AI |
| React 18 SPA | Cloud Storage + Cloud CDN | Global HTTPS LB |
| Clinical uploads | Cloud Storage (private, versioned) | 6-year retention, CMEK |
| Secrets | Secret Manager | Placeholder pattern, never in state |
| Encryption CMEK | Cloud KMS | 90-day rotation |
| WAF / DDoS | Cloud Armor | XSS, SQLi, RFI + rate limit |
| Networking | VPC + PSC + VPC Connector | Private service access |
| Monitoring | Cloud Monitoring + Cloud Logging | Email alerts, uptime checks |

---

## Environment Matrix

| Dimension | dev | qa | staging | prod |
|-----------|-----|----|---------|------|
| GCP Project | patient-access-dev | patient-access-qa | patient-access-staging | patient-access-prod |
| Region | us-central1 | us-central1 | us-central1 | us-central1 |
| Cloud Run min instances | 0 | 1 | 1 | 2 |
| Cloud Run max instances | 2 | 5 | 10 | 20 |
| CPU always allocated | false | false | true | true |
| Cloud SQL tier | db-f1-micro | db-g1-small | db-n1-standard-2 | db-n1-standard-4 |
| Cloud SQL HA | false | false | true (REGIONAL) | true (REGIONAL) |
| Redis tier | BASIC | BASIC | STANDARD_HA | STANDARD_HA |
| Redis memory (GB) | 1 | 1 | 4 | 8 |
| Ollama VM type | e2-medium | e2-standard-2 | e2-standard-4 | e2-standard-4 |
| deletion_protection | false | false | true | true |
| Approval gates | None | None | 1 reviewer | 2 reviewers |

---

## Compute Requirements

### INFRA-001
**Title**: Cloud Run v2 for API  
**Description**: The .NET 9 ASP.NET Core API MUST be deployed as a Cloud Run v2 service in the project region.  
**NFR**: NFR-001 (API availability)  
**Acceptance**: `terraform plan` shows `google_cloud_run_v2_service` resource; service responds to `GET /api/health`.

### INFRA-002
**Title**: Cloud Run scaling per environment  
**Description**: Cloud Run MUST configure min/max instances per the environment sizing matrix.  
**NFR**: NFR-002 (Performance/scaling)  
**Acceptance**: `min_instance_count` and `max_instance_count` match matrix values for each environment.

### INFRA-003
**Title**: Cloud Run HTTPS only  
**Description**: Cloud Run MUST enforce HTTPS; HTTP traffic MUST be rejected or redirected.  
**NFR**: NFR-006 (TLS 1.2+)  
**Acceptance**: Direct HTTP requests to service URL return 301/302 to HTTPS.

### INFRA-004
**Title**: Cloud Run liveness probe  
**Description**: Cloud Run containers MUST configure an HTTP liveness probe on `GET /api/health` port 8080.  
**NFR**: NFR-001 (availability)  
**Acceptance**: `liveness_probe.http_get.path = "/api/health"` present in Terraform config.

### INFRA-005
**Title**: Ollama VM internal only  
**Description**: The Compute Engine VM running Ollama MUST have NO external IP address. AI inference MUST remain within the VPC.  
**NFR**: NFR-005 (HIPAA boundary), NFR-010 (No PHI to external services)  
**Acceptance**: VM `network_interface` has no `access_config` block; no ephemeral or static public IP assigned.

### INFRA-006
**Title**: Ollama model pre-pull on startup  
**Description**: The Ollama VM startup script MUST pull `llama3.2:3b` and `nomic-embed-text` models on first boot.  
**NFR**: AIR-001 (AI model availability)  
**Acceptance**: Startup script contains `ollama pull llama3.2:3b` and `ollama pull nomic-embed-text`.

### INFRA-007
**Title**: Ollama VM shielded instance  
**Description**: The Ollama VM MUST enable Secure Boot, vTPM, and Integrity Monitoring.  
**NFR**: NFR-008 (Security hardening)  
**Acceptance**: `shielded_instance_config` block with all three options set to `true`.

### INFRA-008
**Title**: Cloud Run CPU allocation  
**Description**: `cpu_idle = true` for dev/qa (cost saving); `cpu_idle = false` (CPU always allocated) for staging/prod (latency SLA).  
**NFR**: NFR-002 (latency), cost-center tagging  
**Acceptance**: `resources.cpu_idle` value matches environment matrix.

### INFRA-009
**Title**: Cloud Run VPC egress  
**Description**: Cloud Run services MUST route ALL traffic through the Serverless VPC Access connector (`egress = "ALL_TRAFFIC"`).  
**NFR**: NFR-005 (HIPAA boundary)  
**Acceptance**: `vpc_access.egress = "ALL_TRAFFIC"` in Cloud Run template.

### INFRA-010
**Title**: Cloud Run secret injection  
**Description**: Secrets (JWT key, DB password, Redis auth, Ollama URL, Seq URL) MUST be injected as env vars from Secret Manager — never hardcoded.  
**NFR**: NFR-008, SEC-001  
**Acceptance**: All env vars reference `secret_key_ref` with `version = "latest"`; no plain-text secrets in `.tf` or `.tfvars`.

---

## Networking Requirements

### INFRA-011
**Title**: Custom VPC per environment  
**Description**: Each environment MUST use a dedicated custom VPC with `auto_create_subnetworks = false`.  
**NFR**: NFR-006 (network isolation)  
**Acceptance**: Separate GCP project per environment; `google_compute_network` with `auto_create_subnetworks = false`.

### INFRA-012
**Title**: Private subnet with Google Private Access  
**Description**: The primary subnet MUST enable Private Google Access so Cloud Run and VMs can reach GCP APIs without public IPs.  
**NFR**: NFR-005  
**Acceptance**: `private_ip_google_access = true` on `google_compute_subnetwork`.

### INFRA-013
**Title**: VPC Flow Logs  
**Description**: Subnet MUST enable VPC Flow Logs for security monitoring and forensics.  
**NFR**: NFR-017 (audit), SEC-010  
**Acceptance**: `log_config` block present on subnetwork with `flow_sampling >= 0.5`.

### INFRA-014
**Title**: Private Service Connect for Cloud SQL  
**Description**: Cloud SQL MUST be accessible only via Private Service Connect — no public IP.  
**NFR**: NFR-006 (no plaintext), NFR-005  
**Acceptance**: `google_compute_global_address` + `google_service_networking_connection` provisioned; Cloud SQL `ipv4_enabled = false`.

### INFRA-015
**Title**: Serverless VPC Access Connector  
**Description**: A Serverless VPC Access connector MUST exist so Cloud Run can reach Cloud SQL and Redis over private IP.  
**NFR**: NFR-005, NFR-006  
**Acceptance**: `google_vpc_access_connector` provisioned; Cloud Run references connector ID.

### INFRA-016
**Title**: Default deny-all ingress firewall  
**Description**: VPC MUST have a deny-all ingress firewall rule at lowest priority. Only explicitly required traffic is allowed.  
**NFR**: NFR-008  
**Acceptance**: `google_compute_firewall` with `priority = 65534`, `deny { protocol = "all" }`.

### INFRA-017
**Title**: IAP-only SSH to VMs  
**Description**: SSH access to Ollama VM MUST be restricted to Identity-Aware Proxy source range `35.235.240.0/20`.  
**NFR**: NFR-008 (access control), SEC-005  
**Acceptance**: Firewall rule allows TCP/22 only from IAP CIDR; VM tagged `ollama-vm`.

### INFRA-018
**Title**: Cloud NAT for egress  
**Description**: Private VMs requiring outbound internet access (e.g., Docker image pull) MUST use Cloud NAT — no direct public IPs.  
**NFR**: NFR-005 (boundary control)  
**Acceptance**: `google_compute_router` + `google_compute_router_nat` provisioned; NAT logs errors.

### INFRA-019
**Title**: Block project SSH keys on VMs  
**Description**: `block-project-ssh-keys = "true"` and `enable-oslogin = "TRUE"` MUST be set in VM metadata.  
**NFR**: SEC-005  
**Acceptance**: VM metadata includes both keys.

### INFRA-020
**Title**: No wildcard firewall rules  
**Description**: No firewall rule may use a wildcard (`*`) for both port AND protocol simultaneously without rate limiting.  
**NFR**: NFR-008  
**Acceptance**: tfsec/checkov scan passes; no `allow { protocol = "all" }` on ingress rules.

---

## Database Requirements

### INFRA-021
**Title**: Cloud SQL PostgreSQL 16 private IP only  
**Description**: Cloud SQL instance MUST have `ipv4_enabled = false`; accessible only via private IP.  
**NFR**: NFR-006 (no public exposure)  
**Acceptance**: `ip_configuration.ipv4_enabled = false`; no `authorized_networks` block.

### INFRA-022
**Title**: Cloud SQL SSL enforcement  
**Description**: Cloud SQL MUST require SSL for all connections (`ssl_mode = "ENCRYPTED_ONLY"`).  
**NFR**: NFR-006 (TLS 1.2+)  
**Acceptance**: `require_ssl = true` and `ssl_mode = "ENCRYPTED_ONLY"` in `ip_configuration`.

### INFRA-023
**Title**: Cloud SQL CMEK encryption  
**Description**: Cloud SQL MUST use a customer-managed encryption key (CMEK) from Cloud KMS.  
**NFR**: NFR-007 (AES-256 at rest)  
**Acceptance**: `encryption_key_name` references KMS crypto key; key has 90-day rotation.

### INFRA-024
**Title**: Cloud SQL automated backups with PITR  
**Description**: Automated backups MUST be enabled with point-in-time recovery (PITR) and 30 backup retention.  
**NFR**: DR-013 (RPO <= 1 hour), DR-012 (data retention)  
**Acceptance**: `backup_configuration.enabled = true`, `point_in_time_recovery_enabled = true`, `retained_backups = 30`.

### INFRA-025
**Title**: Cloud SQL HA for staging/prod  
**Description**: staging and prod Cloud SQL instances MUST use `availability_type = "REGIONAL"` for high availability.  
**NFR**: DR-001 (RTO <= 4 hours)  
**Acceptance**: `availability_type = "REGIONAL"` for staging and prod; `"ZONAL"` for dev/qa.

### INFRA-026
**Title**: Cloud SQL deletion protection  
**Description**: staging and prod Cloud SQL instances MUST have `deletion_protection = true`.  
**NFR**: DR-012 (data protection)  
**Acceptance**: Variable `deletion_protection = true` for staging/prod; `false` for dev/qa.

### INFRA-027
**Title**: Cloud SQL database flags — audit logging  
**Description**: Cloud SQL MUST enable `log_connections`, `log_disconnections`, `log_checkpoints`, and `log_min_duration_statement = 1000`.  
**NFR**: NFR-017 (audit)  
**Acceptance**: All four `database_flags` present in Terraform config.

### INFRA-028
**Title**: Cloud SQL Query Insights  
**Description**: Query Insights MUST be enabled for performance monitoring.  
**NFR**: NFR-003 (performance)  
**Acceptance**: `insights_config.query_insights_enabled = true`.

### INFRA-029
**Title**: Memorystore Redis auth  
**Description**: Redis MUST have `auth_enabled = true` and `transit_encryption_mode = "SERVER_AUTHENTICATION"`.  
**NFR**: NFR-006 (TLS), NFR-008 (auth)  
**Acceptance**: Both fields set in `google_redis_instance`.

### INFRA-030
**Title**: Redis HA for staging/prod  
**Description**: staging and prod Redis MUST use `tier = "STANDARD_HA"`.  
**NFR**: DR-001 (availability)  
**Acceptance**: `tier = "STANDARD_HA"` for staging/prod; `"BASIC"` for dev/qa.

---

## Storage Requirements

### INFRA-031
**Title**: Uniform bucket-level access on all GCS buckets  
**Description**: All GCS buckets MUST have `uniform_bucket_level_access = true`.  
**NFR**: SEC-007 (no ACL bypass)  
**Acceptance**: Both SPA and uploads buckets have `uniform_bucket_level_access = true`.

### INFRA-032
**Title**: SPA bucket — website routing  
**Description**: SPA GCS bucket MUST configure `website.main_page_suffix = "index.html"` and `website.not_found_page = "index.html"` for SPA routing.  
**NFR**: NFR-004 (frontend availability)  
**Acceptance**: Both `website` block keys present.

### INFRA-033
**Title**: Uploads bucket versioning  
**Description**: The clinical documents uploads bucket MUST enable versioning.  
**NFR**: DR-012 (data protection)  
**Acceptance**: `versioning.enabled = true` on uploads bucket.

### INFRA-034
**Title**: Uploads bucket 6-year retention  
**Description**: The uploads bucket MUST configure a retention policy of 189,216,000 seconds (6 years). Production bucket retention MUST be locked.  
**NFR**: NFR-017, DR-012 (6-year HIPAA audit retention)  
**Acceptance**: `retention_policy.retention_period = 189216000`; `is_locked = true` for prod.

### INFRA-035
**Title**: Uploads bucket CMEK  
**Description**: The uploads bucket MUST use a customer-managed KMS key for server-side encryption.  
**NFR**: NFR-007 (AES-256)  
**Acceptance**: `encryption.default_kms_key_name` references KMS storage crypto key.

### INFRA-036
**Title**: No public IAM on uploads bucket  
**Description**: The uploads bucket MUST NOT grant `allUsers` or `allAuthenticatedUsers` any IAM role.  
**NFR**: NFR-005, NFR-010  
**Acceptance**: No `google_storage_bucket_iam_member` with `member = "allUsers"` on uploads bucket.

### INFRA-037
**Title**: CDN HTTPS Load Balancer for SPA  
**Description**: The SPA MUST be served via a Global HTTPS Load Balancer with managed SSL certificate and Cloud CDN enabled.  
**NFR**: NFR-006 (TLS), NFR-004 (performance)  
**Acceptance**: `google_compute_global_forwarding_rule` on port 443; `google_compute_managed_ssl_certificate` provisioned.

### INFRA-038
**Title**: HTTP to HTTPS redirect  
**Description**: HTTP port 80 MUST redirect to HTTPS via a separate URL map with `https_redirect = true`.  
**NFR**: NFR-006  
**Acceptance**: `google_compute_url_map` with `default_url_redirect.https_redirect = true` attached to port-80 forwarding rule.

---

## Security Requirements

### SEC-001
**Title**: No hardcoded secrets  
**Description**: No passwords, API keys, tokens, or credentials may appear in any `.tf`, `.tfvars`, or `.tf.json` file.  
**NFR**: NFR-008, SEC-generic  
**Acceptance**: `grep -r "password\s*=\s*\"[^P]" .` returns no matches (only placeholders); secrets sourced via Secret Manager.

### SEC-002
**Title**: Cloud KMS key rotation  
**Description**: All KMS crypto keys MUST have a `rotation_period` of 90 days (`7776000s`).  
**NFR**: NFR-007  
**Acceptance**: `rotation_period = "7776000s"` on all `google_kms_crypto_key` resources.

### SEC-003
**Title**: Secret Manager placeholder pattern  
**Description**: Secret versions MUST be created with placeholder values (`PLACEHOLDER_REPLACE_OUT_OF_BAND`) with `lifecycle.ignore_changes = [secret_data]` to prevent drift.  
**NFR**: SEC-001  
**Acceptance**: `google_secret_manager_secret_version` resources all use placeholder + `ignore_changes`.

### SEC-004
**Title**: Cloud Armor WAF — XSS and SQLi protection  
**Description**: A Cloud Armor security policy MUST include preconfigured rules for `xss-stable`, `sqli-stable`, and `rfi-stable`.  
**NFR**: NFR-008 (OWASP Top 10)  
**Acceptance**: Three `rule` blocks with `evaluatePreconfiguredExpr(...)` expressions in `google_compute_security_policy`.

### SEC-005
**Title**: Cloud Armor rate limiting  
**Description**: Cloud Armor MUST throttle IPs exceeding 1000 requests per 60 seconds.  
**NFR**: NFR-008 (DDoS)  
**Acceptance**: `rate_limit_threshold { count = 1000; interval_sec = 60 }` with `exceed_action = "deny(429)"`.

### SEC-006
**Title**: Least-privilege service accounts  
**Description**: Each component (API, Ollama, Build) MUST have a dedicated service account with only the roles it needs.  
**NFR**: NFR-008  
**Acceptance**: Three `google_service_account` resources; no `roles/owner` or `roles/editor` bindings; `roles/*` is audited.

### SEC-007
**Title**: API SA — Secret Accessor only  
**Description**: The Cloud Run API service account MUST have `roles/secretmanager.secretAccessor`, `roles/cloudsql.client`, `roles/storage.objectCreator`, `roles/logging.logWriter`, `roles/monitoring.metricWriter` — no broader roles.  
**NFR**: NFR-008  
**Acceptance**: Exactly these five role bindings for api-sa; no additional roles.

### SEC-008
**Title**: Ollama SA — minimal permissions  
**Description**: The Ollama VM service account MUST have ONLY `roles/logging.logWriter` and `roles/monitoring.metricWriter`.  
**NFR**: NFR-008, NFR-005  
**Acceptance**: Only two role bindings for ollama-sa.

### SEC-009
**Title**: Sensitive Terraform outputs marked sensitive  
**Description**: All Terraform outputs containing credentials or internal network addresses MUST have `sensitive = true`.  
**NFR**: SEC-001  
**Acceptance**: `terraform output` does not expose secret values; sensitive outputs redacted.

### SEC-010
**Title**: KMS key destroy prevention  
**Description**: KMS crypto keys MUST have `lifecycle { prevent_destroy = true }` to prevent accidental data loss.  
**NFR**: DR-012  
**Acceptance**: `lifecycle.prevent_destroy = true` on both `google_kms_crypto_key` resources.

### SEC-011
**Title**: Shielded VM for Ollama  
**Description**: The Ollama Compute Engine VM MUST enable Secure Boot, vTPM, and Integrity Monitoring.  
**NFR**: NFR-008  
**Acceptance**: `shielded_instance_config` block with all three `enable_*` flags set to `true`.

### SEC-012
**Title**: OS Login on VMs  
**Description**: `enable-oslogin = "TRUE"` MUST be set in VM metadata to use IAM-based SSH authentication.  
**NFR**: SEC-005, NFR-008  
**Acceptance**: VM metadata key `enable-oslogin = "TRUE"`.

### SEC-013
**Title**: Block project-wide SSH keys  
**Description**: `block-project-ssh-keys = "true"` MUST be set to prevent project-level SSH key injection.  
**NFR**: NFR-008  
**Acceptance**: VM metadata key `block-project-ssh-keys = "true"`.

### SEC-014
**Title**: Cloud SQL — no public IP  
**Description**: Cloud SQL instance MUST have `ipv4_enabled = false` at all times.  
**NFR**: NFR-006, NFR-005  
**Acceptance**: `ip_configuration.ipv4_enabled = false`; no `authorized_networks`.

### SEC-015
**Title**: Redis auth token  
**Description**: Memorystore Redis MUST require an auth token (`auth_enabled = true`).  
**NFR**: NFR-008  
**Acceptance**: `auth_enabled = true` on `google_redis_instance`.

### SEC-016
**Title**: Redis TLS  
**Description**: Memorystore Redis MUST use server-authentication TLS (`transit_encryption_mode = "SERVER_AUTHENTICATION"`).  
**NFR**: NFR-006  
**Acceptance**: `transit_encryption_mode = "SERVER_AUTHENTICATION"`.

### SEC-017
**Title**: GCS uniform bucket access  
**Description**: All GCS buckets MUST use uniform bucket-level access (no per-object ACLs).  
**NFR**: SEC-007  
**Acceptance**: `uniform_bucket_level_access = true` on all buckets.

### SEC-018
**Title**: Uploads bucket no public access  
**Description**: Clinical uploads GCS bucket MUST NOT have any public IAM binding.  
**NFR**: NFR-005, NFR-010  
**Acceptance**: No `allUsers` or `allAuthenticatedUsers` bindings on uploads bucket.

### SEC-019
**Title**: Provider version pinning  
**Description**: All Terraform providers MUST be pinned with pessimistic operator `~>`, never floating.  
**NFR**: SEC-generic (supply chain)  
**Acceptance**: All `required_providers` entries use `~>` constraint.

### SEC-020
**Title**: Remote state with GCS backend  
**Description**: Terraform state MUST be stored in a GCS bucket with versioning enabled; state MUST NOT be committed to VCS.  
**NFR**: SEC-001 (state contains sensitive data)  
**Acceptance**: All `backend "gcs"` blocks reference `patient-access-tfstate`; `.gitignore` excludes `*.tfstate*`.

---

## Operational Requirements

### OPS-001
**Title**: Cloud Monitoring uptime check  
**Description**: An HTTPS uptime check MUST be configured on `GET /api/health` with a 60-second period and 10-second timeout.  
**NFR**: NFR-001 (availability SLA)  
**Acceptance**: `google_monitoring_uptime_check_config` with `period = "60s"`, `timeout = "10s"`, `use_ssl = true`.

### OPS-002
**Title**: Alert on API 5xx rate  
**Description**: An alert policy MUST fire when Cloud Run 5xx responses exceed 1% for 60 seconds.  
**NFR**: NFR-001  
**Acceptance**: `google_monitoring_alert_policy` targeting `run.googleapis.com/request_count` with `threshold_value = 0.01`.

### OPS-003
**Title**: Alert on Cloud SQL CPU  
**Description**: An alert MUST fire when Cloud SQL CPU utilization exceeds 80% for 5 minutes.  
**NFR**: NFR-003 (performance)  
**Acceptance**: Alert on `cloudsql.googleapis.com/database/cpu/utilization > 0.8` for `300s`.

### OPS-004
**Title**: Alert on Redis memory  
**Description**: An alert MUST fire when Redis memory utilization exceeds 80% for 5 minutes.  
**NFR**: NFR-003 (performance)  
**Acceptance**: Alert on `redis.googleapis.com/stats/memory/usage_ratio > 0.8` for `300s`.

### OPS-005
**Title**: Alert on uptime failure  
**Description**: An alert MUST fire when the API uptime check fails.  
**NFR**: NFR-001  
**Acceptance**: Alert on `monitoring.googleapis.com/uptime_check/check_passed` count_false > 1.

### OPS-006
**Title**: Audit log metric  
**Description**: A custom log-based metric MUST track audit log writes for HIPAA compliance monitoring.  
**NFR**: NFR-017  
**Acceptance**: `google_logging_metric` filtering `jsonPayload.audit=true`.

### OPS-007
**Title**: Alert on audit log gap  
**Description**: An alert MUST fire when no audit log entries are received for 15 minutes (logging pipeline failure).  
**NFR**: NFR-017  
**Acceptance**: `condition_absent` alert with `duration = "900s"` on audit log metric.

### OPS-008
**Title**: Email notification channel  
**Description**: All alert policies MUST use at least one email notification channel.  
**NFR**: NFR-001 (incident response)  
**Acceptance**: `google_monitoring_notification_channel` of type `email` referenced by all alert policies.

### OPS-009
**Title**: Cloud NAT logging  
**Description**: Cloud NAT MUST log errors for network egress troubleshooting.  
**NFR**: NFR-017 (audit trail)  
**Acceptance**: `log_config { enable = true; filter = "ERRORS_ONLY" }` on `google_compute_router_nat`.

### OPS-010
**Title**: Alert auto-close  
**Description**: All alert policies MUST configure `auto_close = "1800s"` to prevent stale incident noise.  
**NFR**: NFR-001 (operational hygiene)  
**Acceptance**: `alert_strategy.auto_close = "1800s"` on all `google_monitoring_alert_policy` resources.

---

## Environment Configuration Requirements

### ENV-001
**Title**: Separate GCP project per environment  
**Description**: Each environment (dev, qa, staging, prod) MUST use a separate GCP project for billing isolation and blast radius containment.  
**NFR**: NFR-008, cost governance  
**Acceptance**: `project_id` variables are distinct per environment; no shared project.

### ENV-002
**Title**: Separate Terraform state per environment  
**Description**: Each environment MUST use a separate GCS state prefix (`terraform/state/{env}`).  
**NFR**: SEC-020  
**Acceptance**: `backend "gcs" { prefix = "terraform/state/${env}" }` in each environment's `backend.tf`.

### ENV-003
**Title**: Common labels on all resources  
**Description**: Every resource MUST apply `local.common_labels` containing `environment`, `project`, `managed_by`, `owner`, `cost_center`.  
**NFR**: Cost governance, resource discovery  
**Acceptance**: `labels = local.common_labels` present on every non-IAM resource; all five keys populated.

### ENV-004
**Title**: Environment variable validation  
**Description**: All environment input variables MUST include validation blocks rejecting values outside the allowed set.  
**NFR**: SEC-generic (config safety)  
**Acceptance**: `validation { condition = contains(["dev","qa","staging","prod"], var.environment) }` in all `variables.tf` files.

---

## Appendix: NFR / DR Cross-Reference

| Code | Requirement | Implemented By |
|------|-------------|---------------|
| NFR-001 | API availability / uptime | Cloud Run scaling, uptime checks, 5xx alerts |
| NFR-002 | Performance / latency | Cloud Run min instances, cpu_always_allocated for prod |
| NFR-003 | Database performance | Cloud SQL Query Insights, CPU alert, Redis memory alert |
| NFR-004 | Frontend availability | CDN + Global LB + SPA bucket |
| NFR-005 | HIPAA PHI boundary | Ollama VM no external IP, VPC egress only |
| NFR-006 | TLS 1.2+ everywhere | Cloud SQL SSL, Redis TLS, HTTPS LB, HTTP→HTTPS redirect |
| NFR-007 | AES-256 at rest | KMS CMEK on Cloud SQL and uploads bucket |
| NFR-008 | RBAC / access control | Least-privilege SAs, Cloud Armor WAF, deny-all firewall |
| NFR-010 | No PHI to 3rd parties | Ollama on VPC; all secrets internal |
| NFR-017 | 6-year audit log retention | GCS retention 189M seconds; locked in prod; audit log gap alert |
| DR-001 | RTO <= 4 hours | Cloud SQL REGIONAL HA for staging/prod |
| DR-012 | Data retention | Uploads bucket versioning + 6-year retention policy |
| DR-013 | RPO <= 1 hour | Cloud SQL PITR + 30-backup retention |
| AIR-001 | AI model availability | Ollama startup script pre-pulls models |
