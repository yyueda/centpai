data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

resource "aws_security_group" "centpai" {
  name        = "centpai-sg"
  description = "Only allow HTTPS from Telegram Official IPs"

  ingress {
    from_port = 443
    to_port   = 443
    protocol  = "tcp"
    cidr_blocks = [
      "91.108.4.0/22",
      "149.154.160.0/20",
    ]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_role" "centpai" {
  name = "centpai-ec2-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.centpai.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "centpai" {
  name = "centpai-instance-profile"
  role = aws_iam_role.centpai.name
}

resource "aws_instance" "centpai" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"
  key_name               = "centpai"
  vpc_security_group_ids = [aws_security_group.centpai.id]
  iam_instance_profile   = aws_iam_instance_profile.centpai.name

  tags = {
    Name = "centpai"
  }
}
