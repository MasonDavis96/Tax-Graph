from django.shortcuts import render
import pyodbc
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as tick
from io import StringIO
import pandas as pd



def hello_world(request):


####################################################      Get user input from forms     ##########################################################
    

    # Get user input
    id = request.POST.get('AccountID')
    submitbutton = request.POST.get('Submit')

    message = None
    # Value must be a digit - incorrect input was given OR no search criteria was given at all.
    if (id.isdigit() == False):
        message = "Please enter a valid Account Number"
        context= { 'message':message,
        'submitbutton':submitbutton,
        }
        return render(request, 'hello_world.html', context)


####################################################      Connect to/and retrieve info from database     ###########################################


    # Create connection object
    server = 'serverName, port' 
    database = 'databaseName' 
    username = 'name' 
    password = 'password' 
    mydb = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+ password)

    cursor = mydb.cursor()

    cursor.execute("""SELECT TAX_YEAR, RMV, IMPR_RMV, MAV, AV, IMPR_AV, M_ADDRESS_1, SITUS_ADDRESS, ACCOUNT_ID 
    FROM TAX.STATEMENTS WHERE ACCOUNT_ID = ? AND TAX_YEAR >= YEAR(GETDATE())-10 ORDER BY TAX_YEAR ASC;""", (id))

    # Query returned no results
    if (cursor.rowcount == 0):
        mydb.close()
        message = "No results were found for that Account Number"
        context= { 'message':message,
        'submitbutton':submitbutton,
        }
        return render(request, 'hello_world.html', context)

    tax_year = [] # x-axis values
    rmv = [] # y-axis values
    mav = [] # y-axis values
    av = [] # y-axis values
    mailing_name = None
    property_address = None
    account_id = 0
    prev_tax_year = 0

    # 0 = Tax_Year
    # 1 = RMV
    # 2 = IMPR_RMV
    # 3 = MAV
    # 4 = AV
    # 5 = IMPR_AV
    rows = cursor.fetchall() 
    for row in rows:
        # Compare if current tax year (row[0]) == previous tax year. If true, skips the remaining duplicate years.
        if (row[0] == prev_tax_year):
            continue # Restart loop
        else: # append the tax year/rmv/mav/av values to corresponding lists
            # Tax_Year
            tax_year.append(int(row[0]))

            # RMV
            if (row[1] == None and row[2] == None): # If both are empty append 0 for plotting
                rmv.append(0)
            elif (row[1] == None): # If one value is None, then only append the other
                rmv.append(float(row[2]))
            elif (row[2] == None):
                rmv.append(float(row[1]))
            else:
                rmv.append(float(row[1] + row[2])) # Add both the RMV (row[1]) and IMPR_RMV (row[2]) to get total rmv value

            # MAV
            if (row[3] == None):
                mav.append(0)
            else:
                mav.append(float(row[3]))

            # AV
            if (row[4] == None and row[5] == None): # If both are empty append 0 for plotting
                av.append(0)
            elif (row[4] == None): # If one value is empty, then only append the other
                av.append(float(row[5]))
            elif (row[5] == None):
                av.append(float(row[4]))
            else:
                av.append(float(row[4] + row[5])) # Add both the AV (row[4]) and IMPR_AV (row[5]) to get total av value

            mailing_name = row[6]
            property_address = row[7]
            account_id = row[8]

            prev_tax_year = row[0] # Will represent the previous tax year to compare with current tax year (row[0]) at beginning of loop
    
    mydb.close()

        
####################################################      Create graph/table and return to html for display     #############################################


    # Create a figure containing a single axes.
    fig, ax = plt.subplots()
    fig.set_figheight(6)
    fig.set_figwidth(12)

    # Plot the data correlating to RMV, MAV, and AV
    # RMV
    ax.plot(tax_year, rmv, marker='s', color='blue', linewidth=5, alpha=0.3, label='Real Market Value')

    # MAV
    ax.plot(tax_year, mav, marker='.', color='red', linewidth=5, alpha=0.3, label='Maximum Assessed Value')

    # AV
    ax.plot(tax_year, av, marker='o', color='green', linewidth=1.5, label='Assessed Value')

    # Set x/y-axis labels
    ax.set_ylabel('Value', labelpad=10)
    ax.set_xlabel('Year', labelpad=10)

    # Set x-axis ticks to correlate to Tax_Year
    ax.set_xticks(tax_year)

    # Style the ticks
    ax.tick_params(axis='y', direction='inout', length=7, width=1.25)
    ax.tick_params(axis='x', direction='inout', length=7, width=1.25)

    # make sure the tax years span from edge to edge of x-axis
    ax.set_xlim(tax_year[0], tax_year[-1])

    # Format the y-axis ticks labels (Amount) to display a dollar value (ex. 10000 == $10,000)
    fmt = '${x:,.0f}'
    tick1 = tick.StrMethodFormatter(fmt)
    ax.yaxis.set_major_formatter(tick1) 

    # Add a legend
    ax.legend(
        loc='upper center', 
        bbox_to_anchor=(0.5, 1.15), # Place the legend above the plot
        ncol=3, # make the legend into 3 columns, one for each value
    )

    # Adjusting top and right borders tranparency
    ax.spines['top'].set_alpha(0.1)
    ax.spines['right'].set_alpha(0.1)

    # Adjusting bottom and left borders width
    ax.spines['bottom'].set_linewidth(1.5)
    ax.spines['left'].set_linewidth(1.5)

    # Add gridlines
    ax.grid(color='grey', linestyle='-', linewidth=0.25, alpha=0.5)

    # Create data from graph to send to html for display
    imgdata = StringIO()
    fig.savefig(imgdata, format='svg')
    imgdata.seek(0)
    graph = imgdata.getvalue()

    plt.close()

    # Create table to display graph data
    df = pd.DataFrame()
    df['Tax Year'] = tax_year
    df['Real Market Value'] = rmv
    df['Maximum Assessed Value'] = mav
    df['Assessed Value'] = av
    table = df.to_html() # Convert to html to send back and be displayed

    # info to be sent back to html and displayed on submit
    context= { 'account_id':account_id,
    'mailing_name':mailing_name,
    'property_address':property_address,
    'submitbutton':submitbutton,
    'graph':graph,
    'table':table
    }

    return render(request, 'hello_world.html', context)