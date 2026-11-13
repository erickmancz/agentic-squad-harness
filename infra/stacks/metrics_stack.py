"""Coletor de métricas ASH: 100% determinístico, pago por uso, sem VPC."""
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import aws_dynamodb as ddb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_notifications as s3n
from aws_cdk import aws_scheduler as scheduler
from constructs import Construct

LAMBDAS = Path(__file__).resolve().parent.parent / "lambdas"


class AshMetricsStack(cdk.Stack):
    def __init__(self, scope: Construct, cid: str, **kw) -> None:
        super().__init__(scope, cid, **kw)
        ctx = self.node.try_get_context
        dias_raw = int(ctx("eventsRawDays") or 90)
        retencao = logs.RetentionDays.ONE_MONTH

        def bucket(nome: str, regras=None) -> s3.Bucket:
            return s3.Bucket(
                self, nome,
                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                encryption=s3.BucketEncryption.S3_MANAGED,
                enforce_ssl=True,
                object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
                removal_policy=cdk.RemovalPolicy.DESTROY,
                auto_delete_objects=True,
                lifecycle_rules=regras or [],
            )

        eventos = bucket("EventsBucket", [s3.LifecycleRule(id="raw", prefix="raw/",
                                                            expiration=cdk.Duration.days(dias_raw))])
        relatorios = bucket("ReportsBucket")

        tabela = ddb.Table(
            self, "MetricsTable",
            table_name="ash-metrics",
            partition_key=ddb.Attribute(name="pk", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="sk", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        def funcao(nome: str, pasta: str, timeout: int, env: dict) -> lambda_.Function:
            grupo = logs.LogGroup(self, f"{nome}Logs", log_group_name=f"/aws/lambda/{nome}",
                                  retention=retencao, removal_policy=cdk.RemovalPolicy.DESTROY)
            fn = lambda_.Function(
                self, nome.replace("-", "_"),
                function_name=nome,
                runtime=lambda_.Runtime.PYTHON_3_12,
                architecture=lambda_.Architecture.ARM_64,
                handler="handler.handler",
                code=lambda_.Code.from_asset(str(LAMBDAS / pasta)),
                memory_size=256,
                timeout=cdk.Duration.seconds(timeout),
                tracing=lambda_.Tracing.ACTIVE,
                log_group=grupo,
                environment=env,
            )
            return fn

        ingest = funcao("ash-ingest", "ingest", 60, {"TABLE": tabela.table_name})
        ingest.configure_async_invoke(retry_attempts=0)
        tabela.grant_write_data(ingest)
        eventos.grant_read(ingest, "raw/*")
        eventos.add_event_notification(s3.EventType.OBJECT_CREATED, s3n.LambdaDestination(ingest),
                                       s3.NotificationKeyFilter(prefix="raw/", suffix=".jsonl"))

        report = funcao("ash-report", "report", 120,
                        {"TABLE": tabela.table_name, "REPORTS_BUCKET": relatorios.bucket_name})
        tabela.grant_read_data(report)
        relatorios.grant_put(report, "reports/*")

        papel = iam.Role(self, "SchedulerRole", assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"))
        report.grant_invoke(papel)
        scheduler.CfnSchedule(
            self, "WeeklyReport",
            name="ash-relatorio-semanal",
            schedule_expression="cron(0 8 ? * MON *)",
            schedule_expression_timezone="America/Sao_Paulo",
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(mode="OFF"),
            target=scheduler.CfnSchedule.TargetProperty(
                arn=report.function_arn, role_arn=papel.role_arn,
                retry_policy=scheduler.CfnSchedule.RetryPolicyProperty(maximum_retry_attempts=1),
            ),
        )

        cdk.CfnOutput(self, "EventsBucketName", value=eventos.bucket_name)
        cdk.CfnOutput(self, "ReportsBucketName", value=relatorios.bucket_name)
        cdk.CfnOutput(self, "MetricsTableName", value=tabela.table_name)
