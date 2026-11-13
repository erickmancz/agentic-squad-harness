"""Bucket de código: privado, versionado, criptografado e mantido mesmo se a stack for apagada."""
import aws_cdk as cdk
from aws_cdk import aws_s3 as s3
from constructs import Construct


class AshCodeStack(cdk.Stack):
    def __init__(self, scope: Construct, cid: str, **kw) -> None:
        super().__init__(scope, cid, **kw)
        dias = int(self.node.try_get_context("codeNoncurrentDays") or 180)
        bucket = s3.Bucket(
            self, "CodeBucket",
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            lifecycle_rules=[s3.LifecycleRule(
                id="versoes-antigas",
                noncurrent_version_expiration=cdk.Duration.days(dias),
                abort_incomplete_multipart_upload_after=cdk.Duration.days(7),
            )],
        )
        cdk.CfnOutput(self, "CodeBucketName", value=bucket.bucket_name)
