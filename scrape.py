import urllib
import csv
import time
import os
from geopy import geocoders
from geopy.geocoders.google import GQueryError
#from pysqlite2 import dbapi2 as sqlite3
#from sqlite3 import dbapi2 as sqlite3
import sqlite3

full_url = 'http://services.georgia.gov/gbi/sorpics/sor.csv'

countiesicareabout = ['Bibb', 'Monroe', 'Houston', 'Jones', 'Peach', 'Crawford', 'Twiggs']

try:
    deltatime = time.time() - os.path.getmtime('./sor.csv')
    if deltatime > 60 * 60 * 24 * 6:   #If file is older than six days
        print "Old file found. Updating."
        urllib.urlretrieve(full_url, './sor.csv')        
    else:
        print "You have the newest file. No need to do processing."
#        import sys
#        sys.exit()    #die if needed
except (ValueError, os.error):
    print "No file found: ./sor.csv ... downloading now."
    urllib.urlretrieve(full_url, './sor.csv')


    


# OK, now let's fire up our database
geodbconn = sqlite3.connect('./geodb.sqlite')
geodb = geodbconn.cursor()
# Do we have a table? If not, we'll need to create one.
geodb.execute('''select count(*) from sqlite_master where type='table' and name='sexgeo';''')
sqlreturn = geodb.fetchone()
if sqlreturn[0] == 0:
    geodb.execute('''create table sexgeo (fulladdy text, glat text, glong text)''')
    geodb.execute('''create index addyindex on sexgeo (fulladdy)''')   


outputcsv = csv.writer(open('./output.csv', 'wb'))
headerrow = ['name','sex','race','yob','height','weight','haircolor',
'eyecolor','scarsmarkstattoos','streetnumber','street','city','state',
'zip','countyraw','registrationdate','crime','convictiondate','convictionstate',
'incarcerated','predator','absconder','id','resverificationdate',
'glat','glong','latlong','imgurl','ageish','countynamefix', 'warning_flag']
outputcsv.writerow(headerrow)


localcsv = csv.reader(open(r'./sor.csv','r'))
localcsv.next()                             #Skip header row

def colornamefix(x):
    if x == '':
        x = 'unknown'
    elif x == 'Bal':
        x = 'unknown'
    elif x == 'Blk':
        x = 'black'
    elif x == 'Bln':
        x = 'blond'
    elif x == 'Blu':
        x = 'blue'
    elif x == 'Bro':
        x = 'brown'
    elif x == 'Grn':
        x = 'green'
    elif x == 'Gry':
        x = 'gray'
    elif x == 'Haz':
        x = 'hazel'
    elif x == 'Mar':
        x = 'unknown'
    elif x == 'Red':
        x = 'red'
    elif x == 'Sdy':
        x = 'sandy'
    elif x == 'Whi':
        x = 'white'
    elif x == 'Xxx':
        x = 'unknown'
    else:
        x = 'unknown'
    return x



##
##
##Main routine starts below

for line in localcsv:

    for idx, val in enumerate(line):
        line[idx] = val.title().strip();

    line[12] = line[12].upper()         #Fix one state    


## Is this in a place we actually care about?
    if not (line[12] == 'GA' and line[14] in countiesicareabout):
#        print "OK, I'm ignoring ", line[0], ": at",fulladdy
         pass
    else:
        line[7] = colornamefix(line[7])   #Fix eye color
        line[6] = colornamefix(line[6])   #Fix hair color
        age = int(time.strftime('%Y')) - int(line[3])
        line[18] = line[18].upper()         #Fix the other state
        line[1] = line[1].lower()           #lowercase sex
        line[2] = line[2].lower()           #lowercase race
        line[22] = line[22].lower()         #lowercase ID (important!)
        #Next, date fixes from YYYYMMDD to MM/DD/YYYY
        #15=registration date, 17 = conviction date, 23 = residence verification date
        line[15] = line[15][4:6] + "/" + line[15][6:] + "/" + line[15][0:4]
        line[17] = line[17][4:6] + "/" + line[17][6:] + "/" + line[17][0:4]
        line[23] = line[23][4:6] + "/" + line[23][6:] + "/" + line[23][0:4]

        if line[20] == 'Predator':
            warning_flag = "*Predator*"
        else:
            warning_flag = ''
        if line[21] == 'Absonconder':
            warning_flag = warning_flag + " *Absconded*"
        else:
            pass
        if line[19] == 'Incarcerated':
            warning_flag = warning_flag + " *Incarcerated*"
        else:
            pass

        warning_flag = warning_flag.strip()
        print warning_flag
