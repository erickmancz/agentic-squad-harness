#!/usr/bin/env python3
"""App CDK do Agentic Squad Harness (ASH)."""
import os

import aws_cdk as cdk

from stacks.code_stack import AshCodeStack
from stacks.metrics_stack import AshMetricsStack
from stacks.proto_stack import AshProtoStack

app = cdk.App()
env = cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
                      region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"))

AshCodeStack(app, "AshCodeStack", env=env,
             description="ASH: bucket privado e versionado para backup do repositório (git bundle)")
AshMetricsStack(app, "AshMetricsStack", env=env,
                description="ASH: coletor de métricas serverless (S3, Lambda, DynamoDB, Scheduler)")
AshProtoStack(app, "AshProtoStack", env=env,
              description="ASH: hospedagem de protótipo (S3 privado + CloudFront OAC, WAF, TLS)")

ctx = app.node.try_get_context
for chave, valor in {
    "accelerator": "agentic-squad-harness",
    "owner": ctx("owner"),
    "cost-center": ctx("costCenter"),
    "env": ctx("env"),
}.items():
    if valor:
        cdk.Tags.of(app).add(chave, str(valor))

app.synth()
