terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Enable Required Google Cloud APIs
resource "google_project_service" "services" {
  for_each = toset([
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudtrace.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
  ])

  service            = each.key
  disable_on_destroy = false
}

# 2. Artifact Registry for Container Images
resource "google_artifact_registry_repository" "repo" {
  depends_on    = [google_project_service.services]
  location      = var.region
  repository_id = "${var.app_name}-repo"
  description   = "Docker repository for NutriConcierge application images"
  format        = "DOCKER"
}

# 3. Secret Manager for Secure Key Injection
resource "google_secret_manager_secret" "gemini_key" {
  depends_on = [google_project_service.services]
  secret_id  = "gemini-api-key"

  labels = {
    app         = var.app_name
    environment = var.environment
  }

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "gemini_key_version" {
  secret      = google_secret_manager_secret.gemini_key.id
  secret_data = var.gemini_api_key
}

# 4. Service Account with Least-Privilege IAM Roles
resource "google_service_account" "app_sa" {
  account_id   = "${var.app_name}-sa"
  display_name = "Service Account for NutriConcierge Cloud Run"
}

resource "google_secret_manager_secret_iam_member" "secret_access" {
  secret_id = google_secret_manager_secret.gemini_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app_sa.email}"
}

resource "google_project_iam_member" "aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.app_sa.email}"
}

resource "google_project_iam_member" "cloudtrace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.app_sa.email}"
}

resource "google_project_iam_member" "log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.app_sa.email}"
}

# 5. Cloud Run Service with Secret Manager Binding
resource "google_cloud_run_v2_service" "nutriconcierge" {
  depends_on = [
    google_project_service.services,
    google_secret_manager_secret_version.gemini_key_version,
  ]

  name     = "${var.app_name}-${var.environment}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.app_sa.email

    containers {
      image = var.container_image

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      ports {
        container_port = 8501
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      # Secure Secret Injection from Secret Manager
      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }
}

# 6. Public Access Policy (Allow unauthenticated for demo UI)
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.nutriconcierge.location
  service  = google_cloud_run_v2_service.nutriconcierge.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
