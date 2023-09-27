def parse_age_sex_cit_row(row):
    for k, v in row.items():
        if v == 'null':
            row[k] = None
        elif v == '*****':
            row[k] = 0  # exact value, no MoE
        elif k.startswith('Estimate!!') or k.startswith('Margin of Error!!'):
            row[k] = int(v)

    return row


def parse_cvap_row(row):
    # add geo fields
    row.update(parse_geoname(row['geoname']))
    
    for k, v in row.items():
        if k.endswith('_est') or k.endswith('_tot') or k.endswith('number'):
            row[k] = int(v)

    return row


def parse_felon_dis_row(row):
    # update this to get data types right
    row = {
        k.replace('\r', ' '): v
        for k, v in row.items()
    }

    for k, v in row.items():
        if v == '':
            row[k] = 0
        elif '.' in v:
            try:
                row[k] = float(v)
            except ValueError:
                pass
        else:
            try:
                row[k] = int(v.replace(',', ''))
            except ValueError:
                pass

    return row


def parse_geoname(geoname):
    r = dict(state='', name='', geotype='')

    # state data
    if ', ' not in geoname:
        r['state'] = geoname
        r['name'] = r['state']
        r['geotype'] = 'state'
        return r
    
    rest, r['state'] = geoname.rsplit(', ', 1)

    # missing geotype (e.g. "Princeton, New Jersey")
    #
    # doesn't seem to happen in California
    if ' ' not in rest:
        r['name'] = rest
        return r
    
    clarification = ''
    # see examples below

    if rest.endswith(')') and '(' in rest:
        rest = rest[:-1]
        # will add clarification back to name later, see below
        rest, clarification = rest.rsplit(' (', 1)
        
    r['name'], r['geotype'] = rest.rsplit(' ', 1)
    
    # use common name, if provided
    #
    # e.g. "San Buenaventura (Ventura) city, California"
    if r['name'].endswith(')') and '(' in r['name']:
        r['name'] = r['name'][:-1].split('(')[-1]

    # convert "County" -> "county", "CDP" -> "cdp"
    r['geotype'] = r['geotype'].lower()

    # in California, "town" is just a fancy name for city
    if r['geotype'] == 'town' and r['state'] == 'California':
        r['geotype'] = 'city'

    # add County clarification back to name
    if clarification:
        if 'County' in clarification or 'Counties' in clarification:
            # name shared with other CDPs

            #  e.g. "Bayview CDP (Contra Costa County), California"
            r['name'] = f"{r['name']} ({clarification})"

        # some other clarifications we ignore:
        #
        # "Milford city (balance), Connecticut"
        # (Milford includes a village and borough, doesn't happen in CA)

    return r
