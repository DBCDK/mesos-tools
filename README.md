<img src="http://www.dbc.dk/logo.png" alt="DBC" title="DBC" align="right">

# Mesos Tools

Scripts for Mesos application orchestration using Marathon.

# Requirements

The script is developed using python3 and tested against Marathon 1.4.1.

At this time the script does not support groups but only single application deployments.

# Getting Started

Using the scripts.

## Usage

When executed without parameters the following output is given:

```bash
$ ./marathon_deployer
usage: marathon_deployer [-h] -b BASEURL -a ACCESS_TOKEN [-j JSON]
marathon_deployer: error: the following arguments are required: -b/--baseurl, -a/--access-token
```

When executed with the -h parameter the following output is given:

```bash
$ ./marathon_deployer -h
usage: marathon_deployer [-h] -b BASEURL -a ACCESS_TOKEN json

Script for Mesos application orchestration using Marathon

positional arguments:
  json                  file containing marathon application JSON

optional arguments:
  -h, --help            show this help message and exit
  -b BASEURL, --baseurl BASEURL
                        base URL of marathon service
  -a ACCESS_TOKEN, --access-token ACCESS_TOKEN
                        cookie for authentication on marathon
```

To deploy an application both the baseurl and access-token is needed. 

```bash
./marathon_deployer -j mesos-marathon-application.json -b https://marathon.host.com:8443 -a my_secret_access_token
```

## Script behaviour

This section describes how the script behaves in various scenarios.

### New application

When the application does not exist beforehand it will be deployed as a new application using POST on the marathon apps 
endpoint:

    POST /v2/apps

#### Example

__New application__

```
$ ./marathon_deployer marathon-tests/001-create.json --baseurl https://marathon.host.com:8443 --access-token my_secret_access_token
2017-04-26 10:06:01,881 - Marathon - INFO - creating application /dev/mesos-tools/marathon-deployer-test-app
2017-04-26 10:06:02,417 - Marathon - INFO - waiting for version '2017-04-26T08:06:02.433Z' of application /dev/mesos-tools/marathon-deployer-test-app
2017-04-26 10:06:02,461 - Marathon - INFO - waiting for 3 running instance(s) of application /dev/mesos-tools/marathon-deployer-test-app
```

### Existing application

If an application with the same application id already exist in marathon one of two different scenarios can happen:
 - The application config is changed 
 - The application config is not changed

#### Changed application config

In this case the application has a changed application config and will then be updated using PUT on the marathon
application endpoint:
  
    PUT /v2/apps/{app_id}

#### Example

__Scale applcation__

```
$ ./marathon_deployer marathon-tests/002-update.json --baseurl https://marathon.host.com:8443 --access-token my_secret_access_token
2017-04-26 10:09:16,910 - Marathon - INFO - updating version '2017-04-26T08:06:02.433Z' of application /dev/mesos-tools/marathon-deployer-test-app
2017-04-26 10:09:17,465 - Marathon - INFO - waiting for version '2017-04-26T08:09:17.477Z' of application /dev/mesos-tools/marathon-deployer-test-app
2017-04-26 10:09:17,503 - Marathon - INFO - waiting for 5 running instance(s) of application /dev/mesos-tools/marathon-deployer-test-app
```

__Suspending application__

```
$ ./marathon_deployer marathon-tests/003-suspend.json -b https://marathon.host.com:8443 -a my_secret_access_token
2017-04-26 10:16:17,462 - Marathon - INFO - updating version '2017-04-26T08:12:05.580Z' of application /dev/mesos-tools/marathon-deployer-test-app
2017-04-26 10:16:18,193 - Marathon - INFO - waiting for version '2017-04-26T08:16:18.041Z' of application /dev/mesos-tools/marathon-deployer-test-app
2017-04-26 10:16:18,223 - Marathon - INFO - waiting for 0 running instance(s) of application /dev/mesos-tools/marathon-deployer-test-app
```

#### Unchanged application config

In this case the application config is unchanged and will only be restarted using the upgrade strategy already defined
in the application. The restart is done by posting to the marathon application restart endpoint:

    POST /v2/apps/{app_id}/restart

#### Example

__Unchanged application__

```
$ ./marathon_deployer marathon-tests/002-update.json -b https://marathon.host.com:8443 --access-token my_secret_access_token
2017-04-26 10:12:04,995 - Marathon - DEBUG - <...huge debug dump of json objects...>
2017-04-26 10:12:04,995 - Marathon - INFO - restarting version '2017-04-26T08:09:17.477Z' of application /dev/mesos-tools/marathon-deployer-test-app
2017-04-26 10:12:05,562 - Marathon - INFO - waiting for version '2017-04-26T08:12:05.580Z' of application /dev/mesos-tools/marathon-deployer-test-app
2017-04-26 10:12:05,589 - Marathon - INFO - waiting for 5 running instance(s) of application /dev/mesos-tools/marathon-deployer-test-app
```

# Todo/future wishes

 - Support groups
 - Multiple applications
 - Rollback of failed deployments after a user set timeout
