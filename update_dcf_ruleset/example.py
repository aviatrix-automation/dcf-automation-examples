# Import necessary libraries
import json
import os
import requests
import logging

# Disable certificate warnings
import urllib3
urllib3.disable_warnings()

logging.basicConfig(level=logging.DEBUG)


# Main event handler function
def handler(event, context):
    # Parse the body from the event
    body = json.loads(event['body'])

    # Login to the controller and get the CID
    cid = login(os.getenv("CONTROLLER_IP"), os.getenv(
        "CONTROLLER_USER"), os.getenv("CONTROLLER_PASSWORD"))

    # Log the cid
    logging.debug("CID: {}".format(cid))
    logging.debug("ACTION {}".format(body["action"]) )

    # Sanitize accepted inputs
    action = body["action"]
    if action == "ADD_RULE":
        new_policy_list = None
        rule_uuid = None
        rule = body["rule"]
    elif action == "DELETE_RULE":
        new_policy_list = None
        rule_uuid = body["rule_uuid"]
        rule = None
    elif action == "REPLACE_RULE":
        new_policy_list = None
        rule_uuid = body["rule_uuid"]
        rule = body["rule"]
    elif action == "REPLACE_LIST":
        new_policy_list = body["policy_list"]
        priority = None
        rule = None

    # Call the function to update the IP with necessary parameters
    result = update_policy_list(controller_ip=os.getenv("CONTROLLER_IP"), cid=cid,
                                action=action, new_policy_list=new_policy_list, rule_uuid=rule_uuid, rule=rule)

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
def update_policy_list(controller_ip, cid, action, rule=None, new_policy_list=None, rule_uuid=None):
    # URL for the controller API
    url = "https://{}/v2.5/api".format(controller_ip)
    # Parameters to send for the GET request
    headers = {
        "Authorization": "cid {}".format(cid)
    }

    # Log the cid
    logging.debug("Headers: {}".format(headers))

    # Make a GET request to get current SmartGroups
    response = requests.get("https://{}/v2.5/api/microseg/policy-list".format(
        controller_ip), headers=headers, verify=False)
    logging.debug("Response for Existing Policy List: {} {}".format(
        response.status_code, response.text))
    response = response.json()

    # Extract current rules from policy list Smartgroup
    policies = response['policies']
    logging.debug("Existing Policies: {}".format(policies))

    # current_cidrs = [x["all"]["cidr"]
    #                    for x in smartgroup["selector"]["any"]]

    # Depending on the action, calculate the new configured policies
    if action == "ADD_RULE":
        logging.debug("NEW RULE: {}".format(json.dumps(rule)))
        new_policy_config = policies + [rule]
    elif action == "DELETE_RULE":
        new_policy_config = [
            x for x in policies if x['uuid'] != rule_uuid]
    elif action == "REPLACE_RULE":
        rule_uuid = rule["uuid"]
        new_policy_config = [
            x for x in policies if x['uuid'] != rule_uuid]
        new_policy_config.append(rule)
    elif action == "REPLACE_LIST":
        new_policy_config = new_policy_list
    else:
        return {"result": "Failed Invalid Action - supports ADD_RULE, DELETE_RULE, REPLACE_RULE, REPLACE_LIST"}

    logging.debug("New Configured Policies: {}".format(json.dumps(new_policy_config)))

    # Format the new policy list payload
    if action != "REPLACE_LIST":
        payload = {
            "policies": new_policy_config
        }     
    else:
        payload = new_policy_config

    logging.debug("New Policy Config: {}".format(
        json.dumps(payload)))

    # Make a POST request to set the policies
    response = requests.put("https://{}/v2.5/api/microseg/policy-list".format(
        controller_ip), json=payload, headers=headers, verify=False)

    # Log the response
    logging.debug("Response to Policy Update: {} {}".format(
        response.status_code, response.text))

    # Return the results and current filter list
    return {"result": response.json()}


# Test execution to add "aviatrix.com" to the WebGroup - replace SmartGroup UUID and Domains for testing
test_body_add_rule = {"action": "ADD_RULE",
                      "rule":        {
                          "name": "CATCH_ALL",
                          "action": "PERMIT",
                          "src_ads": [
                              "def000ad-0000-0000-0000-000000000000"
                          ],
                          "dst_ads": [
                              "def000ad-0000-0000-0000-000000000000"
                          ],
                          "priority": 1000,
                          "exclude_sg_orchestration": False,
                          "port_ranges": [],
                          "protocol": "PROTOCOL_UNSPECIFIED",
                          "logging": False,
                          "watch": False,
                          "ruleset": 0,
                          "ruleset_name": "",
                          "web_filters": [],
                          "nested_rules": [],
                          "flow_app_requirement": "APP_UNSPECIFIED",
                          "system_resource": False,
                          "decrypt_policy": "DECRYPT_UNSPECIFIED",
                          "desc": ""
                      }}

test_body_replace_rule = {"action": "REPLACE_RULE",
                            "rule_uuid": "ef6f3d49-b42a-442c-9d05-093b0f1903b1",
                          "rule":        {
                              "uuid": "ef6f3d49-b42a-442c-9d05-093b0f1903b1",
                              "name": "CATCH_ALL_IDS1",
                              "action": "PERMIT",
                              "src_ads": [
                                  "def000ad-0000-0000-0000-000000000000"
                              ],
                              "dst_ads": [
                                  "def000ad-0000-0000-0000-000000000000"
                              ],
                              "priority": 1001,
                              "exclude_sg_orchestration": False,
                              "port_ranges": [],
                              "protocol": "PROTOCOL_UNSPECIFIED",
                              "logging": False,
                              "watch": False,
                              "ruleset": 0,
                              "ruleset_name": "",
                              "web_filters": [],
                              "nested_rules": [],
                              "flow_app_requirement": "APP_UNSPECIFIED",
                              "system_resource": False,
                              "decrypt_policy": "DECRYPT_UNSPECIFIED",
                              "desc": ""
                          }}

test_body_delete_rule = {"action": "DELETE_RULE", "rule_uuid":"ef6f3d49-b42a-442c-9d05-093b0f1903b1"}

## UNCOMMENT TO TEST SPECIFIC CASES
## ADD A RULE
# print(handler(
#     {"body": json.dumps(test_body_add_rule)}, None))

## REPLACE A RULE - MAKE SURE THE PAYLOAD INCLUDES THE CORRECT RULE UUID - CAN BE GLEANED FROM THE OUTPUT OF THE ADD_RULE ACTION
# print(handler(
#     {"body": json.dumps(test_body_replace_rule)}, None))

## DELETE A RULE - MAKE SURE THE PAYLOAD INCLUDES THE CORRECT RULE UUID - CAN BE GLEANED FROM THE OUTPUT OF THE ADD_RULE ACTION
# print(handler(
#     {"body": json.dumps(test_body_delete_rule)}, None))