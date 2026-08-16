variable "project_id" {
  description = "The Google Cloud Project ID where NutriConcierge will be deployed"
  type        = string
}

variable "region" {
  description = "The primary Google Cloud region for services"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment (e.g. dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "app_name" {
  description = "The application name"
  type        = string
  default     = "nutri-concierge"
}

variable "container_image" {
  description = "The container image to run on Cloud Run"
  type        = string
  default     = "gcr.io/google.com/cloudsdktool/google-cloud-cli:alpine"
}

variable "gemini_api_key" {
  description = "The Gemini API Key to store securely in Secret Manager"
  type        = string
  sensitive   = true
  default     = "dummy-api-key-replace-in-secret-manager"
}
