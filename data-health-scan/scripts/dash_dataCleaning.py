"""
This python script will contain perform specific functions on datasets that are to be cleaned. This script can be
adjusted depending on the dataset type and the necessary solutions needed to clean the data

The following Error Labels will be assumed as default used where '0' or '1' represent an absent or
present error respectively:

Single/Two Missing Value (miss_val)
Multiple Missing Values (mul_miss_val)
Outlier (outlier)
Large Gap in Data (large_gap)
Formatting Error (fmt_err)


Likewise, the following Solution Labels will be used as default:

Linear Interpolation (lin_intpol)
Spline Interpolation (spln_intpol)
Hour-Day-Filling (hr_day_fill)
Week-Filling (week_fill)
Format correction (fmt_correct)

"""

# Import relevant libraries
from dash_timeseriesClean import Formatting, Errors, Solutions, banner, load_df, error_log
import os


# This script contains one main function (at present, will be expanded) that will call upon other functions in the
# timeseriesClean script to execute the error detection and data cleaning of a dataset
#TODO: Add ignore fmt option
#TODO: Properly document time_idx

def energydata_clean(dataset, only_cleandata=True, save_data='', save_log=False, time_idx=False):
    """
    This script will call upon various functions to perform automated error detection and data cleaning on a given
    dataset. The clean data file is set to not include the raw data by default. This script can take both a dataframe
    input, or a file path to the dataset to load. You SHOULD use the original or LEO name of the file that is to be
    cleaned so that the proper metadata can be associated with it in the Data Cleaning Log.

    NB: For ease of use, if you have multiple datasets for the same time period and of the same resolution, consider
    formatting into one large dataset so that the script can be run once.

    :param dataset: Pandas DataFrame or a full file path to the dataset
    :param only_cleandata: If used, only the cleaned data columns will be saved as output
    :param save_data: Directory path to save the cleaned dataset [default: empty string with no saved output]
    :param save_log: Used to update the LEO Data Cleaning Log on Bitbucket
    :param time_idx: If True, this was filling any missing time periods in the data

    :return: Cleaned Pandas Dataframe
    """

    # Read in the necessary dataframe and collect certain information on the user.
    df = load_df(dataset)
    user = input("\nPlease enter your email for data provenance purposes:")

    if type(dataset) == str:
        # User has submitted a file path for the dataset to load
        f_name = os.path.basename(dataset)
    else:
        # User has submitted a Pandas DataFrame
        f_name = input("\nPlease enter the file name (with extension) for recording in the Cleaning Log. "
                       "\nYou are asked to use the LEO Identifier of the file as per the Foreground Data Catalogue:")

    # Initialize the Formatting class. This is use the default Error and Solution Labels as above
    # NB: This section will be updated to include any preprocessing for general data formatting
    fmt = Formatting()
    
    # Note: this might not pick up if a column is the time index rather than the df index.
    # The following will fill missing rows of a time indexed dataframe
    if time_idx:
        df = fmt.fix_missing_timestamp_index(df, time_idx)

    # Adding the Binary labels for the Error and Solutions that will be applied to the dataset
    cols_toclean, label_ord, binlabel_df = fmt.bin_labels(df)
    

    """
    Automatically detect Errors based on the default Error Labels presented above or specific labels initialized
    with the 'Errors' class. Please note that if the 'Errors' class is initialized with labels that are different
    to the default options you MUST ensure that the formatting of the dataframe above was done using
    the correct number of Error and Solution Labels that you are using.
    
    Use the 'err_labels' argument if needed to enter a list of Error Labels. The following function relies on a 
    wide rande of other functions that will comb through the data in the columns provided, and update the 'Errors' and 
    'Solutions' labels in the dataframe. Details will be output to the console and if you need to learn more about 
    the specific functions used, please have a look at the 'dash_timeseriesClean.py' script that houses them.
    
    The 'err_detect' function will output the following based on the variable names below:
    
    updated_binlabel_df: The updated dataframe with the Error Bin Labels updated
    nan_blocks: Specific index values showing regions of Missing/Nan values in the data
    out_blocks: Specific index values showing regions of Outlier values in the data (based on Z-score method)
    fmt_blocks: Specific index values showing regions of Formatting Errors in the data
    
    NB: The above may vary if the Error labels parsed are altered in later versions
    
    """
    # Initialize the class 'Errors'
    data_errors = Errors()

    # Conduct the error detection process by parsing the prepared dataframe and the columns variable created above
    # This will return the update dataframe as well as dictionaries containing the location of the errors
    # This will also use a default threshold value of '3.0' for the Z-score method for detecting outliers
    updated_binlabel_df, nan_blocks, out_blocks, fmt_blocks = data_errors.err_detect(binlabel_df, cols_toclean)

    # Log the Error detection
    if save_log==True:
        cleanlog_df = error_log(user, f_name, cols_toclean, nan_blocks, out_blocks, fmt_blocks)

    """
    This section of the script will follow on from the automatic detection of Errors and then determine the 
    solutions to apply to the data. Given the nature of applying solutions, specific to the types of data, parts of this 
    script will involve user input and will not be completely automated to avoid the incorrect application of methods to 
    correct the data values. 
    
    It is also important to note that this script has been developed to deal with timeseries power data and thus, datasets
    of other types or data are expected to be dealt with in a more bespoke postprocessing manner using some of the 
    functions that are found in the library and those found in other Python packages
    """

    # Initialize the class 'Solutions'
    data_sols = Solutions(updated_binlabel_df, cols_toclean, label_ord, nan_blocks, out_blocks, fmt_blocks)

    # First need to organize the dataset so that the timestamp column becomes the index. This step also determines the
    # frequency of the data, even if time is already set as the dataframe's index. The default state assumes that
    # the timestamp data are in a single column and not the index. Change using the 'time_idx' flag
    # NB: This should only be performed on datasets with a timestamp column/index
    updated_binlabel_df, freq = data_sols.time_freq(time_idx)
    
    # Todo: Add functionality to skip this function below if power data does not need to be filled
    # The next part of the script will perform data filling on columns that contain power data (the most common
    # cleaning need within Project LEO). Outliers will first be removed from the data (raw data columns will be
    # left untouched), and then the location of these outliers will be combined with information on other missing
    # data which will be used to fill the data and update the 'Solutions' labels.

    # Gaps (> 2 missing values) will be filled using hr/day/week data filling.
    # Other missing values (1/2 occurances) will be filled using interpolation (default: Linear).

    # First remove the outliers from the dataset and replace the missing values with 'Nan' in the respective clean
    # columns. The 'nan_blocks' and 'out_blocks' will be combined into one for later cleaning

    # Ignores this function if no outliers were detected
    banner("APPLICATION OF DATA CLEANING SOLUTIONS")
    banner("Outlier Removal", size='small')

    if len(out_blocks.keys()) > 0:
        print("\nThe dataset will now have any detected outliers removed. These values will be replaced with 'Nan'"
              "\nand these areas of now missing data will be cleaned in the same fashion as other missing data.")
        updated_binlabel_df, out_nan_blocks = data_sols.rvm_outliers(updated_binlabel_df)
    else:
        print("\nAs no outliers were detected in the data (based on the Z-score threshold set), the step of their"
              "\nremoval will be ignored and the dataset will now be cleaned for any missing data.")
        out_nan_blocks = {}

    # The dataframe is now ready for the filling of missing data. Please see the 'power_fill' function in the
    # 'dash_timeseriesClean.py' library for more information. Once this function has run, the dataset will have updated
    # 'Solutions' labels based on the cleaning performed. The output variables, 'fill_blocks' and 'interp_blocks' will
    # give more information on how parts of the dataset were cleaned and what methods were applied

    # Ignores this function if no missing values (including removed outliers) were detected
    if out_nan_blocks:
        print("\nThe dataset will now have any missing values filled. Please see the function documentation for further"
              " details \non how data filling is performed, including the criteria used.")
        updated_binlabel_df, fill_blocks, interp_blocks = data_sols.power_fill(updated_binlabel_df, out_nan_blocks,
                                                                               freq, offset=1, interp='linear')
    else:
        print("\nAs no missing values were detected in the data, the step of data filling will be ignored."
              "\nIf this is the final step of the dataset cleaning, please see the output Error Log for "
              "further information")
        fill_blocks, interp_blocks = {}, {}

    # Updating of the Error Log now that the data have been cleaned. The Error Log will be saved as
    # 'Project LEO Data Cleaning Log.csv'" in the 'Cleaning' directory

    # Updating the Error Log with respect to interpolations performed
    if save_log==True:
        if interp_blocks:
            lin_count, spln_count = 0, 0
            for v in interp_blocks.values():
                lin_count += v[1].count('lin_intpol')
                spln_count += v[1].count('spln_intpol')
            cleanlog_df['Linear Interpolation'] = lin_count
            cleanlog_df['Spline Interpolation'] = spln_count
    
        # Updating the Error Log with respect to the hr/day/week data filling performed
        if fill_blocks:
            hrday_count, week_count = 0, 0
            for v in fill_blocks.values():
                hrday_count += v[1].count('hr_day_fill')
                week_count += v[1].count('week_fill')
            cleanlog_df['Hr_Day Filling'] = hrday_count
            cleanlog_df['Week Filling'] = week_count
    
        # Ask the user is any further cleaning was performed on the dataset for data provenance purposes
        sols_other = input("\nWere any other cleaning methods (external to this script) performed on this dataset? "
                           "\nIf so, please briefly describe below (< 20 words) or state 'n/a' if there is "
                           "nothing to record:")
        cleanlog_df['Other (Solutions)'] = sols_other

    # If the 'only_cleandata' flag is set to 'True', only the cleaned columns, and any uncleaned columns, will be saved
    # Thus, if 'Column A', and 'Column B' were cleaned by the user, the original columns will be dropped from the df
    # but their cleaned version (and all remaining columns) will be kept.
    if only_cleandata:
        cleaned_cols = [c for c in updated_binlabel_df.columns if c.endswith('_cl')]
        cols_to_rvm = [c.replace("_cl", "") for c in cleaned_cols] + ['Errors', 'Solutions']
        updated_binlabel_df.drop(cols_to_rvm, inplace=True, axis=1)

    # Save data if required
    if save_data:
        banner("Saving the Cleaned Data")
        f_path = save_data + f_name.replace(".", "_cleaned.")

        print("{} will be save to {}".format(f_path, save_data))
        updated_binlabel_df.to_csv(f_path, index=False)

    banner("DATA CLEANING COMPLETED")

    return updated_binlabel_df

