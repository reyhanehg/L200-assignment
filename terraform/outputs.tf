output "cloud_run_service_url" {
  description = "The public HTTPS URL of the deployed NutriConcierge service"
  value       = google_cloud_run_v2_service.nutriconcierge.uri
}

output "artifact_registry_repository" {
  description = "The Artifact Registry Docker repository ID"
  value       = google_artifact_registry_repository.repo.id
}

output "service_account_email" {
  description = "The email address of the service account used by Cloud Run"
  value       = google_service_account.app_sa.email
}

output "secret_manager_secret_id" {
  description = "The Secret Manager Secret ID for the Gemini API Key"
  value       = google_secret_manager_secret.gemini_key.secret_id
}
