variable "controller_ip" {
  
}

variable "controller_user" {
  
}

variable "controller_password" {
  default = "admin"
}

variable "resource_name" {
  default = "edl_github"
  
}

variable "timeout" {
  default = 30
}

variable "frequency_minutes" {
  default = 5
  
}

# List of services to be created as SmartGroups
variable "git_services" {
  default = ["git","web"] 
}