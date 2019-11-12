import requests
import xml.etree.ElementTree as ElementTree
import re
import csv
import argparse

# ingredient input file should have a HEADER row with column names:
# - INGREDIENT_RXNORM_CUI
# - INGREDIENT_NAME
# - MME_FACTOR (optional) 
def read_ingredients(csv_filename):
    inf = open(csv_filename)
    inreader = csv.DictReader(inf, delimiter=',', quotechar='"')
    inlist = []

    for row in inreader:
        inlist.append( row )
    
    req_fields = ['INGREDIENT_RXNORM_CUI','INGREDIENT_NAME']
    for field in req_fields:
        if 'INGREDIENT_RXNORM_CUI' not in inlist[0]:
            raise Exception('invalid ingredient input file, missing column: {}'.format(field))

    return(inlist)


def get_rxnav_related(rxcui, tty=None):
    out = []
    if tty == None:
        tty='BN+BPCK+GPCK+IN+MIN+PIN+SBD+SBDC+SBDF+SCD+SCDC+SCDF+SCDG+SBDG'

    rel_type_url = 'https://rxnav.nlm.nih.gov/REST/rxcui/{}/related?tty={}'.format(rxcui,tty)
    r = requests.get(rel_type_url)
    root = ElementTree.fromstring(r.content)

    if root.tag != 'rxnormdata':
        raise Exception('Error making REST request for related tty: invalid root {}'.format(root.tag)  )

    rg = root.find('relatedGroup')
    conceptGroups = rg.findall('conceptGroup') 

    for cgroup in conceptGroups:
        cp = cgroup.findall('conceptProperties')
        #groupTTY = cgroup.find('tty')
        #print('TTY: ',groupTTY.text)
        for elem in cp:
            tty = elem.find('tty')
            rxcui = elem.find('rxcui')
            name = elem.find('name')
            #print('TTY: ', tty.text)
            #print('RXCUI: ', rxcui.text)
            #print('NAME: ', name.text)
            term = {'tty': tty.text, 'rxcui': rxcui.text, 'name': name.text}
            out.append(term)
    return(out)

def parse_med_strength(med_name, ingredient):
    # remove text in brackets to parse strength and unit
    beg_loc = med_name.upper().find('[')
    end_loc = med_name.upper().find(']')
    if beg_loc >= 0:
        med_name = med_name[:beg_loc] + med_name[end_loc+1:]

    #regex for parsing strength and unit
    re_strength = re.compile(r'[0-9\.]+')
    re_unit = re.compile(r'[a-zA-Z\/\-]+')

    key_loc = med_name.upper().find(ingredient.upper())
    strength = None
    unit = None
    if key_loc >= 0:
        rstrength = re_strength.findall(med_name[key_loc:])
        if len(rstrength):
            strength = rstrength[0]
            key_loc = key_loc + med_name[key_loc:].upper().find(strength)
            runit = re_unit.findall(med_name[key_loc:])
            if len(runit):
                unit = runit[0]

    if strength == None:
        strength = ''
    if unit == None:
        unit = ''
    return( {'strength': strength, 'unit': unit} )

# get command line args
clparse = argparse.ArgumentParser(description='find meds related to ingredients')
clparse.add_argument('--input', help='name of the ingredient input file')
clparse.add_argument('--output', help='name of the output file')
args = clparse.parse_args()
if args.input == None:
    print("invalid input, type <programfile> -h for usage")
    exit()
input_filename =  args.input
if args.output == None:
    print("invalid input, type <programfile> -h for usage")
    exit()
output_filename =  args.output

#get ingredients from input file
ingredients = read_ingredients(input_filename)

outf = open(output_filename,'w')
# header
outf.write('INGREDIENT_RXNORM_CUI,INGREDIENT_NAME,TTY,RXNORM_CUI,NAME,INGREDIENT_STRENGTH,UNIT,MME_FACTOR\n') 
for i in ingredients:
    print("Searching related meds for ingredient: {}".format(i['INGREDIENT_NAME']))
    rxnav = get_rxnav_related(i['INGREDIENT_RXNORM_CUI'])
    for term in rxnav:
        d = parse_med_strength(term['name'],i['INGREDIENT_NAME'])
        outf.write('{},{},{},{},"{}",{},{},{}\n'.format(i['INGREDIENT_RXNORM_CUI'],i['INGREDIENT_NAME'],term['tty'],term['rxcui'],term['name'],d['strength'],d['unit'],i['MME_FACTOR']) )

print('see contents of output file: {}'.format(output_filename))
