from time import time
from requests import Session
import requests
import os
import pandas as pd
from tqdm import tqdm
import urllib3
import json
import argparse
import logging

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)

def main():
    # use argparse to get arguments for coPilot URL, username, and password
    parser = argparse.ArgumentParser(description='DCF Log Exporter')
    parser.add_argument('--copilot_url', type=str, help='CoPilot URL',
                        default=os.getenv("AVIATRIX_COPILOT_IP"))
    parser.add_argument('--controller_url', type=str, help='Controller IP',
                        default=os.getenv("AVIATRIX_CONTROLLER_IP"))
    parser.add_argument('--username', type=str, help='CoPilot username',
                        default=os.getenv("AVIATRIX_USERNAME"))
    parser.add_argument('--password', type=str, help='CoPilot password',
                        default=os.getenv("AVIATRIX_PASSWORD"))
    parser.add_argument('--policy_number', type=int, help='Policy Priority Number', default=0)
    parser.add_argument('--export_to_csv', type=bool, help='Export to CSV', default=False)
    parser.add_argument('--relative_start_date', type=int,
                        help='Relative start date in days', default=1)
    args = parser.parse_args()

    cid = controller_login(args.controller_url, args.username, args.password)
    internet_policy_uuids = get_internet_policy_uuids(args.controller_url, cid, policy_number=args.policy_number)

    s = copilot_login(args.username, args.password, args.copilot_url)
    logs_df = get_dcf_logs(s, args.copilot_url, args.relative_start_date,
                 internet_policy_uuids,args.policy_number, args.export_to_csv)
    unique_sni_hostnames = process_l7_webgroup(logs_df)
    print("Unique Port/Proto/Domains for creating Webgroup Policies:")
    print(unique_sni_hostnames)
    non_web_egress = process_l4_smartgroups(logs_df)
    print("Unique Port/Proto/DstIP for creating SmartGroup Policies:")
    print(non_web_egress)
    copilot_logout(s, copilot_url=args.copilot_url)


def copilot_login(username, password, copilot_url):
    login_payload = {
        "username": username,
        "password": password
    }

    s = Session()
    r = s.post("https://"+copilot_url+'/api/login',
               json=login_payload, verify=False)
    return s


def copilot_logout(s, copilot_url):
    r = s.get("https://"+copilot_url+'/api/logout', verify=False)
    return r


def controller_login(controller_ip, controller_user, controller_password):
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

def get_internet_policy_uuids(controller_ip, cid, policy_number):
    internet_smartgroup_id = "def000ad-0000-0000-0000-000000000001"

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

    if policy_number > 0:
        # Filter policies based on policy number
        policy_uuids = [x["uuid"] for x in policies if x["priority"] == policy_number]
    else:
        # Filter policies based on destination SmartGroup including "Public Internet"
        policy_uuids = [x["uuid"] for x in policies if internet_smartgroup_id in x["dst_ads"]
                                and x["uuid"] != "defa11a1-2000-0000-0000-000000000000"]
    logging.debug("Filtered Policy List: {}".format(policy_uuids))

    return policy_uuids

# example post to get DCF logs
# URL: https://{{copilot_url}}/api/microseg/policies/logs
# {"filterModel":{"items":[{"field":"timestamp","operator":"after","id":1413,"value":"2024-05-07"}],"logicOperator":"and","quickFilterValues":[],"quickFilterLogicOperator":"and"},"order":"desc","searchAfter":[1715182143194],"size":100}


