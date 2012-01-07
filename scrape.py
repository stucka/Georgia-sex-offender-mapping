## Now need to implement something to show the city centers (and our lost-and-found section) 

## So we're doing a big rewrite, but maybe this'll help with Missouri ...


import urllib
import csv
import time
import os
from googlegeocoder import GoogleGeocoder
from geopy import geocoders
from geopy.geocoders.google import GQueryError
#from pysqlite2 import dbapi2 as sqlite3
#from sqlite3 import dbapi2 as sqlite3
import sqlite3

#full_url = 'http://services.georgia.gov/gbi/sorpics/sor.csv'
full_url = 'http://gbi.georgia.gov/gbi/sorpics/sor.csv'


# List must be in Proper casing (e.g., Dekalb, Mcintosh)
countiesicareabout = ['Bibb', 'Monroe', 'Houston', 'Jones', 'Peach',
'Crawford', 'Twiggs', 'Wilkinson', 'Laurens', 'Bleckley', 'Baldwin']

# When no address is found, we need a place to put 'em. Goergia OCGA 42-1-12 calls for registry, so let's make
# the error at 42.02, -42.02
errorlat = "42.02"
errorlong = "42.02"
errorlatlong = errorlat + ", " + errorlong

try:
#    deltatime = time.time() - os.path.getmtime('./sor.csv')
    if time.time() - os.path.getmtime('./sor.csv') > 60 * 60 * 24 * 6:   #If file is older than six days
        print "Old file found. Updating."
        urllib.urlretrieve(full_url, './sor.csv')        
    else:
        print "You have the newest file. No need to do processing."
#        import sys
#        sys.exit()    #die if needed
except (ValueError, os.error):
    print "No file found: ./sor.csv ... downloading now."
    urllib.urlretrieve(full_url, './sor.csv')


# OK, now let's fire up our geography database
geodbconn = sqlite3.connect('./geodb.sqlite')
geodb = geodbconn.cursor()
# Do we have a table? If not, we'll need to create one.
geodb.execute('''select count(*) from sqlite_master where type='table' and name='sexgeo';''')
sqlreturn = geodb.fetchone()
if sqlreturn[0] == 0:
    geodb.execute('''create table sexgeo (fulladdy text, glat text, glong text)''')
    geodb.execute('''create index addyindex on sexgeo (fulladdy)''')   
# Do we have a table? If not, we'll need to create one.
geodb.execute('''select count(*) from sqlite_master where type='table' and name='cities';''')
sqlreturn = geodb.fetchone()
if sqlreturn[0] == 0:
    geodb.execute('''create table cities (city text, location text)''')
    geodb.execute('insert into cities values (?,?)', ["NO LOCATION FOUND", errorlatlong])

# OK, let's fire up our bounding box database
# Georgia county data pulled from https://github.com/stucka/us-county-bounding-boxes
bounddbconn = sqlite3.connect('./bounddb.sqlite')
bounddb = bounddbconn.cursor()
# Do we have a table? If not, we'll need to create one.
bounddb.execute('''select count(*) from sqlite_master where type='table' and name='bound';''')
sqlreturn = bounddb.fetchone()
### HEY! I think we're looking to see how many tables have that name, not
### How many things are in that table. Can we flip this around?
if sqlreturn[0] != 159:
# Georgia has 159 counties. Or, it should. If they ever add the one they're
# talking about we'll have to rerun the bounding boxes anyway ...
    bounddb.execute('''drop table if exists bound;''')
    bounddb.execute('''create table bound (statefips text, countyfips text, name text, extentn text, extents text, extente text, extentw text)''')
    localcsv = csv.reader(open(r'./gaboundingbox.csv','r'))
    localcsv.next()                             #Skip header row
    for line in localcsv:
        for idx, val in enumerate(line):
            line[idx] = val.strip();
#        print line
    bounddb.execute('insert into bound values (?,?,?,?,?,?,?)', [line[0], line[1], line[2], line[3], line[4],line[5],line[6]])
    bounddb.execute('''alter table bound add column countyupper text''')
    bounddb.execute('''update bound set countyupper=upper(name)''')
    bounddb.execute('''create index if not exists countyupperindex on bound (countyupper)''')
    bounddbconn.commit()

# OK, now let's fire up our Fusion Tables database -- this should get created
# each time from scratch. So we nuke it and start over. This will hold our main
# output to be uploaded, but we'll keep creating the full CSV for human
# analysis.
if os.path.exists('./ftdb.sqlite'):
        os.remove('./ftdb.sqlite')

