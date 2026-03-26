data "aws_caller_identity" "current" {}

# S3 bucket for deploy artifacts
resource "aws_s3_bucket" "deploy" {
  bucket = "centpai-deploy-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "deploy" {
  bucket                  = aws_s3_bucket.deploy.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM user for GitHub Actions
resource "aws_iam_user" "github_actions" {
  name = "centpai-github-actions"
}

resource "aws_iam_user_policy" "github_actions" {
  name = "centpai-github-actions-policy"
  user = aws_iam_user.github_actions.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:GetObject"]
        Resource = "${aws_s3_bucket.deploy.arn}/centpai/*"
      },
      {
        Effect = "Allow"
        Action = ["ssm:SendCommand"]
        Resource = [
          "arn:aws:ec2:*:*:instance/${aws_instance.centpai.id}",
          "arn:aws:ssm:*::document/AWS-RunShellScript",
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:GetCommandInvocation"]
        Resource = "*"
      },
    ]
  })
}

resource "aws_iam_access_key" "github_actions" {
  user = aws_iam_user.github_actions.name
}

# S3 read access for EC2 to download deploy artifacts
resource "aws_iam_role_policy" "ec2_s3_read" {
  name = "centpai-ec2-s3-read"
  role = aws_iam_role.centpai.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.deploy.arn}/centpai/*"
      },
    ]
  })
}

output "github_actions_access_key_id" {
  description = "Add this as AWS_ACCESS_KEY_ID in GitHub Actions secrets"
  value       = aws_iam_access_key.github_actions.id
}

output "github_actions_secret_access_key" {
  description = "Add this as AWS_SECRET_ACCESS_KEY in GitHub Actions secrets"
  value       = aws_iam_access_key.github_actions.secret
  sensitive   = true
}

output "deploy_bucket_name" {
  description = "Add this as DEPLOY_BUCKET in GitHub Actions secrets"
  value       = aws_s3_bucket.deploy.bucket
}

output "ec2_instance_id" {
  description = "Add this as EC2_INSTANCE_ID in GitHub Actions secrets"
  value       = aws_instance.centpai.id
}
