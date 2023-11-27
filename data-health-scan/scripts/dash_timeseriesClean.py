"""
This python module will contain specific functions for the cleaning of timeseries data in Project LEO. The scripts
will be in keeping with the methods described in the 'Project LEO Data Cleaning and Processing.pdf'
document found on the Sharepoint. This is also further documented in the README.md file found in this folder.

TODO: Some sections of the code can be made into functions as to clean up the script a bit
TODO: Update progressbars where needed:
TODO: Add ignore fmt option
"""

# Importing the relevant modules
from datetime import datetime, timedelta
from scipy import stats
import pandas as pd
import os, csv, sys
import numpy as np


def banner(header, size='large'):
    """
    Simple script to print a banner for separating sections of output information. Automatically adjusts to the
    length of the message being printed.

    :param header: String of message to print
    :param size: Whether to print a large or small banner [default: 'large']

    :return: printed message
    """
    if size == 'large':
        print("\n\n{}".format('-'*(len(header)+8)))
        print("{}".format('-'*(len(header)+8)))
        print("    {}".format(header))
        print("{}\n\n".format('-'*(len(header)+8)))
    else:
        print("\n\n    {}".format(header.title()))
        print("{}\n".format('-'*(len(header)+8)))


def load_df(df, date_cols):
    """
    Simple function which will load in a dataset from user input to the dashboard.

    :param
    df: Data that has been uploaded by the user to the Dashboard
    date_cols: the date cols that have been entered by the user

    :return: df
    """
    time_cols = date_cols

    if len(time_cols) == 2:
        # Todo:Factor in the format of the date field to ensure months aren't treated as days
        # Remove the old time columns and then insert the new time at the front
        new_time_col = '{}_{}'.format(time_cols[0], time_cols[1])
        new_time = pd.to_datetime(df[time_cols[0]] + ' ' + df[time_cols[1]])
        df.drop(time_cols, inplace=True, axis=1)
        df.insert(0, new_time_col, new_time)

    elif len(time_cols) == 1:
        new_time = pd.to_datetime(df[time_cols[0]])
        df.drop(time_cols[0], inplace=True, axis=1)
        df.insert(0, time_cols[0], new_time)

    else:
        df = []
        return df

    return df


# TODO: Add a logging function for times where the user did bespoke cleaning of the data
def error_log(f_name, cols, nan_blocks, out_blocks, fmt_blocks):
    """
    This function will take in the outputs of the "err_detect" function and will use the information to update
    the Project LEO Data Cleaning Log which will lists all the Errors found the dataset.

    NB: This Cleaning Log relies on the default naming of the Error Labels and must be run before the
        'solution_log' function

    :param f_name: File name. Original/LEO Identifier are encouraged for data provenance
    :param cols: The columns that were used for cleaning
    :param nan_blocks: Dict of missing/nan value indices in the dataset and their respective sizes
    :param out_blocks: Dict of outliers value indices in the dataset and their respective sizes
    :param fmt_blocks: Dict of formatting error indices in the dataset and their respective sizes

    :return: A df with the recorded error cleaning and columns for solution input
    """
    banner("UPDATING THE CLEANING LOG")

    # Setup the cleaning log dataframe. Use nan as the initial value.
    clean_cols = ['File name', 'Date Cleaned', 'Columns Cleaned',
                  'Num of Single/Two Missing Values', 'Num of Multiple Missing Values', 'Num of Outliers',
                  'Num of Large Gaps', 'Num of Format Errors', 'Linear Interpolation', 'Spline Interpolation',
                  'Hr_Day Filling', 'Week Filling', 'Format corrections']

    cleanlog_df = pd.DataFrame(np.nan, index=[0], columns=clean_cols)
    cleanlog_df['File name'] = f_name
    cleanlog_df['Date Cleaned'] = datetime.now().strftime("%d/%m/%Y")
    cleanlog_df['Columns Cleaned'] = ', '.join(cols)

    # Missing/Nan values. Mul and Lar gaps are counted as a grouping of missing values. Sin counted individually
    sin, mul, lar = 0, 0, 0
    for key in nan_blocks.keys():
        sin += len([n for n in nan_blocks[key][1] if 0 < n <= 2])
        mul += len([n for n in nan_blocks[key][1] if 2 < n <= 10])
        lar += len([n for n in nan_blocks[key][1] if n > 10])

    cleanlog_df['Num of Single/Two Missing Values'] = sin
    cleanlog_df['Num of Multiple Missing Values'] = mul
    cleanlog_df['Num of Large Gaps'] = lar

    # Outliers, counted individually
    out = 0
    for key in out_blocks.keys():
        out += sum([n for n in out_blocks[key][1]])
    cleanlog_df['Num of Outliers'] = out

    # Formatting errors
    fmt = 0
    for key in fmt_blocks.keys():
        fmt += sum([n for n in fmt_blocks[key][1]])
    cleanlog_df['Num of Format Errors'] = fmt

    return cleanlog_df