ftdbconn = sqlite3.connect('./ftdb.sqlite')
ftdb = ftdbconn.cursor()
ftdb.execute('''create table staging (pointinfo text, location text)''')
ftdb.execute('''create index locationindex on staging (location)''')
#ftdb.execute('''create table upload (pointinfo text, location text)''')
#We'll dynamically create upload later

outputcsv = csv.writer(open('./output.csv', 'wb'))
headerrow = ['name','sex','race','yob','height','weight','haircolor',
'eyecolor','scarsmarkstattoos','streetnumber','street','origcity','origstate',
'zip','countyraw','registrationdate','crime','convictiondate','convictionstate',
'incarcerated','predator','absconder','id','resverificationdate',
'glat','glong','latlong','imgurl','ageish','countynamefix',
'warning_flag', 'shortaddy', 'fulladdy', 'identifying_marks', 'infourl']
outputcsv.writerow(headerrow)

#uploadcsv = csv.writer(open('./upload.tab', 'wb'), delimiter='\t', quoting=csv.QUOTE_MINIMAL, quotechar='}')
uploadcsv = csv.writer(open('./upload.csv', 'wb'))
#quotechar='|', quoting=csv.QUOTE_MINIMAL

headerrow = ['location', 'pointcount', 'marker', 'pointinfo']
uploadcsv.writerow(headerrow)


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
## And here we find the state quit giving us sex offender IDs in the CSV
## Can't scrape 'em until they put their own searchable database back online
## HEY! Placeholder here.    
        line.insert(23, "No ID available")
        line[23] = line[23][4:6] + "/" + line[23][6:] + "/" + line[23][0:4]
        #Next, height
        line[4] = line[4][0:1] + "'" + str(int(line[4][1:])) + '"'        

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
#        print warning_flag
#
        if len(line[14]) > 2:
            CountyTextFix = line[14] + " County, "
            CountyNameFix = line[14] + " County"
        else:
            CountyTextFix = ''
            CountyNameFix = ''

        if len(line[8]) > 2:
            identifying_marks = "; Identifying marks include " + line[8]
        else:
            identifying_marks = ""

        fulladdy = line[9] + " " + line[10] + ", " + line[11] + ", " + CountyTextFix + line[12] + " " + line[13]
        shortaddy = line[9] + " " + line[10] + ", " + line[11]
        infourl = 'http://services.georgia.gov/gbi/gbisor/jsp/Detail.jsp?action=SexualOffenderDetails&sexualoffenderId=' + line[22].upper()
        


        
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
                #county in line[14], needs to be upper, matched
                
                geocoder = GoogleGeocoder()
                search = geocoder.get(fulladdy)
                glat=str(search[0].geometry.location.lat)
                glong=str(search[0].geometry.location.lng)
            except (ValueError, GQueryError):
# HEY CHECK ERROR CONDITIONS
                    print "Location '", fulladdy, "not found. Setting lat-long to 42.02,-42.02, in honor of OCGA 42 1 12"
                    glat = errorlat
                    glong = errorlong
                    gplace = "OCGA 42-1-12 calls for registry, but we can't find this person."
    ## So if things went right, we now have a geocoded address.
    ## Let's put that in the database.                
            geodb.execute('insert into sexgeo values (?,?,?)', [fulladdy, glat, glong])
#            geodbconn.commit()
## Uncomment the above line to record lat-longs as we find them, at the cost of speed
            print line[0], ": geocoded and recorded ", fulladdy, "at ", glat, ", ", glong
        elif sqlreturn[0] == 1:
            glat = str(sqlreturn[1])
            glong = str(sqlreturn[2])
#            print line[0], ": at",fulladdy, " already in database at ", glat, "and", glong
            print line[0], " already in database"
        else:
            print "Multiple rows for same ", fulladdy, ", What the hell did you do?"

        latlong = glat + ", " + glong

        mycity = line[11].upper() + ", " + line[12].upper()


## Now, let's see if we know where this city is.        
        geodb.execute('select count(*) from cities where city = ?', [mycity])
        sqlreturn = geodb.fetchone()
    #    print sqlreturn
        if sqlreturn[0] > 0:
            pass
        else:
            try:
                googlegeo = geocoders.Google()
                for tempplace, (templat, templong) in googlegeo.geocode(mycity, exactly_one=False):
                    citylatlong = str(templat) + ", " + str(templong)
                geodb.execute('insert into cities values (?,?)', [mycity, citylatlong])
                geodbconn.commit()
                print "Found ", mycity, "via Google"
            except (ValueError, GQueryError,TypeError):
                    print "No Google location found for ", mycity
