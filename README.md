# COPA Alert

COPA is a local soccer training facility that provides subscription based
unlimited training classes. Both my kids go there for soccer practice during
soccer off-seasons. Often classes fill up quickly but become available again 
over time as people change their plans.

This python script can be used to poll COPA's instance of DaySmart Recreation,
their IT platform for scheduling, booking and organizing the various training
sessions. It will check the availability of given training sessions and will
output those that have any slots available.

## Configuration

An example configuration is provided in the repository. DaySmart Recreation
username and password have to be set, as well as your athlete's customer_id.
"teams" is how COPA maps their model onto  what DaySmart Recreation internally 
uses for their different training modes (e.g. Specialized Clinics, Speed Lab,
GAmeplay, etc). Since COPA creates new "teams" every quarter, you will have to
configure the ones you are interested in yourself.

Both the customer IDs as well as the team IDs can be retrieved from COPA's
DaySmart Recreation instance. Use the browsers debugging tools. To get the IDs
for the teams, look for requests to the `teams` endpoint and to get the customer
IDs look for requests to the `customers` endpoint. The responses will contain
the team IDs and customer IDs.

## Setup

I personally run this script once every hour and have it send me a push
notification to my phone should it find an open slot in one of the sessions I
have configured. I use Home Assistant for this, but you may want to use some
other setup depending on your needs.