class Formatting:
    """
    This class contains/will contain a few functions for preparing a dataset for Errors and Solutions application.
    Please review the description of the individual functions for more details.

    :param err_labels: The default number of error labels
    :param sol_labels: The default number solution labels
    :param db_path: The main directory to the datasets
    :param log_path: Path for the cleaning log
    :param log_file: Cleaning log name
    """

    def __init__(self,
                 err_labels=5,
                 sol_labels=5,
                 db_path='/Users/mashtine/PycharmProjects/ProjectLEO_Data/Downloads/Submitted Data',
                 log_path='/Users/mashtine/PycharmProjects/ProjectLEO_Data/Cleaning',
                 log_file='Project LEO Data Cleaning Log.csv'):

        self.err_labels = err_labels
        self.sol_labels = sol_labels
        self.db_path = db_path
        self.log_path = log_path
        self.log_file = log_file

    def bin_labels(self, df, data_cols):
        """
        Simple function for the addition of the necessary columns into the raw date to eventually produce the
        cleaned dataframe. This function will add columns for implementing the LEO 'multi-classification labelling'
        method as per the 'Project LEO Data Cleaning and Processing.pdf' document found on the Sharepoint and
        describbed in the BitBuket documentation.

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


        It is best to use subsets of large dataframes (with many parameters) for cleaning. Only input dataframes with
        columns pertaining to relevant data and parameters for the analysis at hand. This function will not add
        columns for the cleaned data as that will be kept in a separate

        :param
        df: Raw dataframe
        data_cols: user selected cols for cleaning

        :return: df: Formatted dataframe with appropriate Error and Solution Labels Included
        """
        df_binlabels = df.copy()

        # This section of the script will take user input of the columns (max. 5) of data that they are interested in
        # cleaning. This is done as for very large datasets, it becomes more impractical to clean many different
        # columns of data that may be of very different data types.
        cols_toclean = data_cols

        # Add in the Error Labels col. This singular col will contain the binary Error Labels for all of the cols to
        # be cleaned. Thus, if 2 cols are to be cleaned, the Error Label col will have the format of "0000000000"
        # where the order of the bits correspond to the respective Error Labels based on the order of the
        # cols submitted by the user. This methods allows for a neater dataframe structure instead of having each
        # col to be cleaned, having 5 of its own Error Label cols.
        df_binlabels['Errors'] = "".zfill(len(cols_toclean) * self.err_labels)

        # Add in the Solution Labels
        df_binlabels['Solutions'] = "".zfill(len(cols_toclean) * self.sol_labels)

        # Add in the columns that will be used to represent the clean data for the columns that were parsed by
        # the user through 'cols_toclean'. The identifier of '_cl' will be added to the column name and until
        # cleaning has been performed, these columns will hold the original data
        for col in cols_toclean:
            col_name = col + '_cl'
            df_binlabels[col_name] = df_binlabels[col]

        # Within the Solutions phase, the user has the option to reenter only the names of energy columns
        # for certain solution functions and thus it is important to record the order the bits in the Errors and
        # Solutions labels. For instance, if this bit system was used, 000000000000000, but only one column of the
        # original three was used to apply a solution, we need a way to extract the exact set of zeros from the full
        # label
        label_ord = {}
        for c, col in enumerate(cols_toclean):
            label_ord[col] = c

        return label_ord, df_binlabels

    #TODO: Incorporate this into second version of cleaning dashboard
    def fix_missing_timestamp_index(self, df, time_idx):
        """
        Currently testings
        If timestamps are missing, this will reindex the dataframe with all missing timestamps, entering nan in empty rows.
        An issue if the timestamp isn't (intended to be) regular, or if the reqular sequence breaks part way through e.g. 3,6,9,12,13,16,19.
        
        
        Returns
        -------
        None.

        """
        
        if not time_idx:
            # The estimation of frequency handles both continuous and discontinuous data
            time_col = df.columns[0]
            df.index = df[time_col]
            df.drop(time_col, axis=1, inplace=True)
            freq = df.index.to_series().diff().mode()[0]
        else:
            freq = df.index.to_series().diff().mode()[0]
        
        start_loc = df.index.get_loc(df[df.index.to_series().diff() == freq].index[0])-1
        start_datetime = df.index[start_loc]
        end_datetime = df.index[-1]
        new_axis = pd.date_range(start=start_datetime, end=end_datetime,
                                freq=freq)

        # reindex with complete timeaxis, fills empty rows with nan
        df = df.reindex(new_axis)
            
        return df


