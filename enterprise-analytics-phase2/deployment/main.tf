terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "your-tf-state-bucket"
    prefix = "enterprise-analytics"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Enable APIs ────────────────────────────────────────────────────────────────

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "aiplatform.googleapis.com",
    "bigquery.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "containerregistry.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# ── Service Account ────────────────────────────────────────────────────────────

resource "google_service_account" "analytics" {
  account_id   = "analytics-platform"
  display_name = "Enterprise Analytics Platform SA"
}

resource "google_project_iam_member" "vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.analytics.email}"
}

resource "google_project_iam_member" "bq_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.analytics.email}"
}

resource "google_project_iam_member" "bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.analytics.email}"
}

# ── Secret Manager ─────────────────────────────────────────────────────────────

resource "google_secret_manager_secret" "secret_key" {
  secret_id = "analytics-secret-key"
  replication { auto {} }
}

# ── Cloud Run — Backend ────────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "backend" {
  name     = "analytics-backend"
  location = var.region

  template {
    service_account = google_service_account.analytics.email
    containers {
      image = "gcr.io/${var.project_id}/analytics-backend:latest"
      resources {
        limits = { memory = "2Gi", cpu = "2" }
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_LOCATION"
        value = var.region
      }
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name = "SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secret_key.secret_id
            version = "latest"
          }
        }
      }
    }
    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }
  }
  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_service_iam_member" "backend_public" {
  location = google_cloud_run_v2_service.backend.location
  service  = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Cloud Run — Frontend ───────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "frontend" {
  name     = "analytics-frontend"
  location = var.region

  template {
    containers {
      image = "gcr.io/${var.project_id}/analytics-frontend:latest"
      env {
        name  = "VITE_API_URL"
        value = google_cloud_run_v2_service.backend.uri
      }
    }
    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }
  }
  depends_on = [google_cloud_run_v2_service.backend]
}

resource "google_cloud_run_service_iam_member" "frontend_public" {
  location = google_cloud_run_v2_service.frontend.location
  service  = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Outputs ────────────────────────────────────────────────────────────────────

output "backend_url"  { value = google_cloud_run_v2_service.backend.uri }
output "frontend_url" { value = google_cloud_run_v2_service.frontend.uri }
