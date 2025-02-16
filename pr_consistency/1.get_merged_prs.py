# The purpose of this script is to download information about all pull
# requests merged into the master branch of the given repository. This
# information is downloaded to a JSON file.

import os
import sys
import json
import requests

from common import get_credentials

QUERY_TEMPLATE = """
{{
  repository(owner: "{owner}", name: "{repository}") {{
    pullRequests(first:100, orderBy: {{direction: ASC, field: CREATED_AT}}, baseRefName: "{basename}", states: MERGED{after}) {{
      edges {{
        node {{
          title
          number
          mergeCommit {{
            oid
          }}
          createdAt
          updatedAt
          mergedAt
          milestone {{
            title
          }}
          labels(first: 10) {{
            edges {{
              node {{
                name
              }}
            }}
          }}
        }}
        cursor
      }}
    }}
  }}
}}
"""

if sys.argv[1:]:
    REPOSITORY = sys.argv[1]
else:
    REPOSITORY = 'astropy/astropy'

OWNER = os.path.dirname(REPOSITORY)
NAME = os.path.basename(REPOSITORY)

print("The repository this script currently works with is '{}'.\n"
      .format(REPOSITORY))

json_filename = f'merged_pull_requests_{NAME}.json'

TOKEN = get_credentials('N/A', needs_token=True)[1]

headers = {"Authorization": f"Bearer {TOKEN}"}

cursor = None

pull_requests = {}

try:
    for basename in ('master', 'main'):
        print('Searching for PRs into branch', basename)

        entries = True
        while entries:
            print('cursor:', cursor)

            if cursor is None:
                after = ''
            else:
                after = f', after:"{cursor}"'

            query = QUERY_TEMPLATE.format(owner=OWNER, repository=NAME, after=after, basename=basename)

            request = requests.post('https://api.github.com/graphql', json={'query': query}, headers=headers)

            if request.status_code != 200:
                raise Exception("Query failed")

            entries = request.json()['data']['repository']['pullRequests']['edges']

            for entry in entries:

                pr = entry['node']
                cursor = entry['cursor']

                pull_requests[str(pr['number'])] = {'milestone': pr['milestone']['title'] if pr['milestone'] else None,
                                                    'title': pr['title'],
                                                    'labels': [edge['node']['name'] for edge in pr['labels']['edges']],
                                                    'merged': pr['mergedAt'].replace('Z', ''),
                                                    'updated': pr['updatedAt'].replace('Z', ''),
                                                    'created': pr['createdAt'].replace('Z', ''),
                                                    'merge_commit': pr['mergeCommit']['oid'] if pr['mergeCommit'] else None}

finally:
    with open(json_filename, 'w') as f:
        json.dump(pull_requests, f, sort_keys=True, indent=2)
