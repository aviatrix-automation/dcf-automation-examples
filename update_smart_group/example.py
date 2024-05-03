# Import necessary libraries
import json
import os
import requests
import logging

# Disable certificate warnings
import urllib3
urllib3.disable_warnings()

logging.basicConfig(level=logging.INFO)


# Main event handler function
def handler(event, context):
    # Parse the body from the event
    body = json.loads(event['body'])

    # Login to the controller and get the CID
    cid = login(os.getenv("CONTROLLER_IP"), os.getenv(
        "CONTROLLER_USER"), os.getenv("CONTROLLER_PASSWORD"))

    # Log the cid
    logging.debug("CID: {}".format(cid))

    # Call the function to update the IP with necessary parameters
    result = update_smartgroup_cidrs(os.getenv("CONTROLLER_IP"),
                                     body["smartgroup_uuid"], body["domains"], cid, body["action"])

    # Format and return the response
    response = {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(result)
    }

    return response

# Function to login to the controller


def login(controller_ip, controller_user, controller_password):
    # URL for the controller API
    url = "https://{}/v2/api".format(controller_ip)
    # Payload to send for login
    payload = {'action': 'login',
               'username': controller_user,
               'password': controller_password}

    headers = {}

    # Make a POST request to the URL with the payload
    response = requests.post(url, headers=headers, data=payload, verify=False)

    # Return the CID from the response
    return response.json()["CID"]


# Function to update the a Webgroup type SmartGroup by adding or removing a domain.  Input is a list of domains to add or remove.
def update_smartgroup_cidrs(controller_ip, smartgroup_uuid, cidrs, cid, action):
    # URL for the controller API
    url = "https://{}/v2.5/api".format(controller_ip) 
    # Parameters to send for the GET request
    headers = {
        "Authorization": "cid {}".format(cid)
    }

    # Log the cid
    logging.debug("Headers: {}".format(headers))

    # Make a GET request to get current SmartGroups
    response = requests.get("https://{}/v2.5/api/app-domains".format(
        controller_ip), headers=headers, verify=False)
    logging.debug("Response for Existing SmartGroups: {} {}".format(response.status_code,response.text))
    response = response.json()

    # Extract current domains from target Smartgroup
    smartgroup = [x for x in response['app_domains']
                  if x["uuid"] == smartgroup_uuid]
    if len(smartgroup) > 0:
        smartgroup = smartgroup[0]
    else:
        logging.info("Current SmartGroups: {}".format(json.dumps(response)))
        return {"result": "Invalid SmartGroup UUID"}

    current_cidrs = [x["all"]["cidr"]
                       for x in smartgroup["selector"]["any"]]

    # Depending on the action, calculate the new configured policies
    if action == "ADD":
        new_configured_policies = list(set(current_cidrs) | set(cidrs))
    elif action == "DELETE":
        new_configured_policies = list(set(current_cidrs) - set(cidrs))
    else:
        return {"result": "Failed Invalid Action - supports ADD or DELETE"}

    # Format the new SmartGroup/WebGroup payload
    selector = []
    for cidr in new_configured_policies:
        selector.append({
            "all": {
                "cidr": cidr
            }
        })
    smartgroup_config = {
        "name": smartgroup["name"],
        "selector": {
            "any": selector
        }
    }

    logging.debug("SmartGroup Config: {}".format(json.dumps(smartgroup_config)))

    # Make a POST request to set the policies
    response = requests.put("https://{}/v2.5/api/app-domains/{}".format(
        controller_ip, smartgroup_uuid), json=smartgroup_config, headers=headers, verify=False)
    
    # Log the response
    logging.debug("Response to SmartGroup Update: {} {}".format(response.status_code,response.text))

    # Return the results and current filter list
    return {"result": response.json()}


# Test execution to add "aviatrix.com" to the WebGroup - replace SmartGroup UUID and Domains for testing
test_body = {"smartgroup_uuid": "6ab5ee9a-6e59-4552-81dd-522804a086e4",
             "domains": ["10.0.0.0/8"],
             "action": "ADD"}

print(handler(
    {"body": json.dumps(test_body)}, None))
