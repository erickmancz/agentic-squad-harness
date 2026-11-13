"""Stack de protótipo: S3 privado servido por CloudFront (OAC), com TLS, cabeçalhos de segurança e WAF.

Segue a base de segurança da fase de descoberta (05-descoberta-produto): bucket privado via OAC,
nada público direto no S3, TLS mínimo, rate-limit no WAF. O protótipo é conteúdo fictício e navegável;
nenhum dado pessoal. A publicação dos arquivos é feita pelo portão publicar-proto (aws s3 sync +
invalidação), não pela stack.
"""
import aws_cdk as cdk
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_wafv2 as waf
from constructs import Construct


class AshProtoStack(cdk.Stack):
    def __init__(self, scope: Construct, cid: str, **kw) -> None:
        super().__init__(scope, cid, **kw)

        bucket = s3.Bucket(
            self, "ProtoBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        # Cabeçalhos de segurança na resposta do CloudFront.
        headers = cloudfront.ResponseHeadersPolicy(
            self, "ProtoHeaders",
            security_headers_behavior=cloudfront.ResponseSecurityHeadersBehavior(
                content_type_options=cloudfront.ResponseHeadersContentTypeOptions(override=True),
                frame_options=cloudfront.ResponseHeadersFrameOptions(
                    frame_option=cloudfront.HeadersFrameOption.DENY, override=True),
                referrer_policy=cloudfront.ResponseHeadersReferrerPolicy(
                    referrer_policy=cloudfront.HeadersReferrerPolicy.NO_REFERRER, override=True),
                strict_transport_security=cloudfront.ResponseHeadersStrictTransportSecurity(
                    access_control_max_age=cdk.Duration.days(365), include_subdomains=True, override=True),
            ),
        )

        # WAF com rate-limit por IP (2000 req / 5 min), associado ao CloudFront (escopo CLOUDFRONT em us-east-1).
        acl = waf.CfnWebACL(
            self, "ProtoWebAcl",
            default_action=waf.CfnWebACL.DefaultActionProperty(allow={}),
            scope="CLOUDFRONT",
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True, metric_name="ash-proto-acl", sampled_requests_enabled=True),
            rules=[waf.CfnWebACL.RuleProperty(
                name="rate-limit",
                priority=0,
                action=waf.CfnWebACL.RuleActionProperty(block={}),
                statement=waf.CfnWebACL.StatementProperty(
                    rate_based_statement=waf.CfnWebACL.RateBasedStatementProperty(
                        limit=2000, aggregate_key_type="IP")),
                visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                    cloud_watch_metrics_enabled=True, metric_name="ash-proto-rate", sampled_requests_enabled=True),
            )],
        )

        dist = cloudfront.Distribution(
            self, "ProtoDist",
            default_root_object="index.html",
            minimum_protocol_version=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
            web_acl_id=acl.attr_arn,
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                response_headers_policy=headers,
            ),
        )

        cdk.CfnOutput(self, "ProtoBucketName", value=bucket.bucket_name)
        cdk.CfnOutput(self, "ProtoDistributionId", value=dist.distribution_id)
        cdk.CfnOutput(self, "ProtoDomainName", value=dist.distribution_domain_name)
