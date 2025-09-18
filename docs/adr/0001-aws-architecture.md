# ADR-0001: Arquitectura AWS (serverless friendly)
- API: FastAPI en AWS Lambda + API Gateway (REST). Alternativa: ECS Fargate.
- DB: RDS Postgres (free-tier, compartida).
- Front: S3 + CloudFront (PWA).
- Jobs: EventBridge (cron) -> Lambda.
- Secrets: AWS Secrets Manager.
Decisión: iniciar local + Render/Railway para staging; luego infra IaC a AWS.