## Let's start outputting the lines we care about, with new data, with a couple tweaks
        line.append(glat)
        line.append(glong)
        line.append(latlong)
        imgurl = 'http://services.georgia.gov/gbi/sorpics/' + line[22] + '.jpg'
        line.append(imgurl)
        line.append(age)
        line.append(CountyNameFix)
        line.append(warning_flag)
        line.append(shortaddy)
        line.append(fulladdy)
        line.append(identifying_marks)
        line.append(infourl)
    #    latlong = glat + ", " + glong
    #    imgurl = 'http://services.georgia.gov/gbi/sorpics/' + line[22] + '.jpg'
    #    outputcsv.writerow(line, glat, glong, latlong, imgurl))
        outputcsv.writerow(line)

## Now let's start putting it in the database
## We're looking for just two items -- a big merge of all the HTML for each
## offender with that data capable of being combined -- plus
## the latlong. One of these is easier than the other. =)
        pointinfo = '<tr><td width=150><A HREF="'
        pointinfo += infourl + '" target="_blank"><img src="'
        pointinfo += imgurl + '" width=150></A></td><td><b>'
        pointinfo += line[0] + '</b><br><i>' + shortaddy
        pointinfo += '</i><br>About ' + str(age) + ', '
        pointinfo += line[2] + ' ' + line[1] + ', '
        pointinfo += line[4] + ', ' + line[5] + ' lbs with '
        pointinfo += line[6] + ' hair  and ' + line[7] + line[8]
        pointinfo += '.<br> Conviction of ' + line[16].lower()
        pointinfo += ' on ' + line[17] + ' in ' + line[18].upper()
        pointinfo += '.<br>Address verified ' + line[23] + warning_flag
        pointinfo += '</td></tr>'

## Now we have our bit for Fusion Tables. Let's add to the database.
        ftdb.execute('insert into staging values (?,?)', [pointinfo, latlong])

        


#                    geodb.execute('insert into sexgeo values (?,?,?)', [fulladdy, glat, glong])
#            geodbconn.commit()


#        print pointinfo        
#localcsv.close()
#outputcsv.close()
geodbconn.commit()
ftdbconn.commit()
print "Done getting our data. Now creating upload database."
ftdb.execute('create table upload AS SELECT group_concat(pointinfo, "   ") as pointinfo, location as location, count(*) as pointcount, "small_red" as marker FROM staging GROUP BY 2')
ftdbconn.commit()
ftdb.execute('update upload set marker="placemark_square_highlight" where pointcount > 1')
ftdbconn.commit()
#geodb.execute('select location from cities')
#mycitycenters = geodb.fetchall()
ftdb.execute('''attach database './geodb.sqlite' as geodbattached''')
ftdb.execute('''update upload set marker="rec_info_circle" where location in (select location from geodbattached.cities)''')
ftdbconn.commit()


#Our big unknown is rec_info_circle
#So what we're looking for is something like
#update upload set marker="rec_info_circle" where location in (select distinct location from citytable)



#Now, let's get our upload CSV rocking
ftdb.execute('select pointinfo, location, pointcount, marker from upload')
for row in ftdb:
#    uploadcsv.writerow(row)
#    print row
    thisthingbetterwork = (row[1], row[2], row[3], row[0].strip())
    uploadcsv.writerow(thisthingbetterwork)


##HEY! Export is broken.
#            sqlreturn = geodb.fetchone()





#create table fml AS
#SELECT group_concat(pointinfo), location, count(*) FROM staging
#GROUP by location
#order by 3 desc
    
    



"""
To-do:
Integrate with Google Fusion tables
Is there a schedule of SOR releases? Can we match that?
Can I create a dummy Fusion Tables template or something to fix the half-dozen
things coming in as location?
Can I get working worthwhile HTML for the info box style?
Is there a dependable way of scaling the images?
Split first and last names
Is there a fuzzy time module, like "a few months ago"?
Figure out how to handle multiple addresses -- JavaScript or in-house?
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
31 shortaddy -- street address, city
32 fulladdy -- includes county, state, zip
33 identifying_marks (reformatted #8)
34 infourl -- sex offender's personal web page

"""



"""
Google Fusion tables sample info window code here:

<div class='googft-info-window' style='font-family: sans-serif'>
<table border=0 cellpadding=3 cellspacing=3>
<tr><td><A HREF="{infourl}" target="_blank"><img src="{imgurl}" width="53%" height="53%"></A></td>
<td><b>{name}</b><br>
<i>{shortaddy}</i><br>
About {ageish}, {race} {sex}, {height}, {weight} lbs with {haircolor} hair and {eyecolor} eyes{identifying_marks}.<br>
Convicted of {crime} on {convictiondate} in {convictionstate}.<br>
Address verified {resverificationdate}
{warning_flag}
</td></tr></table>
</div>

"""