class Errors:
    """
    This class contains many different functions for detecting errors within a parsed dataset.
    Please review the description of the individual functions for more details.

    :param min_size: The minimum size of 'nan' to filter for
    :param thres: The Z-score threshold to use (searches for extreme values only, not sharp voltage changes etc)
    :param fmt_cats: A list of formatting categories that will used by the function to determine how to can the data
    :param log_path: Path for the cleaning log
    :param log_file: Cleaning log name
    """
    # TODO: Eventually neaten up to have the class use 'df' and 'cols' as input and not the functions. Same for Sols
    #  These functions were originally outside of the class

    def __init__(self,
                 min_size=0,
                 thres=5.0,
                 fmt_cats=None,
                 log_path='/Users/mashtine/PycharmProjects/ProjectLEO_Data/Cleaning',
                 log_file='Project LEO Data Cleaning Log.csv'):

        # Use the default labels
        err_labels = ["miss_val", "mul_miss_val", "outlier", "large_gap", "fmt_err"]

        self.err_labels = err_labels
        self.min_size = min_size
        self.thres = thres
        self.fmt_cats = fmt_cats
        self.log_path = log_path
        self.log_file = log_file

    def err_nan_blocks(self, df, cols):
        """
        This function will comb through a dataframe to find regions of 'Nan' blocks in the data depending on the
        minimum size set by the user.
        TODO:This code can be optimised

        :param df: Dataframe to examine
        :param cols: list of cols to clean

        :return: Dictionary of recorded 'nan' blocks for each col examined
        """
        # Determine the indicies of nan locations for each of the columns of interest
        nan_blocks = {}
        for col in cols:
            nans = pd.isnull(df[col]).to_numpy().nonzero()[0]
            blocks = []
            sizes = []

            # Only perform if missing values exist
            if nans.size == 0:
                # Skip the rest of the loop and go to the next column
                continue

            # This loop will pull out consecutive blocks of nans found in the dataframe cols
            for i, nan in enumerate(nans):
                # Ignore 'i-1' idx. The code will restart the code over if this
                # condition is true
                if i == 0:
                    start = nans[0]
                    continue

                # This condition below checks if the current idx is equal to the one before and
                # if the iteration is not at the end. If true, then it restarts the loop as it means that the
                # nan value is part of a larger block
                if (nan == nans[i - 1] + 1) and (i != (len(nans) - 1)):
                    continue

                # Determines if the loop is at the end. If the following is true for both,
                # that mean that the previous nan was not part of a block and the last value is a singular nan as well
                elif i == (len(nans) - 1) and nan - nans[i - 1] != 1:  # last point
                    size = 1
                    if size > self.min_size:
                        blocks.append(nans[i - 1])
                        blocks.append(nan)
                        sizes.append(size)
                        sizes.append(size)
                    continue

                # Block has ended (which is one that ends at the end of the 'nans' list and thus 'end' should be the
                # last nan value
                elif i == (len(nans) - 1) and nan - nans[i - 1] == 1:
                    end = nan

                # Otherwise treat the end as the value before
                else:
                    end = nans[i - 1]

                # If true, treat as a single nan, not a block
                if end == start:
                    block = start
                    size = 1

                else:
                    # Assign the boundaries of the block of nans
                    block = [start, end]
                    size = end - start + 1

                # Only add if the minimum size of a block as been met
                if size > self.min_size:
                    blocks.append(block)
                    sizes.append(size)

                # Restarts to the new block
                start = nan

                # if ignore_start and (len(blocks) > 0):
                #     if 0 in blocks[0]:
                #         del blocks[0]
                #         del sizes[0]

            # Add the blocks and sizes information into a dict for each of the cols
            # The following line will capture any instances where there is only one missing/nan value
            if nans.size == 1:
                blocks.append(nans[0])
                sizes.append(1)

            nan_blocks[col] = [blocks, sizes]

        return nan_blocks

    def err_out_blocks(self, df, cols):
        """
        This function will comb through a dataframe to find regions of outlier blocks in the data depending on the
        Z-score threshold size set by the user. This function will ignore columns that are not numeric in type

        This function relies on the Z-score method to determine periods in the data where the values statistically deviate
        from the normal distribution. A basic explanation on Outliers in Data and visual and statistical methods
        using the Z-score method can be found:
        https://towardsdatascience.com/ways-to-detect-and-remove-the-outliers-404d16608dba

        :param df: Dataframe to examine
        :param cols: list of cols to clean

        :return: Dictionary of recorded outlier blocks for each col examined
        """
        # Determine the indicies of nan locations for each of the columns of interest
        out_blocks = {}

        # Only performs this on columns containing numeric data (or data matching a 'np.number' type)
        num_cols = [c for c in cols if np.issubdtype(df[c].dtype, np.number)]
        non_num = [nn for nn in cols if nn not in num_cols]

        for col in num_cols:
            # Need to perform the Z-score while omitting any 'nan' values in the data. This also maintains the 'nan'
            # values which is needed during the Solutions sections of data cleaning. The Numpy warnings is turned off
            # during this operation and then turned back on once it has been completed
            np.warnings.filterwarnings('ignore')
            outliers = np.where(np.abs(stats.zscore(df[col], nan_policy='omit')) > self.thres)
            np.warnings.resetwarnings()
            blocks = []
            sizes = []

            # Only perform if outliers exist
            if outliers[0].size == 0:
                # Skip the rest of the loop and go to the next column
                continue

            # This loop will pull out consecutive blocks of nans found in the dataframe cols
            outs = outliers[0]
            for o, out in enumerate(outs):
                # Ignore 'i-1' idx. The code will restart the code over if this
                # condition is true
                if o == 0:
                    start = outs[0]
                    continue

                # This condition below checks if the current idx is equal to the one before and
                # if the iteration is not at the end. If true, then it restarts the loop as it means that the
                # nan value is part of a larger block
                if (out == outs[o - 1] + 1) and (o != (len(outs) - 1)):
                    continue

                # Determines if the loop is at the end. If the following is true for both,
                # that mean that the previous nan was not part of a block and the last value is a singular nan as well
                elif o == (len(outs) - 1) and out - outs[o - 1] != 1:  # last point
                    size = 1

                    # Append to main blocks
                    blocks.append(outs[o - 1])
                    blocks.append(out)
                    sizes.append(size)
                    sizes.append(size)
                    continue

                # Block has ended (which is one that ends at the end of the 'nans' list and thus 'end' should be the last
                # nan value
                elif o == (len(outs) - 1) and out - outs[o - 1] == 1:
                    end = out

                # Otherwise treat the end as the value before
                else:
                    end = outs[o - 1]

                # If true, treat as a single nan, not a block
                if end == start:
                    block = start
                    size = 1

                else:
                    # Assign the boundaries of the block of nans
                    block = [start, end]
                    size = end - start + 1

                # Append to main lists
                blocks.append(block)
                sizes.append(size)

                # Restarts to the new block
                start = out

            # Add the blocks and sizes information into a dict for each of the cols
            # The following line will capture any instances where there is only one outlier
            if outs.size == 1:
                blocks.append(outs[0])
                sizes.append(1)

            out_blocks[col] = [blocks, sizes]

        return out_blocks

    def err_fmt_blocks(self, df, cols):
        """
        This function will comb through a dataframe to find regions of formatting errors in the data depending on the
        categories set by the user. This function will ignore columns that are numeric in type

        The available formatting categories are:

        'caps_fmt': Looks for regions where the data differs from the most common case used in the column
        'space_fmt': Looks for regions where the data contains unnecessary spacing
        TODO: Need to think of others. Probably one related to time though this will be difficult to automate
                and perhaps not necessary

        :param df: The formatted dataframe that contains the 'Errors' and 'Solutions' labels
        :param cols: Columns to be checked

        :return: Dictionary of recorded formatting errors for the user submitted cols
        """
        # Use the standard formatting error checks.
        if self.fmt_cats is None:
            fmt_cats = ['caps_fmt', 'space_fmt']
        else:
            fmt_cats = self.fmt_cats

        # Determine the indicies of nan locations for each of the columns of interest
        fmt_blocks = {}

        # Only performs this on columns containing numeric data (or data matching a 'np.number' type)
        num_cols = [c for c in cols if np.issubdtype(df[c].dtype, np.number)]
        non_num = [nn for nn in cols if nn not in num_cols]

        for col in non_num:
            blocks = []
            sizes = []

            if 'caps_fmt' in fmt_cats:
                # This section will pull out a subset of the data to determine the common case of the data
                # Ensures that the dataset is at least twice the size of the random data subset pulled
                samp = 100
                cases_idx = ['lower', 'upper', 'mixed']

                if len(df[col]) > 2 * samp:
                    samp_data = df[col].sample(n=samp).dropna()
                else:
                    samp_data = df[col].sample(n=(len(df[col]) / 2)).dropna()

                # Determines the most common case through examining 'False' cases
                tot = len(samp_data)  # Without any Nan values
                cases = []

                # Create a list of case counts ['lower', 'upper', 'mixed']
                cases.append(len(samp_data[samp_data.str.islower()]))
                cases.append(len(samp_data[samp_data.str.isupper()]))
                cases.append(tot - sum(cases))

                max_idx = cases.index(max(cases))

                # Pull out the indices of times where the common case is not met from the full dataset col
                # There is no way to automatically correct the strings to values of mixed case, so if 'mixed' is the
                # main cat, these will be converted to upper during the 'Solutions' phase
                if max_idx == 0:
                    case_errs = df[col].str.islower().dropna()
                    fmt_idx = np.where(case_errs == False)[0]
                else:
                    case_errs = df[col].str.isupper().dropna()
                    fmt_idx = np.where(case_errs == False)[0]

            if 'space_fmt' in fmt_cats:
                # This section will find values that have spacing in them. 'str.find(' ')' denotes '-1' as regions having no
                # spaces.
                spc_errs = np.where(df[col].dropna().str.find(' ') != -1)[0]
                fmt_idx = np.append(fmt_idx, spc_errs)
                np.sort(fmt_idx)

            else:
                fmt_idx = []
                sys.exit()

            # Only perform if formatting errors exist
            if fmt_idx.size == 0:
                # Skip the rest of the loop and go to the next column
                continue

            # This loop will pull out consecutive blocks of nans found in the dataframe cols
            for f, fmt in enumerate(fmt_idx):
                # Ignore 'i-1' idx. The code will restart the code over if this
                # condition is true
                if f == 0:
                    start = fmt_idx[0]
                    continue

                # This condition below checks if the current idx is equal to the one before and
                # if the iteration is not at the end. If true, then it restarts the loop as it means that the
                # nan value is part of a larger block
                if (fmt == fmt_idx[f - 1] + 1) and (f != (len(fmt_idx) - 1)):
                    continue

                # Determines if the loop is at the end. If the following is true for both,
                # that mean that the previous nan was not part of a block and the last value is a singular nan as well
                elif f == (len(fmt_idx) - 1) and fmt - fmt_idx[f - 1] != 1:  # last point
                    size = 1

                    # Append to main blocks
                    blocks.append(fmt_idx[f - 1])
                    blocks.append(fmt)
                    sizes.append(size)
                    sizes.append(size)
                    continue

                # Block has ended (which is one that ends at the end of the 'nans' list and thus 'end' should be the last
                # nan value
                elif f == (len(fmt_idx) - 1) and fmt - fmt_idx[f - 1] == 1:
                    end = fmt

                # Otherwise treat the end as the value before
                else:
                    end = fmt_idx[f - 1]

                # If true, treat as a single nan, not a block
                if end == start:
                    block = start
                    size = 1

                else:
                    # Assign the boundaries of the block of nans
                    block = [start, end]
                    size = end - start + 1

                # Append to main lists
                blocks.append(block)
                sizes.append(size)

                # Restarts to the new block
                start = fmt

            # Add the blocks and sizes information into a dict for each of the cols
            # The following line will capture any instances where there is only one outlier
            if fmt_idx.size == 1:
                blocks.append(fmt_idx[0])
                sizes.append(1)

            fmt_blocks[col] = [blocks, sizes]

        return fmt_blocks

    def missing_vals(self, df, cols):
        """
        Function for examining the missing/nan values in a dataframe based on the columns parsed by the user.
        The dataframe must first be formatted using the 'bin_labels' function and once run, this function will update the
        labels based on the 'miss_val', 'mul_miss_val', and 'large_gap' Error Labels.

        :param df: A dataframe that has the needed 'Errors' and 'Solutions' columns
        :param cols: The cols that the user would like cleaned

        :return: Dataframe with the 'Errors' col updated to reflect any missing data
        """

        # First determine where the nan/missing values are located within the cols of interest
        nan_blocks = Errors().err_nan_blocks(df, cols)

        # Use 'pos' variables to declare the position of the error labels in the '00000' Error Bit Label
        # This is a bit of hardcoding and the script will fail if this naming structure is not used
        sin_pos = self.err_labels.index("miss_val")
        mul_pos = self.err_labels.index("mul_miss_val")
        lrg_pos = self.err_labels.index("large_gap")
        sin_tot, mul_tot, lrg_tot = 0, 0, 0

        # The output of the 'err_nan_blocks' function will be used to update the Error Labels in the dataframe
        # based on the col where the error lies, and the type of error.
        for i, key in enumerate(nan_blocks.keys()):
            nan_idx = nan_blocks[key][0]
            size_idx = nan_blocks[key][1]

            for s, sze in enumerate(size_idx):
                # This will then change the appropriate Error Label in the 'Errors' col
                # The order of flags to be changed is miss_val, mul_miss_val, large_gap

                if sze == 1:
                    # Find the bit to update in the label based on the number of Error labels,
                    # the column number from the df that is being searched (i), and the position of
                    # of the error label in the order of bits
                    label_idx = (i * len(self.err_labels)) + sin_pos

                    idx = nan_idx[s]
                    label = df["Errors"].iloc[idx]

                    # As strings are immutable, this works to replace the respective bit with a '1' through
                    # slicing
                    new_label = label[:label_idx] + '1' + label[label_idx + 1:]
                    df["Errors"].iloc[idx] = new_label
                    sin_tot += 1

                elif sze == 2:
                    label_idx = (i * len(self.err_labels)) + sin_pos
                    start, end = nan_idx[s][0], nan_idx[s][1]
                    labels = df["Errors"].iloc[start:end + 1]

                    # It is important to change each label individually as to not erode any previous
                    # bit information from other errors
                    for l, lbl in enumerate(labels):
                        new_label = lbl[:label_idx] + '1' + lbl[label_idx + 1:]
                        labels.iloc[l] = new_label

                    # Put the new labels back into the dataframe
                    df["Errors"].iloc[start:end + 1] = labels
                    sin_tot += 1

                # Multiple Missing/Nan Values
                elif 2 < sze <= 10:
                    label_idx = (i * len(self.err_labels)) + mul_pos
                    start, end = nan_idx[s][0], nan_idx[s][1]
                    labels = df["Errors"].iloc[start:end + 1]
                    for l, lbl in enumerate(labels):
                        new_label = lbl[:label_idx] + '1' + lbl[label_idx + 1:]
                        labels.iloc[l] = new_label
                    df["Errors"].iloc[start:end + 1] = labels
                    mul_tot += 1

                # Large Gap in the data
                else:
                    label_idx = (i * len(self.err_labels)) + lrg_pos
                    start, end = nan_idx[s][0], nan_idx[s][1]
                    labels = df["Errors"].iloc[start:end + 1]
                    for l, lbl in enumerate(labels):
                        new_label = lbl[:label_idx] + '1' + lbl[label_idx + 1:]
                        labels.iloc[l] = new_label
                    df["Errors"].iloc[start:end + 1] = labels
                    lrg_tot += 1

        return df, nan_blocks, [sin_tot, mul_tot, lrg_tot]

    def outlier_vals(self, df, cols):
        """
        Function for examining outlier values in a dataframe based on the columns parsed by the user.
        The dataframe must first be formatted using the 'bin_labels' function and once run, this function will update the
        labels based on the 'outlier' Error Label.

        This function relies on the Z-score method to determine periods in the data where the values statistically deviate
        from the normal distribution. A basic explanation on Outliers in Data and visual and statistical methods
        using the Z-score method can be found:
        https://towardsdatascience.com/ways-to-detect-and-remove-the-outliers-404d16608dba

        :param df: A dataframe that has the needed 'Errors' and 'Solutions' columns
        :param cols: The cols that the user would like cleaned

        :return: Dataframe with the 'Errors' col updated to reflect any missing data (including the results values)
        """
        # First determine where the nan/missing values are located within the cols of interest
        out_blocks = Errors().err_out_blocks(df, cols)

        # Use the 'pos' variable to declare the position of the 'outlier' in the '00000' Error Bit Label
        # This is a bit of hardcoding and the script will fail if this naming structure is not used
        out_pos = self.err_labels.index("outlier")
        out_tot = 0

        # The output of the 'err_out_blocks' function will be used to update the Error Labels in the dataframe
        # based on the col where the outlier error lies.
        for i, key in enumerate(out_blocks.keys()):
            out_idx = out_blocks[key][0]
            size_idx = out_blocks[key][1]

            for s, sze in enumerate(size_idx):
                # This will then change the appropriate Error Label in the 'Errors' col
                if sze == 1:
                    # Find the bit to update in the label based on the number of Error labels,
                    # the column number from the df that is being searched (i), and the position of
                    # of the error label in the order of bits
                    label_idx = (i * len(self.err_labels)) + out_pos

                    idx = out_idx[s]
                    label = df["Errors"].iloc[idx]

                    # As strings are immutable, this works to replace the respective bit with a '1' through
                    # slicing
                    new_label = label[:label_idx] + '1' + label[label_idx + 1:]
                    
                    # scot testing below
                    #df.loc[idx, "Errors"] = new_label
                    df.iloc[idx, df.columns.get_loc("Errors")] = new_label
                    out_tot += 1

                else:
                    label_idx = (i * len(self.err_labels)) + out_pos
                    start, end = out_idx[s][0], out_idx[s][1]
                    labels = df["Errors"].iloc[start:end + 1]

                    # It is important to change each label individually as to not erode any previous
                    # bit information from other errors
                    for l, lbl in enumerate(labels):
                        new_label = lbl[:label_idx] + '1' + lbl[label_idx + 1:]
                        labels.iloc[l] = new_label

                    # Put the new labels back into the dataframe
                    df["Errors"].iloc[start:end + 1] = labels
                    out_tot += 1

        return df, out_blocks, out_tot

    def format_vals(self, df, cols):
        """
        Function for examining for formatting issues in a dataframe based on the columns parsed by the user.
        The dataframe must first be formatted using the 'bin_labels' function and once run, this function will update the
        labels based on the 'fmt_err' Error Label.

        :param df: A dataframe that has the needed 'Errors' and 'Solutions' columns
        :param cols: The cols that the user would like cleaned

        :return: Dataframe with the 'Errors' col updated to reflect any missing data (including the results values)
        """
        # First determine where the nan/missing values are located within the cols of interest
        # There is an optional argument 'fmt_cats' but this functionality will be expanded on in later version
        # to accommodate more formatting checks if needed
        fmt_blocks = Errors().err_fmt_blocks(df, cols)

        # Use the 'pos' variable to declare the position of a format error in the '00000' Error Bit Label
        # This is a bit of hardcoding and the script will fail if this naming structure is not used
        fmt_pos = self.err_labels.index("fmt_err")
        fmt_tot = 0

        # The output of the 'err_fmt_blocks' function will be used to update the Error Labels in the dataframe
        # based on the col where the formatting error lies.
        for i, key in enumerate(fmt_blocks.keys()):
            fmt_idx = fmt_blocks[key][0]
            size_idx = fmt_blocks[key][1]

            for s, sze in enumerate(size_idx):
                # This will then change the appropriate Error Label in the 'Errors' col
                if sze == 1:
                    # Find the bit to update in the label based on the number of Error labels,
                    # the column number from the df that is being searched (i), and the position of
                    # of the error label in the order of bits
                    label_idx = (i * len(self.err_labels)) + fmt_pos

                    idx = fmt_idx[s]
                    label = df["Errors"].iloc[idx]

                    # As strings are immutable, this works to replace the respective bit with a '1' through
                    # slicing
                    new_label = label[:label_idx] + '1' + label[label_idx + 1:]
                    df.loc[idx, "Errors"] = new_label
                    fmt_tot += 1

                else:
                    label_idx = (i * len(self.err_labels)) + fmt_pos
                    start, end = fmt_idx[s][0], fmt_idx[s][1]
                    labels = df["Errors"].iloc[start:end + 1]

                    # It is important to change each label individually as to not erode any previous
                    # bit information from other errors
                    for l, lbl in enumerate(labels):
                        new_label = lbl[:label_idx] + '1' + lbl[label_idx + 1:]
                        labels.iloc[l] = new_label

                    # Put the new labels back into the dataframe
                    df["Errors"].iloc[start:end + 1] = labels
                    fmt_tot += 1

        return df, fmt_blocks, fmt_tot

    def err_detect(self, df, cols):
        """
        By default, this function will perform operations using the default Error Labels. If more bespoke error
        dection is needed, please refer to other functions found within this module.

        For standarization and simplicity, the "miss_val" will be treated as both nan and missing data values
        of 1 or two consecutive times. The "mul_miss_val" flag will be applied for consecutive instances of
        3-10 missing values/nan. The "large_gap" flag will be applied for consecutive instances of
        > 10 missing values/nan.

        :param df: The prepared dataframe that contains the Error and Solution Labels
        :param cols: The cols of interest for cleaning

        :return: df: The returned dataframe has updated Error labels to show which parts of the data contain errors
        """
        # This section will be used to check for both the missing values error labels
        # The following functions use the default Error Labels
        totals = []
        updated_df, nan_blocks, count = Errors().missing_vals(df, cols)
        totals.append(count)

        # This section will be used to check for outliers in the data
        # The following functions use the default Error Labels.
        # The Z-score threshold to use for determining the outliers has a default value of 5.0 (extreme values)
        updated_df, out_blocks, count = Errors().outlier_vals(updated_df, cols)
        totals.append(count)

        # This section will be used to check for formatting errors in the data
        # The following functions use the default Error Labels.
        updated_df, fmt_blocks, count = Errors().format_vals(updated_df, cols)
        totals.append(count)

        return updated_df, nan_blocks, out_blocks, fmt_blocks, totals


