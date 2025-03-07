# How it works

## Terminology

The core functionality workflow of Meadowrun is to run a **job** from a **client** (e.g.
your laptop), via [run_function][meadowrun.run_function],
[run_command][meadowrun.run_command], or [run_map][meadowrun.run_map]. The job will run
on a **worker** which is usually on an **instance** (i.e. a remote machine). A single
instance can have one or more workers on it.


## Account
Meadowrun operates entirely in your AWS/Azure account and does not depend on any
external services. The Meadowrun client uses the credentials stored by the AWS/Azure
command line tools and so does not require any additional configuration to manage/access
your AWS/Azure account.


## Allocating jobs to instances

When you run a job, Meadowrun first looks for any existing instances that can
accommodate the CPU/memory requirements you specify. In order to do this, Meadowrun
keeps track of all Meadowrun-managed instances in a DynamoDB/Azure Table, which we'll
call the **instance allocation** table. This table also keeps track of what jobs have
been allocated to each instance and how much CPU/memory is available on each instance.
When you start a job, the Meadowrun client updates the instance allocation table to
reflect the allocation of that job to the chosen instance(s). When a job completes
normally, the worker tries to update the instance allocation table. If the worker
crashes  before it's able to do this, every instance has a **job deallocation** cron job
that reconciles what the instance allocation table says is running on that instance
compared to the actual processes that are running on that instance. (Each worker writes
a PID file so that the job deallocation cron job can correlate the job ids in the
instance allocation table with the process ids on the machine.)


## Starting and stopping instances

If there aren't enough instances to run your job, Meadowrun will launch one or more
instances for you, choosing the cheapest instance types that meet the CPU/memory
requirements you specify. Meadowrun will optionally choose spot instances, taking into
account the maximum interruption probability that you specify.

`meadowrun-manage-<cloud-provider> install`, will create AWS Lambdas/Azure Functions
that run periodically and adjust the number of running instances. Currently, this will
just terminate and deregister any instances that have been idle for more than 30
seconds, but in the future, we plan to support more complex policies.


## Client/worker communication

The Meadowrun client launches workers on remote machines/instances via SSH, and the
client/worker send data using files that are copied via SCP. On first run, the Meadowrun
client generates a private SSH key and stores it as an AWS Secret/Azure Secret. When the
Meadowrun client launches instances, it sets up the corresponding public key in the
instance so that it is able to SSH into the instance.

Each instance is launched with a Meadowrun image that has the Meadowrun worker
pre-installed, so the client just needs to run the `meadowrun-local` on the instance to
launch the worker. Each worker only lives for a single job.


## Deployment

Every job specifies a deployment, which is made up of an **interpreter** and optionally
**code**. The interpreter determines the python version and what libraries are
installed, and the code is "your code".

The options for an interpreter are:

  - A docker container image that you have built and made available in a container
  registry somewhere. In this case,the Meadowrun worker will pull the specified
  imagefrom the specified container registry. For container registries that require
  authentication, see the "Credentials" section.
  - A conda yaml file in your code. In this case, the Meadowrun worker will look for the
  file you specify in your code and create a docker image and run `conda env create -f
  <your file>` in it. This image will get cached in a Meadowrun-managed AWS/Azure
  container registry. (One of the AWS Lambdas/Azure Functions that run periodically will
  clean up images that haven't been used recently.)
  - *Supported on Linux only* *Supported on AWS only* A locally installed conda environment. In this case,
  Meadworun first runs conda locally (`conda env export`) to extract the conda yaml, and
  then proceeds as before. Since Meadowrun allocates Linux VMs, and conda environments
  are not cross-platform, doing this from Windows or Mac is currently not supported.
  There are a few approaches we are considering to work around this limitation. If this
  is important to you, please [open an
  issue](https://github.com/meadowdata/meadowrun/issues/new) describing your use case.

The options for code are:

- Code can be None, which makes sense if e.g. your pre-built docker container image
  already has all the code you need.
- A git repo. The Meadowrun worker will pull the specified branch/commit. For git repos
  that require authentication, see the "Credentials" section.
- *Supported on AWS only* Local python code. By default, Meadowrun can collect all
  Python code on `sys.path` that is not installed in a virtual environment (that should
  be taken care of via interpreter deployments). You can also add paths explicitly.
  Meadowrun zips all python files in these paths and uploads them to S3. The workers
  then unpack the zip file and add the paths back to `sys.path` in the right order.


### Credentials

Some deployments require credentials to e.g. pull a docker container image or a private
git repo. You can upload these credentials, e.g. a username/password or an SSH key, as
an AWS/Azure Secret, and provide Meadowrun with the name of the secret, and the
Meadowrun worker will get the credentials from the secret.


## Map jobs and tasks

Map jobs have one or more tasks, and one or more workers. Each worker can execute one or
more tasks, sequentially. In addition to the normal client/worker communication to start
the worker, the client needs a way to send tasks to each worker, get results back, and
either tell the worker to shut down or send it another task. We use AWS SQS/Azure Queues
for this purpose. There is one request queue that the client uses to send tasks to
workers, and a result queue that the workers use to send results back to the client. A
new pair of queues is created for each map job. (One of the AWS Lambdas/Azure Functions
that run periodically will clean up queues that haven't been used recently.)