#
        if len(line[14]) > 2:
            CountyTextFix = line[14] + " County, "
            CountyNameFix = line[14] + " County"
        else:
            CountyTextFix = ''
            CountyNameFix = ''

        fulladdy = line[9] + " " + line[10] + ", " + line[11] + ", " + CountyTextFix + line[12] + " " + line[13]



        
##
## OK, so let's see if we already know where this address is. We can
## check to see how many times the row shows up; if the row doesn't exist in
## the database, we'll need to try geocoding it through Google, and if that
## doesn't work we'll go through Geocoder.US, and if that doesn't work
## we'll give it the site of the 1903 RMS Republic wreck for no reason
## whatsoever.
## If we do have a single listing, let's grab the lat and long.
## If we have multiple listings for the same address, we probably have
## database corruption.

        geodb.execute('select count(*), glat, glong from sexgeo where fulladdy = ?', [fulladdy])
        sqlreturn = geodb.fetchone()
    #    print sqlreturn
        if sqlreturn[0] == 0:
            try:
                googlegeo = geocoders.Google()
                for tempplace, (templat, templong) in googlegeo.geocode(fulladdy, exactly_one=False):
                    gplace=str(tempplace)
                    glat=str(templat)
                    glong=str(templong)
            except (ValueError, GQueryError):
                try:
                    usgeo = geocoders.GeocoderDotUS()
                    for tempplace, (templat, templong) in usgeo.geocode(fulladdy, exactly_one=False):
                        gplace=str(tempplace)
                        glat=str(templat)
                        glong=str(templong)
                except (ValueError, GQueryError, TypeError):
                    print "Location '", fulladdy, "not found. Setting lat-long to 1903's wreck of the RMS Republic."
                    glat = "40.433333"
                    glong = "-69.766667"
                    gplace = "RMS Republic (1903) wreck site"
    ## So if things went right, we now have a geocoded address.
    ## Let's put that in the database.                
            geodb.execute('insert into sexgeo values (?,?,?)', [fulladdy, glat, glong])
            geodbconn.commit()
            print line[0], ": geocoded and recorded ", fulladdy, "at ", glat, ", ", glong
        elif sqlreturn[0] == 1:
            glat = str(sqlreturn[1])
            glong = str(sqlreturn[2])
#            print line[0], ": at",fulladdy, " already in database at ", glat, "and", glong
            print line[0], " already in database"
        else:
            print "Multiple rows for same ", fulladdy, ", What the hell did you do?"

## Let's start outputting the lines we care about, with new data, with a couple tweaks

        line.append(glat)
        line.append(glong)
        line.append(glat + ", " + glong)
        line.append('http://services.georgia.gov/gbi/sorpics/' + line[22] + '.jpg')
        line.append(age)
        line.append(CountyNameFix)
        line.append(warning_flag)
    #    latlong = glat + ", " + glong
    #    imgurl = 'http://services.georgia.gov/gbi/sorpics/' + line[22] + '.jpg'
    #    outputcsv.writerow(line, glat, glong, latlong, imgurl))
        outputcsv.writerow(line)
        
    
    



"""
To-do:
Integrate with Google Fusion tables
Split first and last names
Add in age, first, last
Fix dates?
Split height into feet (height:1) and inches
str(value(height(-2:)
Do registration, convicted, resverification dates go into Fusion Tables right?
Is there a fuzzy time module, like "a few months ago"?
Figure out how to handle multiple addresses -- JavaScript or in-house?
How handle incarcerated/predator/absconded?
warning_flag text string= ''

Then add warning_flag to header, CSV output


Cure cancer
""" 


    
"""
headerrow = ['name','sex','race','yob','height','weight','haircolor',
'eyecolor','scarsmarkstattoos','streetnumber','street','city','state',
'zip','countyraw','registrationdate','crime','convictiondate','convictionstate',
'incarcerated','predator','absconder','id','resverificationdate',
'glat','glong','latlong','imgurl','ageish','countynamefix']

Source file key with output file key at end
0"NAME
1SEX"
2"RACE"
3"YEAR OF BIRTH"
4"HEIGHT"
5"WEIGHT"
6"HAIR COLOR",
7#"EYE COLOR",
8"SCARS, MARKS, TATTOOS"
9"STREET NUMBER",
10"STREET",
11"CITY"
12"STATE"
13"ZIP CODE"
14"COUNTY"
15"REGISTRATION DATE"
16"CRIME",
17"CONVICTION DATE"
18"CONVICTION STATE"
19"INCARCERATED",
20"PREDATOR",
21"ABSCONDER",
22"SEXUAL OFFENDER ID",
23"RES VERIFICATION DATE"
And then our new stuff
24 glat
25 glong
26 latlong
27 imgurl
28 age (approximate)
29 CountyNameFix
30 warning_flag (predator-obsconder-incarcerated)

"""