class Solutions:
    """
    This class contains many different functions for dealing with errors which were detected within a parsed dataset.
    Please review the description of the individual functions for more details.

    Todo: Add functionality for cleaning of formatting errors

    :param updated_df: The dataframe that has been checked for errors
    :param cols: Columns which have been scanned for errors
    :param nan_blocks: Results of the Nan/Missing value error check
    :param out_blocks: Results of the Outlier value error check
    :param fmt_blocks: Results of the formatting error check
    :param log_path: Path for the cleaning log
    :param log_file: Cleaning log name
    """

    def __init__(self,
                 updated_df, cols, label_ord, nan_blocks, out_blocks, fmt_blocks,
                 log_path='/Users/mashtine/PycharmProjects/ProjectLEO_Data/Cleaning',
                 log_file='Project LEO Data Cleaning Log.csv'):
        # Use the default labels
        sols_labels = ['lin_intpol', 'spln_intpol', 'hr_day_fill', 'week_fill', 'fmt_correct']

        self.updated_df = updated_df
        self.cols = cols
        self.label_ord = label_ord
        self.nan_blocks = nan_blocks
        self.out_blocks = out_blocks
        self.fmt_blocks = fmt_blocks
        self.sols_labels = sols_labels
        self.log_path = log_path
        self.log_file = log_file

    def time_freq(self, time_idx=False):
        """
        This function simply reads in the dataframe (only one with a time column) to determine the frequency of the
        timeseries data. This function works on the assumption that one time column exists in the dataset and
        it is the first column (can be changed using the 'time_index' flag).

        If the dataset does not have time as the index, this will return a dataset where the timestamp col becomes
        the index of the dataframe

        :param: time_idx: A flag for telling the function whether the dataframe uses time as the index

        :return: str: The frequency of the time data
        :return: df: New dataset with proper indexing for Solution application
        """

        # First, set the df index to be the time
        df = self.updated_df
        if not time_idx:
            # The estimation of frequency handles both continuous and discontinuous data
            time_col = df.columns[0]
            df.index = df[time_col]
            df.drop(time_col, axis=1, inplace=True)
            freq = df.index.to_series().diff().min()
        else:
            freq = df.index.to_series().diff().min()

        return df, freq

    def spln_interp(self):
        """
        This function will fill longer/more complex gaps in datasets exhibiting non-linear relationships
        with interpolated data of a higher order.

        :return: df: Dataset with the cleaned data and appropriately recorded solution labels
        """
        test = 'test'

    def rvm_outliers(self, df):
        """
        This simple function when run will comb through the outliers that were detected in previous stages and will
        remove these values, replacing the erroneous data with Nan values in the cleaned columns of the dataset.
        The outliers are removed as to not affect any interpolation methods that are applied to replace them.

        The "out_blocks" will be concatenated with the "nan_blocks", so that in the later stages of filling the data,
        outlier gaps (once removed and filled with Nan) will be treated the same way as missing data gaps. Single
        outlier values (1/2 missing values) will be treated in the same manner as those of any missing data.

        :return: df
        """
        # Create a new dictionary from "nan_blocks" for adding in the "out_blocks"
        out_nan_blocks = self.nan_blocks

        # First, replace any outliers in the data with Nan
        # Then add each of these blocks to the 'out_nan_blocks' dict
        for k, v in zip(self.out_blocks.keys(), self.out_blocks.values()):
            clean_col_name = k + '_cl'
            for block in v[0]:
                if type(block) == list:
                    start, end = block[0], block[-1]
                    df[clean_col_name].iloc[start: end + 1] = np.nan

                    # Join the "out_blocks" to the "out_nan_blocks". This is done to condense the code
                    # so that all operations are run on one dict.
                    if k in out_nan_blocks.keys():
                        out_nan_blocks[k][0].append(block)
                        out_nan_blocks[k][1].append(end - start + 1)
                    else:
                        # If the column was not in the nan_blocks (ie it had no missing values)
                        # this part will add it to the dictionary as it now contains missing data
                        out_nan_blocks[k] = [[block], [end - start + 1]]
                else:
                    df[clean_col_name].iloc[block] = np.nan
                    if k in out_nan_blocks.keys():
                        out_nan_blocks[k][0].append(block)
                        out_nan_blocks[k][1].append(1)
                    else:
                        out_nan_blocks[k] = [[block], [1]]

        return df, out_nan_blocks

    def power_fill(self, df, out_nan_blocks, freq, offset=1, interp='linear'):
        """
        This function will be used to fill data gaps in datasets. NB: Minimum resolution of hourly data.
        Single missing data points are filled with interpolation, 'linear' being the default method.

        Outlier gaps are filled first where possible as to avoid any filling of missing data with erroneaous values

        This method simply fills the power data with averaged data from time periods wrapping the data of an
        appropriate span. For instance, if a single minute of data is missing, this function will use averaged data
        from the previous hour (depending on the 'offset' used) of the same minute and likewise for
        an hour ahead to fill the gap.

        Please note that this function only adds cleaned data to the cleaned version of the data columns.
        The raw data are left untouched. For instance, a column titled 'Data' will have a subsequent column pairing
        called 'Data_cl' where the clean data will be placed into.

        TODO: See how data filling can be improved (e.g.: is the day before/after an adecuate solution?)
        What about sub hourly data, the filling times eg hour before is less relevent. Just use linear?

        :param: df: Takes the dataframe that has time as an index as input. Use the 'time_freq' function if needed
        :param: out_nan_blocks: The combined 'nan_blocks' and 'out_blocks' listing all areas of missing data
        :param: freq: Uses the input of the time frequency
        :param: offset: The number of hours ahead or after to use for averaging
        :param: interp: The default interpolation method. If 'spline' used, the user will be asked for the order to use

        :return: df: Dataframe with the clean data if appropriate
        """

        # Set parameters if spline interpolation used (only other option)
        #TODO: Needs to be updated for the web-app tool for user input
        # if interp == 'spline':
        #     order = input("You have selected to run a spline interpolation method for the filling of single "
        #                   "missing values.\nPlease enter the order number to run these interpolations (eg: 3):")

        # Pulls the data columns from where errors existed
        data_cols = list(out_nan_blocks.keys())
        clean_cols = data_cols

        # Work through each of the energy columns to clean as per the user submission
        interp_blocks = {}
        fill_blocks = {}

        for col in clean_cols:
            clean_col_name = col + '_cl'
            int_blocks, int_lbls = [], []
            f_blocks, f_lbls = [], []

            for block in out_nan_blocks[col][0]:
                # First part deals with multiple missing values (blocks with start and end values, ie, not int values)
                if type(block) == list:
                    # Recreate times of the block given the frequency of the data
                    times = pd.date_range(start=df.index[block[0]], end=df.index[block[-1]], freq=freq)

                    # Determine the periods that occur before and after for gaps less than a week in length
                    # Checks are done below to determine if data exists for these times
                    hr_before = times - timedelta(hours=offset)
                    hr_after = times + timedelta(hours=offset)
                    day_before = times - timedelta(days=1)
                    day_after = times + timedelta(days=1)
                    week_before = times - timedelta(weeks=1)
                    week_after = times + timedelta(weeks=1)

                    # Check if range within entire df range and new range contains no nans
                    # In high-resolution data, you may need to adjust the offset so that you look at the 30-min/min
                    # times before if going an hour before or after goes beyond the dataset timeline

                    #TODO: Consider changing this so that instead of assuming the data is clean if it isn't missing,
                    # a check should be done to see if any errors were recorded using the Error label col
                    # If this only containes "000000" then the data can be used.

                    # SCOT: I think there is an issue with using .loc, if index doesn't exist
                    # https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#indexing-deprecate-loc-reindex-listlike
                    # tried using df[col].loc[df.index.intersection(hr_before)] but then miss-matched arrays for mean. 
                    # have tried filling in missing rows first up.
                    if (((hr_before[0] >= df.index[0]) and (hr_after[0] <= df.index[-1]))
                            and ((not df[col].loc[hr_before].isna().values.any()) and (
                                    not df[col].loc[hr_after].isna().values.any()))):

                        # Fill the missing data with a mean of the hour before and after times
                        # NB: The raw data columns are not filled with data
                        fill_vals = np.mean([df[col].loc[hr_before].values, df[col].loc[hr_after].values], axis=0)
                        df.loc[times, clean_col_name] = fill_vals

                        # Determine the position of the column in the Solutions label.
                        # Also determine the label position with the label order
                        col_pos = self.label_ord[col]
                        fill_pos = self.sols_labels.index("hr_day_fill")

                        # Update the specific label for the column being cleaned
                        label_idx = (col_pos * len(self.sols_labels)) + fill_pos
                        start, end = block[0], block[1]
                        labels = df["Solutions"].iloc[start:end + 1]

                        # As strings are immutable, this works to replace the respective
                        # bit with a '1' through slicing
                        for l, lbl in enumerate(labels):
                            new_label = lbl[:label_idx] + '1' + lbl[label_idx + 1:]
                            labels.iloc[l] = new_label

                        df["Solutions"].iloc[start:end + 1] = labels

                        # Record the application of the solution for reporting to the user after the func runs
                        f_blocks.append(block)
                        f_lbls.append("hr_day_fill")

                    elif (((day_before[0] >= df.index[0]) and (day_after[0] <= df.index[-1]))
                            and ((not df[col].loc[day_before].isna().values.any()) and (
                                    not df[col].loc[day_after].isna().values.any()))):

                        # Fill the missing data with a mean of the day before and after times
                        fill_vals = np.mean([df[col].loc[day_before].values, df[col].loc[day_after].values], axis=0)
                        df.loc[times, clean_col_name] = fill_vals

                        # Update the specific label for the column being cleaned
                        col_pos = self.label_ord[col]
                        fill_pos = self.sols_labels.index("hr_day_fill")
                        label_idx = (col_pos * len(self.sols_labels)) + fill_pos
                        start, end = block[0], block[1]
                        labels = df["Solutions"].iloc[start:end + 1]
                        for l, lbl in enumerate(labels):
                            new_label = lbl[:label_idx] + '1' + lbl[label_idx + 1:]
                            labels.iloc[l] = new_label
                        df["Solutions"].iloc[start:end + 1] = labels

                        # Record the application of the solution for reporting to the user after the func runs
                        f_blocks.append(block)
                        f_lbls.append("hr_day_fill")

                    elif (((week_before[0] >= df.index[0]) and (week_after[0] <= df.index[-1]))
                            and ((not df[col].loc[week_before].isna().values.any()) and (
                                    not df[col].loc[week_after].isna().values.any()))):

                        # Fill the missing data with a mean of the day before and after times
                        fill_vals = np.mean([df[col].loc[week_before].values, df[col].loc[week_after].values], axis=0)
                        df.loc[times, clean_col_name] = fill_vals

                        # Update the specific label for the column being cleaned
                        # This will update the 'week_fill' label
                        col_pos = self.label_ord[col]
                        fill_pos = self.sols_labels.index("week_fill")
                        label_idx = (col_pos * len(self.sols_labels)) + fill_pos
                        start, end = block[0], block[1]
                        labels = df["Solutions"].iloc[start:end + 1]
                        for l, lbl in enumerate(labels):
                            new_label = lbl[:label_idx] + '1' + lbl[label_idx + 1:]
                            labels.iloc[l] = new_label
                        df["Solutions"].iloc[start:end + 1] = labels

                        # Record the application of the solution for reporting to the user after the func runs
                        f_blocks.append(block)
                        f_lbls.append("week_fill")

                    # If the above conditions can not be met, then the block is not able to be filled and thus
                    # the Solutions label will stay unchanged.
                    # Further functionality may be added to address these times
                    else:
                        # Record the lack of solution for reporting to the user after the func runs
                        f_blocks.append(block)
                        f_lbls.append("unfilled")
                        pass

                # This part will deal with single missing values. As single missing values do not need to maintain
                # historical patterns in the data (for instance, 5 hrs of missing data can not be simply filled with
                # interpolated/mean data), linear interpolation will be used to fill these values
                else:
                    # First, pull out the data just before and after the missing value (ie, 3 values)
                    # This code also caters for the one-off instance where the single missing value is at the end or
                    # the start of the data (ie, no value occurs after it). These cases will be left untouched
                    if block == 0 or df[col].iloc[block] == df[col].iloc[-1]:
                        # Data will not be filled and the Solutions label will not be changed
                        # Record the lack of solution for reporting to the user after the func runs
                        int_blocks.append(block)
                        int_lbls.append("unfilled")
                        pass

                    else:
                        # Fill based on the interpolation chosen by the user
                        # if interp == 'linear':
                        df[clean_col_name].iloc[block-1: block+2] = df[col].iloc[block-1: block+2]\
                            .interpolate(method=interp)
                        sols_lbl = 'lin_intpol'
                        int_blocks.append(block)
                        int_lbls.append("lin_intpol")

                        # else:
                        #     df[clean_col_name].iloc[block - 1: block + 2] = df[col].iloc[block - 1: block + 2]\
                        #         .interpolate(method=interp, order=order)
                        #     sols_lbl = 'spln_intpol'
                        #     int_blocks.append(block)
                        #     int_lbls.append("spln_intpol")

                        # Update the Solutions label
                        col_pos = self.label_ord[col]
                        fill_pos = self.sols_labels.index(sols_lbl)
                        label_idx = (col_pos * len(self.sols_labels)) + fill_pos
                        label = df["Solutions"].iloc[block]
                        new_label = label[:label_idx] + '1' + label[label_idx + 1:]
                        df["Solutions"].iloc[block] = new_label

            # Add the relevant recordings for the column being cleaned
            fill_blocks[col] = [f_blocks, f_lbls]
            interp_blocks[col] = [int_blocks, int_lbls]

        # # banner("Gaps More Than 1 Missing Values", size='small')
        # for k in fill_blocks.keys():
        #     print("{}: {} ({})".format(k, fill_blocks[k][0], fill_blocks[k][1]))
        #
        # # banner("Gaps of a Single Missing Value", size='small')
        # for k in interp_blocks.keys():
        #     print("{}: {} ({})".format(k, interp_blocks[k][0], interp_blocks[k][1]))

        return df, fill_blocks, interp_blocks
