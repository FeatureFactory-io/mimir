from pathlib import Path

from aws_cdk import CustomResource, Duration, Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_route53 as route53
from aws_cdk.custom_resources import Provider
from constructs import Construct

# EB CNAME for the live production environment (stable label; follows CNAME swap).
EB_PROD_CNAME = "mimir-prod.eba-8hqkems3.us-east-1.elasticbeanstalk.com"

_LAMBDA_DIR = Path(__file__).resolve().parent.parent / "lambda" / "route53_cname"


class MimirDns(Stack):
    """CloudFront + Route53 CNAME for mimir.{domain} → EB origin.

    Viewer HTTPS terminates at CloudFront; origin is HTTP to the stable
    ``mimir-prod.eba-…`` label so ``swap-environment-cnames`` continues to
    route traffic without DNS updates on promote.

    Route53 uses an idempotent CNAME custom resource (same as Huginn CDN) so
    we can migrate from the legacy EB CNAME without manual console edits.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        domain: str,
        acm_cert_arn: str,
        hosted_zone: route53.IHostedZone | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._domain = domain
        self._acm_cert_arn = acm_cert_arn

        if hosted_zone is None:
            hosted_zone = route53.HostedZone.from_lookup(
                self, "Zone", domain_name=domain
            )

        distribution = self._create_distribution()
        self._upsert_cname(hosted_zone, distribution)

    def _create_distribution(self) -> cloudfront.Distribution:
        """CloudFront distribution: HTTPS viewer → HTTP EB origin."""
        cert = acm.Certificate.from_certificate_arn(
            self,
            "MimirCert",
            self._acm_cert_arn,
        )

        hsts_policy = cloudfront.ResponseHeadersPolicy(
            self,
            "HstsHeaders",
            security_headers_behavior=cloudfront.ResponseSecurityHeadersBehavior(
                strict_transport_security=cloudfront.ResponseHeadersStrictTransportSecurity(
                    access_control_max_age=Duration.seconds(3600),
                    override=True,
                    include_subdomains=True,
                ),
            ),
        )

        return cloudfront.Distribution(
            self,
            "MimirCdn",
            domain_names=[f"mimir.{self._domain}"],
            certificate=cert,
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.HttpOrigin(
                    EB_PROD_CNAME,
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
                response_headers_policy=hsts_policy,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
            ),
        )

    def _upsert_cname(
        self,
        hosted_zone: route53.IHostedZone,
        distribution: cloudfront.Distribution,
    ) -> None:
        """Idempotent CNAME upsert: mimir.{domain} → CloudFront domain."""
        on_event_fn = lambda_.Function(
            self,
            "Route53CnameFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.on_event",
            code=lambda_.Code.from_asset(str(_LAMBDA_DIR)),
            timeout=Duration.minutes(2),
        )

        on_event_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "route53:ListResourceRecordSets",
                    "route53:ChangeResourceRecordSets",
                ],
                resources=[
                    f"arn:aws:route53:::hostedzone/{hosted_zone.hosted_zone_id}",
                ],
            )
        )

        provider = Provider(self, "Route53CnameProvider", on_event_handler=on_event_fn)

        cname_resource = CustomResource(
            self,
            "MimirCnameResource",
            service_token=provider.service_token,
            properties={
                "HostedZoneId": hosted_zone.hosted_zone_id,
                "RecordName": f"mimir.{self._domain}.",
                "TargetDomain": distribution.distribution_domain_name,
                "Ttl": "300",
            },
        )
        cname_resource.node.add_dependency(distribution)
