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
    # Login to the controller and get the CID
    cid = login(os.getenv("AVIATRIX_CONTROLLER_IP"), os.getenv(
        "AVIATRIX_USERNAME"), os.getenv("AVIATRIX_PASSWORD"))
    
    github_endpoints = json.loads(os.getenv("GITHUB_ENDPOINTS"))

    # Log the cid
    logging.debug("CID: {}".format(cid))

    github_ips = get_github_ips(github_endpoints)
    github_smartgroups = get_github_smartgroups(os.getenv("AVIATRIX_CONTROLLER_IP"), cid)

    updated_groups = []
    for endpoint in github_endpoints:
        updated_groups.append(update_github_smartgroup_cidrs(os.getenv("AVIATRIX_CONTROLLER_IP"), github_smartgroups, github_ips, endpoint, cid))

    # Format and return the response
    response = {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(updated_groups)
    }

    return response

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

def get_github_ips(github_endpoints):
    # Make a GET request to get the Github IPs
    response = requests.get("https://api.github.com/meta")
    response = response.json()

    #filter out the response to only include the requested keys in github_endpoints variable
    response = {key: response[key] for key in github_endpoints}
    return response

def filter_only_ipv4(ip_list):
    # Filter out only the IPv4 addresses
    return [x for x in ip_list if ":" not in x]

def get_github_smartgroups(controller_ip, cid):
    # URL for the controller API
    url = "https://{}/v2.5/api".format(controller_ip)
    # Parameters to send for the GET request
    headers = {
        "Authorization": "cid {}".format(cid)
    }

    # Make a GET request to get current SmartGroups
    response = requests.get("https://{}/v2.5/api/app-domains".format(
        controller_ip), headers=headers, verify=False)
    response = response.json()
    
    # Filter SmartGroups for when the name starts with "fqdn_"
    github_smartgroups = [x for x in response['app_domains'] if x["name"].startswith("external_github_")]
    return github_smartgroups

# Function to update the a Webgroup type SmartGroup by adding or removing a domain.  Input is a list of domains to add or remove.
def update_github_smartgroup_cidrs(controller_ip, github_smartgroups, github_ips, endpoint, cid):
    # URL for the controller API
    url = "https://{}/v2.5/api".format(controller_ip) 
    # Parameters to send for the GET request
    headers = {
        "Authorization": "cid {}".format(cid)
    }

    # Log the cid
    logging.debug("Headers: {}".format(headers))

    ## EXAMPLE SMARTGROUP JSON
    # [{'uuid': '60477a53-72d0-4175-a3f6-5b861b77cfed', 'name': 'external_github_git', 'selector': {'any': [{'all': {'cidr': '1.1.1.1'}}]}, 'system_resource': False}]

    ## EXAMPLE GITHUB ENDPOINT NAME
    # "git"

    smartgroup_name = "external_github_{}".format(endpoint)

    # Find the Smartgroup that matches the endpoint
    github_smartgroups = [x for x in github_smartgroups if x["name"] == smartgroup_name]

    # If no SmartGroup is found, set the created flag to True.  If a SmartGroup is found, set the created flag to False.
    created = False
    if len(github_smartgroups) > 0:
        created = True

    # Format the new SmartGroup/WebGroup payload
    selector = []
    for cidr in github_ips[endpoint]:
        # Filter out ipv6 addresses and add v4 addresses to the selector
        if ":" not in cidr:
            selector.append({
                "all": {
                    "cidr": cidr
                }
            })
    smartgroup_config = {
        "name": smartgroup_name,
        "selector": {
            "any": selector
        }
    }

    logging.debug("SmartGroup Config: {}".format(json.dumps(smartgroup_config)))

    # If the SmartGroup exists, extract the UUID and update the SmartGroup.  If the SmartGroup does not exist, create the SmartGroup.
    if created:
        smartgroup = github_smartgroups[0]
        # Make a PUT request to set the policies
        response = requests.put("https://{}/v2.5/api/app-domains/{}".format(
            controller_ip, smartgroup["uuid"]), json=smartgroup_config, headers=headers, verify=False)
    else: 
        # Make a POST request to create the SmartGroup
        response = requests.post("https://{}/v2.5/api/app-domains".format(
            controller_ip), json=smartgroup_config, headers=headers, verify=False)

    # Log the response
    logging.debug("Response to SmartGroup Update: {} {}".format(response.status_code,response.text))

    # Return the results and current filter list
    return {"result": response.json()}

print(handler(
    None, None))
