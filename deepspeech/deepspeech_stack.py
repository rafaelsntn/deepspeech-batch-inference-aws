from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    Duration,
    RemovalPolicy,
    aws_iam as iam,
    aws_batch as batch,
    aws_events as events,
    aws_events_targets as targets,
    Aws
)
from aws_cdk.aws_ecr_assets import DockerImageAsset
from constructs import Construct
import os.path
dirname = os.path.dirname(__file__)

BATCH_IMAGE_REPO_NAME = 'batch-ecr'
BATCH_JOB_QUEUE_NAME = 'batch-queue'
BATCH_JOB_NAME = 'deepspeech-job'
INPUT_BUCKET_NAME = 'deepspeech-bucket'
INPUT_BUCKET_ARN = f'{INPUT_BUCKET_NAME}-{Aws.ACCOUNT_ID}-{Aws.REGION}'
PREFIX = 'deepspeech'

class DeepspeechStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    # VPC for ec2
    self.vpc = ec2.Vpc(self, f'{PREFIX}-vpc',
      cidr="10.0.0.0/16",
      max_azs=2,
      nat_gateways=0
    )

    self.batchSg = ec2.SecurityGroup(self, f'{PREFIX}-batch-sg',
      vpc=self.vpc,
      security_group_name=f'{PREFIX}-batch-sg',
    )

    self.batchSg.add_ingress_rule(
      ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
      ec2.Port.all_traffic()
    )

    batch_inf_image = DockerImageAsset(self, f'{PREFIX}-image',
      directory=os.path.join(dirname, "..", "docker_image"),
    )

    # Roles
    batchJobRole = iam.Role(self, "DeepspeechBatchJobRole", 
      assumed_by=iam.CompositePrincipal(
        iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        iam.ServicePrincipal("ec2.amazonaws.com")
      ),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
          "service-role/AmazonECSTaskExecutionRolePolicy"
        ),
        iam.ManagedPolicy.from_aws_managed_policy_name(
          "service-role/AmazonEC2ContainerServiceforEC2Role"
        ),
      ],
    )
    batchJobExecRole = iam.Role(self, "DeepspeechBatchExecRole",
      assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
          "service-role/AmazonECSTaskExecutionRolePolicy"
        ),
      ],
    )
    compEnvSvcRole = iam.Role.from_role_arn(
      self,
      f'{PREFIX}-compute-role',
      f'arn:aws:iam::{Aws.ACCOUNT_ID}:role/aws-service-role/batch.amazonaws.com/AWSServiceRoleForBatch'
    )

    # Job definition
    batchComputeEnv = batch.CfnComputeEnvironment(
      self,
      f'{PREFIX}-compute-env',
        compute_environment_name=f'{PREFIX}-compute-env',
        type="MANAGED",
        state="ENABLED",
        compute_resources=batch.CfnComputeEnvironment.ComputeResourcesProperty(
          type="FARGATE",
          maxv_cpus=2,
          subnets=[
            self.vpc.public_subnets[0].subnet_id,
            self.vpc.public_subnets[1].subnet_id,
          ],
          security_group_ids=[self.batchSg.security_group_id]
        ),
        service_role=compEnvSvcRole.role_arn,
    )

    batchJobDef = batch.CfnJobDefinition(
      self,
      f'{PREFIX}-job-def',
      job_definition_name=f'{PREFIX}-job-def',
      retry_strategy=batch.CfnJobDefinition.RetryStrategyProperty(
        attempts=1
      ),
      type="container",
      platform_capabilities=["FARGATE"],
      container_properties=batch.CfnJobDefinition.ContainerPropertiesProperty(
        image=f'{batch_inf_image.image_uri}',
        network_configuration=batch.CfnJobDefinition.NetworkConfigurationProperty(
            assign_public_ip="ENABLED"
        ),
        resource_requirements=[
          batch.CfnJobDefinition.ResourceRequirementProperty(
              type="VCPU",
              value="2"
          ),
          batch.CfnJobDefinition.ResourceRequirementProperty(
              type="MEMORY",
              value="4096"
          )
        ],
        job_role_arn=batchJobRole.role_arn,
        execution_role_arn=batchJobExecRole.role_arn,
        command=["python3", "inference.py"],
      )
    )

    # Job access to S3
    s3_actions = ["*"];
    batchJobRole.add_to_policy(
      iam.PolicyStatement(
        resources=[f'arn:aws:s3:::{INPUT_BUCKET_ARN}', f'arn:aws:s3:::{INPUT_BUCKET_ARN}/*'],
        actions=s3_actions,
        effect=iam.Effect.ALLOW,
      )
    )
    batchJobExecRole.add_to_policy(
      iam.PolicyStatement(
        resources=[f'arn:aws:s3:::{INPUT_BUCKET_ARN}', f'arn:aws:s3:::{INPUT_BUCKET_ARN}/*'],
        actions=s3_actions,
        effect=iam.Effect.ALLOW,
      )
    )

    batchJobDef.node.add_dependency(batch_inf_image)

    # Queue
    batchJobQ = batch.CfnJobQueue(
      self,
      f'{PREFIX}-{BATCH_JOB_QUEUE_NAME}',
      compute_environment_order=[
          batch.CfnJobQueue.ComputeEnvironmentOrderProperty(
              compute_environment=batchComputeEnv.ref,
              order=1
          )
        ],
        priority=1,
        state="ENABLED",
        job_queue_name=BATCH_JOB_QUEUE_NAME,
    )

    batchJobSubmitterPolicy = iam.PolicyStatement(
      effect=iam.Effect.ALLOW,
      actions=[
        "batch:DescribeJobQueues",
        "batch:DescribeJobs",
        "batch:DescribeJobDefinitions",
        "batch:ListJobs",
        "batch:DescribeComputeEnvironments",
        "batch:UntagResource",
        "batch:DeregisterJobDefinition",
        "batch:TerminateJob",
        "batch:CancelJob",
        "batch:ListTagsForResource",
        "batch:SubmitJob",
        "batch:RegisterJobDefinition",
        "batch:TagResource",
        "batch:UpdateJobQueue",
      ],
      resources=[
        f'arn:aws:batch:{Aws.REGION}:{Aws.ACCOUNT_ID}:job/*',
        f'arn:aws:batch:{Aws.REGION}:{Aws.ACCOUNT_ID}:job-definition/{batchJobDef.job_definition_name}:*',
        f'arn:aws:batch:{Aws.REGION}:{Aws.ACCOUNT_ID}:job-queue/{batchJobQ.job_queue_name}',
        f'arn:aws:batch:{Aws.REGION}:{Aws.ACCOUNT_ID}:compute-environment/{batchComputeEnv.compute_environment_name}',
      ],
    )

    s3_lambda_policy = iam.PolicyStatement(
      effect=iam.Effect.ALLOW,
      actions=["s3:ListBucket", "s3:GetObject"],
      resources=[f'arn:aws:s3:::{INPUT_BUCKET_ARN}', f'arn:aws:s3:::{INPUT_BUCKET_ARN}/*']
    )

    # S3
    bucket = s3.Bucket(
        self,
        INPUT_BUCKET_NAME,
        bucket_name=INPUT_BUCKET_ARN,
        removal_policy=RemovalPolicy.DESTROY,
        auto_delete_objects=True
    )

    # Lambda function
    _lambdafunc = _lambda.Function(self, f"{PREFIX}-batch-fn",
      runtime=_lambda.Runtime.PYTHON_3_7,
      code=_lambda.Code.from_asset(os.path.join(dirname, "..", "lambda_files")),
      handler="check_files.handler",
      timeout=Duration.seconds(30),
      memory_size=256,
      environment={
        "JOB_NAME":BATCH_JOB_NAME,
        "JOB_QUEUE":batchJobQ.ref,
        "JOB_DEFINITION":batchJobDef.ref,
        "S3_BUCKET_NAME":INPUT_BUCKET_ARN
      }
    )
    _lambdafunc.add_to_role_policy(batchJobSubmitterPolicy)
    _lambdafunc.add_to_role_policy(s3_lambda_policy)


    event_lambda_rule = events.Rule(
      self,
      'eventLambdaRuleDeepspeech',
      schedule=events.Schedule.cron(minute='0', hour='1')
    )
    event_lambda_rule.add_target(targets.LambdaFunction(_lambdafunc))