def get_dcf_logs(s, copilot_url, relative_start_date, policy_uuids, policy_number, export_to_csv=False):
    # get current time in milliseconds
    current_time = int(time()*1000)
    # get start time in milliseconds
    start_time = current_time - (relative_start_date*24*60*60*1000)
    start_time_iso = pd.to_datetime(start_time, unit='ms')
    logging.debug(start_time_iso.isoformat())
    page_size = 100
    # create payload to get DCF logs
    payload = {
        "filterModel": {
            "items": [
                {"field": "policyUuid", "operator": "include", "value": policy_uuids},
                {"field": "timestamp", "operator": "after", "value": start_time_iso.isoformat()}
                ],
            "logicOperator": "and",
            "quickFilterLogicOperator": "and",
            "quickFilterValues": []
        },
        "order": "desc",
        "size": page_size
    }

    count = s.post("https://"+copilot_url +
                   '/api/microseg/policies/logs/count', json=payload, verify=False)
    logging.debug(count.json())

    iterations = count.json()['total']//page_size
    logging.debug(iterations)

    search_after = None
    df = pd.DataFrame()

    print("Getting {} DCF Logs...".format(count.json()['total']))
    for i in tqdm(range(iterations)):
        if search_after:
            payload['searchAfter'] = [ search_after ]
        r = s.post("https://"+copilot_url +
                   '/api/microseg/policies/logs', json=payload, verify=False)
        logging.debug(r.json())
        # concat the new data to the dataframe
        df = pd.concat([df, pd.DataFrame(r.json()['items'])])
        search_after = max([x['_searchAfter'] for x in r.json()['items']])
        logging.debug(search_after)

    logging.debug(df.head())
    logging.info("Number of Logs Indexed: {}".format(len(df)))
    if export_to_csv:
        df.to_csv('dcf_logs_{}_{}.csv'.format(policy_number,start_time), index=False)
    return df

## Example L7 Log
# {'id': '6rXBWY8BReV3HGyVDKv4', 'timestamp': '2024-05-08T19:49:34.000Z', 'policyUuid': 'e82f04ad-ca90-4507-8552-65ddb052f394', 'sourceIp': '10.1.88.234', 'destinationIp': '13.107.42.16', 'protocol': 'TCP', 'sourcePort': 49327, 'destinationPort': 443, 'gatewayHostname': 'cloud-spoke', 'action': 'DROP', 'isEnforced': True, 'tags': ['mitm', 'microseg'], 'mitmSniHostname': 'config.edge.skype.com', '_searchAfter': [1715197774000]}

# Extract unique sni hostnames from L7 logs. Group by port/proto. Export as a dictionary with port/proto as key and list of unique sni hostnames as value
def process_l7_webgroup(df):
    df = df[df['tags'].apply(lambda x: 'mitm' in x)].copy()
    # create a new column with port_proto
    # df['port_proto'] = df['destinationPort'].astype(str) + '_' + df['protocol']
    if len(df)>0:
        unique_sni_hostnames = df.groupby(['destinationPort', 'protocol'])['mitmSniHostname'].unique().to_json(indent=1)
        return unique_sni_hostnames
    else:
        return {}

# Sort heuristics for dest IPs if src_port is less than dst_port, switch src and dst ports and IPs

# Extract unique dst_ips from L4 logs. Group by port/proto. Export as a dictionary with port/proto as key and list of unique dst_ips as value
def process_l4_smartgroups(df):
    df = df[df['tags'].apply(lambda x: 'ebpf' in x)].copy()
    if len(df)>0:
        df['src_port'] = df['sourcePort']
        df['dst_port'] = df['destinationPort']
        df['src_ip'] = df['sourceIp']
        df['dst_ip'] = df['destinationIp']
        df.loc[df['sourcePort'] < df['destinationPort'], ['src_port', 'dst_port']] = df.loc[df['sourcePort'] < df['destinationPort'], ['dst_port', 'src_port']].values
        df.loc[df['sourcePort'] < df['destinationPort'], ['src_ip', 'dst_ip']] = df.loc[df['sourcePort'] < df['destinationPort'], ['dst_ip', 'src_ip']].values
        # # create a new column with port_proto
        # df['port_proto'] = df['dst_port'].astype(str) + '_' + df['protocol']
        unique_dst_ips = df.groupby(['dst_port', 'protocol'])['dst_ip'].unique().to_json(indent=1)
        return unique_dst_ips
    else:  
        return {}

if __name__ == "__main__":
    main()
