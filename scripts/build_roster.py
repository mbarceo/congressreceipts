"""Build data/congress.json and congress.md from unitedstates/congress-legislators (current)."""
import json, sys
src, out_json, out_md = sys.argv[1:4]
STATES = {'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming','DC':'District of Columbia','PR':'Puerto Rico','GU':'Guam','VI':'U.S. Virgin Islands','AS':'American Samoa','MP':'Northern Mariana Islands'}
P = {'Democrat':'D','Republican':'R','Independent':'I'}
rows = []
for l in json.load(open(src)):
    t = l['terms'][-1]
    rows.append({
        'name': l['name'].get('official_full') or f"{l['name']['first']} {l['name']['last']}",
        'last': l['name']['last'],
        'bioguide': l['id']['bioguide'],
        'chamber': 'Senate' if t['type']=='sen' else 'House',
        'state': t['state'], 'state_name': STATES[t['state']],
        'district': t.get('district'),
        'senate_class': t.get('class'),
        'party': P.get(t['party'], t['party']),
        'term_end': t['end'],
        'url': t.get('url'),
    })
rows.sort(key=lambda r: (r['state_name'], r['chamber']!='Senate', r['district'] if r['district'] is not None else -1, r['last']))
json.dump(rows, open(out_json,'w'), indent=1)
h = sum(r['chamber']=='House' for r in rows); s = len(rows)-h
md = [f"# Members of Congress by state\n\n{len(rows)} current members: {s} senators, {h} House members/delegates. Source: unitedstates/congress-legislators.\n"]
cur = None
for r in rows:
    if r['state_name'] != cur:
        cur = r['state_name']; md.append(f"\n## {cur} ({r['state']})\n")
        sec = None
    if r['chamber'] != sec:
        sec = r['chamber']; md.append(f"\n**{'Senate' if sec=='Senate' else 'House'}**\n")
    d = '' if r['district'] is None else (' – At-large' if r['district']==0 else f" – District {r['district']}")
    md.append(f"- [ ] {r['name']} ({r['party']}){d}")
open(out_md,'w').write('\n'.join(md)+'\n')
print(len(rows), s, h)
