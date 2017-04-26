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

    usage: marathon_deployer [-h] --baseurl BASEURL --access-token ACCESS_TOKEN
                             json
    marathon_deployer: error: the following arguments are required: --baseurl, --access-token, json

When executed with the -h parameter the following output is given:
    
    usage: marathon_deployer [-h] --baseurl BASEURL --access-token ACCESS_TOKEN
                             json
    
    Script for Mesos application orchestration using Marathon
    
    positional arguments:
      json                  file containing marathon application JSON
    
    optional arguments:
      -h, --help            show this help message and exit
      --baseurl BASEURL     base URL of marathon service
      --access-token ACCESS_TOKEN
                            cookie for authentication on marathon`

To deploy an application both the baseurl and access-token is needed. 

```bash
./marathon_deployer mesos-marathon-application.json --baseurl https://marathon.host.com:8443 --access-token my_secret_access_token
```

## Script behaviour

This section describes how the script behaves in various scenarios.

### New application

When the application does not exist beforehand it will be deployed as a new application using post on the application id:

    POST /v2/apps

### Existing application

If an application with the same application id already exist in marathon one of two different scenarios can happen:
 - The application config is changed 
 - The application config is not changed

#### Changed application config

(write more)

#### Unchanged application config

(write more)
