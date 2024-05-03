variable "controller_ip" {
  
}

variable "controller_user" {
  
}

variable "controller_password" {
  default = "admin"
}

variable "resource_name" {
  default = "non_web_resolver"
  
}

variable "timeout" {
  default = 30
}

variable "frequency_minutes" {
  default = 5
  
}