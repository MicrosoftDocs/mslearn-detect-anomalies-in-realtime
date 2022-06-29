# Import library to display results
import time
import pandas as pd
from math import pi
import numpy as np
import os
import pytz
import itertools
import shutil
import uuid
import zipfile
from datetime import datetime
from datetime import timedelta, datetime
from datetime import datetime as dt
from dateutil import parser
from urllib.request import urlretrieve
from bokeh.plotting import figure,output_notebook, show
from bokeh.palettes import Blues4
from bokeh.models.sources import ColumnDataSource
from bokeh.models import Band
from bokeh.layouts import gridplot
from bokeh.io import output_file, show, output_notebook, save
from bokeh.io import output_notebook, show, push_notebook
from bokeh.models import DatetimeTickFormatter
from bokeh.models.tools import HoverTool
from bokeh.palettes import Dark2_5 as palette
from ipywidgets import interact, widgets, fixed
from threading import Thread


def display_results(response, upperband, lowerband, sensitivity, anomaly_labels, anomalies):
    plot_data = ColumnDataSource(
        data=dict(x=np.array([], dtype=datetime), y=np.array([], dtype=float), ax=np.array([], dtype=datetime),
                  ay=np.array([], dtype=float), ex=np.array([], dtype=float), basex=np.array([], dtype=datetime),
                  upper=np.array([], dtype=float), lower=np.array([], dtype=float)))

    values = response['value'].tolist()
    label = response['timestamp'].tolist()

    p = figure(x_axis_type='datetime', width=1000, height=600,
               title="Anomaly Detection Result ({0} Sensitivity)".format(sensitivity))

    circle = p.circle('ax', 'ay', size=5, color='tomato', legend_label='Anomaly', source=plot_data)
    value_line = p.line('x', 'y', legend_label='Actual', color="#2222aa", line_width=1, source=plot_data)
    expected_line = p.line('x', 'ex', legend_label='Expected', line_width=1, line_dash="dotdash",
                           line_color='olivedrab', source=plot_data)
    band = Band(base='basex', lower='lower', upper='upper', level='underlay', source=plot_data, fill_alpha=0.5,
                line_width=1, line_color='black')
    p.add_layout(band)
    p.legend.border_line_width = 1
    p.legend.background_fill_alpha = 0.1

    # configure datetime format to be display on the x-axis
    p.xaxis.formatter = DatetimeTickFormatter(
        seconds=["%d%b%y %H:%M:%S"],
        minutes=["%d%b%y %H:%M:%S"],
        hours=["%d%b%y %H:%M:%S"],
        days=["%d%b%y %H:%M:%S"],
        months=["%d%b%y %H:%M:%S"],
        years=["%d%b%y %H:%M:%S"],
        milliseconds=["%d%b%y H:%M:%S"]
    )
    p.xaxis.major_label_orientation = pi / 4
    p.x_range.follow = "end"
    # define display information when cursor hovered over a data point
    hover = HoverTool(tooltips=[('Timestamp', '@x{%Y-%m-%d %H:%M:%S.%3N}'), ('value', '@y')],
                      formatters={'@x': 'datetime'}, )
    p.add_tools(hover)
    handle = show(p, notebook_handle=True)
    stop_threads = False

    def update_callback(id, stop):
        expected_list = response['expectedValues'].tolist()
        upper_list = upperband.tolist()
        lower_list = lowerband.tolist()
        new_data = dict(x=np.array([], dtype=datetime), y=np.array([], dtype=float), ax=np.array([], dtype=datetime),
                        ay=np.array([], dtype=float), ex=np.array([], dtype=float), basex=np.array([], dtype=datetime),
                        upper=np.array([], dtype=float), lower=np.array([], dtype=float))
        period = 1  # in seconds (simulate waiting for new data)x=np.array([], dtype=datetime), y=np.array([], dtype=float),
        n_show = 300  # number of points to keep and showy=np.array([], dtype=float),
        count = 0
        while (count < len(label)):
            timestamp = label[count]
            value = values[count]
            expected_value = expected_list[count]
            upper_value = upper_list[count]
            lower_value = lower_list[count]
            x = np.array([])
            y = np.array([])
            ax = np.array([])
            ay = np.array([])
            ex = np.array([])
            base = np.array([])
            up = np.array([])
            low = np.array([])
            count += 1
            new_data['x'] = [timestamp]
            new_data['y'] = [value]
            new_data['ax'] = np.append(ax, [timestamp])  # skip red dot if timestamp has no anomaly
            new_data['ay'] = np.append(ay, [np.nan])  # skip red dot if data point has no anomaly
            new_data['ex'] = np.append(ex, [expected_value])
            new_data['basex'] = np.append(base, timestamp)
            new_data['upper'] = np.append(up, upper_value)
            new_data['lower'] = np.append(low, lower_value)
            ts = pd.to_datetime(timestamp, format="y-m-d H:M:S")
            # check if current timestamp has an anomaly detected
            if (len(list(filter(lambda x: x == ts, anomaly_labels))) > 0):
                # get the index of anomaly data point
                idx = anomaly_labels.index(ts)
                new_data['ax'] = [anomaly_labels[idx]]
                new_data['ay'] = [anomalies[idx]]
            count += 1
            plot_data.stream(new_data, n_show)
            push_notebook(handle=handle)
            time.sleep(period)
            if stop():
                print("exit")
                break
                # callback to update graph with new data in notebook

    thread = Thread(target=update_callback, args=(id, lambda: stop_threads))
    thread.start()


