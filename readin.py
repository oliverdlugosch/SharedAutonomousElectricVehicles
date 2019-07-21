import datetime

def readin(path):
    # Reads in config file
    # Returns values and parameters from config file
    results = dict()

    initfile = open(path, 'r')
    temp = initfile.readline()
    location = initfile.readline()
    location = location[0:len(location) - 1]
    results['location'] = location

    temp = initfile.readline()
    number_of_cars = int(float(initfile.readline()))
    results['number_of_cars'] = number_of_cars

    temp = initfile.readline()
    number_of_CPs = int(float(initfile.readline()))
    results['number_of_CPs'] = number_of_CPs

    temp = initfile.readline()
    firstday = initfile.readline()
    firstday = firstday[0:len(firstday) - 1]
    firstday = datetime.date(int(firstday[0:4]), int(firstday[5:7]), int(firstday[8:10]))
    results['firstday'] = firstday

    temp = initfile.readline()
    lastday = initfile.readline()
    lastday = lastday[0:len(lastday) - 1]
    lastday = datetime.date(int(lastday[0:4]), int(lastday[5:7]), int(lastday[8:10]))
    results['lastday'] = lastday

    temp = initfile.readline()
    trainingpercentage = int(float(initfile.readline()))
    results['trainingpercentage'] = trainingpercentage

    temp = initfile.readline()
    timestep = int(float(initfile.readline()))
    results['timestep'] = timestep

    temp = initfile.readline()
    EIT_radius = int(float(initfile.readline()))
    results['EIT_radius'] = EIT_radius

    temp = initfile.readline()
    comb_diameter = int(float(initfile.readline()))
    results['Comb_diameter'] = comb_diameter

    temp = initfile.readline()
    ip_address = initfile.readline()
    results['ip_address'] = ip_address[0:len(ip_address)-1]

    temp = initfile.readline()
    minimum_cars = int(float(initfile.readline()))
    results['minimum cars'] = minimum_cars

    temp = initfile.readline()
    maximum_cars = int(float(initfile.readline()))
    results['maximum cars'] = maximum_cars

    initfile.close()
    return results