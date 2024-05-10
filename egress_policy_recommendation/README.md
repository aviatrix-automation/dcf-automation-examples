# Egress Policy Recommendation

This script downloads large amounts of Aviatrix DCF logs from CoPilot and analyzes them for unique domains and IPs to help with refining Egress DCF policy.  The output of the script is a JSON where the key is a Port/Proto combination, and the destination is a set of FQDNs or IPs seen.

A user can optionally output the raw logs, or the pre-filtered policies.


It is recommended to focus on a single policy by using the "--policy_number" option.  Maximum number of logs for download in a single pass is 1M.

##Example Usage:
Edit "aviatrix_env.sh" and load environment variables for the Aviatrix Environment.
```
source aviatrix_env.sh
```

Install requirements
```
pip install -r requirements.txt
```

The following command looks at logs for the last day, hitting policy with the priority of 100, and exports the results to a CSV.
```
python3 egress_policy_recommendation.py --relative_start_date 1 --export_to_csv true --policy_number 100
```

Full Script Options:
```
❯ python3 egress_policy_recommendation.py --help                  
usage: egress_policy_recommendation.py [-h] [--copilot_url COPILOT_URL]
                                       [--controller_url CONTROLLER_URL]
                                       [--username USERNAME]
                                       [--password PASSWORD]
                                       [--policy_number POLICY_NUMBER]
                                       [--export_to_csv EXPORT_TO_CSV]
                                       [--relative_start_date RELATIVE_START_DATE]

DCF Log Exporter

options:
  -h, --help            show this help message and exit
  --copilot_url COPILOT_URL
                        CoPilot URL
  --controller_url CONTROLLER_URL
                        Controller IP
  --username USERNAME   CoPilot username
  --password PASSWORD   CoPilot password
  --policy_number POLICY_NUMBER
                        Policy Priority Number
  --export_to_csv EXPORT_TO_CSV
                        Export to CSV
  --relative_start_date RELATIVE_START_DATE
                        Relative start date in days
```