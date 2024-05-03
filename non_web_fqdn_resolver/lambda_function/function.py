# Import necessary libraries
import json
import os
import requests
import logging
import pydig

# Disable certificate warnings
import urllib3
urllib3.disable_warnings()

logging.basicConfig(level=logging.INFO)

# Main event handler function
def handler(event, context):

    # Login to the controller and get the CID
    cid = login(os.getenv("AVIATRIX_CONTROLLER_IP"), os.getenv(
        "AVIATRIX_USERNAME"), os.getenv("AVIATRIX_PASSWORD"))

    # Log the cid
    logging.debug("CID: {}".format(cid))

    result = get_fqdn_smartgroups(os.getenv("AVIATRIX_CONTROLLER_IP"), cid)

    updated_groups = []
    for smartgroup in result:
        updated_groups.append(update_fqdn_smartgroup_cidrs(os.getenv("AVIATRIX_CONTROLLER_IP"), smartgroup, cid))

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

# Lookup FQDN IP
def lookup_fqdn_ip(fqdn):
    return pydig.query(fqdn, 'A')

def get_fqdn_smartgroups(controller_ip, cid):
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
    fqdn_smartgroups = [x for x in response['app_domains'] if x["name"].startswith("fqdn_")]
    return fqdn_smartgroups

# Function to update the a Webgroup type SmartGroup by adding or removing a domain.  Input is a list of domains to add or remove.
def update_fqdn_smartgroup_cidrs(controller_ip, smartgroup, cid):
    # URL for the controller API
    url = "https://{}/v2.5/api".format(controller_ip) 
    # Parameters to send for the GET request
    headers = {
        "Authorization": "cid {}".format(cid)
    }

    # Log the cid
    logging.debug("Headers: {}".format(headers))

    ## EXAMPLE SMARTGROUP JSON
    # [{'uuid': '60477a53-72d0-4175-a3f6-5b861b77cfed', 'name': 'fqdn_www_google_com', 'selector': {'any': [{'all': {'cidr': '1.1.1.1'}}]}, 'system_resource': False}]

    # Extract target FQDN from Smartgroup Name by removing fqdn_ prefix and replacing underscores with dots
    fqdn = smartgroup["name"].replace("fqdn_", "").replace("_", ".")
    logging.debug("FQDN: {}".format(fqdn))

    # Lookup the IPs for the FQDN
    cidrs = lookup_fqdn_ip(fqdn)
    logging.debug("IP: {}".format(cidrs))

    # Format the new SmartGroup/WebGroup payload
    selector = []
    for cidr in cidrs:
        # Filter out ipv6 addresses and add v4 addresses to the selector
        if ":" not in cidr:
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
        controller_ip, smartgroup["uuid"]), json=smartgroup_config, headers=headers, verify=False)
    
    # Log the response
    logging.debug("Response to SmartGroup Update: {} {}".format(response.status_code,response.text))

    # Return the results and current filter list
    return {"result": response.json()}