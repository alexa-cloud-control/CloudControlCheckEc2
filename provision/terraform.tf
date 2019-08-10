terraform {
  backend "s3" {
    bucket         = "pawel-terraform-state"
    encrypt        = true
    key            = "terraformstates/CloudControlCheckEc2.tfstate"
    dynamodb_table = "alexa-cloud-control-locks"
    region         = "eu-west-1"
    profile        = "pawel"
  }
}