def unzip_file(zip_src, dst_dir):
    r = zipfile.is_zipfile(zip_src)
    if r:
        fz = zipfile.ZipFile(zip_src, 'r')
        for file in fz.namelist():
            fz.extract(file, dst_dir)
    else:
        print('This is not zip')

    # download data file zip file and location each csv file into a dataframe
def load_data(local_data_path, start, end):
    new_dir = os.path.join('.', str(uuid.uuid1()))
    shutil.rmtree(new_dir, ignore_errors=True)
    os.mkdir(new_dir)
    unzip_file(local_data_path, new_dir)
    files = os.listdir(new_dir)
    frames = []
    for file in files:
        if file[-4:] != '.csv':
            continue
        frame = pd.read_csv('{}\\{}'.format(new_dir, file), skip_blank_lines=True)
        frame['timestamp'] = pd.to_datetime(frame['timestamp'])
        var = file[:file.find('.csv')]
        frame = frame.rename(columns={'value': var})
        frame = frame[frame['timestamp'] >= start]
        frame = frame[frame['timestamp'] <= end]
        frame['timestamp'] = frame['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        frame.set_index(['timestamp'], inplace=True)
        frames.append(frame)
    shutil.rmtree(new_dir, ignore_errors=True)
    return frames

def plot_lines_multi(x, y, p, color, name, t_str="hover,save,pan,box_zoom,reset,wheel_zoom", t_loc='above'):
    '''...
    '''
    p.line(x, y, color=color, legend_label=name)

def draw(data_source, local_data_path, result_id, raw_result, sensitivity, start, end):
    # urlretrieve(data_source, local_data_path)
    series = load_data(local_data_path, start, end)
    p_list = []
    colors = itertools.cycle(palette)
    for var, color in zip(series, colors):
        name = var.columns.values[0]
        p_value = figure(background_fill_color="#fafafa", x_axis_type="datetime")
        timestamp_idx = var[name]
        value = pd.to_datetime(var.index)
        # plot_lines_multi(var.index, var[name], p_value, color, name)
        plot_lines_multi(value, timestamp_idx, p_value, color, name)
        # configure datetime format to be display on the x-axis
        p_value.xaxis.formatter = DatetimeTickFormatter(
            days=["%m/%d %H:%M"],
            months=["%m/%d %H:%M"],
            years=["%m/%d %H:%M"],
            hours=["%m/%d %H:%M"],
            minutes=["%m/%d %H:%M"]
        )
        p_value.xaxis.major_label_orientation = pi / 4

        # display timestamp and value when cursor hovered over a data point
        hover = HoverTool(tooltips=[('Timestamp', '@x{%Y-%m-%d %H:%M:%S.%3N}'), ('value', '@y')],
                          formatters={'@x': 'datetime'}, )
        p_value.add_tools(hover)
        p_list.append(p_value)

        # extract isAnomaly, score and severity value from results JSON object
    start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:00")
    end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M:00")
    filter_item = list(
        filter(lambda x: 'value' in x and 'isAnomaly' in x['value'] and datetime.strptime(x['timestamp'],
                                                                                          "%Y-%m-%dT%H:%M:00Z") >= start_dt and datetime.strptime(
            x['timestamp'], "%Y-%m-%dT%H:%M:00Z") <= end_dt, raw_result['results']))
    timestamps = [item['timestamp'] for item in filter_item]
    isAnomaly = [item['value']['isAnomaly'] for item in filter_item]
    score = [item['value']['score'] for item in filter_item]
    Severity = [item['value']['severity'] for item in filter_item]
    result = pd.DataFrame({'Timestamp': timestamps, 'isAnomaly': isAnomaly, 'score': score, 'Severity': Severity})
    result.loc[(result.Severity <= (1 - sensitivity)) & (result.isAnomaly == True), 'isAnomaly'] = False
    result['Timestamp'] = pd.to_datetime(result['Timestamp'])
    result.set_index(['Timestamp'], inplace=True)
    result = result.reindex(['isAnomaly', 'score', 'Severity'], axis=1)
    colors = ['red', 'blue', 'black']

    # append anomaly results to graph
    for col, color in zip(result.columns, colors):
        p = figure(background_fill_color="#fafafa", x_axis_type="datetime")
        p.line(result.index, result[col], color=color, alpha=0.8, legend_label=col)
        # configure datetime format to be display on the x-axis
        p.xaxis.formatter = DatetimeTickFormatter(
            days=["%m/%d %H:%M"],
            months=["%m/%d %H:%M"],
            years=["%m/%d %H:%M"],
            hours=["%m/%d %H:%M"],
            minutes=["%m/%d %H:%M"]
        )
        p.xaxis.major_label_orientation = pi / 4

        # define display information when cursor hovered over a data point
        hover = HoverTool(tooltips=[('Timestamp', '@x{%Y-%m-%d %H:%M:%S.%3N}'), ('value', '@y')],
                          formatters={'@x': 'datetime'}, )
        p.add_tools(hover)
        p_list.append(p)
    grid = gridplot([[x] for x in p_list], sizing_mode='scale_width', plot_height=70)
    show(grid)

    # get anomaly with the highest anomaly score
    result = result.sort_values(by=['score'], ascending=False)
    top_anomaly = list(result[result.isAnomaly].index.strftime('%Y-%m-%dT%H:%M:%SZ'))[0]
    top_anomaly_list = list(result[result.isAnomaly])[0]
    return series, raw_result, top_anomaly

