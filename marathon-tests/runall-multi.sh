#!/bin/bash

#
# Please notice. This is not an automated test.
# An app in different configurations is deployed to marathon,
# but you need to check the output yourself to see if it matches the tests.
#


MARATHON_HOST=$1
ACCESS_TOKEN=$2

echo $MARATHON_HOST
echo $ACCESS_TOKEN

DEPLOYER=../marathon-deployer

echo
echo
echo "*** Test create"
# Create a simple app which just listens to a port. Healthcheck is ok.
cat 101-create.json | $DEPLOYER --baseurl $MARATHON_HOST --access-token $ACCESS_TOKEN -

echo
echo
echo "*** Test restart"
# When using the exact same marathon config as the running or a subset of it, it will trigger a restart
cat 101-create.json | $DEPLOYER --baseurl $MARATHON_HOST --access-token $ACCESS_TOKEN -

echo
echo
echo "*** Test update/scale_only"
# Test that when only changing the instances parameter the application will scale
cat 102-scale.json | $DEPLOYER --baseurl $MARATHON_HOST --access-token $ACCESS_TOKEN -

echo
echo
echo "*** Test restart"
# When scale only conatains the same number of instances as running on marathon, it is a restart
cat 102-scale.json | $DEPLOYER --baseurl $MARATHON_HOST --access-token $ACCESS_TOKEN -

echo
echo
echo "*** Test update/no scale"
# updateing mem and cpus. instances is not changed. This should trigger an update
cat 103-update-no-scale.json | $DEPLOYER --baseurl $MARATHON_HOST --access-token $ACCESS_TOKEN -

echo
echo
echo "*** Test restart"
# no changes to last version. This should be a restart.
cat 103-update-no-scale.json | $DEPLOYER --baseurl $MARATHON_HOST --access-token $ACCESS_TOKEN -

echo
echo
echo "*** Test update and scale"
# updateing to original changes both mem, cpus and instances. This should still trigger an update
cat 101-create.json | $DEPLOYER --baseurl $MARATHON_HOST --access-token $ACCESS_TOKEN -
# restart for this case is already testet!

echo
echo
echo "*** Test suspend: update/scale only"
# Giving zero instances should effectivley be a suspend and
cat 104-suspend.json | $DEPLOYER --baseurl $MARATHON_HOST --access-token $ACCESS_TOKEN -

echo
echo
echo "*** Test restart"
# Giving zero instances to a suspend app should actually be a restart
cat 104-suspend.json | $DEPLOYER --baseurl $MARATHON_HOST --access-token $ACCESS_TOKEN -
